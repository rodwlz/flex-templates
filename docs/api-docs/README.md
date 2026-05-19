# API Documentation Learning Path

Interactive HTML documentation for the FlexTemplates API architecture and patterns.

## Pages

- **index.html** — Hub page with three learning cards
- **architecture.html** — Page 1/3: Core design principles (from API_ARCHITECTURE_SUMMARY.md)
- **template.html** — Page 2/3: Step-by-step pattern guide (from API_PATTERN_TEMPLATE.md)
- **pong.html** — Page 3/3: Complete worked example (from PONG_EXAMPLE.md)

## Features

- Interactive navigation (Previous/Next/Hub buttons)
- Progress indicators (Page X of 3)
- Syntax highlighting via Prism.js (Python, Bash, JavaScript, JSON)
- Copy-to-clipboard buttons on code blocks
- Responsive design (mobile, tablet, desktop)
- Reusable color scheme from onboarding.html

## Quick Start

1. **Open in browser:** Click `index.html` or navigate to `docs/api-docs/` in your file explorer
2. **Start learning:** Click any of the three learning cards (Architecture, Pattern, Example)
3. **Navigate:** Use Previous/Next buttons to move through the learning path
4. **Copy code:** Click the "Copy" button on any code block to copy to clipboard
5. **Return home:** Click "Back to Hub" from any page to return to the index

## Technical Details

### File Structure

```
docs/api-docs/
├── index.html              Hub page with three learning cards
├── architecture.html       Page 1 of 3: Architecture overview
├── template.html           Page 2 of 3: Pattern template
├── pong.html              Page 3 of 3: Complete example
├── css/
│   └── docs.css           Shared stylesheet
├── js/
│   └── script.js          Copy-to-clipboard functionality
└── README.md              This file
```

### Content Source Files

Documentation content is sourced from markdown:
- `docs/API_ARCHITECTURE_SUMMARY.md` → `architecture.html`
- `docs/API_PATTERN_TEMPLATE.md` → `template.html`
- `docs/PONG_EXAMPLE.md` → `pong.html`

To update content: Edit the markdown files, then convert to HTML preserving all structure.

### Styling

- **CSS:** `css/docs.css` contains all styling including:
  - Color scheme (reused from onboarding.html: primary #2563eb, accent #f59e0b)
  - Typography (system font stack, line-height 1.6)
  - Code blocks (dark background for Prism.js)
  - Navigation buttons (primary blue, hover effects, disabled states)
  - Responsive breakpoints (768px tablet, 480px mobile)

### JavaScript

- **Copy function:** `js/script.js` provides `copyToClipboard(button)` handler
  - Gets code text from adjacent `<code>` element
  - Writes to clipboard via `navigator.clipboard.writeText()`
  - Shows "Copied!" feedback for 2 seconds
  - Graceful error handling for clipboard failures

### Syntax Highlighting

- **Library:** Prism.js v1.29.0 (loaded from CDN)
- **Theme:** prism-tomorrow (dark theme)
- **Languages:** Python, Bash, JavaScript, JSON
- **Implementation:** Automatic detection via `language-python`, `language-bash`, etc. class names

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android 90+)

**Note:** Clipboard API (used for copy buttons) requires HTTPS or localhost. Works in all modern browsers.

## Navigation Guide

### Learning Path Flow

```
index.html (Hub)
  ├─ Card 1: Architecture Overview → architecture.html (Page 1/3)
  │   Next → template.html
  │
  ├─ Card 2: Pattern Template → template.html (Page 2/3)
  │   Previous → architecture.html
  │   Next → pong.html
  │
  └─ Card 3: Complete Example → pong.html (Page 3/3)
      Previous → template.html
      (Next disabled on last page)
```

Each page has buttons to navigate forward/backward or return to hub at any time.

## Development

### No Build Process Required

All files are static HTML/CSS/JavaScript served as-is. No build tools, transpilers, or package managers needed.

### Making Changes

To update content:
1. Edit source markdown file (`docs/API_ARCHITECTURE_SUMMARY.md`, etc.)
2. Convert markdown to HTML manually, preserving all structure
3. Update corresponding HTML file (`architecture.html`, etc.)
4. Test navigation and copy buttons in browser

### Adding New Pages

To add a new documentation page:
1. Create markdown source (e.g., `docs/NEW_TOPIC.md`)
2. Convert to HTML (e.g., `docs/api-docs/newtopic.html`)
3. Add a new card to `index.html` linking to it
4. Update navigation links in adjacent pages
5. Update this README with new page location

## Testing Checklist

- [ ] All four HTML files open without errors in browser
- [ ] Hub page (index.html) displays three cards
- [ ] Each card links to correct documentation page
- [ ] Code blocks display with syntax highlighting
- [ ] Copy buttons appear on all code blocks
- [ ] Click "Copy" → button shows "Copied!" and text is copied to clipboard
- [ ] After 2 seconds, button reverts to "Copy"
- [ ] Previous/Next navigation buttons work correctly
- [ ] "Back to Hub" buttons return to index.html
- [ ] Page displays correctly on mobile (375px width)
- [ ] Page displays correctly on tablet (768px width)
- [ ] Page displays correctly on desktop (1920px width)
- [ ] All links are active and working
- [ ] No JavaScript errors in browser console

## Troubleshooting

### Copy buttons not working
- Check browser console for errors: F12 → Console tab
- Verify you're using HTTPS or localhost (Clipboard API requirement)
- Check that `js/script.js` is loaded (Network tab)

### Syntax highlighting not showing
- Verify Prism.js loaded from CDN (Network tab, look for cdnjs.cloudflare.com)
- Check that code block has `language-python` (or appropriate language) class
- Refresh page (Ctrl+F5 or Cmd+Shift+R) to clear cache

### Navigation buttons not working
- Verify file paths in `onclick="window.location.href=..."` attributes
- Check that all HTML files exist in `docs/api-docs/` directory
- Ensure no typos in filenames (case-sensitive on some servers)

## Notes

- Pages are fully self-contained (no external dependencies except Prism.js CDN)
- All content is formatted for easy reading and learning
- Code examples are preserved exactly from source markdown
- No runtime dependencies—pure HTML, CSS, and JavaScript
- Responsive design works on all modern browsers and devices

## License

This documentation is part of the FlexTemplates project.
