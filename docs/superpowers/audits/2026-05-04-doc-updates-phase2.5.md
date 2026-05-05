# Documentation Updates — Phase 2.5 Tracking

**Date:** 2026-05-04  
**Status:** Deferred. These updates do NOT block Phase 2 — code is correct, docs are aspirational/drifted.

---

## DI_GUIDE.md

**Reality check:**
- The codebase does **NOT use the `dependency_injector` library** or a DI container pattern
- `main.py` performs **direct wiring** without a container — it instantiates services directly and passes them to adapters
- `FletRouter.set_props_factory()` receives a callable that returns a dict of services — this is **manual wiring**, not container injection
- Services receive dependencies through constructors, which is genuine DI, but no container automates it
- There is **NO `lib/container.py`** file in the codebase
- No `@inject` decorators or `Depends(Provide[...])` patterns exist in the actual code
- No `dependency_injector` imports anywhere except docs

**What's wrong in the doc:**
- Entire sections 2-6 (lines 102-349) describe a `Container` class that does not exist
- Section "The DI Container (dependency-injector library)" (lines 102-127) — completely aspirational, never implemented
- "FlexTemplates 2.0 Container" section (lines 160-218) — describes a container.py file with DeclarativeContainer syntax that is not in the codebase
- "Using the Container in Code" → FastAPI example (lines 232-252) — uses `@inject` and `Depends(Provide[...])` which are not used anywhere
- "Wiring the Container" section (lines 323-348) — describes `container.wire()` call that never happens
- Real code in `main.py` (lines 56-90) shows direct instantiation and lambda-based props factories, not container patterns

