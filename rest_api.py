import datetime as dt
import base64
import requests
import json

class RestAPI():
	"""
	Generic REST API object
	"""

	def __init__(self,url,secret):
		"""
		Initialize api wrapper and obtain a bearer token
		"""

		self.url=url

		# add a trailing forward slash if necessary
		if self.url[-1]!='/':
			self.url+='/'

		self.secret=secret
		self.bearer_token=None
		self.get_bearer_token()

	def get_bearer_token(self):
		"""
		Get a bearer token object
		"""

		self.bearer_token=BearerToken(url=self.url+"token",secret=self.secret)

	def get_patron(self,barcode="21945001416669"):
		"""
		Make REST API call to get a patron record
		"""

		# request a new bearer token if necessary
		self.bearer_token.refresh()

		# important fields are expirationDate and blockInfo
		url=self.url+f"patrons/find?barcode={barcode}&fields=names,barcodes,expirationDate,blockInfo"
		response=requests.get(url,headers={"Authorization":"Bearer "+self.bearer_token.token},timeout=1)

		return json.loads(response.text)

class BearerToken():
	"""
	Maintains a bearer token
	"""

	def __init__(self,url=None,secret=""):
		"""
		Initialize the bearer token object and obtain a token.
		"""

		# instance variables
		self.url=url
		self.expiration=None
		self.token=None

		# obtain the base64-encoded version of the secret
		if isinstance(secret,str):
			secret=bytes(secret,"utf-8")
		self.secret=base64.encodebytes(secret)[:-1].decode("utf-8")

		if self.url is not None:
			self.get_token()

	def get_token(self):
		"""
		Obtain a bearer token; self.token will remain None if the request doesn't succeed.
		"""

		curtime=dt.datetime.now()
		response=requests.post(self.url,headers={"Authorization":"Basic "+self.secret},timeout=1)

		# check if the request was successful; anything but 200 is failure here
		if response.status_code==200:
			response_dict=json.loads(response.text)
			self.token=response_dict['access_token']
			self.expiration=curtime+dt.timedelta(seconds=int(response_dict['expires_in']))

	def is_expired(self):
		"""
		Check if the bearer token is expired
		"""

		if self.token is None:
			return True
		return dt.datetime.now()>self.expiration+dt.timedelta(seconds=10)

	def refresh(self):
		"""
		Get a new bearer token if the current one is expired.
		"""

		if self.is_expired():
			self.get_token()
