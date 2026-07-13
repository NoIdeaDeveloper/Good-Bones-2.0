#!/usr/bin/env python3
"""Static site generator for Good Bones legal pages."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "src" / "templates"
CONTENT = ROOT / "src" / "content"
DATA = ROOT / "src" / "data"

CONTACT_BLOCK = """<p><strong>{company}</strong><br />Email: <a href="mailto:{email}">{email}</a><br />Phone: <a href="tel:{phone_href}">{phone}</a><br />{address}</p>"""


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def apply_contact(html: str, contact: dict) -> str:
    replacements = {
        "{{company}}": contact["company"],
        "{{email}}": contact["email"],
        "{{phone}}": contact["phone"],
        "{{phone_href}}": contact["phone_href"],
        "{{address}}": contact["address"],
        "{{social_instagram}}": contact["social"]["instagram"],
        "{{social_linkedin}}": contact["social"]["linkedin"],
        "{{social_twitter}}": contact["social"]["twitter"],
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def build_page(data_file: Path, output_file: Path, contact: dict) -> None:
    data = json.loads(data_file.read_text(encoding="utf-8"))
    layout = load_template("legal_layout.html")

    page_title = data["page_title"]
    title = f"{page_title} — {contact['company']}"
    description = f"{page_title} for {contact['company']}, an Edmonton website consulting company."
    slug = output_file.stem
    canonical_url = f"{contact['domain']}/{slug}.html"

    toc = "\n".join(
        f'      <a href="#{s["id"]}">{s["heading"]}</a>'
        for s in data["sections"]
    )

    sections = []
    for s in data["sections"]:
        body = s["body"]
        if s.get("use_contact"):
            body += "\n        " + CONTACT_BLOCK.format(**contact)
        sections.append(
            f'      <section id="{s["id"]}">\n        <h2>{s["heading"]}</h2>\n        {body}\n      </section>'
        )
    content = "\n\n".join(sections)

    head = load_template("head.html")
    head = apply_contact(head, contact)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])

    html = layout
    html = html.replace("{{head}}", head)
    html = html.replace("{{nav}}", apply_contact(load_template("nav.html"), contact))
    html = html.replace("{{footer}}", apply_contact(load_template("footer.html"), contact))
    html = html.replace("{{page_title}}", page_title)
    html = html.replace("{{intro}}", data["intro"])
    html = html.replace("{{date}}", data["last_updated"])
    html = html.replace("{{toc}}", toc)
    html = html.replace("{{content}}", content)

    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def main() -> None:
    contact = load_json("contact.json")

    pages = {
        "privacy.json": ROOT / "privacy.html",
        "terms.json": ROOT / "terms.html",
        "accessibility.json": ROOT / "accessibility.html",
    }

    for src, dst in pages.items():
        build_page(CONTENT / src, dst, contact)


if __name__ == "__main__":
    main()
