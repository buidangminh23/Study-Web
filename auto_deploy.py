import time
import subprocess
import requests
import os
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [auto-deploy] %(message)s",
    datefmt="%H:%M:%S"
)

GITHUB_API = "https://api.github.com"
OWNER = os.getenv("GITHUB_OWNER", "buidangminh23")
REPO = os.getenv("GITHUB_REPO", "Study-Web")
BRANCH = os.getenv("GITHUB_BRANCH", "main")
PAT = os.getenv("GITHUB_PAT", "")
POLL_INTERVAL = int(os.getenv("DEPLOY_INTERVAL", "20"))

HEADERS = {"Authorization": f"token {PAT}"} if PAT else {}

_last_sha = None


def get_latest_sha():
    url = f"{GITHUB_API}/repos/{OWNER}/{REPO}/commits/{BRANCH}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()["sha"]
    except Exception as e:
        logging.warning(f"Failed to fetch latest commit: {e}")
        return None


def git_pull():
    result = subprocess.run(
        ["git", "pull", "origin", BRANCH],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    if result.returncode == 0:
        logging.info(f"git pull OK: {result.stdout.strip()}")
    else:
        logging.error(f"git pull failed: {result.stderr.strip()}")
    return result.returncode == 0


def run():
    global _last_sha
    logging.info(f"Auto-deploy started (polling every {POLL_INTERVAL}s, branch={BRANCH})")
    _last_sha = get_latest_sha()
    logging.info(f"Initial commit: {_last_sha[:8] if _last_sha else 'unknown'}")

    while True:
        time.sleep(POLL_INTERVAL)
        latest = get_latest_sha()
        if latest and latest != _last_sha:
            logging.info(f"New commit detected: {_last_sha[:8] if _last_sha else '?'} -> {latest[:8]}")
            if git_pull():
                _last_sha = latest
                logging.info("Deploy complete.")
        else:
            logging.debug("No new commits.")


if __name__ == "__main__":
    run()
