#!/usr/bin/env python3
"""Static site generator for Good Bones."""

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "src" / "templates"
CONTENT = ROOT / "src" / "content"
DATA = ROOT / "src" / "data"

CONTACT_BLOCK = """<p><strong>{company}</strong><br />Email: <a href="mailto:{email}">{email}</a><br />Phone: <a href="tel:{phone_href}">{phone}</a><br />{address}</p>"""

# Build-time minification flags. Set to False to keep human-readable CSS/JS/HTML.
MINIFY_CSS = True
MINIFY_JS = True
MINIFY_HTML = True


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_content_json(*parts: str) -> dict:
    return json.loads((CONTENT / Path(*parts)).read_text(encoding="utf-8"))


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def load_inline_asset(path: Path) -> str:
    """Return a minified asset suitable for inlining into HTML.

    The returned string is indented two spaces so it sits neatly inside a
    <style> or <script> block.
    """
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".css" and MINIFY_CSS:
        minified = minify_css(raw)
    elif path.suffix.lower() == ".js" and MINIFY_JS:
        minified = minify_js(raw)
    else:
        minified = raw
    return "\n".join(f"  {line}" for line in minified.splitlines())


def minify_css(css: str) -> str:
    """Return a compacted version of CSS without external dependencies.

    Uses rcssmin when available; otherwise falls back to a safe regex-based
    stripper that removes comments and redundant whitespace.
    """
    try:
        import rcssmin  # type: ignore
        return rcssmin.cssmin(css)
    except ImportError:
        pass

    # Remove comments.
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # Trim whitespace around punctuation that doesn't need it.
    css = re.sub(r"\s*([{}:;,>+~()])\s*", r"\1", css)
    # Keep a single space after closing brace so selectors remain separated.
    css = re.sub(r"}\s*", "} ", css)
    # Collapse repeated whitespace and trim.
    css = re.sub(r"\s+", " ", css).strip()
    return css


def minify_js(js: str) -> str:
    """Return a compacted version of JS without external dependencies.

    Uses jsmin when available; otherwise falls back to a conservative
    regex-based stripper that removes comments and collapses whitespace.
    """
    try:
        import jsmin as jsmin_lib  # type: ignore
        return jsmin_lib.jsmin(js)
    except ImportError:
        pass

    # Remove single-line comments.
    js = re.sub(r"//.*?$", "", js, flags=re.MULTILINE)
    # Remove multi-line comments.
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    # Collapse whitespace, but keep spaces around keywords/identifiers safe.
    js = re.sub(r"\s+", " ", js).strip()
    return js


def minify_html(html: str) -> str:
    """Return a compacted version of HTML without external dependencies.

    Removes leading whitespace on each line and collapses blank lines.
    Preserves contents of <pre>, <textarea>, <script>, and <style>.
    """
    tags_to_preserve = {"pre", "textarea", "script", "style"}
    preserve: list[str] = []

    def store(match: re.Match) -> str:
        preserve.append(match.group(0))
        return f"\x00{len(preserve) - 1}\x00"

    # Preserve the bodies of the listed tags.
    pattern = re.compile(
        r"<(%s)\b[^>]*>.*?</\1>" % "|".join(tags_to_preserve),
        re.DOTALL | re.IGNORECASE,
    )
    html = pattern.sub(store, html)

    # Trim leading whitespace per line, then collapse consecutive blanks.
    lines = [line.rstrip() for line in html.splitlines()]
    html = "\n".join(line for line in lines if line)

    # Restore preserved blocks.
    for i, block in enumerate(preserve):
        html = html.replace(f"\x00{i}\x00", block, 1)

    return html


def relative_base_path(output_file: Path) -> str:
    """Return the relative prefix (e.g. '' or '../') for assets and page links.

    ROOT-level pages use an empty prefix; pages inside subfolders use '../'.
    """
    depth = len(output_file.relative_to(ROOT).parts) - 1
    return "../" * depth


