# API Documentation HTML Conversion — Design Spec

**Goal:** Convert existing markdown documentation to an interactive HTML learning path with navigation, styling, and code syntax highlighting.

**Approach:** Reuse existing content from three MD files, organize into a multi-page learning path with hub navigation.

---

## Content & Structure

### Source Files (Content Preserved As-Is)
- `docs/API_ARCHITECTURE_SUMMARY.md` → `docs/api-docs/architecture.html` (Page 1/3)
- `docs/API_PATTERN_TEMPLATE.md` → `docs/api-docs/template.html` (Page 2/3)
- `docs/PONG_EXAMPLE.md` → `docs/api-docs/pong.html` (Page 3/3)

### New Files
- `docs/api-docs/index.html` — Hub page with three cards linking to docs
- `docs/api-docs/css/docs.css` — Shared styling (reuse onboarding.html color scheme)

### Learning Path Flow
1. **index.html** — Hub landing page, three cards (Architecture / Pattern Template / Pong Example)
2. **architecture.html** — "Page 1 of 3", understand the pattern
3. **template.html** — "Page 2 of 3", learn to add new entities
4. **pong.html** — "Page 3 of 3", see complete worked example

---

## Page Template (All Pages)

```
<header>
  - Site title + breadcrumb/progress ("Page 1 of 3")
  - Main heading from MD file
</header>

<main>
  - Converted MD content (paragraphs, code blocks, tables, lists)
  - Code blocks with syntax highlighting (Prism.js)
  - Copy-to-clipboard button on code blocks
  - Expandable sections (CSS toggles or simple JS)
</main>

<nav class="page-nav">
  - Previous button (disabled on page 1)
  - Back to Hub button
  - Next button (disabled on page 3)
  - Progress indicator ("1/3", "2/3", "3/3")
</nav>
```

---

## Styling (docs.css)

**Reuse from onboarding.html:**
- Color scheme (--primary: #2563eb, --accent: #f59e0b, etc.)
- Typography (system font stack, line-height: 1.6)
- Responsive layout (max-width: 1200px, padding adjustments)

**New styles:**
- Code blocks: dark background, Prism syntax highlighting, monospace font
- Copy button: small, bottom-right of code block, "Copied!" tooltip
- Navigation buttons: primary blue with hover effects
- Progress indicator: subtle text or badge at top
- Expandable sections: chevron icon, smooth height transitions

---

## Interactive Elements

### Code Blocks
- Syntax highlighting via Prism.js (CDN)
- Copy button that shows "Copied!" toast for 2 seconds
- Optional: "Expand full example" toggle for large blocks

### Navigation
- Previous/Next/Hub buttons with disabled state styling
- Smooth page transitions (fade or slight slide)
- Progress indicator shows "Page X of 3"

### Expandable Sections (in Template)
- Use markdown's `<details>` or CSS `:checked` pattern
- Smooth height animation on expand/collapse
- Chevron icon rotates with state

---

## Conversion Details

### Markdown to HTML Conversion
- Headings → `<h1>`, `<h2>`, etc. (preserve hierarchy)
- Code blocks (triple backticks) → `<pre><code class="language-python">` (for Prism highlighting)
- Bold/italic → `<strong>`, `<em>`
- Lists → `<ul>`, `<ol>`
- Tables → `<table>` with `<thead>`, `<tbody>`
- Links → `<a href>` (preserve URLs)

### Prism.js Integration
- Link CDN in `<head>`: `https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js`
- Add language CSS: `https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css`
- Code blocks auto-highlighted via class names (language-python, language-javascript, language-bash, etc.)

---

## Task Division

| Task | Model | Output |
|------|-------|--------|
| Create shared CSS (docs.css) + page template structure | **Sonnet** | Reusable styles & layout |
| Create index.html hub with three cards | **Sonnet** | Landing page |
| Convert 3 MD files to HTML, add navigation | **Haiku** | Three content pages |
| Wire up Prism.js, add copy buttons, final polish | **Opus** | Syntax highlighting + interactivity |

---

## Success Criteria

✅ All three MD files converted to HTML (content preserved exactly)
✅ Hub page with three cards, each links to corresponding page
✅ Each page shows progress ("1 of 3", "2 of 3", "3 of 3")
✅ Previous/Next navigation buttons work correctly
✅ Code blocks have syntax highlighting (Prism.js)
✅ Code blocks have copy-to-clipboard button
✅ Styling matches onboarding.html color scheme
✅ Pages are responsive (mobile-friendly)
✅ All links work (internal navigation + external references)
✅ Zero broken images/references

---

## File Structure

```
docs/
└── api-docs/
    ├── index.html           (hub page)
    ├── architecture.html    (page 1/3)
    ├── template.html        (page 2/3)
    ├── pong.html            (page 3/3)
    └── css/
        └── docs.css         (shared styles)
```

---

## Notes

- Keep page file sizes reasonable (convert once, load fast)
- Prism.js auto-detects language from class names
- Copy button can be simple (no external clipboard library, use built-in API)
- Progress indicator can be static text or a visual badge
- All existing MD content is preserved; no rewriting
