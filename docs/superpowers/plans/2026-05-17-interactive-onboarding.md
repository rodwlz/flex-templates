# FlexTemplates 2.0 — Interactive HTML Onboarding Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page interactive HTML dashboard that serves as the visual entry point to FlexTemplates documentation, helping new users understand the architecture, choose a learning path, and navigate to relevant docs.

**Architecture:** The dashboard is a self-contained HTML file with embedded CSS and vanilla JS. It displays: (1) an interactive architecture layer diagram, (2) three reading paths with time estimates and descriptions, (3) a "What I want to do?" quick-nav section, (4) a data flow visualization showing how requests flow through layers, and (5) links to all documentation files. No build step, no npm dependencies — the file can be opened directly in a browser or served as a static asset.

**Tech Stack:** HTML5, CSS3 (flexbox/grid), vanilla JavaScript (no frameworks), SVG for diagrams.

---

## File Structure

```
docs/
├── onboarding.html          ← Single self-contained dashboard file
├── (all existing docs remain unchanged)
└── superpowers/plans/
    └── 2026-05-17-interactive-onboarding.md  ← This plan
```

The `onboarding.html` file embeds all CSS and JS inline. It references the existing docs via relative links and GitHub URLs as fallbacks.

---

## Task Breakdown

### Task 1: Build the HTML Structure & Layout

**Files:**
- Create: `docs/onboarding.html`

- [ ] **Step 1: Write the HTML skeleton with heading and navigation**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlexTemplates 2.0 — Interactive Onboarding</title>
    <style>
        /* CSS will be added in Task 2 */
    </style>
</head>
<body>
    <nav class="header">
        <div class="header-content">
            <h1>FlexTemplates 2.0</h1>
            <p class="tagline">A LEGO-pattern Python framework: Flet UI + FastAPI + SQLAlchemy</p>
        </div>
    </nav>

    <main class="container">
        <!-- Sections will be added in Tasks 2-5 -->
    </main>

    <footer class="footer">
        <p>&copy; 2026 FlexTemplates. <a href="https://github.com/QuantumWolf-flex-templates">GitHub</a></p>
    </footer>

    <script>
        // JavaScript will be added in Task 5
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify file is created and opens in browser**

```bash
# Create the file
touch docs/onboarding.html

# Open in default browser (or manual: File > Open in your browser)
cat docs/onboarding.html
```

Expected: File created at `docs/onboarding.html`, opens as a blank page with header/footer only.

---

### Task 2: Add CSS Styling (Layout, Colors, Typography)

**Files:**
- Modify: `docs/onboarding.html` (add CSS to `<style>` tag)

- [ ] **Step 1: Add CSS variables, reset, and global styles**

Replace the empty `<style>` block with:

```css
:root {
    --primary: #2563eb;
    --primary-dark: #1e40af;
    --primary-light: #dbeafe;
    --accent: #f59e0b;
    --text: #1f2937;
    --text-light: #6b7280;
    --bg: #ffffff;
    --bg-light: #f9fafb;
    --border: #e5e7eb;
    --success: #10b981;
    --info: #06b6d4;
    --warning: #f97316;
    --layer-bg: #fef3c7;
    --layer-border: #f59e0b;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
}

.header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 2rem 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.header-content {
    max-width: 1200px;
    margin: 0 auto;
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

.tagline {
    font-size: 1.1rem;
    opacity: 0.9;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.section {
    margin-bottom: 3rem;
    scroll-margin-top: 80px;
}

.section h2 {
    font-size: 1.8rem;
    color: var(--primary);
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--border);
}

.section h3 {
    font-size: 1.3rem;
    color: var(--text);
    margin-top: 1.5rem;
    margin-bottom: 1rem;
}

.footer {
    background: var(--bg-light);
    border-top: 1px solid var(--border);
    padding: 2rem 1rem;
    text-align: center;
    margin-top: 3rem;
    color: var(--text-light);
}

.footer a {
    color: var(--primary);
    text-decoration: none;
}

.footer a:hover {
    text-decoration: underline;
}

/* Responsive */
@media (max-width: 768px) {
    .header h1 {
        font-size: 1.8rem;
    }
    
    .tagline {
        font-size: 1rem;
    }
    
    .section h2 {
        font-size: 1.5rem;
    }
}
```

- [ ] **Step 2: Verify styling loads correctly**