def get_minified_source(path: Path) -> bytes:
    """Return the source bytes for a file, optionally minified."""
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".css" and MINIFY_CSS:
        return minify_css(raw.decode("utf-8")).encode("utf-8")
    if suffix == ".js" and MINIFY_JS:
        return minify_js(raw.decode("utf-8")).encode("utf-8")
    return raw


# Lazily-populated mapping of logical asset path -> hashed relative path.
_ASSET_FINGERPRINTS: dict[str, str] = {}


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def _remove_stale_fingerprints(directory: Path, stem: str, suffix: str) -> None:
    """Delete previous fingerprinted copies of an asset in *directory*."""
    pattern = re.compile(re.escape(stem) + r"\.[0-9a-f]{8,32}" + re.escape(suffix) + r"$")
    for item in directory.iterdir():
        if item.is_file() and pattern.match(item.name):
            item.unlink()


def compute_asset_fingerprints() -> dict[str, str]:
    """Copy selected static assets to content-hashed filenames.

    Returns a mapping of logical relative path (e.g.
    "fonts/bebasneue-v16-latin.woff2") to the new hashed relative path (e.g.
    "fonts/bebasneue-v16-latin.a1b2c3d4.woff2"). Previous fingerprinted copies
    are removed first so stale files don't accumulate in the repo.
    """
    assets = [
        ("fonts/bebasneue-v16-latin.woff2", ROOT / "fonts" / "bebasneue-v16-latin.woff2"),
        ("fonts/spacegrotesk-v22-latin.woff2", ROOT / "fonts" / "spacegrotesk-v22-latin.woff2"),
        ("favicon.png", ROOT / "favicon.png"),
        ("favicon.ico", ROOT / "favicon.ico"),
        ("og-image.png", ROOT / "og-image.png"),
    ]
    fingerprints: dict[str, str] = {}
    for logical, src in assets:
        if not src.exists():
            print(f"Warning: asset {src} not found; skipping fingerprinting")
            continue
        digest = _file_hash(src)
        _remove_stale_fingerprints(src.parent, src.stem, src.suffix)
        dst = src.parent / f"{src.stem}.{digest}{src.suffix}"
        shutil.copy2(src, dst)
        fingerprints[logical] = str(dst.relative_to(ROOT)).replace("\\", "/")
        print(f"Fingerprinted {logical} -> {fingerprints[logical]}")
    global _ASSET_FINGERPRINTS
    _ASSET_FINGERPRINTS = fingerprints
    return fingerprints


def asset_fingerprints() -> dict[str, str]:
    if not _ASSET_FINGERPRINTS:
        compute_asset_fingerprints()
    return _ASSET_FINGERPRINTS


def hashed_asset_url(logical: str, base_path: str = "") -> str:
    """Return the fingerprinted URL for an asset.

    *logical* is the repo-relative path of the source asset, e.g.
    "fonts/bebasneue-v16-latin.woff2". *base_path* is the page-relative prefix
    ("" or "../").
    """
    hashed = asset_fingerprints().get(logical)
    if not hashed:
        return f"{base_path}{logical}"
    return f"{base_path}{hashed}"


def absolute_hashed_asset_url(logical: str, domain: str) -> str:
    """Return the absolute fingerprinted URL for root-level assets like OG images."""
    hashed = asset_fingerprints().get(logical)
    if not hashed:
        return f"{domain}/{logical}"
    return f"{domain}/{hashed}"


def apply_asset_hashes(html: str, base_path: str = "") -> str:
    """Replace {{asset:<logical>}} placeholders with fingerprinted URLs."""
    def repl(match: re.Match) -> str:
        return hashed_asset_url(match.group(1).strip(), base_path)
    return re.sub(r"\{\{asset:([^}]+)\}\}", repl, html)


def inline_fonts_css(base_path: str) -> str:
    """Return minified fonts.css with hashed, base-path-aware font URLs."""
    path = ROOT / "fonts" / "fonts.css"
    if not path.exists():
        return ""
    css = path.read_text(encoding="utf-8")

    def rewrite_url(match: re.Match) -> str:
        filename = match.group(1)
        logical = f"fonts/{filename}"
        return f'url("{hashed_asset_url(logical, base_path)}")'

    css = re.sub(r'url\(["\']?([^"\')]+)["\']?\)', rewrite_url, css)
    if MINIFY_CSS:
        css = minify_css(css)
    return "\n".join(f"  {line}" for line in css.splitlines())


