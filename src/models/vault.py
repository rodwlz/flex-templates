import json
from flet.security import decrypt, encrypt
from dotenv import load_dotenv
import os

class Vault:
    '''
    For extra safety move this file to a muted folder
    '''
    def __init__(self, secrets_file="src/.secrets/secrets.json"):
        load_dotenv()
        self.__secrets_file = secrets_file
        self.__key = os.getenv("MASTER-PASSWORD")
        self.__secrets = self._read_secrets()

    def store_secret(self, tag, value):
        encrypted_value = encrypt(value, self.__key)

            # Update secrets with new key-value pair
        self.__secrets[tag] = encrypted_value

            # Write secrets to JSON file
        with open(self.__secrets_file, 'w') as f:
            json.dump(self.__secrets, f, indent=4)

    def _read_secrets(self) -> dict :
        try:
            # Load secrets from JSON file if it exists
            with open(self.__secrets_file, 'r') as f:
                __secrets = json.load(f)
            return __secrets
           
        except Exception as e:
            print(f"Error reading secrets: {e}")
            return {}
        
    def get_secret(self,tag:str) -> str :
        return decrypt(self.__secrets[tag], self.__key)
    
vault = Vault()

