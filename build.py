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


def relative_base_path(output_file: Path) -> str:
    """Return the relative prefix (e.g. '' or '../') for assets and page links.

    ROOT-level pages use an empty prefix; pages inside subfolders use '../'.
    """
    depth = len(output_file.relative_to(ROOT).parts) - 1
    return "../" * depth


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


def build_schema(page_type: str, contact: dict, **kwargs) -> str:
    """Return a Schema.org JSON-LD script tag for the given page type."""
    base = {"@context": "https://schema.org"}
    publisher = {
        "@type": "Organization",
        "name": contact["company"],
        "url": contact["domain"],
        "logo": f"{contact['domain']}/favicon.png",
    }

    if page_type == "webpage":
        data = {
            **base,
            "@type": "WebPage",
            "name": kwargs["title"],
            "url": kwargs["url"],
            "description": kwargs["description"],
            "dateModified": kwargs["date_modified"],
            "publisher": publisher,
        }
    elif page_type == "blog":
        posts = kwargs["posts"]
        data = {
            **base,
            "@type": "Blog",
            "name": "The Good Bones Blog",
            "url": kwargs["url"],
            "description": kwargs["description"],
            "publisher": publisher,
            "blogPost": [
                {
                    "@type": "BlogPosting",
                    "headline": p["title"],
                    "url": f"{contact['domain']}/blog/{p['slug']}.html",
                    "datePublished": p["date"],
                }
                for p in posts
            ],
        }
    elif page_type == "blogposting":
        data = {
            **base,
            "@type": "BlogPosting",
            "headline": kwargs["title"],
            "url": kwargs["url"],
            "description": kwargs["description"],
            "datePublished": kwargs["date"],
            "dateModified": kwargs["date"],
            "author": {
                "@type": "Organization",
                "name": kwargs["author"],
            },
            "publisher": publisher,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": kwargs["url"],
            },
            "image": contact["og"]["image"],
        }
    else:
        data = {
            **base,
            "@type": "WebPage",
            "name": kwargs.get("title", contact["company"]),
            "url": kwargs.get("url", contact["domain"]),
            "description": kwargs.get("description", ""),
            "publisher": publisher,
        }

    json_text = json.dumps(data, indent=2)
    indented = "\n".join(f"  {line}" for line in json_text.splitlines())
    return f"<script type=\"application/ld+json\">\n{indented}\n</script>"


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

    base_path = relative_base_path(output_file)

    head = load_template("head.html")
    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")

    last_updated_iso = datetime.strptime(data["last_updated"], "%B %d, %Y").strftime("%Y-%m-%d")
    schema = build_schema(
        "webpage",
        contact,
        title=title,
        url=canonical_url,
        description=description,
        date_modified=last_updated_iso,
    )
    head = head.replace("{{schema_json}}", schema)

    html = layout
    # NOTE: Subresource integrity (SRI) is not added here because all assets
    # (CSS, JS, fonts, favicons) are self-hosted in this repo. If a CDN is
    # reintroduced later, generate SRI hashes for those <link>/<script> tags.
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
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

    output_file = ROOT / "blog" / f"{post['slug']}.html"
    base_path = relative_base_path(output_file)

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "article")

    schema = build_schema(
        "blogposting",
        contact,
        title=post["title"],
        url=canonical_url,
        description=description,
        date=date_iso,
        author=post["author"],
    )
    head = head.replace("{{schema_json}}", schema)

    tags_html = "\n".join(f'      <span class="blog-tag">{tag}</span>' for tag in post.get("tags", []))

    html = layout
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    html = html.replace("{{title}}", post["title"])
    html = html.replace("{{date_iso}}", date_iso)
    html = html.replace("{{date_display}}", date_display)
    html = html.replace("{{author}}", post["author"])
    html = html.replace("{{tags}}", tags_html)
    html = html.replace("{{excerpt}}", post["excerpt"])
    body_indented = "\n".join(f"        {line}" for line in post["body"].splitlines())
    # Convert root-relative links inside post bodies to be relative to this page.
    body_indented = body_indented.replace('href="/index.html', f'href="{base_path}index.html')
    html = html.replace("{{body}}", body_indented)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def build_blog_index(posts: list[dict], contact: dict) -> None:
    layout = load_template("blog_index.html")
    head = load_template("head.html")

    title = f"Blog — {contact['company']}"
    description = f"Ideas, updates, and web wisdom from {contact['company']}".rstrip('.') + '.'
    canonical_url = f"{contact['domain']}/blog/index.html"

    output_file = ROOT / "blog" / "index.html"
    base_path = relative_base_path(output_file)

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", contact["og"]["image"])
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")

    schema = build_schema(
        "blog",
        contact,
        url=canonical_url,
        description=description,
        posts=posts,
    )
    head = head.replace("{{schema_json}}", schema)

    cards = []
    for post in posts:
        date_iso, date_display = format_date(post["date"])
        tags = "\n".join(f'            <span class="blog-tag">{tag}</span>' for tag in post.get("tags", []))
        cards.append(
            f'      <a class="blog-card" href="{post["slug"]}.html">\n'
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
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    html = html.replace("{{posts}}", "\n\n".join(cards))

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def build_blog(contact: dict) -> list[dict]:
    posts_file = CONTENT / "blog" / "posts.json"
    if not posts_file.exists():
        print("No blog posts found; skipping blog build.")
        return []

    data = json.loads(posts_file.read_text(encoding="utf-8"))
    posts = sorted(data.get("posts", []), key=lambda p: p["date"], reverse=True)

    if not posts:
        print("No blog posts found; skipping blog build.")
        return []

    build_blog_index(posts, contact)
    for post in posts:
        build_blog_post(post, contact)
    return posts


def build_sitemap(contact: dict, posts: list[dict]) -> None:
    """Generate sitemap.xml with <lastmod> for all public pages."""
    domain = contact["domain"]
    today = datetime.now().strftime("%Y-%m-%d")
    urls: list[dict] = []

    # Homepage uses the mtime of the hand-written index.html.
    index_mtime = datetime.fromtimestamp((ROOT / "index.html").stat().st_mtime)
    urls.append({
        "loc": f"{domain}/",
        "lastmod": index_mtime.strftime("%Y-%m-%d"),
        "priority": "1.0",
        "changefreq": "weekly",
    })

    # Legal pages use the last_updated date from their content JSON.
    legal_pages = {
        "privacy.json": ("privacy.html", "0.3", "yearly"),
        "terms.json": ("terms.html", "0.3", "yearly"),
        "accessibility.json": ("accessibility.html", "0.3", "yearly"),
    }
    for src, (filename, priority, changefreq) in legal_pages.items():
        data = json.loads((CONTENT / src).read_text(encoding="utf-8"))
        lastmod = datetime.strptime(data["last_updated"], "%B %d, %Y").strftime("%Y-%m-%d")
        urls.append({
            "loc": f"{domain}/{filename}",
            "lastmod": lastmod,
            "priority": priority,
            "changefreq": changefreq,
        })

    # Blog index uses the most recent post date.
    blog_index_lastmod = max((p["date"] for p in posts), default=today)
    urls.append({
        "loc": f"{domain}/blog/index.html",
        "lastmod": blog_index_lastmod,
        "priority": "0.7",
        "changefreq": "weekly",
    })

    # Individual blog posts use their publish date.
    for post in posts:
        urls.append({
            "loc": f"{domain}/blog/{post['slug']}.html",
            "lastmod": post["date"],
            "priority": "0.6",
            "changefreq": "yearly",
        })

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{url['loc']}</loc>")
        lines.append(f"    <lastmod>{url['lastmod']}</lastmod>")
        lines.append(f"    <priority>{url['priority']}</priority>")
        lines.append(f"    <changefreq>{url['changefreq']}</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")

    sitemap_path = ROOT / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {sitemap_path}")


def main() -> None:
    contact = load_json("contact.json")

    pages = {
        "privacy.json": ROOT / "privacy.html",
        "terms.json": ROOT / "terms.html",
        "accessibility.json": ROOT / "accessibility.html",
    }

    for src, dst in pages.items():
        build_page(CONTENT / src, dst, contact)

    posts = build_blog(contact)
    build_sitemap(contact, posts)


if __name__ == "__main__":
    main()
