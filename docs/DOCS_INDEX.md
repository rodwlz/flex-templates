# FlexTemplates 2.0 — Documentation Index

## Overview

This folder contains everything you need to understand and implement FlexTemplates 2.0 — a LEGO-style Python fullstack framework.

---

## Start Here

### [QUICKSTART.md](QUICKSTART.md)
**5-minute overview + cheat sheet**
- The 5-line architecture
- The 3 core contracts
- Common tasks (add endpoint, add view, add service)
- File organization
- Debugging checklist
- Read this first if you're in a hurry

### [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md)
**Deep dive into contracts (Pydantic models)**
- What contracts are and why they matter
- The three core contracts: ActionRequest, ActionResult, Event
- How contracts flow through the system
- The Pong example (keyboard OR neural net, same engine)
- How to write your own contracts
- Testing with contracts
- Common mistakes to avoid
- Read this to understand how data moves through the system

### [DI_GUIDE.md](DI_GUIDE.md)
**Dependency Injection explained**
- What DI is and why it matters
- The dependency-injector library
- Provider types (Singleton, Factory, Callable)
- FlexTemplates 2.0 container structure
- Using the container in FastAPI, Flet, and tests
- Common DI patterns
- Read this to understand how pieces are wired together

### [PONG_EXAMPLE.md](PONG_EXAMPLE.md)
**Complete worked example: Pong in FlexTemplates 2.0**
- Problem: building the same game for keyboard, API, and RL training
- Step-by-step implementation:
  1. Define contracts (PongState, PongInput)
  2. Build pure engine (no dependencies)
  3. Write input adapters (keyboard, neural net)
  4. Wrap in service (ActionRequest/ActionResult)
  5. Expose via API
  6. Training loop for RL
- How different input sources drive the same engine
- Why this architecture is so powerful
- Read this to see a complete working example

### [WRAPPERS.md](WRAPPERS.md)
**The simple snap API — nav, vault, events, SimpleService**
- The model → wrapper → snap pattern explained
- `self.nav.go()`, `self.vault.get()`, `self.events.emit()`
- `SimpleService` — write services without match-statement boilerplate
- Full worked example using all three snaps together
- Read this before building any new view or service

### [VAULT_USAGE.md](VAULT_USAGE.md)
**How to retrieve secrets from code**
- Vault architecture (two-key design, encrypted on disk)
- All vault actions (get, set, delete, list_keys, save, lock, unlock, status)
- Real-world examples: database service, API client, view code
- Error handling and state machine
- Testing secrets
- Security best practices
- Read this to integrate vault into your services

---

## Architecture & Implementation

### [C:\Users\rodwlz\.claude\plans\refactored-wibbling-forest.md](C:\Users\rodwlz\.claude\plans\refactored-wibbling-forest.md)
**The official implementation plan**
- Complete folder structure
- Core interfaces (ABCs)
- DI container design
- Config & vault system
- Entry point boot sequence
- Migration map (v1 → v2)
- 6-phase build order
- Handoff notes for Sonnet/Opus
- Use this as the authoritative design document

---

## Memory & Context

Your memory files (in `.claude/projects/e--QuantumWolf-flex-templates/memory/`) contain:

- **user_philosophy.md** — Your LEGO philosophy, security philosophy, use cases
- **current_codebase_snapshot.md** — What works/broken in the current v1 code
- **component_audit.md** — Save/Improve/Rewrite verdict for every v1 module
- **feedback_code_philosophy.md** — Your coding principles (small readable code, error handling)

These auto-load in future conversations for context.

---

## Learning Path

### Path 1: Quick Understanding (1 hour)

1. Read [QUICKSTART.md](QUICKSTART.md) (10 min)
2. Skim [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) contracts section (15 min)
3. Read [PONG_EXAMPLE.md](PONG_EXAMPLE.md) (20 min)
4. Review the plan's "Data Flows" section (15 min)

### Path 2: Deep Understanding (3 hours)

1. Read [QUICKSTART.md](QUICKSTART.md) (15 min)
2. Read [CONTRACTS_GUIDE.md](CONTRACTS_GUIDE.md) fully (45 min)
3. Read [DI_GUIDE.md](DI_GUIDE.md) fully (45 min)
4. Read [PONG_EXAMPLE.md](PONG_EXAMPLE.md) fully (30 min)
5. Review the plan's entire structure (30 min)
6. Sketch out your first service on paper (15 min)

### Path 3: Implementation Ready (4 hours)

1. Complete Path 2
2. Read the architecture plan fully (60 min)
3. Read component_audit.md and understand migration map (30 min)
4. Walk through Phase 1 of build order and understand dependencies (15 min)
5. For each file in Phase 1, sketch its structure before implementation (30 min)

---

## Quick Reference

### The Three Contracts

```python
# Request: "I want to do something"
ActionRequest(action="create_user", data={"username": "alice"})

# Result: "Here's what happened"
ActionResult(success=True, data={"id": 42}, events=[Event(...)])

# Event: "Something happened, listeners should react"
Event(type="user.created", payload={"id": 42})
```

### The Three Layers

```
[View / API endpoint] ← ActionRequest/Result contracts → [Service]
                                                          ↓ uses
                                                      [Repository]
                                                          ↓ operates on
                                                      [ORM/Database]
```

### The DI Container

