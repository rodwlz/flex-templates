# Troubleshooting Guide — FlexTemplates 2.0

When things break, this is where you find the fix. Each error has:
- **What it means** — Plain English
- **Why it happens** — The root cause
- **How to fix** — Step-by-step solution with code
- **How to prevent** — Best practice to avoid it next time

---

## Table of Contents

1. [Database Errors](#database-errors)
2. [Import & Wiring Errors](#import--wiring-errors)
3. [Vault & Configuration Errors](#vault--configuration-errors)
4. [Flet UI Errors](#flet-ui-errors)
5. [Service Errors](#service-errors)
6. [Testing Errors](#testing-errors)
7. [How to Debug](#how-to-debug)

---

## Database Errors

### "database is locked"

**What it means:** SQLite is already in use by another process and can't handle concurrent writes.

**Why it happens:**
- Multiple test workers trying to write to the same SQLite file simultaneously
- The dev app running while you try to run tests
- A background task or server still holding the database connection

**How to fix:**

1. **Stop the dev app:**
   ```bash
   # Kill any running python main.py processes
   # Windows:
   taskkill /IM python.exe /F
   # macOS/Linux:
   pkill -f "python main.py"
   ```

2. **Run tests in serial mode** (not parallel):
   ```bash
   pytest tests/ -v  # -v shows each test
   # Do NOT use pytest-xdist with SQLite:
   pytest tests/ -n auto  # ❌ WRONG for SQLite
   ```

3. **Use in-memory database** for tests (recommended in conftest.py):
   ```python
   # tests/conftest.py
   @pytest.fixture
   def db_factory():
       factory = SessionFactory("sqlite:///:memory:")  # ← in-memory, not file
       factory.create_tables(Base)
       return factory
   ```

**How to prevent:**
- Always use in-memory SQLite for tests: `sqlite:///:memory:`
- In production, use PostgreSQL (no file locking issues)
- Kill old processes before running tests: `pgrep python | xargs kill -9`

---

### "no such table: users"

**What it means:** The database schema doesn't match your code — a table is missing.

**Why it happens:**
- Forgot to run migrations after changing a model
- Created a new ORM model but haven't created the table yet
- Using a fresh SQLite file without bootstrapping the schema

**How to fix:**

1. **Create tables immediately** (dev environment):
   ```python
   from lib.database.session import SessionFactory
   from lib.database.base import Base
   
   factory = SessionFactory("sqlite:///dev.db")
   factory.create_tables(Base)  # ← creates all missing tables
   print("✓ Tables created")
   ```

2. **Or use Alembic** (for tracked migrations):
   ```bash
   # Create a migration for new changes
   alembic revision --autogenerate -m "add users table"
   
   # Apply it
   alembic upgrade head
   
   # Verify it worked
   sqlite3 dev.db ".tables"
   ```

3. **Check what tables exist:**
   ```python
   from lib.database.session import SessionFactory
   
   factory = SessionFactory("sqlite:///dev.db")
   with factory.session() as s:
       result = s.execute(
           "SELECT name FROM sqlite_master WHERE type='table'"
       )
       print([row[0] for row in result])
   ```

**How to prevent:**
- After editing any ORM model (`lib/models/`), always run migrations:
  ```bash
  alembic revision --autogenerate -m "describe your change"
  alembic upgrade head
  ```
- In tests, use `factory.create_tables(Base)` in conftest.py so the schema is fresh every test run
- Add a smoke test that verifies core tables exist:
  ```python
  def test_schema_has_users_table(db_factory):
      with db_factory.session() as s:
          result = s.execute("SELECT COUNT(*) FROM users")
          # If this doesn't crash, table exists
  ```

---

### "UNIQUE constraint failed: users.username"

**What it means:** You tried to insert or update a row with a duplicate value in a unique column.

**Why it happens:**
- Your code tries to create a user with a username that already exists
- You forgot to check if a record exists before creating it
- A test didn't clean up after itself and left duplicate data

**How to fix:**

1. **Check before creating:**
   ```python
   from lib.repositories.user_repository import UserRepository
   from lib.database.session import SessionFactory
   
   factory = SessionFactory("sqlite:///dev.db")
   repo = UserRepository(factory)
   
   # Check first
   existing = repo.list(username="alice")
   if existing:
       print(f"User 'alice' already exists with id {existing[0].id}")
   else:
       user = repo.create({"username": "alice", "email": "alice@example.com"})
       print(f"Created user {user.id}")
   ```

2. **Handle the error gracefully:**
   ```python
   from sqlalchemy.exc import IntegrityError
   from lib.services.user_service import UserService
   
   service = UserService(factory)
   try:
       user = service.create_user("alice", "alice@example.com")
   except IntegrityError as e:
       if "UNIQUE constraint" in str(e):
           print("Error: Username already taken")
       else:
           raise
   ```

3. **In a service method:**
   ```python
   def create(self, data: dict) -> dict:
       repo = UserRepository(self._factory)
       
       # Check if username is taken
       existing = repo.list(username=data["username"])
       if existing:
           raise ValueError(f"Username '{data['username']}' is already taken")
       
       # Now safe to create
       user = repo.create(data)
       return {"id": str(user.id), "username": user.username}
   ```

**How to prevent:**
- Always validate before creating:
  ```python
  # In your service, before repo.create():
  existing = repo.list(username=data["username"])
  if existing:
      raise ValueError(f"Username taken")
  ```
- In tests, use unique data per test:
  ```python
  import uuid
  
  def test_create_user():
      unique_name = f"user_{uuid.uuid4()}"
      user = service.create_user(unique_name, "test@example.com")
      assert user["username"] == unique_name
  ```
- Add database constraints in your ORM model (SQLAlchemy will catch them):
  ```python
  class User(Base):
      __tablename__ = "users"
      username: Mapped[str] = mapped_column(String, unique=True, index=True)
  ```

---

### "FOREIGN KEY constraint failed"

**What it means:** You tried to create/update a row that references a non-existent parent row.

**Why it happens:**
- You assigned a role_id to a user, but that role doesn't exist
- You tried to delete a role that has users assigned to it
- A fixture forgot to create the parent record before using it

**How to fix:**

1. **Verify parent exists before creating child:**
   ```python
   from lib.repositories.user_repository import UserRepository
   from lib.repositories.role_repository import RoleRepository
   from lib.database.session import SessionFactory
   
   factory = SessionFactory("sqlite:///dev.db")
   user_repo = UserRepository(factory)
   role_repo = RoleRepository(factory)
   
   # Create parent first
   role = role_repo.create({"name": "admin", "description": "Administrator"})
   print(f"Created role: {role.id}")
   
   # Now safe to reference it
   user = user_repo.create({
       "username": "alice",
       "email": "alice@example.com",
       "password_hash": "...",
       "salt": "...",
   })
   user_repo.add_role(user.id, role.id)
   print(f"Assigned role to user")
   ```

2. **Check foreign key constraint in your model:**
   ```python
   from sqlalchemy import Column, ForeignKey, String, Table, Uuid
   
   class User(Base):
       __tablename__ = "users"
       role_id: Mapped[uuid.UUID] = mapped_column(
           Uuid, 
           ForeignKey("roles.id", ondelete="CASCADE"),  # ← constraint
           nullable=True
       )
   ```

3. **When deleting, cascade or re-assign:**
   ```python
   # Option 1: The model uses ondelete="CASCADE" — children auto-delete
   # Option 2: Manually re-assign before deleting
   
   role_id_to_delete = "..."
   users_with_role = user_repo.list(role_id=role_id_to_delete)
   for user in users_with_role:
       user_repo.update(user.id, {"role_id": None})
   
   # Now safe to delete
   role_repo.delete(role_id_to_delete)
   ```

**How to prevent:**
- In tests, use fixtures that create parents first:
  ```python
  @pytest.fixture
  def role(db_factory):
      repo = RoleRepository(db_factory)
      return repo.create({"name": "admin", "description": "Admin role"})
  
  @pytest.fixture
  def user_with_role(db_factory, role):
      repo = UserRepository(db_factory)
      user = repo.create({...})
      repo.add_role(user.id, role.id)
      return user
  ```
- In your ORM model, use `ondelete="CASCADE"` or `ondelete="SET NULL"` to auto-cleanup:
  ```python
  role_id: Mapped[uuid.UUID] = mapped_column(
      Uuid,
      ForeignKey("roles.id", ondelete="CASCADE")  # ← auto-delete if role deleted
  )
  ```

---

## Import & Wiring Errors

### "ModuleNotFoundError: No module named 'lib'"

**What it means:** Python can't find the `lib` package. The project isn't installed.

**Why it happens:**
- You didn't run `pip install -e .` in the project root
- You're running Python from the wrong directory
- The `pyproject.toml` file is missing or malformed

**How to fix:**

1. **Install the package in editable mode:**
   ```bash
   cd /path/to/flex-templates
   pip install -e .
   ```
   The `-e` flag means "editable" — Python will look in the current directory, not site-packages.

2. **Verify the install:**
   ```bash
   python -c "import lib; print(lib.__file__)"
   ```
   If it prints a path inside the project, you're good.

3. **Check pyproject.toml exists:**
   ```bash
   ls -la pyproject.toml  # Should exist
   ```

4. **If still broken, reinstall:**
   ```bash
   pip uninstall flex-templates
   pip install -e .
   ```

**How to prevent:**
- Always run `pip install -e .` after cloning:
  ```bash
  git clone <repo>
  cd flex-templates
  pip install -e .
  python main.py
  ```
- Add a smoke test to your CI:
  ```bash
  python -c "from lib.services.user_service import UserService; print('✓ Imports work')"
  ```

---

### "ImportError: cannot import name 'UserService' from 'lib.services'"

**What it means:** The module exists, but the class isn't exported from it.

**Why it happens:**
- You renamed the class but forgot to update imports elsewhere
- The class is defined but not exported in `__init__.py`
- You're importing from the wrong module (typo in path)
- Circular import — A imports B, B imports A

**How to fix:**

1. **Verify the class exists and is spelled correctly:**
   ```bash
   grep -n "class UserService" lib/services/user_service.py
   ```
   If it prints a line number, the class exists. Check the spelling matches your import.

2. **Check if it's exported in __init__.py:**
   ```bash
   cat lib/services/__init__.py
   ```
   Should contain: `from lib.services.user_service import UserService`
   
   If not, add it:
   ```python
   # lib/services/__init__.py
   from lib.services.user_service import UserService
   from lib.services.role_service import RoleService
   
   __all__ = ["UserService", "RoleService"]
   ```

3. **Check for circular imports:**
   ```bash
   # Try importing in isolation
   python -c "from lib.services.user_service import UserService"
   
   # If that crashes with "ImportError: cannot import name...", it's circular
   # Look for: A imports B, B imports A
   grep "from lib.services" lib/repositories/user_repository.py
   grep "from lib.repositories" lib/services/user_service.py
   ```

4. **Verify the import path:**
   ```python
   # ✓ Correct
   from lib.services.user_service import UserService
   
   # ❌ Wrong (typo)
   from lib.services.user_sevice import UserService  # typo: sevice
   
   # ❌ Wrong (wrong module)
   from lib.repositories.user_service import UserService  # repositories, not services
   ```

**How to prevent:**
- Import at the top of your file, where you can see it:
  ```python
  # lib/views/users.py
  from lib.services.user_service import UserService  # ← line 1
  
  class UsersView(BaseView):
      ...
  ```
- Avoid circular imports by importing only what you need:
  ```python
  # ✓ Good: import specific class
  from lib.repositories.user_repository import UserRepository
  
  # ❌ Bad: import entire module (more likely to cause circular imports)
  from lib import repositories  # Then: repositories.UserRepository
  ```
- Use `python -c "from lib.services.user_service import UserService"` to test imports before using them

---

### "KeyError: 'user_service'" (missing in props)

**What it means:** Your view tried to get `user_service` from props, but it wasn't wired.

**Why it happens:**
- The service exists in the container, but not in the props factory
- You misspelled the service name
- The props factory wasn't updated when you added a new service

**How to fix:**

1. **Check where props are wired** (usually `main.py` or `lib/container.py`):
   ```python
   # main.py — set up props factory
   def set_props_factory(container):
       def props_factory():
           return {
               "user_service": container.user_service(),
               "role_service": container.role_service(),
               "vault_service": container.vault_service(),
           }
       return props_factory
   
   props = set_props_factory(container)
   router.set_props_factory(props)
   ```

2. **Add the missing service to props:**
   ```python
   # If you added a new service, add it here:
   def set_props_factory(container):
       def props_factory():
           return {
               "user_service": container.user_service(),
               "role_service": container.role_service(),
               "vault_service": container.vault_service(),
               "my_new_service": container.my_new_service(),  # ← Add this
           }
       return props_factory
   ```

3. **Check the service name matches exactly:**
   ```python
   # View code
   my_service = props["my_service"]  # Spelling matters!
   
   # Props factory
   "my_service": container.my_service(),  # ← Must match exactly
   ```

4. **Verify the service exists in the container:**
   ```bash
   grep -n "my_new_service" lib/container.py
   ```

**How to prevent:**
- Keep a checklist in `main.py` or `lib/container.py` of all services that should be in props:
  ```python
  # Services available in props (keep this up to date!)
  # - user_service (UserService)
  # - role_service (RoleService)
  # - vault_service (VaultService)
  # - my_new_service (MyNewService)  ← Add here when you add the service
  ```
- Test props in a smoke test:
  ```python
  def test_props_has_required_services():
      props = props_factory()
      assert "user_service" in props
      assert "role_service" in props
      assert "vault_service" in props
  ```

---

### "AttributeError: 'NoneType' object has no attribute 'username'"

**What it means:** You called a method on `None`. Usually means a database query returned nothing.

**Why it happens:**
- You called `.get()` or similar, it returned `None`, and you didn't check
- A service method returned `None` instead of raising an exception
- You forgot to handle the "not found" case

**How to fix:**

1. **Always check for None before using:**
   ```python
   from lib.repositories.user_repository import UserRepository
   import uuid
   
   repo = UserRepository(factory)
   user = repo.get(uuid.UUID("123e4567-e89b-12d3-a456-426614174000"))
   
   # ✓ Check first
   if user is None:
       print("User not found")
   else:
       print(f"Username: {user.username}")
   ```

2. **Or raise an exception early:**
   ```python
   def get_user(self, data: dict) -> dict:
       repo = UserRepository(self._factory)
       user = repo.get(uuid.UUID(data["id"]))
       
       # ✓ Raise immediately if not found
       if user is None:
           raise ValueError(f"User {data['id']} not found")
       
       # Now we know user is not None
       return {"id": str(user.id), "username": user.username}
   ```

3. **Use the safe access pattern:**
   ```python
   user = repo.get(user_id)
   username = user.username if user else "Unknown"
   ```

**How to prevent:**
- Always handle the "not found" case in your service:
  ```python
  class UserService(SimpleService):
      def get(self, data: dict) -> dict:
          repo = UserRepository(self._factory)
          user = repo.get(uuid.UUID(data["id"]))
          
          # Always check
          if user is None:
              raise ValueError(f"User {data['id']} not found")
          
          return {...}  # Safe to use user here
  ```
- Write tests for the "not found" case:
  ```python
  def test_get_nonexistent_user_raises_error(service):
      with pytest.raises(ValueError, match="not found"):
          service.get({"id": "nonexistent-id"})
  ```

---

## Vault & Configuration Errors

### "Vault is locked"

**What it means:** The vault exists but hasn't been unlocked with the master key yet.

**Why it happens:**
- The app started but didn't call `vault_service.unlock()`
- The master key (`VAULT_MASTER_KEY`) isn't set in `.secrets/.env`
- A view tried to access vault secrets before the unlock dialog

**How to fix:**

1. **Unlock the vault on startup:**
   ```python
   # main.py — early in boot
   from lib.security.vault_service import VaultService
   from lib.security.vault_store import VaultStore
   
   vault_store = VaultStore(".secrets/vault.json")
   vault_service = VaultService(
       vault_store,
       master_key="your-master-key",
       env_path=".secrets/.env"
   )
   
   # Unlock immediately
   from lib.contracts.base import ActionRequest
   result = vault_service.execute(ActionRequest(action="unlock"))
   if not result.success:
       print(f"Failed to unlock vault: {result.error}")
       sys.exit(1)
   
   print("✓ Vault unlocked")
   ```

2. **Check that .secrets/.env exists and has the key:**
   ```bash
   cat .secrets/.env
   # Should contain:
   # VAULT_MASTER_KEY=your-secret-key
   # VAULT_CONFIRM_KEY=your-confirm-key
   ```

3. **If the keys are missing, bootstrap the vault:**
   ```python
   result = vault_service.execute(ActionRequest(action="bootstrap"))
   if result.success:
       print(f"Vault bootstrapped. Keys written to {vault_service._env_path}")
       # Now read them back for subsequent runs
   ```

**How to prevent:**
- Always unlock the vault before any view tries to read from it:
  ```python
  # main.py, before ft.run() or serving the API
  result = vault_service.execute(ActionRequest(action="unlock"))
  if not result.success:
      raise RuntimeError(f"Cannot start without vault: {result.error}")
  ```
- Add a startup check:
  ```python
  def test_vault_unlocked_at_startup():
      # This test should pass if your startup sequence is correct
      assert vault_service.unlocked, "Vault not unlocked during startup"
  ```

---

### "Secret 'POSTGRES_URL' not found"

**What it means:** You tried to get a secret from the vault, but it doesn't exist.

**Why it happens:**
- The secret was never set in the vault
- The vault was reset/wiped and the key was lost
- You misspelled the key name

**How to fix:**

1. **List all available keys:**
   ```python
   from lib.contracts.base import ActionRequest
   
   result = vault_service.execute(ActionRequest(action="list_keys"))
   if result.success:
       print(f"Available keys: {result.data['keys']}")
   else:
       print(f"Error: {result.error}")
   ```

2. **Add the missing secret:**
   ```python
   result = vault_service.execute(
       ActionRequest(
           action="set",
           data={
               "key": "POSTGRES_URL",
               "value": "postgresql://user:pass@localhost/mydb"
           }
       )
   )
   
   if result.success:
       print("✓ Secret added (in-memory)")
       # Now save it to disk
       save_result = vault_service.execute(
           ActionRequest(action="save", data={"confirm_key": "..."})
       )
       if save_result.success:
           print("✓ Secret persisted to disk")
   ```

3. **Check the secret was set:**
   ```python
   result = vault_service.execute(
       ActionRequest(action="get", data={"key": "POSTGRES_URL"})
   )
   if result.success:
       print(f"POSTGRES_URL = {result.data['value']}")
   else:
       print(f"Not found: {result.error}")
   ```

**How to prevent:**
- Document all required secrets:
  ```python
  # README or docs/VAULT_USAGE.md
  # Required secrets:
  # - POSTGRES_URL (PostgreSQL connection string)
  # - VAULT_MASTER_KEY (encrypt/decrypt vault)
  # - VAULT_CONFIRM_KEY (persist changes)
  ```
- Bootstrap the vault with defaults on first run:
  ```python
  if not vault_service.vault_exists:
      print("First run — setting up vault...")
      vault_service.execute(
          ActionRequest(
              action="set",
              data={"key": "POSTGRES_URL", "value": "..."}
          )
      )
      vault_service.execute(ActionRequest(action="save", ...))
  ```

---

### "Failed to decrypt vault: corrupted data"

**What it means:** The vault file is damaged or the master key is wrong.

**Why it happens:**
- The vault file was edited manually or got corrupted
- The master key changed but old vault.json still uses the old key
- A network drive disconnected while writing the vault file

**How to fix:**

1. **Backup and reset the vault:**
   ```bash
   # Back up the corrupted vault
   mv .secrets/vault.json .secrets/vault.json.backup
   
   # Bootstrap a fresh vault
   python -c "
   from lib.security.vault_service import VaultService
   from lib.security.vault_store import VaultStore
   from lib.contracts.base import ActionRequest
   
   vault = VaultService(
       VaultStore('.secrets/vault.json'),
       master_key='your-key',
       env_path='.secrets/.env'
   )
   result = vault.execute(ActionRequest(action='bootstrap'))
   print(result)
   "
   ```

2. **Restore secrets from backup** (if you have them):
   ```python
   # Manually re-add secrets
   vault_service.execute(
       ActionRequest(
           action="set",
           data={"key": "POSTGRES_URL", "value": "postgresql://..."}
       )
   )
   vault_service.execute(ActionRequest(action="save", ...))
   ```

3. **Check the master key is correct:**
   ```python
   # The key in .secrets/.env must match what you're using
   with open(".secrets/.env") as f:
       for line in f:
           if "VAULT_MASTER_KEY" in line:
               print(f"Master key in file: {line.split('=')[1]}")
   ```

**How to prevent:**
- Never edit `.secrets/vault.json` manually — use the API
- Store the master key in a secure location (not version control)
- Test vault persistence in your test suite:
  ```python
  def test_vault_persists_after_save():
      vault.execute(ActionRequest(action="set", data={...}))
      vault.execute(ActionRequest(action="save", ...))
      
      # Reload the vault
      vault2 = VaultService(VaultStore(".secrets/vault.json"))
      result = vault2.execute(ActionRequest(action="get", ...))
      assert result.success
  ```

---

## Flet UI Errors

### "RuntimeError: run_task() called outside a page context"

**What it means:** You tried to call `page.run_task()` from outside an async context, or the page object isn't available.

**Why it happens:**
- You're calling an async function directly instead of through `page.run_task()`
- The page object wasn't passed to your component
- A view method tried to run async code without the page

**How to fix:**

1. **Use page.run_task() for async operations:**
   ```python
   # ❌ Wrong — can't call async directly in event handler
   def on_click(e):
       user = await service.get_user_async(user_id)  # SyntaxError!
   
   # ✓ Correct — use page.run_task()
   def on_click(e):
       async def fetch_user():
           user = await service.get_user_async(user_id)
           # Update UI after async work
           page.snack_bar = ft.SnackBar(ft.Text(f"Got {user['username']}"))
           page.snack_bar.open = True
           page.update()
       
       page.run_task(fetch_user)
   ```

2. **Pass page to your component:**
   ```python
   # lib/views/users.py
   class UsersView(BaseView):
       def build_content(self):
           # self.page is available in BaseView
           def on_click(e):
               async def load_users():
                   users = await self.user_service.list_users_async()
                   # Update UI
                   self.page.update()
               
               self.page.run_task(load_users)
           
           return ft.ElevatedButton("Load", on_click=on_click)
   ```

3. **If page is None, check the view inheritance:**
   ```python
   # ✓ Correct — inherit from BaseView
   from lib.ui.layouts.base_view import BaseView
   
   class MyView(BaseView):
       def build_content(self):
           # self.page is guaranteed to be available
           pass
   
   # ❌ Wrong — plain class, no page
   class MyView:
       def __init__(self, page):
           self.page = page  # ← Have to do this yourself
   ```

**How to prevent:**
- Always inherit from `BaseView` in your views:
  ```python
  from lib.ui.layouts.base_view import BaseView
  
  class MyView(BaseView):
      def build_content(self):
          return ft.Column([...])
  ```
- Use `page.run_task()` for any async work in event handlers:
  ```python
  def on_click(e):
      async def do_work():
          result = await some_async_call()
          self.page.update()
      
      self.page.run_task(do_work)  # Always wrap async in run_task
  ```

---

### "TypeError: Button() got an unexpected keyword argument 'text'"

**What it means:** Flet 0.84+ changed the Button API. `text=` is no longer a parameter.

**Why it happens:**
- You're using old Flet code (pre-0.84) on Flet 0.84+
- The dependency documentation wasn't updated after the Flet upgrade

**How to fix:**

1. **Replace text= with the new API:**
   ```python
   # ❌ Old (Flet < 0.84)
   button = ft.ElevatedButton(text="Click me")
   menu = ft.PopupMenuItem(text="Save")
   
   # ✓ New (Flet 0.84+)
   button = ft.ElevatedButton("Click me")
   menu = ft.PopupMenuItem(content=ft.Text("Save"))
   ```

2. **For controls that need content=:**
   ```python
   # ❌ Old
   button = ft.ElevatedButton(text="Hi")
   
   # ✓ New
   button = ft.ElevatedButton(content=ft.Text("Hi"))
   
   # Or use the convenience shorthand
   button = ft.ElevatedButton("Hi")  # Flet interprets as content
   ```

3. **Check your pyproject.toml for the Flet version:**
   ```ini
   [project]
   dependencies = [
       "flet>=0.84",  # ← Make sure version is 0.84+
   ]
   ```

**How to prevent:**
- Check your Flet version and ensure all controls use the new API (0.84+)
- Search for `text=ft.` in your code:
  ```bash
  grep -r "text=ft\." lib/
  ```
  Replace with `content=ft.Text(...)`.
- Add a test that creates common controls:
  ```python
  def test_flet_button_api():
      # This will fail on wrong Flet version
      button = ft.ElevatedButton("Click")
      assert button is not None
  ```

---

### "AttributeError: 'CoroutineType' object has no attribute 'open'"

**What it means:** You tried to use a coroutine result as if it were the actual value.

**Why it happens:**
- You called an async function without `await`
- You forgot to handle the async result properly in an event handler

**How to fix:**

1. **Identify the async call and wrap it:**
   ```python
   # ❌ Wrong — result is a coroutine, not the actual value
   def on_click(e):
       snack = page.snack_bar.open = service.load_data()  # Returns coroutine!
       page.update()  # Won't work
   
   # ✓ Correct — wrap in page.run_task
   def on_click(e):
       async def load_and_show():
           data = await service.load_data()  # Now we have the value
           page.snack_bar = ft.SnackBar(ft.Text(f"Loaded {data}"))
           page.snack_bar.open = True
           page.update()
       
       page.run_task(load_and_show)
   ```

2. **Or make the function sync:**
   ```python
   # If service.load_data() doesn't need to be async, don't make it async
   class MyService:
       # ✓ Sync version — easier to use in Flet
       def load_data(self):
           return {"value": 42}
       
       # Async only if you really need it (network calls, etc.)
       async def load_data_from_network(self):
           result = await fetch(url)
           return result
   ```

**How to prevent:**
- Keep service methods sync unless they truly need async:
  ```python
  # ✓ Good — simple services are sync
  class UserService:
      def get_user(self, user_id):
          repo = UserRepository(self._factory)
          return repo.get(user_id)
  ```
- Use page.run_task() for anything async:
  ```python
  # When you do need async, always wrap it
  page.run_task(async_function)  # Not: async_function()
  ```

---

### "Page route changed, but view didn't update"

**What it means:** The URL changed but the Flet page is still showing the old view.

**Why it happens:**
- The router wasn't called after the route changed
- The view function is missing (module doesn't have `view(page, props)`)
- A view returned `None` or an empty control

**How to fix:**

1. **Call page.update() after navigation:**
   ```python
   # ❌ Wrong — just changes the route
   page.route = "/users"
   # View doesn't update!
   
   # ✓ Correct — route change + update
   page.route = "/users"
   page.update()
   ```

2. **Or use the NavigationService (if available):**
   ```python
   from lib.services.navigation_service import NavigationService
   from lib.contracts.base import ActionRequest
   
   nav_service = NavigationService(event_bus)
   # Use the execute(ActionRequest) API with action="visit"
   result = nav_service.execute(
       ActionRequest(action="visit", data={"url": "/users"})
   )
   page.update()  # Still need to update the page
   ```

3. **Verify the view module exists and has the view() function:**
   ```bash
   # If you're navigating to /users, check:
   ls lib/views/users.py
   grep "def view" lib/views/users.py  # Must have this function
   ```

4. **Check the view function signature:**
   ```python
   # ✓ Correct signature
   def view(page: ft.Page, props: dict) -> ft.View:
       return ft.View([...])
   
   # ❌ Wrong — missing return
   def view(page, props):
       pass  # Returns None!
   
   # ❌ Wrong — wrong parameters
   def view(page):
       return ft.View([...])  # Missing props
   ```

**How to prevent:**
- Every view file must have:
  ```python
  def view(page, props):
      return SomeView(page, props).render()
  ```
- Use the router to navigate:
  ```python
  nav_service.execute(ActionRequest(action="visit", data={"url": "/users"}))
  page.update()  # Still required
  ```
- Add a smoke test that loads each view:
  ```python
  def test_users_view_loads():
      from lib.views.users import view
      from tests.conftest import FakePage
      
      page = FakePage()
      props = {"user_service": mock_service}
      result = view(page, props)
      
      assert result is not None
      assert len(result.controls) > 0
  ```

---

## Service Errors

### "ValueError: Username already taken"

**What it means:** The service rejected the request because the data violates a business rule.

**Why it happens:**
- The service has validation logic that caught the error
- You tried to create a duplicate record
- Required field is missing or invalid

**How to fix:**

1. **Check the error message and fix the input:**
   ```python
   from lib.services.user_service import UserService
   
   service = UserService(factory)
   try:
       user = service.create({"username": "alice", "email": "alice@example.com"})
   except ValueError as e:
       print(f"Validation error: {e}")
       # e.g.: "Username 'alice' is already taken"
       # → Use a different username
   ```

2. **Validate before calling the service:**
   ```python
   from lib.repositories.user_repository import UserRepository
   
   repo = UserRepository(factory)
   username = input("Username: ")
   
   # Check first
   existing = repo.list(username=username)
   if existing:
       print("❌ That username is taken")
   else:
       user = service.create({
           "username": username,
           "email": input("Email: ")
       })
       print(f"✓ User created: {user['id']}")
   ```

3. **In a Flet view:**
   ```python
   def on_create_click(e):
       username = username_input.value
       
       # Validate
       try:
           user = self.user_service.create({
               "username": username,
               "email": email_input.value
           })
           page.snack_bar = ft.SnackBar(ft.Text("✓ User created"))
       except ValueError as err:
           # Show error to user
           page.snack_bar = ft.SnackBar(ft.Text(f"❌ {err}"), bgcolor=ft.Colors.RED)
       
       page.snack_bar.open = True
       page.update()
   ```

**How to prevent:**
- Raise informative errors in your service:
  ```python
  class UserService(SimpleService):
      def create(self, data: dict) -> dict:
          username = data.get("username", "")
          
          if not username:
              raise ValueError("Username is required")
          
          if len(username) < 3:
              raise ValueError("Username must be at least 3 characters")
          
          existing = repo.list(username=username)
          if existing:
              raise ValueError(f"Username '{username}' is already taken")
          
          # Now safe to create
          user = repo.create(data)
          return {"id": str(user.id), ...}
  ```
- Add tests for the error cases:
  ```python
  def test_create_user_rejects_duplicate_username(service):
      service.create({"username": "alice", ...})
      
      with pytest.raises(ValueError, match="already taken"):
          service.create({"username": "alice", ...})
  ```

---

### "Transaction rolled back after error"

**What it means:** The database transaction failed and all changes were discarded.

**Why it happens:**
- A constraint was violated (UNIQUE, FOREIGN KEY, etc.)
- A database error occurred during the transaction
- The session wasn't properly committed

**How to fix:**

1. **Use the proper transaction handling:**
   ```python
   from lib.database.session import SessionFactory
   
   factory = SessionFactory("sqlite:///dev.db")
   
   # ✓ Correct — uses context manager
   with factory.session() as session:
       user = User(username="alice", email="alice@example.com")
       session.add(user)
       # Commits automatically on exit
   ```

2. **Or use the Unit of Work pattern (if available):**
   ```python
   from lib.repositories.user_repository import UserRepository
   
   uow = factory.unit_of_work()
   try:
       # Use repo() to get repository within transaction
       repo = uow.repo(UserRepository)
       user = repo.create({"username": "alice", "email": "alice@example.com"})
       
       # Preview changes before committing
       diff = uow.stage()
       print(f"Will create: {diff}")
       
       # Commit the transaction
       uow.commit()
   except Exception:
       uow.rollback()
       raise
   ```

3. **Check what caused the rollback:**
   ```python
   from sqlalchemy.exc import SQLAlchemyError
   
   with factory.session() as session:
       try:
           user = User(username="alice", email="alice@example.com")
           session.add(user)
           session.commit()
       except SQLAlchemyError as e:
           print(f"Database error: {e}")
           # e.g. "UNIQUE constraint failed"
           raise
   ```

**How to prevent:**
- Always validate before adding to the database:
  ```python
  # Before you add to session
  existing = repo.list(username=data["username"])
  if existing:
      raise ValueError("Username taken")  # Fail fast
  
  # Now safe to add
  user = User(**data)
  session.add(user)
  ```
- Test your database operations:
  ```python
  def test_create_user_with_duplicate_username_fails(db_factory):
      repo = UserRepository(db_factory)
      repo.create({"username": "alice", ...})
      
      # Should fail on second create
      with pytest.raises(Exception):  # SQLAlchemy error
          repo.create({"username": "alice", ...})
  ```

---

## Testing Errors

### "ConnectionError: Can't connect to SQLite database"

**What it means:** A test tried to connect to a database that doesn't exist or is locked.

**Why it happens:**
- The test database file was deleted
- Multiple tests are trying to write to the same file (concurrency)
- The in-memory database wasn't created (`sqlite:///:memory:`)

**How to fix:**

1. **Use in-memory SQLite in tests:**
   ```python
   # tests/conftest.py
   @pytest.fixture
   def db_factory():
       # ✓ In-memory — fresh database for each test
       factory = SessionFactory("sqlite:///:memory:")
       factory.create_tables(Base)
       return factory
   ```

2. **Run tests serially (not parallel):**
   ```bash
   # ✓ Good — serial, no locking issues
   pytest tests/ -v
   
   # ❌ Bad — parallel workers, SQLite locks up
   pytest tests/ -n auto
   ```

3. **If using a file-based database, ensure it exists:**
   ```python
   from pathlib import Path
   
   db_path = Path("tests/test.db")
   db_path.parent.mkdir(exist_ok=True)
   
   factory = SessionFactory(f"sqlite:///{db_path}")
   factory.create_tables(Base)  # Create schema
   ```

**How to prevent:**
- Always use in-memory SQLite for tests:
  ```python
  @pytest.fixture
  def db_factory():
      factory = SessionFactory("sqlite:///:memory:")  # ← Always this
      factory.create_tables(Base)
      return factory
  ```
- Test the database setup itself:
  ```python
  def test_database_fixture_creates_tables(db_factory):
      with db_factory.session() as session:
          result = session.execute(
              "SELECT name FROM sqlite_master WHERE type='table'"
          )
          tables = [row[0] for row in result]
          assert "users" in tables
  ```

---

### "pytest: fixture 'user_repo' not found"

**What it means:** Your test tried to use a fixture, but it's not defined.

**Why it happens:**
- The fixture isn't in `conftest.py`
- The fixture name is misspelled
- You're in the wrong test file (fixtures aren't inherited across files)

**How to fix:**

1. **Add the fixture to conftest.py:**
   ```python
   # tests/conftest.py
   @pytest.fixture
   def user_repo(db_factory):
       return UserRepository(db_factory)
   ```

2. **Use it in your test:**
   ```python
   # tests/test_repositories.py
   def test_create_user(user_repo):  # ← name must match fixture name
       user = user_repo.create({
           "username": "alice",
           "email": "alice@example.com"
       })
       assert user.id is not None
   ```

3. **Check the spelling:**
   ```python
   # ❌ Fixture is user_repo
   @pytest.fixture
   def user_repo(db_factory):
       return UserRepository(db_factory)
   
   # ❌ Test asks for user_repo (correct) but misspelled in code
   def test_something(usr_repo):  # Typo!
       usr_repo.list()  # Fixture doesn't match
   ```

**How to prevent:**
- Keep all shared fixtures in one place (`tests/conftest.py`)
- Use meaningful fixture names:
  ```python
  @pytest.fixture
  def db_factory():  # Good — clear what it is
      ...
  
  @pytest.fixture
  def user_repo(db_factory):  # Good — clear what it returns
      ...
  
  # ❌ Bad — unclear
  @pytest.fixture
  def f():
      ...
  ```
- Add new fixtures to conftest.py as you add new tests:
  ```python
  # tests/conftest.py
  @pytest.fixture
  def role_repo(db_factory):
      return RoleRepository(db_factory)
  
  @pytest.fixture
  def user_with_roles(user_repo, role_repo):
      role = role_repo.create({"name": "admin", ...})
      user = user_repo.create({...})
      user_repo.add_role(user.id, role.id)
      return user
  ```

---

### "Async test hangs (times out)"

**What it means:** A test started an async operation but never finished waiting for it.

**Why it happens:**
- An async function wasn't awaited
- A Flet page.run_task() wasn't given time to complete
- The test didn't use the proper async test pattern

**How to fix:**

1. **Use pytest's async support:**
   ```python
   # tests/conftest.py — add this fixture
   @pytest.fixture
   def fake_page():
       class FakePage:
           def run_task(self, coro_fn, *args, **kwargs):
               """Run async tasks synchronously in tests."""
               import asyncio
               asyncio.run(coro_fn(*args, **kwargs))
       
       return FakePage()
   ```

2. **Use the fixture in your test:**
   ```python
   # tests/test_views.py
   def test_user_view_loads_data(fake_page):
       # fake_page.run_task() handles async automatically
       view = UsersView(fake_page, props)
       
       # Click the load button
       view.on_load_click(None)
       
       # FakePage.run_task ran the async code synchronously
       # So we can make assertions immediately
       assert view.user_list.controls > 0
   ```

3. **Or use pytest-asyncio if you must be truly async:**
   ```bash
   pip install pytest-asyncio
   ```
   ```python
   import pytest
   
   @pytest.mark.asyncio
   async def test_async_operation():
       result = await some_async_call()
       assert result is not None
   ```

**How to prevent:**
- Keep Flet views sync; don't make them async
  ```python
  # ✓ Good — sync, easy to test
  def on_click(e):
      users = self.user_service.list_users()
      self.page.update()
  
  # ❌ Bad — async, harder to test
  async def on_click(e):
      users = await self.user_service.list_users_async()
      self.page.update()
  ```
- Use page.run_task() to wrap async code, not plain async:
  ```python
  page.run_task(async_function)  # ✓ Works in tests with proper fixture
  ```

---

## How to Debug

When something goes wrong and you can't find the error in the docs, use this systematic approach:

### 1. Read the Full Error Message

```
Traceback (most recent call last):
  File "lib/views/users.py", line 45, in on_create_click
    user = self.user_service.create(data)
  File "lib/services/user_service.py", line 52, in create
    existing = repo.list(username=username)
  File "lib/repositories/user_repository.py", line 78, in list
    return session.query(User).filter(User.username == username).all()
sqlalchemy.exc.OperationalError: no such table: users
```

**What you learn:**
- Line 78 of `user_repository.py` crashes
- The error is "no such table: users"
- The call chain: view → service → repository → database

**Next step:** Look at the "database errors" section above. This is "no such table: users".

### 2. Isolate the Problem

Don't test the whole app. Test the piece that broke in isolation.

```python
# If the error is in UserRepository, test it alone:
from lib.repositories.user_repository import UserRepository
from lib.database.session import SessionFactory

factory = SessionFactory("sqlite:///dev.db")
repo = UserRepository(factory)

# Try the operation that failed
try:
    users = repo.list(username="alice")
    print(f"✓ Found {len(users)} users")
except Exception as e:
    print(f"✗ Error: {e}")
    print(f"  Type: {type(e).__name__}")
```

This tells you: Is it the repository? The database? The query?

### 3. Add Print Statements

Don't be shy. Debugging is about seeing what's actually happening.

```python
# In the failing function
def create(self, data: dict) -> dict:
    username = data.get("username", "")
    print(f"DEBUG: create() called with username={username}")
    
    repo = UserRepository(self._factory)
    print(f"DEBUG: created repo = {repo}")
    
    existing = repo.list(username=username)
    print(f"DEBUG: existing = {existing}")
    
    if existing:
        raise ValueError(f"Username taken")
    
    user = repo.create(data)
    print(f"DEBUG: created user = {user}")
    
    return {"id": str(user.id)}
```

Run the test and look at the debug output. Where does it stop?

### 4. Check the Database

Is the data actually there?

```python
# Open a database shell
sqlite3 dev.db

# Run raw SQL
sqlite> SELECT * FROM users;
sqlite> SELECT COUNT(*) FROM users;
sqlite> SELECT * FROM sqlite_master WHERE type='table';
```

Or from Python:

```python
from lib.database.session import SessionFactory

factory = SessionFactory("sqlite:///dev.db")

with factory.session() as session:
    # Run raw SQL
    result = session.execute("SELECT * FROM users")
    for row in result:
        print(row)
```

### 5. Check the Service Isolation

If you're testing a service, isolate it from the database:

```python
# Mock the factory (UserService takes a SessionFactory, not a repo)
from unittest.mock import Mock

mock_factory = Mock()
# You can mock individual repo() calls if needed:
# mock_factory.session.return_value = MockSession()

service = UserService(mock_factory)

# Now test the service without touching the database
result = service.create({"username": "alice", "email": "alice@example.com"})
print(result)
```

If this works but the real service fails, the problem is in the repository or database, not the service.

### 6. Use Repository Directly

Test the repository without the service:

```python
from lib.repositories.user_repository import UserRepository
from lib.database.session import SessionFactory
from lib.database.base import Base

factory = SessionFactory("sqlite:///:memory:")
factory.create_tables(Base)

repo = UserRepository(factory)

# Create a user
user = repo.create({"username": "alice", "email": "alice@example.com"})
print(f"Created: {user.id}")

# Get it back
retrieved = repo.get(user.id)
print(f"Retrieved: {retrieved.username}")

# List all
all_users = repo.list()
print(f"Total: {len(all_users)}")
```

If this works, the repository is fine. If it fails, the problem is in the repository or ORM model.

### 7. Check Imports and Wiring

If you get `ModuleNotFoundError` or `KeyError: 'service_name'`:

```bash
# Check that the module exists
ls lib/services/my_service.py

# Check that it's importable
python -c "from lib.services.my_service import MyService; print('✓')"

# Check that it's in the container
grep -n "my_service" lib/container.py

# Check that it's in props
grep -n "my_service" main.py
```

### 8. Run One Test at a Time

Don't run all tests. Run the one that's failing:

```bash
# Run one test file
pytest tests/test_services.py -v

# Run one test function
pytest tests/test_services.py::test_create_user -v

# Run with debug output
pytest tests/test_services.py::test_create_user -vv -s

# -s means "don't capture print statements" — you'll see your debug prints
```

### 9. Check the Test Fixtures

If a test uses a fixture and it fails, check conftest.py:

```bash
# What fixtures are available?
pytest --fixtures tests/conftest.py

# Is your fixture listed?
grep "@pytest.fixture" tests/conftest.py
```

### 10. Search the Codebase

If you still can't figure it out, search:

```bash
# Search for a class
grep -r "class UserService" lib/

# Search for a function
grep -r "def create_user" lib/

# Search for an error message
grep -r "User not found" lib/

# Search for where something is imported
grep -r "from lib.services.user_service" .
```

---

## Quick Reference

| Error | Section | Quick Fix |
|-------|---------|-----------|
| `database is locked` | Database Errors | Use in-memory SQLite, run tests serially |
| `no such table` | Database Errors | Run `factory.create_tables(Base)` or `alembic upgrade head` |
| `UNIQUE constraint failed` | Database Errors | Check before creating, use `repo.list()` to verify |
| `FOREIGN KEY constraint failed` | Database Errors | Create parent before child, use cascade in model |
| `ModuleNotFoundError: lib` | Import Errors | Run `pip install -e .` |
| `ImportError: cannot import name` | Import Errors | Check spelling, verify export in `__init__.py` |
| `KeyError: 'service_name'` (props) | Import Errors | Add service to props factory in `main.py` |
| `Vault is locked` | Vault Errors | Call `vault_service.execute(ActionRequest(action="unlock"))` |
| `Secret not found` | Vault Errors | Use `list_keys` action to see available secrets |
| `TypeError: Button() got text=` | Flet Errors | Use `ft.ElevatedButton("text")` or `content=ft.Text("text")` |
| `ValueError: Username already taken` | Service Errors | Check before creating, validate input |
| `AttributeError: 'NoneType'` | Service/UI Errors | Check for `None` before calling methods |
| `fixture not found` | Testing Errors | Add to `tests/conftest.py` |
| `Async test hangs` | Testing Errors | Use sync fixtures with `asyncio.run()` |

---

## Need More Help?

1. **For architecture questions:** See [GETTING_STARTED.md](GETTING_STARTED.md)
2. **For design patterns:** See [API_PATTERN_TEMPLATE.md](API_PATTERN_TEMPLATE.md)
3. **For complete example:** See [PONG_EXAMPLE.md](PONG_EXAMPLE.md)
4. **For vault operations:** See [VAULT_USAGE.md](VAULT_USAGE.md)
5. **For testing:** See [TESTING.md](TESTING.md)
6. **For conventions:** See [CONVENTIONS.md](CONVENTIONS.md)
