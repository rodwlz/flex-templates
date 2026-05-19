---
title: "Documentation Index"
category: core
audience: [developer, agent]
related: []
agent_priority: high
---
# FlexTemplates 2.0 — Documentation Index

This folder contains everything you need to understand and extend
FlexTemplates 2.0 — a forkable Python framework with a Flet UI, a FastAPI
backend, and a SQLAlchemy data layer, all sharing one process.

---

## Start here

### [ARCHITECTURE.md](core/ARCHITECTURE.md)
**The "you are here" map (5-minute read)**

Layer stack, how a request flows, the core pieces (contracts, services,
registries, EventBus, router), and a file tour. Land here first; jump from
here to the deeper docs.

### [QUICKSTART.md](guides/QUICKSTART.md)
**Boot the project locally**

Set up `.env`, unlock the vault, run the app, run the tests.

### [CONVENTIONS.md](core/CONVENTIONS.md)
**Naming, structure, and contract conventions — the ground truth**

- Vault key patterns and registry name derivation
- Class / method naming rules
- Module structure with placement rules
- Import boundary rules per layer
- Full action reference (every service, every action, every data shape)
- When to use `SimpleService` vs custom `execute()`

Read this before adding new code.

---

## Deep dives

### [CONTRACTS_GUIDE.md](core/CONTRACTS_GUIDE.md)
**How data moves between layers**

The three core contracts (`ActionRequest`, `ActionResult`, `Event`), a real
end-to-end walkthrough (`ConnectionTester`), the HTTP angle (same service
called from Flet and from `/caches/{name}`), the Pong demo, common mistakes,
testing patterns.

### [ADDING_STUFF.md](guides/ADDING_STUFF.md)
**Recipes for common tasks**

Add a SQL database, a cache backend, a view, a service, an API route.
Follow the pattern; the framework handles the wiring.

### [WRAPPERS.md](guides/WRAPPERS.md)
**The simple snap API**

`self.nav.go()`, `self.vault.get()`, `self.events.emit()`, and `SimpleService`
boilerplate-free service definitions. Read before building any new view.

### [VAULT_USAGE.md](reference/VAULT_USAGE.md)
**Encrypted secrets management**

Two-key vault design (master + confirm), all vault actions, real-world
service examples, security notes.

### [PONG_EXAMPLE.md](examples/PONG_EXAMPLE.md)
**Complete worked example**

A pure game engine driven by either a keyboard or a mock neural net — same
code, swap one line. The architecture pitch as runnable code.

### [TESTING.md](reference/TESTING.md)
**Test strategy and patterns**

In-memory SQLite, `FakePage` for view tests, fixture conventions, how to
exercise a service without Flet or a real DB.

---

## Builder guides

The "I'm sitting down to write code right now" docs. Pick the one that
matches the layer you're working in.

### [API_DEVELOPMENT.md](guides/API_DEVELOPMENT.md)
**Build HTTP endpoints — validation, errors, testing**

The canonical shape of a FastAPI route, request validation, mapping
`ActionResult` failures to HTTP status codes, response shaping, testing
endpoints with `TestClient`, and the three operation types
(immediate / staged / approval). Pair with
[API_PATTERN_TEMPLATE.md](examples/API_PATTERN_TEMPLATE.md) for the step-by-step
walkthrough when adding a new entity.

### [VIEW_DEVELOPMENT.md](guides/VIEW_DEVELOPMENT.md)
**Build Flet views — props, event handlers, async**

The props pattern (how views get services), calling services safely from
handlers, error display, async patterns in Flet, and the canonical view
file structure. Read before touching anything under `lib/views/`.

---

## Decision trees

### [DECISION_TREES.md](reference/DECISION_TREES.md)
**When should I use X vs Y?**

Five decision trees with YES/NO branches and concrete code examples:
`SimpleService` vs `StagingService`, immediate vs staged vs approval endpoints,
when to emit an `Event`, new service vs new method, and `SimpleService` vs
custom `execute()`. Skim before designing anything non-trivial.

---

## Troubleshooting & anti-patterns

### [TROUBLESHOOTING.md](troubleshooting/TROUBLESHOOTING.md)
**When things break — 20 common errors with fixes**

Organized by symptom (database errors, import/wiring errors, vault errors,
Flet UI errors, service errors, testing errors), each entry has *what it
means*, *why it happens*, *how to fix*, and *how to prevent*. Ends with a
short "how to debug" playbook for problems not in the list.

