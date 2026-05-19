# FlexTemplates Docs Portal & Agent Index — Design Spec

**Date:** 2026-05-19
**Status:** Approved

---

## Goal

Two deliverables in one pass:

1. **HTML documentation portal** — Expand `docs/api-docs/` from a 3-page API learning path into a full 8-page categorized developer docs site.
2. **Agent-readable documentation layer** — Restructure `docs/` into subfolders, add YAML frontmatter to every `.md`, and create a root `CLAUDE.md` agent context file.

Both a human developer and an AI agent dropping into this repo cold should be able to orient themselves and find what they need in under 2 minutes.

---

## Part 1: HTML Documentation Portal

### Hub Page (`docs/api-docs/index.html`) — Complete Redesign

Replace the current 3-card grid with 3 labeled category sections. Each section has a color-coded left accent border, a one-line description, and 2–3 cards.

**Title:** "FlexTemplates Developer Documentation" (replaces "API Documentation Learning Path")
**Subtitle:** "Everything you need to build, extend, and debug."

#### Section 1 — Core Concepts (blue accent)
> Understand the architecture before you build anything.

| Card | File | CTA |
|---|---|---|
| 📐 Architecture Overview | architecture.html | Start Learning → |
| 🧩 Pattern Template | template.html | Learn the Pattern → |
| 🎮 Complete Example: Pong | pong.html | See Example → |

#### Section 2 — Builder Guides (green accent)
> Task-focused guides for building API endpoints and views.

| Card | File | CTA |
|---|---|---|
| 🔌 API Development | api-development.html | Build Endpoints → |
| 🖼 View Development | view-development.html | Build Views → |
| 🌳 Decision Trees | decision-trees.html | Choose Patterns → |

#### Section 3 — Troubleshooting & Reference (amber accent)
> Fix issues fast. Avoid mistakes before they happen.

| Card | File | CTA |
|---|---|---|
| 🔧 Troubleshooting Guide | troubleshooting.html | Fix Issues → |
| 🚫 Anti-Patterns | anti-patterns.html | Avoid Mistakes → |

---

### 5 New HTML Pages

Each new page uses the existing structure: same `docs.css`, same Prism.js CDN, same copy-to-clipboard JS. Content converted from the corresponding `.md` source.

| HTML File | Source `.md` | Section | Position |
|---|---|---|---|
| `api-development.html` | `docs/guides/API_DEVELOPMENT.md` | Builder Guides | 1 of 3 |
| `view-development.html` | `docs/guides/VIEW_DEVELOPMENT.md` | Builder Guides | 2 of 3 |
| `decision-trees.html` | `docs/reference/DECISION_TREES.md` | Builder Guides | 3 of 3 |
| `troubleshooting.html` | `docs/troubleshooting/TROUBLESHOOTING.md` | Troubleshooting | 1 of 2 |
| `anti-patterns.html` | `docs/troubleshooting/ANTI_PATTERNS.md` | Troubleshooting | 2 of 2 |

---

### Navigation Design

**Breadcrumb** on every page:
```
Core Concepts > Architecture Overview
Builder Guides > API Development
Troubleshooting & Reference > Troubleshooting Guide
```

**Prev/Next** navigates within the same category only:
- Core Concepts: architecture → template → pong (unchanged)
- Builder Guides: api-development → view-development → decision-trees
- Troubleshooting: troubleshooting → anti-patterns

**"Back to Hub"** button always visible on every page.

**Existing pages** (architecture.html, template.html, pong.html) get:
- Breadcrumb added: `Core Concepts > [page name]`
- Header subtitle updated from "Page X of 3" → breadcrumb text
- No other changes needed

---

### CSS Additions to `docs.css`

Three new accent-border variables for section color coding:
```css
--section-core: #2563eb;       /* blue — Core Concepts */
--section-builder: #16a34a;    /* green — Builder Guides */
--section-troubleshoot: #d97706; /* amber — Troubleshooting */
```

Section headers on hub use `border-left: 4px solid var(--section-*)`.
Cards inherit no color change — just the section header above them signals the grouping.

---

## Part 2: Agent-Readable Documentation

### New `docs/` Folder Structure

```
docs/
├── DOCS_INDEX.md                  ← root nav (humans + agents), updated with new paths
│
├── core/                          ← must-read foundation
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md
│   └── CONTRACTS_GUIDE.md
│
├── guides/                        ← task-focused how-to
│   ├── GETTING_STARTED.md
│   ├── QUICKSTART.md
│   ├── ADDING_STUFF.md
│   ├── WRAPPERS.md
│   ├── API_DEVELOPMENT.md
│   ├── VIEW_DEVELOPMENT.md
│   └── ONBOARDING_DEPLOYMENT.md
│
├── reference/                     ← look up when needed
│   ├── DECISION_TREES.md
│   ├── VAULT_USAGE.md
│   ├── TESTING.md
│   └── API_ARCHITECTURE_SUMMARY.md
│
├── troubleshooting/               ← fix problems, avoid mistakes
│   ├── TROUBLESHOOTING.md
│   └── ANTI_PATTERNS.md
│
├── examples/                      ← complete worked examples
│   ├── PONG_EXAMPLE.md
│   └── API_PATTERN_TEMPLATE.md
│
├── api-docs/                      ← HTML interactive docs (unchanged internally)
│
└── superpowers/                   ← internal plans/specs/audits (unchanged)
```

