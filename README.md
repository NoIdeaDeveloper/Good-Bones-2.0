# Good Bones Web Inc.

A vibrant, strategy-first website for an Edmonton website consulting company.

## Development

This is a static site. The legal pages (`privacy.html`, `terms.html`, `accessibility.html`) are generated from JSON content and HTML templates using `build.py`.

### Build the legal pages

```bash
python3 build.py
```

### Project structure

```
.
├── index.html              # Homepage
├── 404.html                # Error page
├── css/
│   ├── global.css          # Shared styles
│   └── index.css           # Homepage-only styles
├── script.js               # Site interactions (ES module)
├── fonts/                  # Self-hosted Bebas Neue and Space Grotesk
├── src/
│   ├── content/            # JSON content for legal pages
│   ├── data/
│   │   └── contact.json     # Shared contact + social info
│   └── templates/          # Reusable HTML partials
├── build.py                # Static site generator for legal pages
├── sitemap.xml
└── robots.txt
```

### Before committing

1. Update `src/data/contact.json` if contact details, social URLs, or domain change.
2. Run `python3 build.py` to regenerate legal pages.
3. Verify the generated HTML in `privacy.html`, `terms.html`, and `accessibility.html`.

## Deployment

Upload the repository root to any static host. No server-side runtime is required.

## Notes

- The contact form is currently a demo and does not submit anywhere.
- All assets (CSS, JS, fonts, favicons) are self-hosted.
- Run `python3 build.py --watch` is not implemented; use a file watcher if desired.