### [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md)
**What not to do, and why — 15 anti-patterns with before/after code**

The mistakes new contributors make, grouped by layer (services,
repositories, views, container/wiring). Each anti-pattern shows the broken
code, why it breaks, and the corrected version. Read alongside
[CONVENTIONS.md](core/CONVENTIONS.md) — this is the "why the rules exist" doc.

---

## Documentation Structure

| Folder | Contents |
|---|---|
| `core/` | ARCHITECTURE, CONVENTIONS, CONTRACTS_GUIDE |
| `guides/` | GETTING_STARTED, QUICKSTART, ADDING_STUFF, WRAPPERS, API_DEVELOPMENT, VIEW_DEVELOPMENT, ONBOARDING_DEPLOYMENT |
| `reference/` | DECISION_TREES, VAULT_USAGE, TESTING, API_ARCHITECTURE_SUMMARY |
| `troubleshooting/` | TROUBLESHOOTING, ANTI_PATTERNS |
| `examples/` | PONG_EXAMPLE, API_PATTERN_TEMPLATE |
| `api-docs/` | Interactive HTML documentation portal |

---

## Reading paths

### "I want to use this codebase" — 30 minutes

1. [ARCHITECTURE.md](core/ARCHITECTURE.md) — orient yourself (10 min)
2. [CONVENTIONS.md](core/CONVENTIONS.md) — skim §1-§6 for the rules (10 min)
3. [ADDING_STUFF.md](guides/ADDING_STUFF.md) — find the recipe for what you're adding (10 min)

### "I want to understand the architecture" — 90 minutes

1. [ARCHITECTURE.md](core/ARCHITECTURE.md) — full read (15 min)
2. [CONVENTIONS.md](core/CONVENTIONS.md) — full read (20 min)
3. [CONTRACTS_GUIDE.md](core/CONTRACTS_GUIDE.md) — full read with the walkthrough (30 min)
4. [PONG_EXAMPLE.md](examples/PONG_EXAMPLE.md) — see the LEGO pitch in action (20 min)
5. Skim [tests/test_interfaces.py](../tests/test_interfaces.py) and
   [tests/test_repository_base.py](../tests/test_repository_base.py) for
   runnable specs of the base abstractions (5 min)

### "I'm building an API endpoint" — 60 minutes