Open `docs/onboarding.html` in browser. Expected: Blue header with white text, proper spacing, responsive on mobile.

---

### Task 3: Build the Architecture Diagram Section

**Files:**
- Modify: `docs/onboarding.html` (add architecture section to `<main>`)

- [ ] **Step 1: Add HTML structure for architecture section**

Add this inside `<main class="container">` after the opening tag:

```html
<section class="section" id="architecture">
    <h2>📐 The Architecture — At a Glance</h2>
    <p>FlexTemplates follows a LEGO-block pattern where layers talk via <strong>contracts</strong>, and every piece can be swapped without touching the rest.</p>
    
    <div class="architecture-container">
        <div class="layer-group">
            <div class="layer" data-layer="views">
                <span class="layer-icon">🖼️</span>
                <span class="layer-name">Views</span>
                <span class="layer-desc">Flet pages</span>
            </div>
            <div class="layer" data-layer="api">
                <span class="layer-icon">🔌</span>
                <span class="layer-name">API Routes</span>
                <span class="layer-desc">FastAPI endpoints</span>
            </div>
        </div>

        <div class="arrow">↓</div>

        <div class="layer-group">
            <div class="layer" data-layer="services">
                <span class="layer-icon">⚙️</span>
                <span class="layer-name">Services</span>
                <span class="layer-desc">Business logic</span>
            </div>
            <div class="layer" data-layer="contracts">
                <span class="layer-icon">📋</span>
                <span class="layer-name">Contracts</span>
                <span class="layer-desc">ActionRequest/Result</span>
            </div>
        </div>

        <div class="arrow">↓</div>

        <div class="layer-group">
            <div class="layer" data-layer="repositories">
                <span class="layer-icon">🗄️</span>
                <span class="layer-name">Repositories</span>
                <span class="layer-desc">Data access (CRUD)</span>
            </div>
            <div class="layer" data-layer="adapters">
                <span class="layer-icon">🔄</span>
                <span class="layer-name">Adapters</span>
                <span class="layer-desc">Redis, files, external APIs</span>
            </div>
        </div>

        <div class="arrow">↓</div>

        <div class="layer-group">
            <div class="layer" data-layer="database">
                <span class="layer-icon">💾</span>
                <span class="layer-name">Database</span>
                <span class="layer-desc">SQLAlchemy ORM</span>
            </div>
        </div>
    </div>

    <div class="layer-details" id="layer-info">
        <p style="color: var(--text-light); text-align: center;">Click a layer to learn more</p>
    </div>
</section>
```

- [ ] **Step 2: Add CSS for architecture diagram**

Add to `<style>` block:

