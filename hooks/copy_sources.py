"""mkdocs hook: publish raw Markdown and the agent files alongside the built site.

Appending ``.md`` to any docs URL returns the page's raw Markdown, the convention
agents (and the Claude docs) rely on. mkdocs renders ``.md`` to HTML, so this hook
copies every source ``.md`` into the built site at the same path, and copies the
repo-root agent files (``llms.txt``, ``llms-full.txt``, ``lanorme.schema.json``)
to the site root. The Markdown stays the source of truth; the HTML is a rendering.
"""

from __future__ import annotations

import shutil
from pathlib import Path

_AGENT_FILES = ("llms.txt", "llms-full.txt", "lanorme.schema.json")


def on_post_build(*, config: object, **kwargs: object) -> None:
    """Copy raw Markdown and the agent files into the built site directory."""
    docs_dir = Path(config["docs_dir"])
    site_dir = Path(config["site_dir"])
    repo_root = docs_dir.parent

    for source in docs_dir.rglob("*.md"):
        target = site_dir / source.relative_to(docs_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for name in _AGENT_FILES:
        extra = repo_root / name
        if extra.is_file():
            shutil.copy2(extra, site_dir / name)
