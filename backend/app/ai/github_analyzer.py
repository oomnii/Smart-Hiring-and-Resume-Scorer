import httpx
import logging
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models.domain import CandidateGitHub
from ..database import SessionLocal

logger = logging.getLogger(__name__)

_GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ScreenerAI-GitHubAnalyzer",
}


def extract_github_username(github_url: str) -> Optional[str]:
    """Extract username from a GitHub URL or bare username."""
    if not github_url:
        return None
    raw = github_url.strip().strip("/")
    if not raw:
        return None

    # Bare username (no URL)
    if "/" not in raw and "github.com" not in raw.lower():
        if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", raw):
            return raw
        return None

    parts = raw.replace("https://", "").replace("http://", "").split("/")
    gh_idx = next((i for i, p in enumerate(parts) if "github.com" in p.lower()), -1)
    if gh_idx == -1 or gh_idx + 1 >= len(parts):
        return None
    username = parts[gh_idx + 1].strip()
    if not username or username.lower() in ("orgs", "settings", "topics", "explore"):
        return None
    return username


async def fetch_github_data(username: str) -> Dict[str, Any]:
    """Fetch user profile and public repos from GitHub."""
    data: Dict[str, Any] = {
        "username": username,
        "valid": False,
        "metrics": {"followers": 0, "public_repos": 0, "total_stars": 0, "top_projects": []},
        "top_languages": {},
        "error": None,
    }

    try:
        async with httpx.AsyncClient(headers=_GITHUB_HEADERS, follow_redirects=True) as client:
            user_resp = await client.get(f"https://api.github.com/users/{username}", timeout=15.0)
            if user_resp.status_code == 404:
                data["error"] = f"GitHub user '{username}' not found."
                return data
            if user_resp.status_code == 403:
                data["error"] = "GitHub API rate limit. Please try again later."
                return data
            if user_resp.status_code != 200:
                data["error"] = f"Failed to fetch GitHub user '{username}' ({user_resp.status_code})."
                return data

            user_json = user_resp.json()
            data["valid"] = True
            data["metrics"]["followers"] = user_json.get("followers", 0)
            data["metrics"]["public_repos"] = user_json.get("public_repos", 0)

            repos_resp = await client.get(
                f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated",
                timeout=20.0,
            )
            if repos_resp.status_code == 403:
                data["error"] = "GitHub API rate limit while fetching repositories."
                return data
            if repos_resp.status_code != 200:
                data["error"] = f"Failed to fetch repositories for '{username}'."
                return data

            repos = repos_resp.json()
            if not isinstance(repos, list):
                data["error"] = f"Unexpected GitHub repos response for '{username}'."
                return data

            if not repos:
                # Valid profile with zero public repos — still storeable
                return data

            total_stars = 0
            lang_counts: Dict[str, int] = {}
            for r in repos:
                total_stars += r.get("stargazers_count", 0) or 0
                lang = r.get("language")
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

            data["metrics"]["total_stars"] = total_stars
            sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
            data["top_languages"] = {k: v for k, v in sorted_langs[:5]}

            sorted_by_stars = sorted(repos, key=lambda x: x.get("stargazers_count", 0) or 0, reverse=True)
            top_projects = []
            for r in sorted_by_stars[:3]:
                top_projects.append({
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count", 0) or 0,
                    "url": r.get("html_url"),
                })
            data["metrics"]["top_projects"] = top_projects

    except Exception as e:
        logger.error(f"GitHub API Error for {username}: {e}")
        data["error"] = f"An unexpected error occurred: {e}"

    return data


def _persist_github(db: Session, candidate_id: str, github_url: str, username: str, github_data: Dict[str, Any]) -> None:
    record = db.query(CandidateGitHub).filter(CandidateGitHub.candidate_id == candidate_id).first()
    if record:
        record.github_url = github_url
        record.username = username
        record.metrics = github_data.get("metrics") or {}
        record.top_languages = github_data.get("top_languages") or {}
    else:
        record = CandidateGitHub(
            candidate_id=candidate_id,
            github_url=github_url,
            username=username,
            metrics=github_data.get("metrics") or {},
            top_languages=github_data.get("top_languages") or {},
        )
        db.add(record)
    db.commit()


async def analyze_and_store_github(candidate_id: str, github_url: str, db: Optional[Session] = None):
    """
    Analyze GitHub profile and store/update in DB.
    Opens its own DB session when called from BackgroundTasks (do not reuse request session).
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        username = extract_github_username(github_url)
        if not username:
            logger.error(f"Could not extract username from GitHub URL: {github_url}")
            return {"ok": False, "error": "Invalid GitHub URL or username"}

        # Normalize stored URL
        normalized_url = github_url.strip()
        if "github.com" not in normalized_url.lower():
            normalized_url = f"https://github.com/{username}"

        github_data = await fetch_github_data(username)

        if not github_data.get("valid"):
            err = github_data.get("error") or "GitHub profile could not be validated"
            logger.info(f"Not storing GitHub data for {username}: {err}")
            return {"ok": False, "error": err}

        _persist_github(db, candidate_id, normalized_url, username, github_data)
        logger.info(f"Stored GitHub analysis for candidate {candidate_id} (@{username})")
        return {
            "ok": True,
            "username": username,
            "warning": github_data.get("error"),
            "metrics": github_data.get("metrics"),
            "top_languages": github_data.get("top_languages"),
        }
    except Exception as e:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        logger.error(f"Failed handling DB for GitHub analysis: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if owns_session and db is not None:
            db.close()
