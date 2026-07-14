# Good Bones Web Inc.

A vibrant, strategy-first website for an Edmonton website consulting company.

## Development

This is a static site. The homepage (`index.html`), 404 page (`404.html`), legal pages (`privacy.html`, `terms.html`, `accessibility.html`), the blog section (`blog/`), the sitemap, and the Atom feed are all generated from JSON content and HTML templates using `build.py`.

### Build the site

```bash
python3 build.py
```

### Project structure

```
.
├── index.html              # Homepage (generated)
├── 404.html                # Error page (generated)
├── css/
│   ├── global.css          # Shared styles
│   ├── index.css           # Homepage-only styles
│   └── blog.css            # Blog index + post styles
├── script.js               # Site interactions (ES module)
├── fonts/                  # Self-hosted Bebas Neue and Space Grotesk
├── src/
│   ├── content/            # JSON content for generated pages
│   │   ├── 404/
│   │   │   └── content.json      # 404 page copy
│   │   ├── home/
│   │   │   └── content.json      # Homepage copy
│   │   ├── *.json                # Legal page copy
│   │   └── blog/
│   │       └── posts.json        # Blog post metadata and HTML bodies
│   ├── data/
│   │   └── contact.json     # Shared contact + social info
│   └── templates/          # Reusable HTML partials and page layouts
│       ├── index.html      # Homepage layout
│       ├── 404.html        # 404 page layout
│       └── *.html          # Shared partials
├── build.py                # Static site generator
├── sitemap.xml             # Generated sitemap
└── robots.txt
```

### Before committing

1. Update `src/data/contact.json` if contact details, social URLs, or domain change.
2. Add or edit blog posts in `src/content/blog/posts.json`. The homepage blog teaser and `blog/feed.xml` update automatically.
3. Run `python3 build.py` to regenerate all generated pages and assets.
4. Verify the generated HTML in `index.html`, `404.html`, `privacy.html`, `terms.html`, `accessibility.html`, `blog/index.html`, `blog/*.html`, `blog/feed.xml`, and `sitemap.xml`.
5. Commit any generated file changes so the CI build stays reproducible.

## Deployment

Upload the repository root to any static host. No server-side runtime is required.

## Notes

- The contact form is currently a demo and does not submit anywhere.
- All assets (CSS, JS, fonts, favicons) are self-hosted.
- Run `python3 build.py --watch` is not implemented; use a file watcher if desired.