```css
.architecture-container {
    margin: 2rem 0;
    padding: 2rem;
    background: var(--bg-light);
    border-radius: 8px;
    border: 1px solid var(--border);
}

.layer-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
}

.layer {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 1.5rem 1rem;
    background: linear-gradient(135deg, var(--layer-bg) 0%, #fef9e7 100%);
    border: 2px solid var(--layer-border);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: center;
}

.layer:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 12px rgba(245, 158, 11, 0.2);
    border-color: var(--accent);
}

.layer-icon {
    font-size: 2rem;
}

.layer-name {
    font-weight: 600;
    color: var(--text);
}

.layer-desc {
    font-size: 0.9rem;
    color: var(--text-light);
}

.arrow {
    text-align: center;
    font-size: 1.5rem;
    color: var(--border);
    margin: 1rem 0;
}

.layer-details {
    margin-top: 2rem;
    padding: 1.5rem;
    background: var(--primary-light);
    border-left: 4px solid var(--primary);
    border-radius: 4px;
    min-height: 100px;
}

@media (max-width: 768px) {
    .architecture-container {
        padding: 1rem;
    }

    .layer-group {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 3: Verify diagram displays correctly**

Open browser. Expected: Golden boxes arranged vertically with arrows, hover effect works, "Click a layer to learn more" message appears.

---

### Task 4: Build the Reading Paths Section

**Files:**
- Modify: `docs/onboarding.html` (add reading paths section)

- [ ] **Step 1: Add HTML for reading paths**

Add after the architecture section:

```html
<section class="section" id="reading-paths">
    <h2>📚 Choose Your Learning Path</h2>
    <p>Pick the path that fits your goals and time budget.</p>

    <div class="paths-container">
        <div class="path-card" id="path-use">
            <div class="path-header use">
                <h3>🚀 Use It (30 min)</h3>
                <span class="path-time">15 min reading + 15 min setup</span>
            </div>
            <p>Get the project running locally and understand the basic architecture.</p>
            <ol>
                <li><a href="ARCHITECTURE.md">ARCHITECTURE.md</a> — 10 min overview</li>
                <li><a href="CONVENTIONS.md">CONVENTIONS.md</a> — Skim §1-§6 (10 min)</li>
                <li><a href="ADDING_STUFF.md">ADDING_STUFF.md</a> — Find your recipe (10 min)</li>
                <li><a href="QUICKSTART.md">QUICKSTART.md</a> — Boot the project (5 min)</li>
            </ol>
            <button class="btn btn-primary" onclick="document.getElementById('quick-nav').scrollIntoView({behavior: 'smooth'})">Start Here</button>
        </div>

        <div class="path-card" id="path-understand">
            <div class="path-header understand">
                <h3>🧠 Understand It (90 min)</h3>
                <span class="path-time">Full deep dive</span>
            </div>
            <p>Master the architecture and be ready to extend anything.</p>
            <ol>
                <li><a href="ARCHITECTURE.md">ARCHITECTURE.md</a> — Full read (15 min)</li>
                <li><a href="CONVENTIONS.md">CONVENTIONS.md</a> — Full read (20 min)</li>
                <li><a href="CONTRACTS_GUIDE.md">CONTRACTS_GUIDE.md</a> — Full + walkthrough (30 min)</li>
                <li><a href="PONG_EXAMPLE.md">PONG_EXAMPLE.md</a> — See it in action (20 min)</li>
                <li>Skim test specs in <code>tests/test_interfaces.py</code> (5 min)</li>
            </ol>
            <button class="btn btn-primary" onclick="window.open('CONTRACTS_GUIDE.md')">Read Now</button>
        </div>

        <div class="path-card" id="path-extend">
            <div class="path-header extend">
                <h3>🔧 Extend It (recipe-based)</h3>
                <span class="path-time">30 min per recipe</span>
            </div>
            <p>Pick a specific task and follow the step-by-step guide.</p>
            <ul>
                <li><strong>New SQL database:</strong> <a href="ADDING_STUFF.md">ADDING_STUFF.md</a> §11</li>
                <li><strong>New cache backend:</strong> <a href="ADDING_STUFF.md">ADDING_STUFF.md</a> §12</li>
                <li><strong>New Flet view:</strong> <a href="ADDING_STUFF.md">ADDING_STUFF.md</a></li>
                <li><strong>New service:</strong> <a href="WRAPPERS.md">WRAPPERS.md</a> + <a href="CONVENTIONS.md">CONVENTIONS.md</a> §7</li>
                <li><strong>New API route:</strong> <a href="ADDING_STUFF.md">ADDING_STUFF.md</a></li>
            </ul>
            <button class="btn btn-primary" onclick="document.getElementById('quick-nav').scrollIntoView({behavior: 'smooth'})">Find a Recipe</button>
        </div>
    </div>
</section>
```

- [ ] **Step 2: Add CSS for path cards**

Add to `<style>` block:

```css
.paths-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin: 2rem 0;
}

.path-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
}

.path-card:hover {
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}

