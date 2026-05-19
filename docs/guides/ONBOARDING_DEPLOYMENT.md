# Interactive Onboarding Dashboard — Deployment Guide

## Overview

`docs/onboarding.html` is a single, self-contained HTML file that serves as the visual entry point to FlexTemplates documentation. It requires no build step, no dependencies, and no server-side rendering.

## How to Use

### Local Development

1. Open `docs/onboarding.html` directly in your browser:
   - **Windows/Mac:** Double-click the file
   - **Linux:** `xdg-open docs/onboarding.html` or `firefox docs/onboarding.html`

2. All links to `.md` files assume they're in the `docs/` directory (relative paths).

### Serving on a Web Server

If hosting on GitHub Pages, Netlify, or similar:

```bash
# Place onboarding.html in your /docs folder (GitHub Pages)
# or root folder (Netlify)
# It will be accessible at: https://your-domain.com/onboarding.html
```

### Linking from README

Add a link to the onboarding dashboard in your `README.md`:

```markdown
## 🚀 Getting Started

**New to FlexTemplates?** Start here: [**Interactive Onboarding Dashboard**](docs/onboarding.html)

Or dive into the docs:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 5-min overview
- [QUICKSTART.md](docs/QUICKSTART.md) — Set up locally
```

## How It Works

The dashboard uses relative links to open documentation files in the same `docs/` directory:

```
docs/
├── onboarding.html          ← Dashboard (you are here)
├── ARCHITECTURE.md          ← Linked
├── QUICKSTART.md            ← Linked
├── CONVENTIONS.md           ← Linked
├── CONTRACTS_GUIDE.md       ← Linked
├── ADDING_STUFF.md          ← Linked
├── WRAPPERS.md              ← Linked
├── VAULT_USAGE.md           ← Linked
├── PONG_EXAMPLE.md          ← Linked
├── TESTING.md               ← Linked
└── DOCS_INDEX.md            ← Not linked (for internal reference)
```

## Customization

The HTML is a single file with embedded CSS and JavaScript. To customize:

### Change colors

Edit the CSS variables at the top of the `<style>` block:

```css
:root {
    --primary: #2563eb;        /* Change this to your brand color */
    --accent: #f59e0b;
    /* ... other variables ... */
}
```

### Update layer descriptions

Edit the `layerInfo` object in the `<script>` block to add/modify layer details.

### Add new quick-nav links

Add to the `.quicklinks-grid` section:

```html
<a href="NEW_DOC.md" class="quicklink">
    <span class="icon">🆕</span>
    <span class="label">New Feature</span>
</a>
```

## Browser Compatibility

- **Modern browsers (2022+):** Full support (Chrome, Firefox, Safari, Edge)
- **IE 11:** Not supported (uses CSS Grid, ES6)
- **Mobile browsers:** Full responsive support

## Performance

- **File size:** ~32 KB (minified, uncompressed)
- **Load time:** <100ms on most connections
- **Rendering:** Instant (no async JS, no API calls)
- **Offline-capable:** Yes (all content is static HTML)

## Analytics (Optional)

The dashboard includes a placeholder for tracking which learning paths users select:

```javascript
document.querySelectorAll('.path-card').forEach(card => {
    card.addEventListener('click', function() {
        const pathId = this.id;
        console.log('Path selected:', pathId);
        // Replace console.log() with your analytics call
    });
});
```

To add Google Analytics or similar, insert your tracking code in the `<head>` block.

## Troubleshooting

**Links not working?**
- Ensure all `.md` files are in the `docs/` directory
- Check relative paths (should be just `FILENAME.md`, not `/docs/FILENAME.md`)

**Styling looks wrong?**
- Try a different browser (CSS Grid support)
- Disable browser extensions that modify CSS
- Clear browser cache (Ctrl+Shift+R / Cmd+Shift+R)

**Responsive layout broken?**
- Check viewport meta tag in `<head>`: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- Test in actual mobile browser or DevTools responsive mode

---

**Last updated:** 2026-05-17
