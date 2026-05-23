import time
import subprocess
import os
import re
import logging
import threading
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

OWNER = os.getenv("GITHUB_OWNER", "buidangminh23")
REPO = os.getenv("GITHUB_REPO", "Study-Web")
BRANCH = os.getenv("GITHUB_BRANCH", "main")
PAT = os.getenv("GITHUB_PAT", "")
POLL_INTERVAL = int(os.getenv("DEPLOY_INTERVAL", "30"))
VERCEL_SCOPE = os.getenv("VERCEL_SCOPE", "buidangminh23s-projects")
VERCEL_PROJECT = os.getenv("VERCEL_PROJECT", "study-web")
# How long to wait for Vercel to finish deploying before cleanup (seconds)
VERCEL_DEPLOY_WAIT = int(os.getenv("VERCEL_DEPLOY_WAIT", "60"))

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def run_git(*args):
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=REPO_DIR
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_vercel(*args):
    result = subprocess.run(
        ["vercel"] + list(args),
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def has_changes():
    code, out, _ = run_git("status", "--porcelain")
    return code == 0 and bool(out)


def push():
    remote_url = f"https://{PAT}@github.com/{OWNER}/{REPO}.git"
    run_git("add", "-A")
    code, out, err = run_git("commit", "-m", "Auto-deploy: sync changes")
    if code != 0:
        if "nothing to commit" in err or "nothing to commit" in out:
            return False
        logging.error(f"git commit failed: {err}")
        return False
    code, out, err = run_git("push", remote_url, BRANCH)
    if code != 0:
        logging.error(f"git push failed: {err}")
        return False
    logging.info(f"Pushed to GitHub: {out or 'OK'}")
    return True


def get_deployment_urls():
    """Return list of deployment URLs for the project, newest first (deduped)."""
    code, out, _ = run_vercel("ls", VERCEL_PROJECT, "--scope", VERCEL_SCOPE)
    if code != 0:
        return []
    urls = re.findall(r'https://\S+\.vercel\.app', out)
    seen, unique = set(), []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def cleanup_old_deployments():
    """Wait for new deployment to be ready, then delete all old ones."""
    logging.info(f"Waiting {VERCEL_DEPLOY_WAIT}s for Vercel deployment to finish...")
    time.sleep(VERCEL_DEPLOY_WAIT)

    urls = get_deployment_urls()
    if len(urls) <= 1:
        logging.info("Only 1 deployment — nothing to clean up.")
        return

    newest, old = urls[0], urls[1:]
    logging.info(f"Keeping: {newest}")
    logging.info(f"Deleting {len(old)} old deployment(s)...")
    for url in old:
        code, _, err = run_vercel("rm", url, "--yes", "--scope", VERCEL_SCOPE)
        if code == 0:
            logging.info(f"Deleted: {url}")
        else:
            logging.warning(f"Could not delete {url}: {err}")
    logging.info("Cleanup done.")


def run():
    if not PAT:
        logging.error("GITHUB_PAT not set in .env — auto-deploy disabled")
        return
    logging.info(f"Auto-deploy started (polling every {POLL_INTERVAL}s)")
    while True:
        try:
            if has_changes():
                logging.info("Changes detected, pushing...")
                pushed = push()
                if pushed:
                    # Run cleanup in background so it doesn't block the poll loop
                    t = threading.Thread(
                        target=cleanup_old_deployments,
                        daemon=True,
                        name="vercel-cleanup"
                    )
                    t.start()
            else:
                logging.debug("No changes.")
        except Exception as e:
            logging.error(f"Error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
