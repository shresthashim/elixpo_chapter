#code was used to format the prompt by highlighting words that match the hashtags in the prompt.
#in the entire dataset for recoovering the past generated images with updated prompts for markdown.

import firebase_admin
from firebase_admin import credentials, firestore
import spacy
import asyncio
from keybert import KeyBERT

# Load a pre-trained NLP model (spaCy model)
nlp = spacy.load('en_core_web_md')

# Initialize KeyBERT for keyword extraction
kw_model = KeyBERT('distilbert-base-nli-mean-tokens')

# Initialize Firebase Admin SDK
cred = credentials.Certificate("./elixpoai-firebase-adminsdk-poswc-728c25f591.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# References
image_ref = db.collection("ImageGen")

async def generate_keywords(prompt, num_keywords=10):
    """Generate keywords using KeyBERT."""
    keywords = kw_model.extract_keywords(prompt, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=num_keywords)
    return [keyword[0] for keyword, _ in keywords]  # Return one-word keywords

def format_matching_hashtags(prompt, hashtags):
    """Format the prompt by highlighting words that match the hashtags."""
    # Split the prompt into words
    prompt_words = prompt.split()

    # Escape markdown characters to avoid interference
    escape_md = lambda text: text.replace("*", "\\*").replace("_", "\\_").replace("~", "\\~")

    # Apply markdown formatting only to words that match hashtags
    for hashtag in hashtags:
        escaped_hashtag = escape_md(hashtag.lstrip('#'))  # Remove hashtag symbol from the word
        for word in prompt_words:
            # If the word matches a hashtag (case-insensitive), apply markdown formatting
            if word.lower() == escaped_hashtag.lower():  
                prompt = prompt.replace(word, f"**_`{escaped_hashtag}`_**")

    return prompt

async def process_documents():
    """Process each document in the ImageGen collection, match prompt words to hashtags."""
    last_doc_name = None
    try:
        # Fetch all documents in the ImageGen collection
        docs = image_ref.stream()

        tasks = []
        for doc in docs:
            # Get document reference and data
            doc_ref = doc.reference
            doc_data = doc.to_dict()

            # Fetch the prompt and hashtags from the document
            prompt = doc_data.get("prompt")
            hashtags = doc_data.get("hashtags", [])  # Hashtags is an array

            # Add task to update each document
            tasks.append(update_document(doc_ref, prompt, hashtags))
                
            last_doc_name = doc.id

        # Await all tasks to ensure asynchronous execution
        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Error processing document {last_doc_name}: {e}")

async def update_document(doc_ref, prompt, hashtags):
    """Update the document by formatting the prompt with matching hashtags."""
    try:
        # Format the prompt by highlighting words that match hashtags
        formatted_prompt = format_matching_hashtags(prompt, hashtags)

        # Update the document by overwriting the 'formatted_prompt' field
        doc_ref.update({
            "formatted_prompt": formatted_prompt
        })
        print(f"Document {doc_ref.id} updated with formatted prompt: {formatted_prompt}")

    except Exception as e:
        print(f"Error updating document {doc_ref.id}: {e}")

# Run the main function
if __name__ == "__main__":
    asyncio.run(process_documents())