**18 `.md` files** move from flat `docs/` into subfolders. `DOCS_INDEX.md` stays at `docs/` root.

---

### Cross-Reference Updates

Every internal link in every doc gets updated to the new relative path. Strategy:

- Links **from** `docs/DOCS_INDEX.md` → prefix with subfolder: `core/ARCHITECTURE.md`
- Links **from** `docs/core/*.md` → sibling: `CONVENTIONS.md`, parent: `../DOCS_INDEX.md`, cross-folder: `../guides/QUICKSTART.md`
- Links **from** `docs/guides/*.md` → cross-folder: `../core/ARCHITECTURE.md`
- Links **from** `docs/reference/*.md` → cross-folder: `../core/CONVENTIONS.md`
- Links **from** `docs/troubleshooting/*.md` → cross-folder: `../core/ARCHITECTURE.md`
- Links **from** `docs/examples/*.md` → cross-folder: `../core/CONVENTIONS.md`
- Links **from** `README.md` (root) → `docs/core/ARCHITECTURE.md`, `docs/guides/QUICKSTART.md`, etc.
- Links **from** `ONBOARDING_COMPLETE.md` (root) → update all `docs/` references

The HTML site (`docs/api-docs/`) links to `.md` source files only in `README.md` comments — those get updated but don't affect browser navigation.

---

### Root `CLAUDE.md` — Agent Master Context

Location: `CLAUDE.md` at the project root (alongside `README.md`).

Purpose: An agent landing in this repo reads this file first. Dense, no prose — all pointers.

**Schema:**
```markdown
# FlexTemplates — Agent Context

## What This Is
[3 sentences: Flet + FastAPI + SQLAlchemy, LEGO modularity, ActionRequest/ActionResult contracts]

## Architecture (30 seconds)
[ASCII layer diagram]

## Key Files
| File | Purpose |
|---|---|
| lib/container.py | Only file that names concrete implementations |
| lib/contracts/base.py | ActionRequest, ActionResult, Event — the plugs |
| ... | ... |

## Documentation Map
| Folder | Read When |
|---|---|
| docs/core/ | Before writing any code |
| docs/guides/ | Building a specific feature |
| docs/reference/ | Looking up a pattern or convention |
| docs/troubleshooting/ | Something broke or smells wrong |
| docs/examples/ | Need a complete worked example |

## Reading Paths
- Add an API endpoint → docs/guides/API_DEVELOPMENT.md → docs/reference/DECISION_TREES.md
- Add a Flet view → docs/guides/VIEW_DEVELOPMENT.md → docs/guides/WRAPPERS.md
- Something is broken → docs/troubleshooting/TROUBLESHOOTING.md
- Understand the system → docs/core/ARCHITECTURE.md → docs/core/CONVENTIONS.md
- Understand contracts → docs/core/CONTRACTS_GUIDE.md

## Top 5 Conventions That Surprise People
[5 bullets from CONVENTIONS.md]

## Top 3 Anti-Patterns to Avoid
[3 bullets from ANTI_PATTERNS.md]
```

Target length: ~120–150 lines.

---

### YAML Frontmatter Schema

Added to the top of every `.md` file in `docs/` (all subfolders). Five fields:

```yaml
---
title: "Human-readable title"
category: core              # core | guide | reference | troubleshooting | example
audience: [developer, agent]
related:
  - ../core/CONVENTIONS.md
  - ../guides/ADDING_STUFF.md
agent_priority: high        # high | medium | low
---
```

**`agent_priority` rules:**
- `high` — Read proactively before touching related code: ARCHITECTURE, CONVENTIONS, CONTRACTS_GUIDE, TROUBLESHOOTING, ANTI_PATTERNS
- `medium` — Read when working in that area: QUICKSTART, ADDING_STUFF, API_DEVELOPMENT, VIEW_DEVELOPMENT, DECISION_TREES, WRAPPERS, TESTING, VAULT_USAGE
- `low` — Reference lookup only: PONG_EXAMPLE, API_PATTERN_TEMPLATE, API_ARCHITECTURE_SUMMARY, GETTING_STARTED, ONBOARDING_DEPLOYMENT

---

### `DOCS_INDEX.md` Updates

- Add folder structure overview section at the top (after title)
- Update all internal links to new subfolder paths
- Keep all existing reading paths — just fix the file references

---

## Files to Create / Modify