.path-header {
    padding: 1.5rem 1rem;
    color: white;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.path-header h3 {
    margin: 0;
    font-size: 1.3rem;
    color: white;
}

.path-time {
    font-size: 0.9rem;
    opacity: 0.9;
}

.path-header.use {
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
}

.path-header.understand {
    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.path-header.extend {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.path-card ol,
.path-card ul {
    margin: 0;
    padding: 1rem 1.5rem;
    flex-grow: 1;
}

.path-card li {
    margin-bottom: 0.8rem;
    line-height: 1.6;
}

.path-card a {
    color: var(--primary);
    text-decoration: none;
    font-weight: 500;
}

.path-card a:hover {
    text-decoration: underline;
}

.path-card p {
    padding: 1rem 1.5rem 0;
    color: var(--text-light);
}

.btn {
    margin: 1rem 1.5rem;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-block;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
    transform: translateY(-1px);
}

@media (max-width: 768px) {
    .paths-container {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 3: Verify cards display correctly**

Open browser. Expected: Three colored cards side-by-side (cyan/purple/green headers), content lists, buttons are clickable.

---

### Task 5: Build the Quick Navigation & Data Flow Sections

**Files:**
- Modify: `docs/onboarding.html` (add quick-nav and data-flow sections)

- [ ] **Step 1: Add quick-nav HTML**

Add after reading paths section:

```html
<section class="section" id="quick-nav">
    <h2>❓ What Do I Want to Do?</h2>
    <p>Quick links to the right doc based on your goal.</p>

    <div class="quicklinks-grid">
        <a href="QUICKSTART.md" class="quicklink">
            <span class="icon">⚡</span>
            <span class="label">Get Running Locally</span>
        </a>
        <a href="CONTRACTS_GUIDE.md" class="quicklink">
            <span class="icon">📊</span>
            <span class="label">Understand Data Flow</span>
        </a>
        <a href="CONVENTIONS.md" class="quicklink">
            <span class="icon">📏</span>
            <span class="label">Learn the Rules</span>
        </a>
        <a href="ADDING_STUFF.md" class="quicklink">
            <span class="icon">➕</span>
            <span class="label">Add a New Feature</span>
        </a>
        <a href="WRAPPERS.md" class="quicklink">
            <span class="icon">🎁</span>
            <span class="label">Use the Snap API</span>
        </a>
        <a href="VAULT_USAGE.md" class="quicklink">
            <span class="icon">🔐</span>
            <span class="label">Manage Secrets</span>
        </a>
        <a href="TESTING.md" class="quicklink">
            <span class="icon">✅</span>
            <span class="label">Write Tests</span>
        </a>
        <a href="PONG_EXAMPLE.md" class="quicklink">
            <span class="icon">🎮</span>
            <span class="label">See a Complete Example</span>
        </a>
    </div>
</section>
```

- [ ] **Step 2: Add data-flow HTML**

Add after quick-nav section:

```html
<section class="section" id="data-flow">
    <h2>🔄 How Data Flows (Example: Navigation)</h2>
    <p>Here's what happens when a user clicks a button in Flet:</p>

    <div class="flow-diagram">
        <div class="flow-step">
            <div class="step-number">1</div>
            <div class="step-content">
                <h4>User clicks NavButton</h4>
                <code>NavButton("Products", "/products")</code>
            </div>
        </div>

        <div class="flow-arrow">→</div>

        <div class="flow-step">
            <div class="step-number">2</div>
            <div class="step-content">
                <h4>Button calls NavigationService</h4>
                <code>service.execute(ActionRequest(action="visit", data={"url": "/products"}))</code>
            </div>
        </div>

        <div class="flow-arrow">→</div>

        <div class="flow-step">
            <div class="step-number">3</div>
            <div class="step-content">
                <h4>Service publishes Event</h4>
                <code>EventBus.publish(Event(type="nav.route_changed", ...))</code>
            </div>
        </div>

        <div class="flow-arrow">→</div>

        <div class="flow-step">
            <div class="step-number">4</div>
            <div class="step-content">
                <h4>Adapter listens to Event</h4>
                <code>FletNavigationAdapter subscribes; calls page.go()</code>
            </div>
        </div>

        <div class="flow-arrow">→</div>

        <div class="flow-step">
            <div class="step-number">5</div>
            <div class="step-content">
                <h4>Router loads view</h4>
                <code>FletRouter matches "/products" and loads ProductsView</code>
            </div>
        </div>

        <div class="flow-arrow">→</div>

        <div class="flow-step">
            <div class="step-number">6</div>
            <div class="step-content">
                <h4>View renders</h4>
                <code>page.update() — UI painted</code>
            </div>
        </div>
    </div>

    <p style="text-align: center; margin-top: 1.5rem; color: var(--text-light);">
        <strong>Key insight:</strong> NavigationService knows nothing about Flet. FletNavigationAdapter is the only piece with Flet imports. This is the LEGO pattern in action.
    </p>
</section>
```

- [ ] **Step 3: Add CSS for quick-nav and data-flow**

Add to `<style>` block:

```css
.quicklinks-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
}

.quicklink {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, var(--primary-light) 0%, #dbeafe 100%);
    border: 2px solid var(--primary);
    border-radius: 8px;
    text-decoration: none;
    color: var(--primary);
    font-weight: 500;
    transition: all 0.3s ease;
}

.quicklink:hover {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    transform: translateY(-4px);
    box-shadow: 0 8px 12px rgba(37, 99, 235, 0.2);
}

.quicklink .icon {
    font-size: 2rem;
}

.flow-diagram {
    margin: 2rem 0;
    padding: 2rem;
    background: var(--bg-light);
    border-radius: 8px;
    border: 1px solid var(--border);
}

.flow-step {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
    padding: 1rem;
    background: white;
    border-left: 4px solid var(--primary);
    border-radius: 4px;
}

.step-number {
    min-width: 40px;
    width: 40px;
    height: 40px;
    background: var(--primary);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    flex-shrink: 0;
}

.step-content h4 {
    margin: 0 0 0.5rem;
    color: var(--text);
}

.step-content code {
    background: var(--bg-light);
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.85rem;
    color: var(--primary-dark);
    overflow-x: auto;
    display: block;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.flow-arrow {
    text-align: center;
    color: var(--border);
    font-size: 1.2rem;
    margin: 0.5rem 0;
}

@media (max-width: 768px) {
    .quicklinks-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .flow-step {
        flex-direction: column;
    }

    .flow-arrow {
        transform: rotate(90deg);
        margin: 0.25rem 0;
    }
}
```

- [ ] **Step 4: Verify quicklinks and flow diagram display**

Open browser. Expected: Eight blue-bordered icons with labels (responsive grid), flow diagram with numbered steps and code snippets.

---

### Task 6: Add JavaScript Interactivity

**Files:**
- Modify: `docs/onboarding.html` (add JS to `<script>` tag)

- [ ] **Step 1: Add layer click handler**

Replace the empty `<script>` block with:

```javascript
// Architecture layer details
const layerInfo = {
    views: {
        title: "Views (lib/views/)",
        desc: "Flet pages that render the UI. Each view receives services via a props dict and never imports services directly.",
        examples: ["home.py", "admin/databases.py", "admin/caches.py"],
        docs: "See ADDING_STUFF.md and WRAPPERS.md"
    },
    api: {
        title: "API Routes (lib/api/routes/)",
        desc: "FastAPI endpoints that expose services over HTTP. Same services called from Flet are available via REST.",
        examples: ["users.py", "caches.py"],
        docs: "See ADDING_STUFF.md"
    },
    services: {
        title: "Services (lib/services/)",
        desc: "Business logic classes that implement IService. Most subclass SimpleService for automatic action dispatch.",
        examples: ["NavigationService", "ConnectionTester", "CacheTester"],
        docs: "See CONTRACTS_GUIDE.md and CONVENTIONS.md §7"
    },
    contracts: {
        title: "Contracts (lib/contracts/)",
        desc: "Pure Pydantic models (ActionRequest, ActionResult, Event). The standard vocabulary every layer uses.",
        examples: ["ActionRequest", "ActionResult", "Event"],
        docs: "See CONTRACTS_GUIDE.md"
    },
    repositories: {
        title: "Repositories (lib/repositories/)",
        desc: "Data access layer. Every repo extends AbstractRepository[T] and provides CRUD on a domain model.",
        examples: ["UserRepository", "AbstractRepository"],
        docs: "See tests/test_repository_base.py"
    },
    adapters: {
        title: "Adapters (lib/adapters/)",
        desc: "Non-SQL backends. RedisAdapter for caching, FileAdapter for CSV/JSON/Parquet reads.",
        examples: ["RedisAdapter", "FileAdapter"],
        docs: "See ADDING_STUFF.md §12"
    },
    database: {
        title: "Database (lib/database/)",
        desc: "SQLAlchemy ORM layer. SessionFactory manages DB connections; ConnectionRegistry stores named connections.",
        examples: ["SessionFactory", "ConnectionRegistry"],
        docs: "See tests/test_session.py"
    }
};

// Handle layer clicks
document.querySelectorAll('.layer').forEach(layer => {
    layer.addEventListener('click', function() {
        const layerName = this.dataset.layer;
        const info = layerInfo[layerName];
        
        const detailsDiv = document.getElementById('layer-info');
        detailsDiv.innerHTML = `
            <h4 style="margin: 0 0 0.5rem; color: var(--primary);">${info.title}</h4>
            <p style="margin: 0 0 1rem;">${info.desc}</p>
            <p style="margin: 0 0 0.5rem; font-size: 0.9rem;"><strong>Examples:</strong> ${info.examples.join(', ')}</p>
            <p style="margin: 0; font-size: 0.85rem; color: var(--text-light);">${info.docs}</p>
        `;
    });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Track which path was clicked (optional analytics)
document.querySelectorAll('.path-card').forEach(card => {
    card.addEventListener('click', function() {
        const pathId = this.id;
        console.log('Path selected:', pathId);
    });
});

// Mobile menu helper (future enhancement)
function toggleMobileMenu() {
    // Placeholder for mobile nav toggle if needed
}
```

- [ ] **Step 2: Test interactivity in browser**

Open browser and test:
- Click each layer box → details update below
- Click "Start Here", "Read Now" buttons → scroll to target sections
- Hover over cards → visual effects work

Expected: Layer details populate dynamically, buttons scroll smoothly, all interactions are responsive.

---

### Task 7: Add All Documentation Links Footer

**Files:**
- Modify: `docs/onboarding.html` (add comprehensive docs section)

- [ ] **Step 1: Add docs reference section**

Add before closing `</main>` tag:

```html
<section class="section" id="all-docs">
    <h2>📖 All Documentation</h2>
    <p>Complete reference for every aspect of FlexTemplates.</p>

    <div class="docs-grid">
        <div class="doc-card">
            <h4>🏗️ Core Concepts</h4>
            <ul>
                <li><a href="ARCHITECTURE.md">ARCHITECTURE.md</a> — Layer stack & request flow</li>
                <li><a href="CONTRACTS_GUIDE.md">CONTRACTS_GUIDE.md</a> — How layers communicate</li>
                <li><a href="CONVENTIONS.md">CONVENTIONS.md</a> — Rules & patterns (source of truth)</li>
            </ul>
        </div>

        <div class="doc-card">
            <h4>🚀 Getting Started</h4>
            <ul>
                <li><a href="QUICKSTART.md">QUICKSTART.md</a> — Set up & run locally</li>
                <li><a href="ADDING_STUFF.md">ADDING_STUFF.md</a> — Step-by-step recipes</li>
                <li><a href="WRAPPERS.md">WRAPPERS.md</a> — Snap-in API (nav/vault/events)</li>
            </ul>
        </div>

        <div class="doc-card">
            <h4>🔐 Security & Config</h4>
            <ul>
                <li><a href="VAULT_USAGE.md">VAULT_USAGE.md</a> — Encrypted secrets manager</li>
            </ul>
        </div>

        <div class="doc-card">
            <h4>🎮 Examples & Testing</h4>
            <ul>
                <li><a href="PONG_EXAMPLE.md">PONG_EXAMPLE.md</a> — Complete worked example</li>
                <li><a href="TESTING.md">TESTING.md</a> — Test patterns & fixtures</li>
            </ul>
        </div>
    </div>
</section>
```

- [ ] **Step 2: Add CSS for docs grid**

Add to `<style>` block:

```css
.docs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
}

.doc-card {
    padding: 1.5rem;
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    transition: all 0.3s ease;
}

.doc-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-color: var(--primary);
}

.doc-card h4 {
    margin: 0 0 1rem;
    color: var(--primary);
    font-size: 1.1rem;
}

.doc-card ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.doc-card li {
    margin-bottom: 0.75rem;
}

.doc-card a {
    color: var(--primary);
    text-decoration: none;
    font-weight: 500;
}

.doc-card a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .docs-grid {
        grid-template-columns: 1fr;
    }
}
```

- [ ] **Step 3: Verify all docs section displays**

Open browser. Expected: Four cards with documentation links, properly categorized, hover effects work.

---

### Task 8: Test Full Page & Polish

**Files:**
- Verify: `docs/onboarding.html`

- [ ] **Step 1: Test on desktop browser (Chrome/Firefox/Safari)**

Open `docs/onboarding.html` and verify:
- Header displays with gradient
- Architecture diagram loads with clickable layers
- All three path cards visible and buttons work
- Quick-nav grid with 8 icons loads
- Data flow diagram displays with numbered steps
- Docs grid shows all categories
- All links are clickable (open in new tabs)
- Responsive on full screen

Expected: All sections render correctly, no console errors, links work.

- [ ] **Step 2: Test on mobile (DevTools or actual device)**

Use Chrome DevTools responsive mode (iPhone 12/iPad):
- Header scales appropriately
- Cards stack to single column
- Text remains readable
- Buttons are easily tappable (min 44px height)
- No horizontal scrolling
- Flow diagram arrows rotate 90° on mobile

Expected: Fully responsive, no layout breaks, touch-friendly.

- [ ] **Step 3: Validate HTML & CSS**

Run W3C validation (optional but good practice):
```bash
# HTML validation (or use https://validator.w3.org/)
# No major warnings or errors expected

# CSS is embedded, so manual review is fine
# Check for vendor prefixes if needed (not required for modern browsers)
```

Expected: No critical errors, clean markup.

- [ ] **Step 4: Commit the complete file**

```bash
git add docs/onboarding.html
git commit -m "feat: add interactive HTML onboarding dashboard

- Single-page dashboard with no external dependencies
- Architecture diagram with clickable layer details
- Three reading paths (use/understand/extend) with time estimates
- Quick-nav links to all documentation
- Data flow visualization with real example
- Comprehensive documentation reference grid
- Fully responsive design (desktop/tablet/mobile)
- Vanilla HTML5/CSS3/JS (no build step, no npm deps)"
```

Expected: Commit lands cleanly, 1 file changed.

---

### Task 9: Create Deployment Instructions

**Files:**
- Create: `docs/ONBOARDING_DEPLOYMENT.md`

- [ ] **Step 1: Write deployment guide**

```markdown
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

\`\`\`bash
# Place onboarding.html in your /docs folder (GitHub Pages)
# or root folder (Netlify)
# It will be accessible at: https://your-domain.com/onboarding.html
\`\`\`

### Linking from README

Add a link to the onboarding dashboard in your \`README.md\`:

\`\`\`markdown
## 🚀 Getting Started

**New to FlexTemplates?** Start here: [**Interactive Onboarding Dashboard**](docs/onboarding.html)

Or dive into the docs:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 5-min overview
- [QUICKSTART.md](docs/QUICKSTART.md) — Set up locally
\`\`\`

## How It Works

The dashboard uses relative links to open documentation files in the same \`docs/\` directory:

\`\`\`
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
\`\`\`

## Customization

The HTML is a single file with embedded CSS and JavaScript. To customize:

### Change colors

Edit the CSS variables at the top of the \`<style>\` block:

\`\`\`css
:root {
    --primary: #2563eb;        /* Change this to your brand color */
    --accent: #f59e0b;
    /* ... other variables ... */
}
\`\`\`

### Update layer descriptions

Edit the \`layerInfo\` object in the \`<script>\` block to add/modify layer details.

### Add new quick-nav links

Add to the \`.quicklinks-grid\` section:

\`\`\`html
<a href="NEW_DOC.md" class="quicklink">
    <span class="icon">🆕</span>
    <span class="label">New Feature</span>
</a>
\`\`\`

## Browser Compatibility

- **Modern browsers (2022+):** Full support (Chrome, Firefox, Safari, Edge)
- **IE 11:** Not supported (uses CSS Grid, ES6)
- **Mobile browsers:** Full responsive support

## Performance

- **File size:** ~20-25 KB (minified, uncompressed)
- **Load time:** <100ms on most connections
- **Rendering:** Instant (no async JS, no API calls)
- **Offline-capable:** Yes (all content is static HTML)

## Analytics (Optional)

The dashboard includes a placeholder for tracking which learning paths users select:

\`\`\`javascript
document.querySelectorAll('.path-card').forEach(card => {
    card.addEventListener('click', function() {
        const pathId = this.id;
        console.log('Path selected:', pathId);
        // Replace console.log() with your analytics call
    });
});
\`\`\`

To add Google Analytics or similar, insert your tracking code in the \`<head>\` block.

## Troubleshooting

**Links not working?**
- Ensure all \`.md\` files are in the \`docs/\` directory
- Check relative paths (should be just \`FILENAME.md\`, not \`/docs/FILENAME.md\`)

**Styling looks wrong?**
- Try a different browser (CSS Grid support)
- Disable browser extensions that modify CSS
- Clear browser cache (Ctrl+Shift+R / Cmd+Shift+R)

**Responsive layout broken?**
- Check viewport meta tag in \`<head>\`: \`<meta name="viewport" content="width=device-width, initial-scale=1.0">\`
- Test in actual mobile browser or DevTools responsive mode

---

**Last updated:** 2026-05-17
\`\`\`

- [ ] **Step 2: Commit deployment guide**

```bash
git add docs/ONBOARDING_DEPLOYMENT.md
git commit -m "docs: add onboarding dashboard deployment guide"
```

Expected: Commit lands cleanly.
```

