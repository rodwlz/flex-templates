import pysftp
from src.vault_secrets.vault import vault
import os

try:
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    # Define the connection parameters
    host = vault.get_secret('1-SFTP-HOST')
    username = vault.get_secret('1-SFTP-USERNAME')
    private_key = vault.get_secret('1-SFTP-KEY')
    port = int(vault.get_secret('1-SFTP-PORT'))

# Establish the SFTP connection
    with pysftp.Connection(host, username=username, private_key=private_key, port=port, cnopts=cnopts) as sftp:
        # List remote directory contents
        
        remote_dir = '/'
        dir_contents = sftp.listdir(remote_dir)
        os.system('cls')
        print("Remote directory contents:")
        for item in dir_contents:
            print(item)

except Exception as e:
    print('Error at connection:',e)