1. [CONTRACTS_GUIDE.md](core/CONTRACTS_GUIDE.md) — understand `ActionRequest` / `ActionResult` (15 min)
2. [API_DEVELOPMENT.md](guides/API_DEVELOPMENT.md) — validation, errors, testing, response shaping (25 min)
3. [DECISION_TREES.md](reference/DECISION_TREES.md) — pick immediate vs staged vs approval (5 min)
4. [API_PATTERN_TEMPLATE.md](examples/API_PATTERN_TEMPLATE.md) — copy the recipe and edit (10 min)
5. Skim the service anti-patterns in
   [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md#service-anti-patterns) (5 min)

### "I'm building a Flet view" — 45 minutes

1. [WRAPPERS.md](guides/WRAPPERS.md) — the `nav` / `vault` / `events` snap API (10 min)
2. [VIEW_DEVELOPMENT.md](guides/VIEW_DEVELOPMENT.md) — props pattern, handlers, async (20 min)
3. Skim the view anti-patterns in
   [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md#view-anti-patterns) (10 min)
4. [PONG_EXAMPLE.md](examples/PONG_EXAMPLE.md) — see a complete UI driven by services (5 min)

### "Something is broken" — 5 to 30 minutes

1. [TROUBLESHOOTING.md](troubleshooting/TROUBLESHOOTING.md) — search by error text or symptom
2. If the error isn't listed, jump to
   [TROUBLESHOOTING.md → How to Debug](troubleshooting/TROUBLESHOOTING.md#how-to-debug)
3. If the code "works but smells wrong," check
   [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md) for the layer you're in
4. If you're unsure which pattern to use, run through
   [DECISION_TREES.md](reference/DECISION_TREES.md)

### "I want to extend it" — pick the recipe

- New SQL database → [ADDING_STUFF.md §11](guides/ADDING_STUFF.md)
- New cache backend → [ADDING_STUFF.md §12](guides/ADDING_STUFF.md)
- New Flet view → [VIEW_DEVELOPMENT.md](guides/VIEW_DEVELOPMENT.md) +
  [ADDING_STUFF.md](guides/ADDING_STUFF.md)
- New service → [WRAPPERS.md](guides/WRAPPERS.md) for `SimpleService`,
  [CONVENTIONS.md §7](core/CONVENTIONS.md) for the action reference,
  [DECISION_TREES.md](reference/DECISION_TREES.md) if you're unsure which kind
- New API route → [API_DEVELOPMENT.md](guides/API_DEVELOPMENT.md) +
  [API_PATTERN_TEMPLATE.md](examples/API_PATTERN_TEMPLATE.md), with
  [lib/api/routes/users.py](../lib/api/routes/users.py) as the working template

---

## Coverage by user type

| You are... | Start with | Then read |
|---|---|---|
| A new contributor | [ARCHITECTURE.md](core/ARCHITECTURE.md), [GETTING_STARTED.md](guides/GETTING_STARTED.md) | [CONVENTIONS.md](core/CONVENTIONS.md), [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md) |
| Building an API route | [API_DEVELOPMENT.md](guides/API_DEVELOPMENT.md) | [API_PATTERN_TEMPLATE.md](examples/API_PATTERN_TEMPLATE.md), [DECISION_TREES.md](reference/DECISION_TREES.md) |
| Building a Flet view | [VIEW_DEVELOPMENT.md](guides/VIEW_DEVELOPMENT.md) | [WRAPPERS.md](guides/WRAPPERS.md), [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md#view-anti-patterns) |
| Designing a service | [WRAPPERS.md](guides/WRAPPERS.md), [CONTRACTS_GUIDE.md](core/CONTRACTS_GUIDE.md) | [DECISION_TREES.md](reference/DECISION_TREES.md), [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md#service-anti-patterns) |
| Hitting an error | [TROUBLESHOOTING.md](troubleshooting/TROUBLESHOOTING.md) | [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md) (if pattern is wrong) |
| Writing tests | [TESTING.md](reference/TESTING.md) | [API_DEVELOPMENT.md → Testing Endpoints](guides/API_DEVELOPMENT.md#testing-endpoints) |
| Reviewing code | [CONVENTIONS.md](core/CONVENTIONS.md), [ANTI_PATTERNS.md](troubleshooting/ANTI_PATTERNS.md) | [DECISION_TREES.md](reference/DECISION_TREES.md) |

---

## Quick questions

- **"Which kind of service should I write?"** →
  [DECISION_TREES.md](reference/DECISION_TREES.md) (`SimpleService` vs `StagingService`,
  `SimpleService` vs custom `execute()`).
- **"Should this endpoint be immediate, staged, or approval-required?"** →
  [DECISION_TREES.md](reference/DECISION_TREES.md).
- **"What HTTP status code should I return on a failed `ActionResult`?"** →
  [API_DEVELOPMENT.md → Error Handling](guides/API_DEVELOPMENT.md#error-handling).
- **"How do I show an error from a service in my Flet view?"** →
  [VIEW_DEVELOPMENT.md → Event Handlers](guides/VIEW_DEVELOPMENT.md#event-handlers).
- **"My test says 'database is locked' — what now?"** →
  [TROUBLESHOOTING.md → Database Errors](troubleshooting/TROUBLESHOOTING.md#database-errors).
- **"Why can't my service import another service directly?"** →
  [ANTI_PATTERNS.md → Service Anti-Patterns](troubleshooting/ANTI_PATTERNS.md#service-anti-patterns).

---

## Key principles (in one screen)

1. **Contracts are the boundary.** Layers talk via `ActionRequest` /
   `ActionResult` / `Event`. Inside a layer, do whatever's cheapest.
2. **`SimpleService` is the default.** One method per action, plain dicts as
   returns, free wrapping, free exception trapping.
3. **Registries are global lookup tables.** `ConnectionRegistry`,
   `CacheRegistry`. Exempt from the props-dict rule.
4. **Repositories don't know about contracts.** They return ORM objects;
   services translate.
5. **Views never import services directly.** They get them via the `props`
   dict from the router.
6. **`main.py` is the only file that names concrete types.** Everything else
   programs to interfaces or contracts.
7. **Tests are the spec.** If you can't test through the contract, the
   contract is leaking abstraction.

---

## Project history

The `superpowers/` subfolder contains plans, specs, and audit reports for
each phase of the project — useful if you want to trace why a particular
decision was made. Newcomers can skip it.
