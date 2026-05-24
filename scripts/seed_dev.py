"""
Seed script for dev — idempotent, safe to run multiple times.

Creates:
  - Role: admin
  - User: admin / admin@example.com  password: admin123  role: admin
  - 6 sample products

Run from the project root:
    python scripts/seed_dev.py
"""

import sys
import os
import uuid
from decimal import Decimal
from pathlib import Path

# Make sure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Apply Alembic migrations before touching the DB
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_cmd
try:
    alembic_cmd.upgrade(AlembicConfig("alembic.ini"), "head")
    print("Migrations applied")
except Exception as e:
    print(f"  Alembic skipped ({e}), continuing...")

from lib.database.session import SessionFactory, ConnectionRegistry
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository
from lib.repositories.product_repository import ProductRepository
from lib.security.password import hash_password

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
ConnectionRegistry.register(url=DB_URL, name="default")
ConnectionRegistry.register(url=DB_URL, name="postgres")  # matches primary_database default
factory = ConnectionRegistry.get("default")

# ── Roles ────────────────────────────────────────────────────────────────────

role_repo = RoleRepository(factory)
existing_roles = role_repo.filter_by(name="admin")
if existing_roles:
    _rid = existing_roles[0]["id"]
    admin_role_id = _rid if isinstance(_rid, uuid.UUID) else uuid.UUID(_rid)
    print(f"  Role 'admin' already exists ({admin_role_id})")
else:
    role_obj = role_repo.create({"name": "admin", "description": "Full system access"})
    admin_role_id = role_obj.id
    print(f"OK Role 'admin' created ({admin_role_id})")

# ── Admin user ────────────────────────────────────────────────────────────────

user_repo = UserRepository(factory)
existing_users = user_repo.filter_by(username="admin")
if existing_users:
    _uid = existing_users[0]["id"]
    admin_user_id = _uid if isinstance(_uid, uuid.UUID) else uuid.UUID(str(_uid))
    print(f"  User 'admin' already exists ({admin_user_id})")
else:
    password_hash, salt = hash_password("admin123")
    user_obj = user_repo.create({
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": password_hash,
        "salt": salt,
        "is_active": True,
    })
    admin_user_id = user_obj.id
    print(f"OK User 'admin' created ({admin_user_id})")

# Assign admin role (idempotent)
assigned = user_repo.add_role(admin_user_id, admin_role_id)
if assigned:
    print("OK Role 'admin' assigned to user 'admin'")
else:
    print("  Role already assigned")

# ── Sample products ───────────────────────────────────────────────────────────

SAMPLE_PRODUCTS = [
    {"name": "Wireless Keyboard",  "price": Decimal("49.99"),  "stock_qty": 25, "is_active": True},
    {"name": "USB-C Hub 7-Port",   "price": Decimal("34.95"),  "stock_qty": 40, "is_active": True},
    {"name": "Mechanical Mouse",   "price": Decimal("79.00"),  "stock_qty": 15, "is_active": True},
    {"name": "Monitor Stand",      "price": Decimal("29.50"),  "stock_qty": 8,  "is_active": True},
    {"name": "Webcam HD 1080p",    "price": Decimal("89.99"),  "stock_qty": 12, "is_active": True},
    {"name": "Cable Organiser Kit","price": Decimal("14.99"),  "stock_qty": 50, "is_active": False},
]

product_repo = ProductRepository(factory)
for p in SAMPLE_PRODUCTS:
    existing = product_repo.filter_by(name=p["name"])
    if existing:
        print(f"  Product '{p['name']}' already exists")
    else:
        product_repo.create(p)
        print(f"OK Product '{p['name']}' created  ${p['price']}")

print("\nDone. Log in with:  admin / admin123")
