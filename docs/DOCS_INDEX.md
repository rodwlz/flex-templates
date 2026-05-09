# FlexTemplates 2.0 — Documentation Index

This folder contains everything you need to understand and extend
FlexTemplates 2.0 — a forkable Python framework with a Flet UI, a FastAPI
backend, and a SQLAlchemy data layer, all sharing one process.

---

## Start here

### [ARCHITECTURE.md](ARCHITECTURE.md)
**The "you are here" map (5-minute read)**

Layer stack, how a request flows, the core pieces (contracts, services,
registries, EventBus, router), and a file tour. Land here first; jump from
here to the deeper docs.

### [QUICKSTART.md](QUICKSTART.md)
**Boot the project locally**

Set up `.env`, unlock the vault, run the app, run the tests.

### [CONVENTIONS.md](CONVENTIONS.md)
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

### [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md)
**How data moves between layers**

The three core contracts (`ActionRequest`, `ActionResult`, `Event`), a real
end-to-end walkthrough (`ConnectionTester`), the HTTP angle (same service
called from Flet and from `/caches/{name}`), the Pong demo, common mistakes,
testing patterns.

### [ADDING_STUFF.md](ADDING_STUFF.md)
**Recipes for common tasks**

Add a SQL database, a cache backend, a view, a service, an API route.
Follow the pattern; the framework handles the wiring.

### [WRAPPERS.md](WRAPPERS.md)
**The simple snap API**

`self.nav.go()`, `self.vault.get()`, `self.events.emit()`, and `SimpleService`
boilerplate-free service definitions. Read before building any new view.

### [VAULT_USAGE.md](VAULT_USAGE.md)
**Encrypted secrets management**

Two-key vault design (master + confirm), all vault actions, real-world
service examples, security notes.

### [PONG_EXAMPLE.md](PONG_EXAMPLE.md)
**Complete worked example**

A pure game engine driven by either a keyboard or a mock neural net — same
code, swap one line. The architecture pitch as runnable code.

### [TESTING.md](TESTING.md)
**Test strategy and patterns**

In-memory SQLite, `FakePage` for view tests, fixture conventions, how to
exercise a service without Flet or a real DB.

---

## Files in this folder

| File | One-line summary |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The "you are here" map |
| [QUICKSTART.md](QUICKSTART.md) | Boot the project locally |
| [CONVENTIONS.md](CONVENTIONS.md) | Naming + structure + contracts (ground truth) |
| [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) | How layers talk via Pydantic plugs |
| [ADDING_STUFF.md](ADDING_STUFF.md) | Recipes: add DB / cache / view / service / route |
| [WRAPPERS.md](WRAPPERS.md) | `nav` / `vault` / `events` / `SimpleService` snap API |
| [VAULT_USAGE.md](VAULT_USAGE.md) | Vault API + secrets workflow |
| [PONG_EXAMPLE.md](PONG_EXAMPLE.md) | LEGO architecture in 30 lines of code |
| [TESTING.md](TESTING.md) | Test patterns and fixtures |
| [DOCS_INDEX.md](DOCS_INDEX.md) | This file |
| `superpowers/` | Plans, specs, and audit reports tracking the project's history |

---

## Reading paths

### "I want to use this codebase" — 30 minutes

1. [ARCHITECTURE.md](ARCHITECTURE.md) — orient yourself (10 min)
2. [CONVENTIONS.md](CONVENTIONS.md) — skim §1-§6 for the rules (10 min)
3. [ADDING_STUFF.md](ADDING_STUFF.md) — find the recipe for what you're adding (10 min)

### "I want to understand the architecture" — 90 minutes

1. [ARCHITECTURE.md](ARCHITECTURE.md) — full read (15 min)
2. [CONVENTIONS.md](CONVENTIONS.md) — full read (20 min)
3. [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) — full read with the walkthrough (30 min)
4. [PONG_EXAMPLE.md](PONG_EXAMPLE.md) — see the LEGO pitch in action (20 min)
5. Skim [tests/test_interfaces.py](../tests/test_interfaces.py) and
   [tests/test_repository_base.py](../tests/test_repository_base.py) for
   runnable specs of the base abstractions (5 min)

### "I want to extend it" — pick the recipe

- New SQL database → [ADDING_STUFF.md §11](ADDING_STUFF.md)
- New cache backend → [ADDING_STUFF.md §12](ADDING_STUFF.md)
- New Flet view → [ADDING_STUFF.md](ADDING_STUFF.md)
- New service → [WRAPPERS.md](WRAPPERS.md) for `SimpleService`,
  [CONVENTIONS.md §7](CONVENTIONS.md) for the action reference
- New API route → [ADDING_STUFF.md](ADDING_STUFF.md) plus
  [lib/api/routes/users.py](../lib/api/routes/users.py) as a template

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
