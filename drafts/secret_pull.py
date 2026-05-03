"""Pull a secret from the vault.

Run from the project root:
    python drafts/secret_pull.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.security.vault import open_vault

vault = open_vault()
print(vault.get("POSTGRES_USER"))
