import sys
assert sys.version_info >= (3,6)

import re
import datetime as dt
import hashlib
from patron import Patron


class LibraryCard():
	"""
	Generic library card object.
	"""

	def __init__(self,barcode=None,barcode_length=0,patron=None,expiration=dt.datetime(2020,1,1),blocks=""):
		self.patron=patron
		self.barcode=str(barcode)
		self.hashed_barcode=None
		self.barcode_length=int(barcode_length)
		self.expiration=expiration
		self.blocks=blocks

		# if the barcode isn't valid, set the barcode to none as a clue
		if not self.has_valid_barcode():
			self.barcode=None
		else:
			self.hash_barcode()

	def hash_barcode(self):
		"""
		Generates and stores the SHA-3 512 hash of the barcode

		>>> print(card1.hashed_barcode)
		206363246bac3ae3226a56e20e6132f59beddf7cc19aab2fc3b52ba885ad3e44de55c894202fd223b7c7fa16a69f502c15d74c6fae86d85204c33ba8759efbd0
		"""
		self.hashed_barcode=hashlib.sha3_512(bytes(self.barcode,'utf-8')).hexdigest()

	def is_expired(self):
		"""
		Checks if card has expired.

		>>> card1.is_expired()
		False
		>>> card2.is_expired()
		True
		>>> card3.is_expired()
		True
		"""

		return self.expiration < dt.datetime.now()

	def has_valid_barcode(self):
		"""
		Checks if the barcode is minimally valid (has right number of digits).
		"""

		if self.barcode is None:
			return False

		return re.match(f'^[0-9]{{{self.barcode_length}}}$',str(self.barcode)) is not None

	def has_no_blocks(self):
		"""
		Checks if account has any blocks.
		"""

		return self.blocks == ""

	def has_patron(self):
		"""
		Checks if this card links to a patron object.

		Note that this does not check the validity of the patron object itself.

		>>> card1.has_patron()
		True
		>>> card2.has_patron()
		False
		>>> card3.has_patron()
		False
		"""

		return isinstance(self.patron,Patron)

	def is_valid(self):
		"""
		Composite test of the previous 4 individual checks.

		>>> card1.is_valid()
		True
		>>> card2.is_valid()
		False
		>>> card3.is_valid()
		False
		"""

		return self.has_patron() and self.has_valid_barcode() and not self.is_expired() and self.has_no_blocks()

	def list_properties(self):
		"""
		Gets useful properties of the object as a list of strings.

		Returns a list with alternating string entries: [key, value, ...]
		"""

		disp_list=["card barcode","%s"%(self.barcode)]
		disp_list.extend(["expiration","%s"%(str(self.expiration))])
		return disp_list

class PPLibraryCard(LibraryCard):
	"""
	PPL library card object.
	"""

	def __init__(self,fail_blocks=['g'],**kw):
		"""
		Initialize `LibraryCard` object with a barcode length of 14.
		"""

		super().__init__(barcode_length=14,**kw)
		self.fail_blocks=fail_blocks

	def has_no_blocks(self):
		"""
		Checks if account has any blocks.

		>>> card1.has_no_blocks()
		True
		>>> card2.has_no_blocks()
		True
		>>> card3.has_no_blocks()
		False
		"""

		for block in self.fail_blocks:
			if self.blocks == block:
				return False
		return True

	def has_valid_barcode(self):
		"""
		Checks if the barcode has the correct first 7 digits, and the correct length overall.

		Parameters
		----------
		None

		Returns
		-------
		boolean

		Examples
		--------
		Test card1
		>>> card1.has_valid_barcode()
		True

		Test card2

		>>> card2.has_valid_barcode()
		False

		Test card3

		>>> card3.has_valid_barcode()
		False
		"""

		if self.barcode is None:
			return False

		return re.match(f'^2194500[0-9]{{{self.barcode_length-7}}}$',str(self.barcode)) is not None

if __name__ == "__main__":
	"""
	Test the code in this file
	"""
	import doctest
	doctest.testmod(extraglobs={
		'card1': PPLibraryCard(barcode="21945001234567", expiration=dt.datetime(3020,1,1), patron=Patron()),
		'card2': PPLibraryCard(barcode="21845001234567"),
		'card3': PPLibraryCard(barcode="",blocks="g")
		})
