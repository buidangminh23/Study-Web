import time
import subprocess
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

OWNER = os.getenv("GITHUB_OWNER", "buidangminh23")
REPO = os.getenv("GITHUB_REPO", "Study-Web")
BRANCH = os.getenv("GITHUB_BRANCH", "main")
PAT = os.getenv("GITHUB_PAT", "")
POLL_INTERVAL = int(os.getenv("DEPLOY_INTERVAL", "30"))

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def run_git(*args):
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=REPO_DIR
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


def run():
    if not PAT:
        logging.error("GITHUB_PAT not set in .env — auto-deploy disabled")
        return
    logging.info(f"Auto-deploy started (polling every {POLL_INTERVAL}s)")
    while True:
        try:
            if has_changes():
                logging.info("Changes detected, pushing...")
                push()
            else:
                logging.debug("No changes.")
        except Exception as e:
            logging.error(f"Error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
