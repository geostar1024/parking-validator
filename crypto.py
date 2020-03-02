import cryptography
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Crypto():
	"""
	Helper class that holds a Fernet instance and decrypts the REST API keys

	Note that the salt is hardcoded here right now
	If the salt is changed, the encrypt method should be used to generate new tokens

	"""
	def __init__(self, crypted_key=b'gAAAAABeWxn1q0ehfaEt-3bcDQu3fkVKVtd3D8P-ENpNSSfDjaIKNB4mSeHqvidKaiY1VuuLgAGB19oI6vRSiL84ocj9zWcXAw==', crypted_secret=b'gAAAAABeWxorEzRGnR0UNM91MhHl1S9lM64AavasJOUVXoxQ12B8aSQnARGriSqwZRpjx5gYxwBKQaQcH4SWD9OFCTq1m9J8sQ==', password="password", salt=b'\xe8\x17\x99\x83\x94\xa6\xa7\xcf\x98\xefR\x80\xb4\x86|I'):
		self.crypted_key=crypted_key
		self.crypted_secret=crypted_secret
		self.password=password.encode('utf-8')

		self.setup_fernet(salt=salt)


	def setup_fernet(self,salt=None):
		"""
		Helper function to set up the Fernet instance

		"""

		if salt is None:
			salt=self.gensalt()
		kdf=PBKDF2HMAC(
			algorithm=hashes.SHA256(),
			length=32,
			salt=salt,
			iterations=100000,
			backend=default_backend()
		)
		self.key=base64.urlsafe_b64encode(kdf.derive(self.password))
		self.fernet=Fernet(self.key)

	def encrypt(self,text=None,gensalt=True):
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
		return self.fernet.decrypt(self.crypted_key)+b':'+self.fernet.decrypt(self.crypted_secret)

	def gensalt(self,length=16):
		"""
		Generate a random salt, 16 bytes in length by default

		"""
		return os.urandom(length)

if __name__ == "__main__":
	import doctest
	doctest.testmod(extraglobs={'c':Crypto()})