```python
# Define once
class Container:
    config = Singleton(AppConfig)
    user_repo = Factory(UserRepository, session=...)
    user_service = Factory(UserService, repo=user_repo)

# Use in FastAPI
@inject
async def endpoint(service = Depends(Provide[Container.user_service])):
    ...

# Use in Flet
props = {"user_service": container.user_service()}

# Use in tests (manually, no container)
service = UserService(repository=mock_repo, event_bus=mock_bus)
```

### File Organization

```
flex_app/
├── contracts/         # Pydantic models (pure data)
├── core/              # Interfaces (ABCs) + EventBus
├── config/            # Settings + vault
├── database/          # SQLAlchemy setup
├── models/            # ORM tables
├── repositories/      # Data access
├── services/          # Business logic
├── api/               # FastAPI routes
├── ui/                # Flet components + layout
├── views/             # Flet page modules
├── container.py       # DI wiring
└── main.py            # Boot sequence
```

---

## Key Principles

1. **Contracts are the boundaries** — Everything flows through ActionRequest/ActionResult
2. **Services are pure** — They receive contracts, return contracts; they don't know about UI/API/DB
3. **Repositories hide DB** — Services call repositories, not the database directly
4. **Everything is injected** — No imports of concrete classes except in container.py
5. **Tests are manual** — Tests wire mocks directly; they never use the container
6. **Code is small** — Each file does one thing, fits on one screen
7. **LEGO plugs** — Change any input/output adapter without touching the logic

---

## Common Tasks

**Add a new API endpoint:**
1. Create a service method in services/
2. Add a FastAPI route in api/routes/
3. Wire the service in container.py

**Add a new Flet view:**
1. Create views/my_view.py with `def view(page, props):`
2. URL /my_view automatically routes to it
3. Services are passed in props dict

**Add a new service:**
1. Create repositories/my_repository.py
2. Create services/my_service.py
3. Wire both in container.py

**Test a service:**
1. Create tests/test_my_service.py
2. Mock the repository with unittest.mock
3. Wire mocks manually (no container)

---

## Build Order (6 Phases)

### Phase 1 — Foundation
Contracts, config, vault, EventBus, DI skeleton.
Files: `contracts/base.py`, `core/interfaces.py`, `core/events.py`, `config/settings.py`, `config/vault.py`, `container.py` skeleton

### Phase 2 — Database & Services
UserService tested with no Flet, no FastAPI.
Files: `database/`, `models/user.py`, `repositories/`, `services/user_service.py`

### Phase 3 — NavigationService
Full browser-like history, zero Flet.
Files: `services/navigation_service.py`

### Phase 4 — FastAPI Backend
API endpoints with DI-injected services.
Files: `api/server.py`, `api/router_registry.py`, `api/routes/`

### Phase 5 — Flet UI Layer
App boots, navigation works, views render.
Files: `ui/`, `views/`, `main.py`

### Phase 6 — Pong Demo
Validates the full LEGO architecture.
Files: `games/`

---

## FAQ

**Q: Do I have to read all of this?**
A: No. Read QUICKSTART.md first (5 min). If you want to implement, read CONTRACTS_GUIDE.md and DI_GUIDE.md (90 min total). If you want to really understand, read everything.

**Q: Can I start implementing without reading?**
A: You can, but you'll hit the same questions the documentation answers. Better to invest 1-2 hours upfront than debug later.

**Q: Which guide explains Services best?**
A: CONTRACTS_GUIDE.md shows data flow through services. PONG_EXAMPLE.md shows a complete service. DI_GUIDE.md explains how services get their dependencies.

**Q: I'm confused about contracts. Where do I start?**
A: Read the "What Are Contracts?" section of CONTRACTS_GUIDE.md, then the Pong example. Contracts click once you see them in action.

**Q: Can I use this architecture with different tech (Django, Flask, Streamlit)?**
A: Yes. The contracts and services layer are pure Python. You can swap the API framework (FastAPI → Flask) or UI framework (Flet → Streamlit) and the core logic stays identical.

**Q: Isn't this over-engineered?**
A: For a simple script, yes. For something you'll hand off, modify, test, or expand — no. This architecture shines when you have multiple frontends (UI + API + RL trainer), tests that can't rely on a database, or changes that shouldn't ripple through the codebase.

**Q: Where do I start implementing?**
A: Phase 1 of the plan — contracts + config + vault + EventBus. These are foundational; everything else depends on them.

---

## Getting Help

- **Architecture questions?** → Review the plan
- **Contracts confusion?** → CONTRACTS_GUIDE.md + PONG_EXAMPLE.md
- **DI confusion?** → DI_GUIDE.md + PONG_EXAMPLE.md
- **How do I add X?** → QUICKSTART.md "Common Tasks"
- **What files do I need?** → The plan's folder structure
- **What's the build order?** → Phase 1-6 above

---

## Files in This Folder

- **QUICKSTART.md** — 5-minute overview + cheat sheet
- **CONTRACTS_GUIDE.md** — Deep dive into Pydantic contracts
- **DI_GUIDE.md** — Deep dive into dependency injection
- **PONG_EXAMPLE.md** — Complete worked example
- **WRAPPERS.md** — Simple snap API (nav / vault / events / SimpleService)
- **VAULT_USAGE.md** — Vault API reference + examples
- **DOCS_INDEX.md** — This file
