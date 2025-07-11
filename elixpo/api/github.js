import fetch from 'node-fetch';

const GITHUB_TOKEN = process.env.GITHUB_PAT;

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { projectURL } = req.body;
  if (!projectURL) return res.status(400).json({ error: 'projectURL is required' });

  try {
    const [owner, repo] = projectURL.replace("https://github.com/", "").split("/");

    const repoResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json"
      }
    });
    const repoData = await repoResponse.json();

    const contributorsRes = await fetch(`https://api.github.com/repos/${owner}/${repo}/contributors`, {
      headers: { Authorization: `Bearer ${GITHUB_TOKEN}` }
    });
    const contributors = await contributorsRes.json();

    res.json({
      name: repoData.name,
      description: repoData.description,
      stars: repoData.stargazers_count,
      topics: repoData.topics,
      owner: repoData.owner.login,
      contributors: contributors.slice(0, 10),
      url: repoData.html_url,
      ownerLogo: repoData.owner.avatar_url
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch GitHub data' });
  }
}
