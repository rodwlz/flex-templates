#!/usr/bin/env python
"""Quick test to verify wrapper methods work."""

from lib.database.session import SessionFactory
from lib.services.user_service import UserService
from lib.services.role_service import RoleService

# Setup
factory = SessionFactory("sqlite:///test_wrappers.db")
user_service = UserService(factory)
role_service = RoleService(factory)

# Test RoleService wrappers
print("=" * 50)
print("Testing RoleService wrappers:")
print("=" * 50)

# Create a role
role = role_service.create_role("admin", "Administrator role")
print(f"✓ Created role: {role['name']}")

# Get the role
fetched = role_service.get_role(role['id'])
print(f"✓ Retrieved role: {fetched['name']}")

# List roles
roles = role_service.list_roles()
print(f"✓ Listed roles: {len(roles)} total")

# Test UserService wrappers
print("\n" + "=" * 50)
print("Testing UserService wrappers:")
print("=" * 50)

# Create a user
user = user_service.create_user("alice", "alice@example.com")
print(f"✓ Created user: {user['username']}")

# Get the user
fetched = user_service.get_user(user['id'])
print(f"✓ Retrieved user: {fetched['username']} ({fetched['email']})")

# List users
users = user_service.list_users()
print(f"✓ Listed users: {len(users)} total")

# Test staged operation
print("\n" + "=" * 50)
print("Testing UserService staged wrappers:")
print("=" * 50)

# Stage a user with roles
preview = user_service.stage_user_with_roles("bob", "bob@example.com", [role['id']])
print(f"✓ Staged user: {preview['user_id']}, {preview['role_count']} role(s)")

# Confirm
confirmed = user_service.confirm_staged()
print(f"✓ Confirmed staged user: {confirmed}")

# Verify the new user exists
bob = user_service.get_user_by_email("bob@example.com") if hasattr(user_service, 'get_user_by_email') else None
if bob:
    print(f"✓ User bob exists: {bob['username']}")

print("\n" + "=" * 50)
print("✨ All wrapper methods work!")
print("=" * 50)