### New Files
| File | Action |
|---|---|
| `CLAUDE.md` | Create — agent master context (~150 lines) |
| `docs/api-docs/api-development.html` | Create — converted from API_DEVELOPMENT.md |
| `docs/api-docs/view-development.html` | Create — converted from VIEW_DEVELOPMENT.md |
| `docs/api-docs/decision-trees.html` | Create — converted from DECISION_TREES.md |
| `docs/api-docs/troubleshooting.html` | Create — converted from TROUBLESHOOTING.md |
| `docs/api-docs/anti-patterns.html` | Create — converted from ANTI_PATTERNS.md |
| `docs/core/` | Create directory |
| `docs/guides/` | Create directory |
| `docs/reference/` | Create directory |
| `docs/troubleshooting/` | Create directory |
| `docs/examples/` | Create directory |

### Files to Move (git mv — preserves history)
| From | To |
|---|---|
| `docs/ARCHITECTURE.md` | `docs/core/ARCHITECTURE.md` |
| `docs/CONVENTIONS.md` | `docs/core/CONVENTIONS.md` |
| `docs/CONTRACTS_GUIDE.md` | `docs/core/CONTRACTS_GUIDE.md` |
| `docs/GETTING_STARTED.md` | `docs/guides/GETTING_STARTED.md` |
| `docs/QUICKSTART.md` | `docs/guides/QUICKSTART.md` |
| `docs/ADDING_STUFF.md` | `docs/guides/ADDING_STUFF.md` |
| `docs/WRAPPERS.md` | `docs/guides/WRAPPERS.md` |
| `docs/API_DEVELOPMENT.md` | `docs/guides/API_DEVELOPMENT.md` |
| `docs/VIEW_DEVELOPMENT.md` | `docs/guides/VIEW_DEVELOPMENT.md` |
| `docs/ONBOARDING_DEPLOYMENT.md` | `docs/guides/ONBOARDING_DEPLOYMENT.md` |
| `docs/DECISION_TREES.md` | `docs/reference/DECISION_TREES.md` |
| `docs/VAULT_USAGE.md` | `docs/reference/VAULT_USAGE.md` |
| `docs/TESTING.md` | `docs/reference/TESTING.md` |
| `docs/API_ARCHITECTURE_SUMMARY.md` | `docs/reference/API_ARCHITECTURE_SUMMARY.md` |
| `docs/TROUBLESHOOTING.md` | `docs/troubleshooting/TROUBLESHOOTING.md` |
| `docs/ANTI_PATTERNS.md` | `docs/troubleshooting/ANTI_PATTERNS.md` |
| `docs/PONG_EXAMPLE.md` | `docs/examples/PONG_EXAMPLE.md` |
| `docs/API_PATTERN_TEMPLATE.md` | `docs/examples/API_PATTERN_TEMPLATE.md` |

### Files to Modify (cross-reference updates)
| File | Changes |
|---|---|
| `docs/DOCS_INDEX.md` | All 18 internal links updated to subfolder paths + folder overview section added |
| `README.md` | All `docs/` links updated to new subfolder paths |
| `ONBOARDING_COMPLETE.md` | All `docs/` links updated |
| Every moved `.md` file | Frontmatter added + internal cross-references updated |
| `docs/api-docs/index.html` | Full hub redesign |
| `docs/api-docs/architecture.html` | Breadcrumb added, header updated |
| `docs/api-docs/template.html` | Breadcrumb added, header updated |
| `docs/api-docs/pong.html` | Breadcrumb added, header updated |
| `docs/api-docs/css/docs.css` | Section accent color variables + section header styles |
| `docs/api-docs/README.md` | File list updated with 5 new pages |

---

## Success Criteria

### HTML Portal
- [ ] Hub shows 3 sections with 8 cards total
- [ ] Each section has color-coded accent border
- [ ] All 5 new pages exist with syntax highlighting and copy buttons
- [ ] Breadcrumb shows correct section on every page
- [ ] Prev/Next navigates within category only
- [ ] All existing pages still work (no broken navigation)
- [ ] Renders correctly on mobile (375px), tablet (768px), desktop

### Folder Structure
- [ ] All 18 `.md` files moved to correct subfolder
- [ ] `git mv` used (not copy+delete) — history preserved
- [ ] All internal cross-references updated and working
- [ ] No 404s in any existing doc link
- [ ] `docs/DOCS_INDEX.md` links all work with new paths

### Agent Documentation
- [ ] `CLAUDE.md` exists at project root
- [ ] All `.md` files in docs/ subfolders have 5-field YAML frontmatter
- [ ] `agent_priority` set correctly on all files
- [ ] `related:` paths use correct relative paths from each file's new location
- [ ] `README.md` links updated

---

## Notes

- Use `git mv` for all file moves — preserves git blame and history
- HTML pages for long guides (TROUBLESHOOTING.md is 1,710 lines) should use `<details>/<summary>` collapsible sections per error category to avoid overwhelming scroll length
- `docs/superpowers/` folder is untouched — internal tooling only
- `ONBOARDING_COMPLETE.md` at root stays at root (historical record)
- `test_wrappers.py` at root is untracked scratch file — not part of this work
