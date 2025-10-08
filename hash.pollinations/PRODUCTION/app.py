import os
import hmac
import hashlib
import jwt
import time
import requests
import asyncio
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from githubScan import PollinationsTokenScanner  
from rq import Queue
from redis import Redis
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# === ENV VARS ===
APP_ID = os.getenv("GITHUB_APP_ID")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")      
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")  
PRIVATE_KEY = open("polli-guard.pem", "r").read()  
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# === INIT ===
app = Flask(__name__)
mongo = MongoClient(MONGO_URI)
db = mongo["poll-token"]
users_col = db["users"]       # authorized logins
events_col = db["events"]     # webhook + scan logs
redis_conn = Redis()
leak_queue = Queue("leaks", connection=redis_conn)
leaks_col = db["leaks"] 

# === HELPERS ===
def verify_signature(payload, signature):
    if not signature:
        logger.warning("No signature provided in webhook request")
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest("sha256=" + mac.hexdigest(), str(signature))

def get_jwt():
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10 minutes
        "iss": APP_ID
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def get_installation_token(installation_id):
    headers = {
        "Authorization": f"Bearer {get_jwt()}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.json()["token"]


# === ROUTES ===
@app.route("/install")
def install():
    """Redirect to GitHub OAuth"""
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}&scope=user:email&redirect_uri={request.host_url}auth"
    )
    return f'<a href="{github_auth_url}">Install PolliGuard</a>'

@app.route("/auth")
def auth():
    """OAuth callback"""
    code = request.args.get("code")
    if not code:
        return "❌ No code provided", 400

    url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code
    }
    r = requests.post(url, data=data, headers=headers)
    r.raise_for_status()
    resp_json = r.json()

    if "access_token" not in resp_json:
        return f"❌ Failed to get token: {resp_json}", 400

    access_token = resp_json["access_token"]

    # Fetch user info
    user_info = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"}
    ).json()

    # Fetch user emails
    emails = requests.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"token {access_token}"}
    ).json()
    primary_email = next((email["email"] for email in emails if email["primary"]), user_info.get("email", ""))

    # Store login in Mongo
    users_col.update_one(
        {"id": user_info["id"]},
        {"$set": {
            "login": user_info["login"],
            "id": user_info["id"],
            "access_token": access_token,
            "email": primary_email,
            "timestamp": time.time()
        }},
        upsert=True
    )
    users_col.update_one(
        {"id": user_info["id"]},
        {"$set": {
            "login": user_info["login"],
            "id": user_info["id"],
            "access_token": access_token,
            "timestamp": time.time()
        }},
        upsert=True
    )

    return f"✅ User {user_info.get('login')} authorized PolliGuard"

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles GitHub webhook events"""
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        abort(400, "Invalid signature")

    event = request.headers.get("X-GitHub-Event", "ping")
    payload = request.json

    if event == "ping":
        return jsonify({"msg": "pong"}), 200

    if event == "push":
        try:
            repo = payload["repository"]["full_name"]
            username = payload["repository"]["owner"]["login"]
            installation_id = payload["installation"]["id"]

            logger.info(f"Push detected on {repo} by {username}")

            # Get installation token
            token = get_installation_token(installation_id)
            os.environ["githubToken"] = token  # pass to scanner

            # Run scanner on push files
            scanner = PollinationsTokenScanner()
            commits = payload.get("commits", [])
            result = asyncio.run(scanner.scan_push_files(repo, commits, token, username))

            # Store event + result in Mongo
            events_col.insert_one({
                "event": "push",
                "repo": repo,
                "username": username,
                "installation_id": installation_id,
                "timestamp": time.time(),
                "result": result
            })
            
            # Get user email from DB
            user_doc = users_col.find_one({"login": username})
            user_email = user_doc.get("email") if user_doc else f"{username}@users.noreply.github.com"
            
            # Queue emails for leaks
            for leak in result:
                leak_info = {
                    "repo_url": leak["repo_url"],
                    "file_path": leak["file_path"],
                    "line_number": leak["line_number"],
                    "token": leak["token"],
                    "commit_hash": leak["commit_hash"],
                    "diff_info": leak["diff_info"],
                    "receiver_email": user_email,
                    "timestamp": time.time()
                }
                leak_queue.enqueue("emailWorkerScript.process_leak", leak_info)
        except Exception as e:
            logger.exception(f"Error processing push event: {e}")
            abort(500, "Internal server error")

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
