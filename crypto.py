import cryptography
import base64
import os
import getpass
import toml
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Crypto():
	"""
	Helper class that holds a Fernet instance and decrypts the REST API keys

	"""
	def __init__(self, crypted_key_secret=b'gAAAAABeXQ5i1z3_04b1D7xLrJYuWu8RWgksvqrbYEQeHQnkU741n70VUdY2ek5IltHLuQJFoi-JexgoijwUkBLS4VG1VzKCTQ==', password="password", salt=b's6yLfvn3S2wfb9l0hA44-w=='):
		self.crypted_key_secret=crypted_key_secret
		self.password=password.encode('utf-8')
		self.setup_fernet(salt=base64.urlsafe_b64decode(salt))


	def setup_fernet(self,salt=None):
		"""
		Helper function to set up the Fernet instance

		"""

		if salt is None:
			salt=self.gen_salt()
		kdf=PBKDF2HMAC(
			algorithm=hashes.SHA256(),
			length=32,
			salt=salt,
			iterations=100000,
			backend=default_backend()
		)
		self.key=base64.urlsafe_b64encode(kdf.derive(self.password))
		self.fernet=Fernet(self.key)

	def encrypt(self,text=None):
		"""
		Encrypt the given text with the `Crypto` object's Fernet instance

		If called without arguments, prompts the user for input

		"""
		if text is None:
			text=input("text to encrypt: ")
		return self.fernet.encrypt(text.encode('utf-8'))

	def decrypt(self):
		"""
		Decrypt the client key and secret with the `Crypto` object's Fernet instance

		Returns
		-------
		concatenated client key and secret

		>>> c.decrypt()
		b'key:secret'
		"""
		return self.fernet.decrypt(self.crypted_key_secret)

	def gen_salt(self,length=16):
		"""
		Generate a random salt, 16 bytes in length by default

		>>> len(c.gen_salt())
		16
		"""
		return os.urandom(length)

def gen_token(update_config=False):
	"""
	Generate new salt and token for a given password and text

	Optionally insert that into the parking validation configuration file

	For an REST API key, the text should be in the form: <api_key>:<client_secret>

	"""

	print("This will generate a new salt and encrypted token, and update the config file.\nYou will be prompted for the password first.\n")

	salt=base64.urlsafe_b64encode(Crypto.gen_salt(Crypto))
	password=getpass.getpass("password for encryption: ")
	print("\nIf encrypting new API key, format is <api_key>:<client_secret>\n")
	crypto=Crypto(password=password,salt=salt)
	crypto.crypted_key_secret=crypto.encrypt()
	try:
		crypto.decrypt()
		print("Decryption test successful!")
		if not update_config:
			print(f"salt: {salt}")
			print(f"client key and secret token: {crypto.crypted_key_secret}")
		else:
			config=toml.load("parking_validator.conf")
			config['sierra rest api']['salt']=salt.decode('utf-8')
			config['sierra rest api']['crypted_key_secret']=crypto.crypted_key_secret.decode('utf-8')
			toml.dump(config,open("parking_validator.conf",'w+'))
	except:
		print("Decryption test failed!")

def gen_email_password(update_config=False):
	"""
	Generate new salt and crypted email password for a given password and text

	Optionally insert that into the parking validation configuration file

	"""

	salt=base64.urlsafe_b64encode(Crypto.gen_salt(Crypto))
	password=getpass.getpass("password for encryption: ")
	crypto=Crypto(password=password,salt=salt)
	crypto.crypted_key_secret=crypto.encrypt()
	try:
		crypto.decrypt()
		print("Decryption test successful!")
		if not update_config:
			print(f"salt: {salt}")
			print(f"crypted email password: {crypto.crypted_key_secret}")
		else:
			config=toml.load("parking_validator.conf")
			config['reports']['salt']=salt.decode('utf-8')
			config['reports']['crypted_email_password']=crypto.crypted_key_secret.decode('utf-8')
			toml.dump(config,open("parking_validator.conf",'w+'))
	except:
		print("Decryption test failed!")


if __name__ == "__main__":
	if len(sys.argv)>1:
		if sys.argv[1]=="passwd_token":
			gen_token(update_config=True)
		if sys.argv[1]=="passwd_email":
			gen_email_password(update_config=True)
	else:
		import doctest
		doctest.testmod(extraglobs={'c':Crypto()})
