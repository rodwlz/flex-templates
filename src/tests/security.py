from src.middleware.security import Security


#salt = Security.generate_salt()
salt = Security.generate_salt()
hash = Security.hash_password("password123",salt)
print(f"salt: {salt}")
print(f"hash: {hash}")