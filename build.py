#!/usr/bin/env python3
"""Static site generator for Good Bones legal pages."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "src" / "templates"
CONTENT = ROOT / "src" / "content"


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def build_page(data_file: Path, output_file: Path) -> None:
    data = json.loads(data_file.read_text(encoding="utf-8"))
    layout = load_template("legal_layout.html")

    page_title = data["page_title"]
    description = f"{page_title} for Good Bones Web Inc., an Edmonton website consulting company."
    title = page_title

    toc = "\n".join(
        f'      <a href="#{s["id"]}">{s["heading"]}</a>'
        for s in data["sections"]
    )

    content = "\n\n".join(
        f'      <section id="{s["id"]}"\u003e\n        <h2>{s["heading"]}</h2\u003e\n        {s["body"]}\n      </section>'
        for s in data["sections"]
    )

    html = layout
    html = html.replace("{{head}}", load_template("head.html").replace("{{title}}", title).replace("{{description}}", description))
    html = html.replace("{{nav}}", load_template("nav.html"))
    html = html.replace("{{footer}}", load_template("footer.html"))
    html = html.replace("{{page_title}}", page_title)
    html = html.replace("{{intro}}", data["intro"])
    html = html.replace("{{date}}", data["last_updated"])
    html = html.replace("{{toc}}", toc)
    html = html.replace("{{content}}", content)

    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def main() -> None:
    pages = {
        "privacy.json": ROOT / "privacy.html",
        "terms.json": ROOT / "terms.html",
        "accessibility.json": ROOT / "accessibility.html",
    }

    for src, dst in pages.items():
        build_page(CONTENT / src, dst)


if __name__ == "__main__":
    main()
