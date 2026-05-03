import bcrypt
from src.vault_secrets.vault import vault 

class Security:
    @staticmethod
    def generate_salt():
        return bcrypt.gensalt().decode()

    @staticmethod
    def hash_password(password:str,salt:str):
        return bcrypt.hashpw(bytes(password,'utf-8'), bytes(salt,'utf-8')).decode()

    @staticmethod
    def verify_password(plain_password, hashed_password, salt) -> bool:
        expected_hash = bcrypt.hashpw(plain_password.encode("utf-8"), salt.encode("utf-8"))
        return hashed_password == expected_hash.decode("utf-8")

    @staticmethod
    def master_auth(key:str)->bool: #Unlocks Admin control for password manager
       print('Access Granted Mater_Admin')
       return key == vault.get_secret('MASTER-PASSWORD')

    @staticmethod
    def expose_secrets():
        return vault._secrets


# Example usage:
'''password = "password123"
salt = Security.generate_salt()
hashed_password = Security.hash_password(password, salt)
print("Hashed password:", hashed_password)
is_valid = Security.verify_password(password, hashed_password, salt)
print("Password is valid:", is_valid)
'''