"""The README charter is the canonical editorial policy."""
from pathlib import Path

START = "<!-- EDITORIAL_CHARTER_START -->"
END = "<!-- EDITORIAL_CHARTER_END -->"


def charter_text() -> str:
    readme = Path(__file__).resolve().parent.parent / "README.md"
    text = readme.read_text()
    return text.split(START, 1)[1].split(END, 1)[0].strip()
