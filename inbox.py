"""Read-and-clear helper for manual_inbox.md — a free-text drop-in for
anything you personally spot (Twitter, Instagram, a brand email, word of
mouth) that isn't automatically fetchable. Adapted from ai-content/inbox.py.
"""
import datetime
import re
from pathlib import Path

DIR = Path(__file__).parent
INBOX_FILE = DIR / "manual_inbox.md"
ARCHIVE_FILE = DIR / "manual_inbox_archive.md"
TEMPLATE = (
    "<!--\n"
    "Paste anything here as you come across it — a link, a screenshot description,\n"
    "something a friend told you about, a brand's Instagram post, whatever. Any\n"
    "source works, this isn't Twitter-specific. Anything in this file gets folded\n"
    "into the next digest, then archived automatically (see manual_inbox_archive.md)\n"
    "and this file is cleared back to empty.\n"
    "-->\n"
)


def read_and_archive():
    """Return today's inbox content (or "" if empty/only the template comment),
    then archive it and reset the inbox file."""
    if not INBOX_FILE.exists():
        INBOX_FILE.write_text(TEMPLATE)
        return ""

    raw = INBOX_FILE.read_text()
    without_comments = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    content = without_comments.strip()

    if not content:
        return ""

    date = datetime.date.today().strftime("%Y-%m-%d")
    with ARCHIVE_FILE.open("a") as f:
        f.write(f"\n## {date}\n{content}\n")

    INBOX_FILE.write_text(TEMPLATE)
    return content


def main():
    content = read_and_archive()
    if content:
        print("## Manually spotted (any source)")
        print(content)


if __name__ == "__main__":
    main()
