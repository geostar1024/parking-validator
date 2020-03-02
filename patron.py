import datetime as dt

class Patron():
	"""
	Generic library patron object.
	"""

	def __init__(self,first_name="default",last_name="patron", card=None, validations=0, max_validations=1, last_validation=None, validation_interval=2*3600):
		"""
		Initialize the patron with sensible defaults.
		"""

		self.first_name=first_name
		self.last_name=last_name
		self.card=card

		# validations is an integer, potentially allowing for multiple validations each day
		self.validations=int(validations)

		# last validation is the timestamp when the last validation took place; could be None
		self.last_validation=last_validation

		# validation interval is number of seconds between allowed validations
		self.validation_interval=int(validation_interval)

		# maximum validations per day
		self.max_validations=int(max_validations)

	# returns true if validation is possible for this patron
	def can_be_validated(self):
		"""
		Checks whether this patron is eligible for validation

		Successful validation requires:
			-max validations have not been reached
			-library card is valid
			-previous validation (if any) has expired
		"""

		# nonexistent library card is automatic failure; usually shouldn't happen
		if self.card is None:
			return False

		if self.last_validation is not None:
			if (dt.datetime.now()-self.last_validation).total_seconds()<self.validation_interval:
				return False

		return self.validations < self.max_validations and self.card.is_valid()

	def list_properties(self):
		"""
		Gets useful properties of the object as a list of strings.

		Returns a list with alternating string entries: [key, value, ...]
		"""

		disp_list=["patron name","%s %s"%(self.first_name,self.last_name)]
		if self.card is None:
			disp_list.extend(["card","None"])
		else:
			disp_list.extend(self.card.list_properties())
		disp_list.extend(["validations","%d/%d"%(self.validations,self.max_validations)])
		disp_list.append("last validation")
		if self.last_validation is None:
			disp_list.append("None")
		else:
			disp_list.append(self.last_validation.strftime("%H:%M:%S"))
		return disp_list
