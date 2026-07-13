#!/usr/bin/env python3
"""Static site generator for Good Bones legal pages and blog."""

import json
from datetime import datetime
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
    head = head.replace("{{domain}}", contact["domain"])

    html = layout
    # NOTE: Subresource integrity (SRI) is not added here because all assets
    # (CSS, JS, fonts, favicons) are self-hosted in this repo. If a CDN is
    # reintroduced later, generate SRI hashes for those <link>/<script> tags.
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


def format_date(date_str: str) -> tuple[str, str]:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    display = dt.strftime("%B %d, %Y").replace(" 0", " ")
    return dt.strftime("%Y-%m-%d"), display


def build_blog_post(post: dict, contact: dict) -> None:
    layout = load_template("blog_post.html")
    head = load_template("head.html")

    title = f"{post['title']} — {contact['company']}"
    description = post["excerpt"]
    canonical_url = f"{contact['domain']}/blog/{post['slug']}.html"
    date_iso, date_display = format_date(post["date"])

    head = apply_contact(head, contact)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])

    tags_html = "\n".join(f'      <span class="blog-tag">{tag}</span>' for tag in post.get("tags", []))

    html = layout
    html = html.replace("{{head}}", head)
    html = html.replace("{{nav}}", apply_contact(load_template("nav.html"), contact))
    html = html.replace("{{footer}}", apply_contact(load_template("footer.html"), contact))
    html = html.replace("{{title}}", post["title"])
    html = html.replace("{{date_iso}}", date_iso)
    html = html.replace("{{date_display}}", date_display)
    html = html.replace("{{author}}", post["author"])
    html = html.replace("{{tags}}", tags_html)
    html = html.replace("{{excerpt}}", post["excerpt"])
    html = html.replace("{{body}}", post["body"])

    output_file = ROOT / "blog" / f"{post['slug']}.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def build_blog_index(posts: list[dict], contact: dict) -> None:
    layout = load_template("blog_index.html")
    head = load_template("head.html")

    title = f"Blog — {contact['company']}"
    description = f"Ideas, updates, and web wisdom from {contact['company']}."
    canonical_url = f"{contact['domain']}/blog/index.html"

    head = apply_contact(head, contact)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])

    cards = []
    for post in posts:
        date_iso, date_display = format_date(post["date"])
        tags = "\n".join(f'<span class="blog-tag">{tag}</span>' for tag in post.get("tags", []))
        cards.append(
            f'      <a class="blog-card" href="/blog/{post["slug"]}.html">\n'
            f'        <div class="blog-card__meta">\n'
            f'          <time datetime="{date_iso}">{date_display}</time>\n'
            f'          <div class="blog-card__tags">\n{tags}\n          </div>\n'
            f'        </div>\n'
            f'        <h2 class="blog-card__title">{post["title"]}</h2>\n'
            f'        <p class="blog-card__excerpt">{post["excerpt"]}</p>\n'
            f'        <span class="blog-card__more" aria-hidden="true">Read post →</span>\n'
            f'      </a>'
        )

    html = layout
    html = html.replace("{{head}}", head)
    html = html.replace("{{nav}}", apply_contact(load_template("nav.html"), contact))
    html = html.replace("{{footer}}", apply_contact(load_template("footer.html"), contact))
    html = html.replace("{{posts}}", "\n\n".join(cards))

    output_file = ROOT / "blog" / "index.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def build_blog(contact: dict) -> None:
    posts_file = CONTENT / "blog" / "posts.json"
    if not posts_file.exists():
        print("No blog posts found; skipping blog build.")
        return

    data = json.loads(posts_file.read_text(encoding="utf-8"))
    posts = sorted(data.get("posts", []), key=lambda p: p["date"], reverse=True)

    if not posts:
        print("No blog posts found; skipping blog build.")
        return

    build_blog_index(posts, contact)
    for post in posts:
        build_blog_post(post, contact)


def main() -> None:
    contact = load_json("contact.json")

    pages = {
        "privacy.json": ROOT / "privacy.html",
        "terms.json": ROOT / "terms.html",
        "accessibility.json": ROOT / "accessibility.html",
    }

    for src, dst in pages.items():
        build_page(CONTENT / src, dst, contact)

    build_blog(contact)


if __name__ == "__main__":
    main()