def cache_bust_for(output_file: Path) -> str:
    """Return the query-string cache buster for the generated HTML page.

    Pages generated by this build share the same bust hash so users never
    get a stale global.css when script.js changes, but both change together
    on any build. The hash is based on the combined bytes of the tracked
    static files that ship with the page. If minification is enabled, the
    hash is computed from the minified bytes so content changes are still
    reflected.
    """
    tracked = {
        ROOT / "script.min.js": ROOT / "script.js",
        ROOT / "css" / "global.min.css": ROOT / "css" / "global.css",
        ROOT / "css" / "index.min.css": ROOT / "css" / "index.css",
        ROOT / "css" / "blog.min.css": ROOT / "css" / "blog.css",
    }
    combined = b""
    for path in tracked.values():
        if path.exists():
            combined += get_minified_source(path)
    digest = hashlib.md5(combined).hexdigest()[:8]
    return f"?v={digest}"


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
        "{{external_link_rel}}": contact.get("external_link_rel", "noopener noreferrer"),
        "{{external_link_target}}": contact.get("external_link_target", "_blank"),
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
        "logo": absolute_hashed_asset_url("favicon.png", contact["domain"]),
    }

    if page_type == "webpage":
        data = {
            **base,
            "@type": "WebPage",
            "name": kwargs["title"],
            "url": kwargs["url"],
            "description": kwargs["description"],
            "publisher": publisher,
        }
        if kwargs.get("date_modified"):
            data["dateModified"] = kwargs["date_modified"]
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
            "image": kwargs.get("image", absolute_hashed_asset_url("og-image.png", contact["domain"])),
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
    cache_bust = cache_bust_for(output_file)
    og_image_url = absolute_hashed_asset_url("og-image.png", contact["domain"])

    head = load_template("head.html")
    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{fonts_css}}", inline_fonts_css(base_path))
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", og_image_url)
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")
    head = apply_asset_hashes(head, base_path)

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
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
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


TAG_ACCENT_COLORS = ["yellow", "coral", "teal", "violet", "pink", "mint"]


def tag_accent_class(tags: list[str]) -> str:
    """Return an accent color class based on the first tag."""
    if not tags:
        return "blog-tag--yellow"
    first = tags[0].lower()
    if any(word in first for word in ("design", "brand", "ui", "visual")):
        return "blog-tag--violet"
    if any(word in first for word in ("performance", "speed", "seo", "rescue", "fix")):
        return "blog-tag--coral"
    if any(word in first for word in ("edmonton", "local", "small business", "business")):
        return "blog-tag--teal"
    return "blog-tag--yellow"