**What's still valid:**
- Conceptual sections 1 and "The Problem DI Solves" (lines 3-99) — explain DI philosophy correctly and apply to the codebase
- "Rules of Thumb" section (lines 534-554) — accurately describes what the codebase does (pass dependencies, don't create them)
- The final summary (lines 557-567) — correctly identifies FlexTemplates as DI-based and LEGO-compatible
- Example services like `NavigationService` DO receive EventBus through constructor (genuine DI), so dependency-passing patterns are correct

**Effort to fix:** 4-5 hours
- Delete or replace sections 102-349 (container library, wiring, FastAPI examples)
- Rewrite "Using the Container in Code" to show actual `main.py` direct wiring pattern with FletRouter props factory
- Keep conceptual intro and rules
- Update examples to match real services (NavigationService, VaultService, ConnectionTester, etc.)
- Show how views receive services via props dict, not through decorators

**Priority:** Medium
- The conceptual material is valuable; guides developers correctly on the principle
- But misleading examples could waste time when implementing — developers would try to use `dependency_injector` and find it missing
- Should be fixed early in Phase 2.5 to prevent confusion during onboarding

---

## CONTRACTS_GUIDE.md

**Reality check:**
- The codebase **DOES use Pydantic-based contracts** as described
- `ActionRequest`, `ActionResult`, and `Event` exist in `lib/contracts/base.py` and match the guide exactly
- Services do implement `execute(request: ActionRequest) -> ActionResult` pattern
- Real services: `NavigationService`, `CacheRegistry`, `ConnectionTester`, `CacheTester`, `SchemaInspector`
- No `UserService` class exists anywhere in the codebase (only in docs and comments)
- Import paths in examples use `lib.` prefix, which is correct (main.py confirms no `flex_app.` in current code)

**What's wrong in the doc:**
- **Line 9, 21, 39, 44, 193, 298**: All examples use `UserService` class which does NOT exist in the codebase
- Lines 44-56, 184-221, 254-283: Multiple extended examples built around `UserService` — they create false expectations
- Pages 243-246 reference a `UserRepository` that doesn't exist in actual code
- Lines 232-252: Example of repository with `IRepository` interface — does exist (in lib/core/interfaces.py) but no actual UserRepository implementation
- No running example service is shown that developers can examine in the actual codebase

**What's still valid:**
- The three core contracts section (lines 69-139) — `ActionRequest`, `ActionResult`, `Event` are 100% accurate
- "How Contracts Flow Through the System" conceptual diagram (lines 291-329) — architecture is correct
- "How to Write Your Own Contracts" section (lines 441-571) — methodology is correct
- "Common Mistakes to Avoid" (lines 506-567) — all advice applies to real code
- "Testing with Contracts" (lines 571-602) — test pattern is correct

**Effort to fix:** 3-4 hours
- Replace all `UserService` examples with real services from codebase (NavigationService, ConnectionTester, CacheTester)
- Remove UserRepository examples or document that it's a template (no actual user model in v2)
- Keep the three core contracts section as-is
- Keep "How to Write Your Own Contracts" and testing sections — they're accurate
- Update import paths to match real package structure if any drift detected (brief scan shows `lib.` is correct)

**Priority:** High
- A new developer following the UserService examples will find nothing to examine in the code
- The pattern is correct but the examples are aspirational — causes confusion and wasted time searching for non-existent classes
- Real services are simple enough to use as examples (NavigationService is ~50 lines)

---

## PONG_EXAMPLE.md

**Reality check:**
- `games/` directory **DOES exist** with actual game files
- Files present: `contracts.py`, `engine.py`, `keyboard_adapter.py`, `mock_neural_adapter.py`, `view.py`, `__init__.py`
- Actual import paths are `from games.` not `flex_app.games` (or `from flex_app.games`)
- The game engine, adapters, and contracts described in the doc **do exist and match the specification**
- `PongState` and `PongInput` contracts exist in `games/contracts.py`
- `PongEngine` exists in `games/engine.py`
- `KeyboardAdapter` exists in `games/keyboard_adapter.py`
- `MockNeuralAdapter` exists (there is no "NeuralAdapter" but a "MockNeuralAdapter" for testing)
- `games/view.py` integrates everything and can be run standalone

**What's wrong in the doc:**
- Line 140: `class KeyboardAdapter` → actually exists, but example methods are simplified; real code has different method names (`on_key_down`, `on_key_up` vs. simplified `on_key` in example)
- Line 188: `class NeuralAdapter` → does NOT exist; codebase has `MockNeuralAdapter` instead (lines 187-227 describe a non-existent class)
- Lines 319-358: Training loop example (`train.py`) does NOT exist in games/ directory
- Line 57: `from games.contracts import` → correct, but the example shows `from games.contracts` whereas the import path in actual view.py is `from games.contracts`
- Line 28: import example shows `from games.contracts` which is correct, but some earlier text might reference `flex_app.games`

**What's still valid:**
- File structure (lines 431-442) — matches reality, just add `mock_neural_adapter.py` to the list
- Step 1-3 (contracts, pure engine, keyboard adapter) — all exist and work as documented
- Steps 5-7 (service wrapper, API endpoint, training loop) — concepts are valid but code examples don't exist yet
- Testing section (lines 448-489) — matches the pattern (tests can run without Flet)
- The LEGO philosophy explanation (lines 403-427) — accurate and the real code validates it

**Effort to fix:** 2-3 hours
- Update line 140+ KeyboardAdapter example to match actual method signatures (`on_key_down`, `on_key_up`)
- Replace NeuralAdapter section (lines 188-227) with actual MockNeuralAdapter code (or note that it's for testing/mocking)
- Note that train.py doesn't exist (was aspirational example for RL training)
- Verify import paths are all `games.` not `flex_app.games` (brief scan shows they are correct)
- Update file structure list to include `mock_neural_adapter.py`
- Add a note that PongService, pong.py, and train.py are future work (not yet implemented)

**Priority:** Medium
- The doc is MOSTLY correct — the game code exists and works as described
- Only step 4 (NeuralAdapter) is significantly wrong; step 5-7 are aspirational but not blocking
- Developers can actually run `flet run games/view.py` and see the LEGO pattern work
- But misleading example class names (NeuralAdapter vs. MockNeuralAdapter) should be corrected

---

## Summary

| Doc | Blocks Phase 2? | Drift Severity | Effort | Priority |
|-----|-----------------|-----------------|--------|----------|
| DI_GUIDE.md | No | High (container doesn't exist) | 4-5h | Medium |
| CONTRACTS_GUIDE.md | No | Medium (UserService doesn't exist) | 3-4h | High |
| PONG_EXAMPLE.md | No | Low (code mostly correct) | 2-3h | Medium |

**Total estimated effort:** 9-12 hours

**Key findings:**
1. **DI_GUIDE.md** describes an aspirational DI container system never implemented. The actual code does genuine DI (dependency passing) but without a container library. This is the biggest drift.
2. **CONTRACTS_GUIDE.md** is conceptually correct but uses non-existent UserService examples throughout. The pattern is valid; the examples just don't exist.
3. **PONG_EXAMPLE.md** is mostly accurate. The game code exists and validates the LEGO architecture. Only NeuralAdapter and training loop are aspirational.

**Recommended Phase 2.5 order:**
1. **Fix CONTRACTS_GUIDE.md first** — high priority, impact on developer clarity (swap UserService for real services)
2. **Fix PONG_EXAMPLE.md second** — medium priority, lower effort, corrects working example (update adapter names, note missing pieces)
3. **Fix DI_GUIDE.md last** — medium priority but larger effort, conceptual rewrite (replace container sections with actual main.py pattern)

**Not blocking Phase 2 because:**
- The code is correct and working (services, contracts, LEGO architecture all validated)
- Docs are aspirational/descriptive of a pattern, not prescriptive instructions being followed
- Developers can learn from CONVENTIONS.md, QUICKSTART.md, and examining actual code
- Phase 2 completion does not depend on these three docs being rewritten
