# ARGO Agent — marketing site

The static marketing / landing website for **ARGO Agent v3.0**.

This is a plain static site: hand-written HTML, CSS and a small amount of
vanilla JavaScript. There is **no build step**, no framework and no external
network dependency — every asset is local and a system font stack is used, so
the site renders correctly fully offline.

## Contents

```
website/
├── index.html      # landing page — hero, features, architecture, why ARGO, quick start
├── docs.html       # documentation landing page (links into /docs/)
├── download.html   # download & install options (try-it, setup script, Docker, Helm, PyPI, native)
├── css/style.css   # responsive, dark-mode-friendly stylesheet (no frameworks)
├── js/main.js      # mobile nav toggle, smooth-scroll fallback, copy-to-clipboard
├── CNAME           # custom-domain placeholder for GitHub Pages
└── README.md       # this file
```

## Preview locally

From inside the `website/` directory, start any static file server. The
project standard is Python's built-in server:

```bash
cd website
python3 -m http.server 8000
```

Then open <http://localhost:8000> in a browser.

Any static server works equally well (for example `npx serve`), since the site
has no build step and no server-side logic.

## Deployment

The site is designed to be served by any static host:

- **GitHub Pages** — point Pages at the `website/` directory (or publish its
  contents to the `gh-pages` branch). The included `CNAME` file configures the
  custom domain.
- **Any static host** — Netlify, Cloudflare Pages, S3 + CloudFront, nginx, etc.
  Just upload the contents of `website/` as-is.

### The `CNAME` file

`website/CNAME` contains the placeholder custom domain `argo-agent.io`. It is
**a placeholder** — GitHub Pages reads this file to bind the custom domain.
Replace it with the project's real domain (and configure DNS accordingly)
before going live. If you are not using a custom domain, delete the file.

## Notes

- All content is in English.
- ARGO v3.0 is alpha software approaching general availability; the site states
  this honestly and does not claim the project is production-ready.
- No CDN links, analytics or third-party scripts are included.