def build_blog_post(post: dict, contact: dict, all_posts: list[dict]) -> None:
    layout = load_template("blog_post.html")
    head = load_template("head.html")

    title = f"{post['title']} — {contact['company']}"
    description = post["excerpt"]
    canonical_url = f"{contact['domain']}/blog/{post['slug']}.html"
    date_iso, date_display = format_date(post["date"])

    output_file = ROOT / "blog" / f"{post['slug']}.html"
    base_path = relative_base_path(output_file)
    cache_bust = cache_bust_for(output_file)

    og_image_url = absolute_hashed_asset_url("og-image.png", contact["domain"])

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{fonts_css}}", inline_fonts_css(base_path))
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", og_image_url)
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "article")
    head = apply_asset_hashes(head, base_path)

    schema = build_schema(
        "blogposting",
        contact,
        title=post["title"],
        url=canonical_url,
        description=description,
        date=date_iso,
        author=post["author"],
        image=og_image_url,
    )
    head = head.replace("{{schema_json}}", schema)

    tags = post.get("tags", [])
    accent = tag_accent_class(tags)
    tags_html = "\n".join(f'      <span class="blog-tag {accent}">{tag}</span>' for tag in tags)
    tags_inline_html = "\n".join(f'        <span class="blog-tag {accent}">{tag}</span>' for tag in tags)

    # Build related posts (up to 2 other posts, newest first)
    related = [p for p in all_posts if p["slug"] != post["slug"]][:2]
    related_html = ""
    if related:
        related_cards = []
        for idx, p in enumerate(related, start=1):
            p_date_iso, p_date_display = format_date(p["date"])
            p_tags = p.get("tags", [])
            p_accent = tag_accent_class(p_tags)
            rel_title_id = f"related-title-{idx}"
            rel_excerpt_id = f"related-excerpt-{idx}"
            related_cards.append(
                f'      <a class="blog-card blog-card--related" href="{p["slug"]}.html" aria-labelledby="{rel_title_id}" aria-describedby="{rel_excerpt_id}">\n'
                f'        <div class="blog-card__meta">\n'
                f'          <time datetime="{p_date_iso}">{p_date_display}</time>\n'
                f'        </div>\n'
                f'        <h3 class="blog-card__title" id="{rel_title_id}">{p["title"]}</h3>\n'
                f'        <p class="blog-card__excerpt" id="{rel_excerpt_id}">{p["excerpt"]}</p>\n'
                f'        <span class="blog-card__more" aria-hidden="true">Read post →</span>\n'
                f'        <span class="blog-card__accent {p_accent}" aria-hidden="true"></span>\n'
                f'      </a>'
            )
        related_html = (
            '    <aside class="blog-related" aria-label="Related posts">\n'
            '      <h2 class="blog-related__title">More from the blog</h2>\n'
            '      <div class="blog-related__grid">\n'
            + "\n\n".join(related_cards) +
            "\n      </div>\n"
            "    </aside>"
        )

    html = layout
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{title}}", post["title"])
    html = html.replace("{{date_iso}}", date_iso)
    html = html.replace("{{date_display}}", date_display)
    html = html.replace("{{author}}", post["author"])
    # Replace the two tag placeholders separately: hero tags and footer tags.
    html = html.replace("{{tags}}", tags_html, 1)
    html = html.replace("{{tags}}", tags_inline_html, 1)
    html = html.replace("{{excerpt}}", post["excerpt"])
    body_indented = "\n".join(f"        {line}" for line in post["body"].splitlines())
    # Convert root-relative links inside post bodies to be relative to this page.
    body_indented = body_indented.replace('href="/index.html', f'href="{base_path}index.html')
    html = html.replace("{{body}}", body_indented)
    html = html.replace("{{related}}", related_html)

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
    cache_bust = cache_bust_for(output_file)

    og_image_url = absolute_hashed_asset_url("og-image.png", contact["domain"])

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{fonts_css}}", inline_fonts_css(base_path))
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", og_image_url)
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")
    head = apply_asset_hashes(head, base_path)

    schema = build_schema(
        "blog",
        contact,
        url=canonical_url,
        description=description,
        posts=posts,
    )
    head = head.replace("{{schema_json}}", schema)

    featured_post = posts[0]
    featured_date_iso, featured_date_display = format_date(featured_post["date"])
    featured_tags = featured_post.get("tags", [])
    featured_accent = tag_accent_class(featured_tags)
    featured_tags_html = "\n".join(
        f'          <span class="blog-tag {featured_accent}">{tag}</span>' for tag in featured_tags
    )
    featured_title_id = "blog-title-featured"
    featured_excerpt_id = "blog-excerpt-featured"
    featured_html = (
        f'    <a class="blog-card blog-card--featured" href="{featured_post["slug"]}.html" aria-labelledby="{featured_title_id}" aria-describedby="{featured_excerpt_id}">\n'
        f'      <div class="blog-card__content">\n'
        f'        <div class="blog-card__meta">\n'
        f'          <time datetime="{featured_date_iso}">{featured_date_display}</time>\n'
        f'          <span class="blog-card__featured-label">Featured</span>\n'
        f'        </div>\n'
        f'        <div class="blog-card__tags">\n{featured_tags_html}\n        </div>\n'
        f'        <h2 class="blog-card__title" id="{featured_title_id}">{featured_post["title"]}</h2>\n'
        f'        <p class="blog-card__excerpt" id="{featured_excerpt_id}">{featured_post["excerpt"]}</p>\n'
        f'        <span class="blog-card__more" aria-hidden="true">Read the latest post →</span>\n'
        f'      </div>\n'
        f'      <span class="blog-card__accent {featured_accent}" aria-hidden="true"></span>\n'
        f'    </a>'
    )

    cards = []
    for index, post in enumerate(posts[1:], start=1):
        date_iso, date_display = format_date(post["date"])
        tags = post.get("tags", [])
        accent = tag_accent_class(tags)
        tags_html = "\n".join(f'            <span class="blog-tag {accent}">{tag}</span>' for tag in tags)
        title_id = f"blog-title-{index}"
        excerpt_id = f"blog-excerpt-{index}"
        cards.append(
            f'      <a class="blog-card" href="{post["slug"]}.html" aria-labelledby="{title_id}" aria-describedby="{excerpt_id}">\n'
            f'        <div class="blog-card__meta">\n'
            f'          <time datetime="{date_iso}">{date_display}</time>\n'
            f'        </div>\n'
            f'        <div class="blog-card__tags">\n{tags_html}\n          </div>\n'
            f'        <h2 class="blog-card__title" id="{title_id}">{post["title"]}</h2>\n'
            f'        <p class="blog-card__excerpt" id="{excerpt_id}">{post["excerpt"]}</p>\n'
            f'        <span class="blog-card__more" aria-hidden="true">Read post →</span>\n'
            f'        <span class="blog-card__accent {accent}" aria-hidden="true"></span>\n'
            f'      </a>'
        )

    html = layout
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{featured}}", featured_html)
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
        build_blog_post(post, contact, posts)
    return posts


