import argparse
import html
import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "canvas-recordings"


def chrome_history_paths() -> list[Path]:
    root = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    paths = []
    default = root / "Default" / "History"
    if default.exists():
        paths.append(default)
    for path in root.glob("*/History"):
        if path.exists() and path not in paths:
            paths.append(path)
    return paths


def normalize_echo360_url(url: str) -> str | None:
    parsed = urlparse(url)
    if "echo360.net.au" not in parsed.netloc or not parsed.path.startswith("/ui/player/"):
        return None
    query = parse_qs(parsed.query)
    clean_query = {"autoplay": "false", "automute": "false"}
    if "secureLinkAccessDataId" in query and query["secureLinkAccessDataId"]:
        clean_query["secureLinkAccessDataId"] = query["secureLinkAccessDataId"][0]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(clean_query), ""))


def read_history(limit: int, title_contains: str) -> list[dict]:
    recordings = {}
    for path in chrome_history_paths():
        copied = Path(tempfile.gettempdir()) / f"study-web-{path.parent.name}-history.sqlite"
        try:
            shutil.copy2(path, copied)
            connection = sqlite3.connect(copied)
            cursor = connection.cursor()
            cursor.execute(
                """
                select title, url, last_visit_time
                from urls
                where lower(url) like '%echo360.net.au/ui/player/%'
                order by last_visit_time desc
                limit ?
                """,
                (limit * 5,),
            )
            for title, url, visited in cursor.fetchall():
                if title_contains and title_contains.lower() not in (title or "").lower():
                    continue
                normalized = normalize_echo360_url(url)
                if not normalized:
                    continue
                key = urlparse(normalized).path
                recordings.setdefault(key, {"title": title or key.rsplit("/", 1)[-1], "url": normalized, "visited": visited})
            connection.close()
        except (OSError, sqlite3.Error):
            continue
    return sorted(recordings.values(), key=lambda item: item["visited"], reverse=True)[:limit]


def card_html(recording: dict, index: int) -> str:
    title = html.escape(recording["title"])
    url = html.escape(recording["url"])
    label = f"Recording {index}"
    return (
        '<article class="canvas-recording-card">'
        f'<div class="canvas-recording-frame"><iframe src="{url}" title="{title}" loading="lazy" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe></div>'
        '<div class="canvas-recording-body">'
        f'<span class="recording-kicker">{label}</span>'
        f"<h3>{title}</h3>"
        "<p>Echo360 recording imported from Chrome history.</p>"
        f'<div class="recording-actions"><a href="{url}" target="_blank" rel="noopener">Open Echo360 player</a></div>'
        "</div>"
        "</article>"
    )


def build_lesson(args: argparse.Namespace, recordings: list[dict]) -> dict:
    cards = "".join(card_html(recording, index) for index, recording in enumerate(recordings, start=1))
    return {
        "title": args.lesson_title,
        "summary": f"Echo360 recordings imported from Canvas for {args.subject}.",
        "widget_type": "none",
        "position": 1,
        "is_published": True,
        "content_html": (
            f"<h2>{html.escape(args.lesson_title)}</h2>"
            '<p class="recording-note">These recordings open through Canvas/Echo360. If the player asks for access, open Canvas in the same browser first and then reload this page.</p>'
            f'<section class="canvas-recording-gallery" aria-label="Canvas Echo360 recordings">{cards}</section>'
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", default="Linear Algebra and Applications")
    parser.add_argument("--section", default="Canvas Recordings")
    parser.add_argument("--lesson-title", default="Canvas Echo360 Recordings")
    parser.add_argument("--position", type=int, default=6)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--title-contains", default="")
    args = parser.parse_args()

    root = Path.cwd()
    subject_dir = root / "app" / "content" / "subjects" / args.subject
    section_dir = subject_dir / args.section
    section_dir.mkdir(parents=True, exist_ok=True)
    recordings = read_history(args.limit, args.title_contains)
    if not recordings:
        raise SystemExit("No Echo360 player URLs found in Chrome history.")
    (section_dir / "section.json").write_text(json.dumps({"title": args.section, "position": args.position}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lesson_path = section_dir / f"01-{slugify(args.lesson_title)}.json"
    lesson_path.write_text(json.dumps(build_lesson(args, recordings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(lesson_path)


if __name__ == "__main__":
    main()