def build_sitemap(contact: dict, posts: list[dict]) -> None:
    """Generate sitemap.xml with <lastmod> for all public pages.

    All <lastmod> values are derived from content JSON or post dates so the
    output is deterministic across CI runs. File mtimes are not used because
    they change on every checkout.
    """
    domain = contact["domain"]
    urls: list[dict] = []

    # Homepage uses the most recent homepage content update or, failing that,
    # the most recent blog post date.
    home_json = CONTENT / "home" / "content.json"
    if home_json.exists():
        home_data = json.loads(home_json.read_text(encoding="utf-8"))
        home_lastmod = datetime.strptime(home_data.get("last_updated", "January 1, 2020"), "%B %d, %Y").strftime("%Y-%m-%d")
    else:
        home_lastmod = max((p["date"] for p in posts), default="2020-01-01")
    urls.append({
        "loc": f"{domain}/",
        "lastmod": home_lastmod,
        "priority": "1.0",
        "changefreq": "weekly",
    })

    # 404 page uses the last_updated date from its content JSON.
    notfound_data = json.loads((CONTENT / "404" / "content.json").read_text(encoding="utf-8"))
    notfound_lastmod = datetime.strptime(notfound_data.get("last_updated", "January 1, 2020"), "%B %d, %Y").strftime("%Y-%m-%d")
    urls.append({
        "loc": f"{domain}/404.html",
        "lastmod": notfound_lastmod,
        "priority": "0.1",
        "changefreq": "yearly",
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
    blog_index_lastmod = max((p["date"] for p in posts), default="2020-01-01")
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


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def build_feed(contact: dict, posts: list[dict]) -> None:
    """Generate an Atom feed for the blog."""
    if not posts:
        return

    domain = contact["domain"]
    updated_iso = max((p["date"] for p in posts), default=datetime.now().strftime("%Y-%m-%d"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{xml_escape('The Good Bones Blog')}</title>",
        f"  <link href=\"{domain}/blog/index.html\" />",
        f"  <link rel=\"self\" href=\"{domain}/blog/feed.xml\" />",
        f"  <id>{domain}/blog/index.html</id>",
        f"  <updated>{updated_iso}T00:00:00Z</updated>",
        "  <author>",
        f"    <name>{xml_escape(contact['company'])}</name>",
        "  </author>",
    ]

    for post in posts:
        post_url = f"{domain}/blog/{post['slug']}.html"
        date_iso, _ = format_date(post["date"])
        summary = xml_escape(post["excerpt"])
        lines.append("  <entry>")
        lines.append(f"    <title>{xml_escape(post['title'])}</title>")
        lines.append(f"    <link href=\"{post_url}\" />")
        lines.append(f"    <id>{post_url}</id>")
        lines.append(f"    <updated>{date_iso}T00:00:00Z</updated>")
        lines.append(f"    <summary>{summary}</summary>")
        lines.append("  </entry>")

    lines.append("</feed>")

    feed_path = ROOT / "blog" / "feed.xml"
    feed_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {feed_path}")


def build_home_index(contact: dict, posts: list[dict]) -> None:
    """Generate the homepage from template + content JSON."""
    layout = load_template("index.html")
    data = load_content_json("home", "content.json")

    output_file = ROOT / "index.html"
    base_path = relative_base_path(output_file)
    cache_bust = cache_bust_for(output_file)

    title = data["title"]
    description = data["description"]
    canonical_url = contact["domain"] + "/"

    head = load_template("head.html")
    og_image_url = absolute_hashed_asset_url("og-image.png", contact["domain"])

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{fonts_css}}", inline_fonts_css(base_path))
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", og_image_url)
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")
    head = apply_asset_hashes(head, base_path)
    head = head.replace("{{schema_json}}", build_schema("home", contact, title=title, url=canonical_url, description=description))

    # FAQ content (optional)
    faq_data = load_content_json("home", "faq.json") if (CONTENT / "home" / "faq.json").exists() else {}
    faq_title = faq_data.get("title", "Frequently asked questions")
    faq_subtitle = faq_data.get("subtitle", "")
    faq_contact_prompt = faq_data.get("contact_prompt", "Still have questions?")
    faq_contact_cta = faq_data.get("contact_cta", "Reach out")
    faq_contact_link = faq_data.get("contact_link", "#contact")
    faq_items = ""
    if faq_data.get("items"):
        faq_items = "\n\n".join(
            f'        <article class="faq__item" id="{item["id"]}">\n'
            f'          <h3 class="visually-hidden" id="faq-title-{idx}">{item["question"]}</h3>\n'
            f'          <button class="faq__question" type="button" aria-expanded="false" aria-controls="faq-answer-{idx}">\n'
            f'            <span class="faq__question-text" aria-hidden="true">{item["question"]}</span>\n'
            f'            <span class="faq__icon" aria-hidden="true"><span class="faq__icon-line faq__icon-line--h" aria-hidden="true"></span><span class="faq__icon-line faq__icon-line--v" aria-hidden="true"></span></span>\n'
            f'          </button>\n'
            f'          <div class="faq__answer" id="faq-answer-{idx}" role="region" aria-labelledby="faq-title-{idx}">\n'
            f'            <div class="faq__answer-inner"><p>{item["answer"]}</p></div>\n'
            f'          </div>\n'
            f'        </article>'
            for idx, item in enumerate(faq_data["items"], start=1)
        )

    # Simple scalar replacements from content.json.
    scalar_keys = [
        "eyebrow", "lede", "about_title", "about_intro", "about_body",
        "services_title", "services_sub", "work_title", "work_sub",
        "testimonials_title", "testimonials_sub", "cta_title", "cta_sub",
        "contact_title", "contact_intro", "blog_teaser_title", "blog_teaser_sub",
    ]

    project_cards = []
    for index, project in enumerate(data["projects"]):
        title_id = f"work-title-{index + 1}"
        desc_id = f"work-desc-{index + 1}"
        project_cards.append(
            f'      <a class="work-card tilt" href="#contact" data-tilt aria-labelledby="{title_id}" aria-describedby="{desc_id}">\n'
            f'        <div class="work-card__image {project["image_class"]}">\n'
            f'          <div class="mini-browser" aria-hidden="true">\n'
            f'            <div class="mini-browser__bar"><span></span><span></span><span></span></div>\n'
            f'            <div class="mini-browser__body">\n'
            f'              <div class="mini-browser__hero"></div>\n'
            f'              <div class="mini-browser__grid"><span></span><span></span><span></span><span></span></div>\n'
            f'            </div>\n'
            f'          </div>\n'
            f'          <span class="work-card__peek" aria-hidden="true">Case study</span>\n'
            f'        </div>\n'
            f'        <div class="work-card__body">\n'
            f'          <h3 id="{title_id}">{project["title"]}</h3>\n'
            f'          <p id="{desc_id}">{project["description"]}</p>\n'
            f'          <span class="tag {project["tag_class"]}">{project["tag"]}</span>\n'
            f'          <span class="work-card__cta" aria-hidden="true">Request case study <span aria-hidden="true">→</span></span>\n'
            f'        </div>\n'
            f'      </a>'
        )

    stats_html = "\n".join(
        f'            <div class="about__stat about__stat--{stat["accent"]}" data-count="{stat["count"]}">\n'
        f'              <strong>{stat["value"]}</strong>\n'
        f'              <span class="about__stat__label">{stat["label"]}</span>\n'
        f'            </div>'
        for stat in data["stats"]
    )

    testimonial_cards = []
    for t in data["testimonials"]:
        testimonial_cards.append(
            f'      <blockquote class="testimonial tilt {t["class"]}" data-tilt>\n'
            f'        <span class="testimonial__pin" aria-hidden="true"></span>\n'
            f'        <div class="testimonial__quote-mark" aria-hidden="true">“</div>\n'
            f'        <p>{t["quote"]}</p>\n'
            f'        <footer>\n'
            f'          <span class="avatar" aria-hidden="true">{t["initials"]}</span>\n'
            f'          <div>\n'
            f'            <span class="stars" aria-hidden="true">★★★★★</span>\n'
            f'            <span class="visually-hidden">5 out of 5 stars</span>\n'
            f'            <cite>{t["name"]}</cite>\n'
            f'            <span>{t["role"]}</span>\n'
            f'          </div>\n'
            f'        </footer>\n'
            f'      </blockquote>'
        )

    # Blog teaser from the two most recent posts.
    teaser_posts = sorted(posts, key=lambda p: p["date"], reverse=True)[:2]
    teaser_cards = []
    for index, post in enumerate(teaser_posts):
        title_id = f"blog-post-{index + 1}"
        excerpt_id = f"blog-excerpt-{index + 1}"
        date_iso, date_display = format_date(post["date"])
        tags_html = "\n".join(f'          <span>{tag}</span>' for tag in post.get("tags", []))
        teaser_cards.append(
            f'      <a class="blog-teaser__card" href="{base_path}blog/{post["slug"]}.html" aria-labelledby="{title_id}" aria-describedby="{excerpt_id}">\n'
            f'        <div class="blog-teaser__meta">\n'
            f'          <time datetime="{date_iso}">{date_display}</time>\n'
            f'{tags_html}\n'
            f'        </div>\n'
            f'        <h3 class="blog-teaser__title" id="{title_id}">{post["title"]}</h3>\n'
            f'        <p class="blog-teaser__excerpt" id="{excerpt_id}">{post["excerpt"]}</p>\n'
            f'        <span class="blog-teaser__more" aria-hidden="true">Read post <span aria-hidden="true">→</span></span>\n'
            f'      </a>'
        )

    html = layout
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    # Replace remaining base_path in nav after apply_contact.
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    # Replace remaining cache_bust in footer after apply_contact.
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{projects}}", "\n\n".join(project_cards))
    html = html.replace("{{stats}}", stats_html)
    html = html.replace("{{testimonials}}", "\n\n".join(testimonial_cards))
    html = html.replace("{{blog_teaser_posts}}", "\n\n".join(teaser_cards))
    html = html.replace("{{faq_title}}", faq_title)
    html = html.replace("{{faq_subtitle}}", faq_subtitle)
    html = html.replace("{{faq_contact_prompt}}", faq_contact_prompt)
    html = html.replace("{{faq_contact_cta}}", faq_contact_cta)
    html = html.replace("{{faq_contact_link}}", faq_contact_link)
    html = html.replace("{{faq_items}}", faq_items)
    for key in scalar_keys:
        html = html.replace("{{" + key + "}}", data.get(key, ""))
    # Contact data replacement is handled by apply_contact in nav/footer; also do direct body.
    html = apply_contact(html, contact)

    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def build_404(contact: dict) -> None:
    """Generate the 404 page from template + content JSON."""
    layout = load_template("404.html")
    data = load_content_json("404", "content.json")

    output_file = ROOT / "404.html"
    base_path = relative_base_path(output_file)
    cache_bust = cache_bust_for(output_file)
    last_updated_iso = datetime.strptime(data["last_updated"], "%B %d, %Y").strftime("%Y-%m-%d")

    title = data["title"]
    description = data["description"]
    canonical_url = f"{contact['domain']}/404.html"

    head = load_template("head.html")
    og_image_url = absolute_hashed_asset_url("og-image.png", contact["domain"])

    head = apply_contact(head, contact)
    head = head.replace("{{base_path}}", base_path)
    head = head.replace("{{fonts_css}}", inline_fonts_css(base_path))
    head = head.replace("{{title}}", title)
    head = head.replace("{{description}}", description)
    head = head.replace("{{canonical_url}}", canonical_url)
    head = head.replace("{{og_image}}", og_image_url)
    head = head.replace("{{og_image_alt}}", contact["og"]["image_alt"])
    head = head.replace("{{twitter_handle}}", contact["og"]["twitter_handle"])
    head = head.replace("{{domain}}", contact["domain"])
    head = head.replace("{{og_type}}", "website")
    head = apply_asset_hashes(head, base_path)
    head = head.replace("{{schema_json}}", build_schema("webpage", contact, title=title, url=canonical_url, description=description, date_modified=last_updated_iso))

    html = layout
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    html = html.replace("{{head}}", head)
    nav = apply_contact(load_template("nav.html"), contact)
    footer = apply_contact(load_template("footer.html"), contact)
    html = html.replace("{{nav}}", nav.replace("{{base_path}}", base_path))
    # Replace any remaining base_path markers in nav.
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{footer}}", footer.replace("{{base_path}}", base_path))
    # Replace any remaining base_path/cache_bust markers in footer.
    html = html.replace("{{base_path}}", base_path)
    html = html.replace("{{cache_bust}}", cache_bust)
    for key in ["code_label", "heading", "sub", "help_title"]:
        html = html.replace("{{" + key + "}}", data.get(key, ""))

    if MINIFY_HTML:
        html = minify_html(html)
    output_file.write_text(html, encoding="utf-8")
    print(f"Built {output_file}")


def write_minified_assets() -> None:
    """Write minified versions of CSS and JS with conventional .min names.

    The generated HTML references these minified files directly, while the
    source CSS/JS files in the repo remain readable for development.
    """
    mappings = {
        ROOT / "css" / "global.css": ROOT / "css" / "global.min.css",
        ROOT / "css" / "index.css": ROOT / "css" / "index.min.css",
        ROOT / "css" / "blog.css": ROOT / "css" / "blog.min.css",
        ROOT / "script.js": ROOT / "script.min.js",
    }
    for src, dst in mappings.items():
        if not src.exists():
            continue
        dst.write_text(get_minified_source(src).decode("utf-8"), encoding="utf-8")
        print(f"Wrote {dst}")


def main() -> None:
    contact = load_json("contact.json")

    # Write minified CSS/JS and fingerprint static assets before generating
    # pages so every generated reference points to the correct hashed file.
    write_minified_assets()
    compute_asset_fingerprints()

    pages = {
        "privacy.json": ROOT / "privacy.html",
        "terms.json": ROOT / "terms.html",
        "accessibility.json": ROOT / "accessibility.html",
    }

    for src, dst in pages.items():
        build_page(CONTENT / src, dst, contact)

    posts = build_blog(contact)
    build_home_index(contact, posts)
    build_404(contact)
    build_feed(contact, posts)
    build_sitemap(contact, posts)


if __name__ == "__main__":
    main()
