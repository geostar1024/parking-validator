import datetime as dt
from enum import Enum
import sqlite3
import hashlib
import csv
import numpy as np

class SQLite3Database():
	"""
	Wrapper for sqlite3 database access.

	Implicitly requires some knowledge of what fields are available in the Patron and LibraryCard objects
	"""

	def __init__(self,database_file):
		"""
		Initialize the wrapper object.

		Note that the database connection is *not* opened here
		"""

		self.database_file=database_file
		self.db=None
		self.db_cursor=None

	class Logs(Enum):
		"""
		Predefined log strings, intended for log table.
		"""

		PATRONS_RESET="patron db reset"
		VALIDATION_SUCCESS="success"
		ADMIN_MODE="admin on"
		VALIDATION_FAIL="fail"

	def open_db(self):
		"""
		Open database connection, specifying that additional field types are to be parsed.
		"""

		self.db=sqlite3.connect(self.database_file,detect_types=sqlite3.PARSE_DECLTYPES)
		self.db_cursor=self.db.cursor()

	def close_db(self):
		"""
		Close database connection.
		"""

		self.db.close()

	def create_patron_table(self):
		"""
		Creates patron table if it doesn't already exist.
		"""

		self.db_cursor.execute("CREATE TABLE IF NOT EXISTS patrons(id INTEGER PRIMARY KEY, hashed_barcode TEXT unique, blocks TEXT, validations INTEGER, last_validation TIMESTAMP)")
		self.db.commit()

	def drop_patron_table(self,run=False):
		"""
		Drops the entire patron table.

		CAUTION: be careful to only run this when intending to clear the patron database
		"""

		if not run:
			return

		# possibly the patron table might not exist
		try:
			self.db_cursor.execute("DROP TABLE patrons")
		except sqlite3.OperationalError:
			pass
		self.db.commit()

	def insert_patron(self,patron):
		"""
		Attempts to insert a new patron record into the patron table of the local database.

		If the barcode already exists, then update the existing record instead
		"""

		try:
			self.db_cursor.execute("INSERT INTO patrons(hashed_barcode,blocks) VALUES(?,?)",(patron.card.hashed_barcode,patron.card.blocks))

		# should only raise an error if patron is already in the local database
		except sqlite3.IntegrityError:
			self.db_cursor.execute("UPDATE patrons set blocks = ? WHERE hashed_barcode = ?",(patron.card.blocks,patron.card.hashed_barcode))
		self.db.commit()

	def reset_patron_validation(self,patron):
		"""
		Reset the validations count and last validation time for the specified patron.
		"""

		self.db_cursor.execute("UPDATE patrons SET validations = ?, last_validation = ? WHERE hashed_barcode = ?",(0,None, patron.card.hashed_barcode))
		self.db.commit()

	def retrieve_patron_validations(self,patron):
		"""
		Obtain the validations count and last validation time for the specified patron.

		Note that this modifies the patron object directly.
		"""

		self.db_cursor.execute("SELECT validations, last_validation from patrons WHERE hashed_barcode = ?",(patron.card.hashed_barcode,))
		raw_results=self.db_cursor.fetchone()
		if raw_results[0] is None:
			patron.validations=0
		else:
			patron.validations=raw_results[0]
		patron.last_validation=raw_results[1]

	def do_patron_validation(self,patron):
		"""
		Do validation for the specified patron, on the database end of things.

		Also puts a validation entry into the log table.
		"""

		self.db_cursor.execute("UPDATE patrons SET validations = ?, last_validation = ? WHERE hashed_barcode = ?",(patron.validations, patron.last_validation, patron.card.hashed_barcode))
		self.log_validation()
		self.db.commit()

	def create_log_table(self):
		"""
		Creates the log table in the local database.
		"""

		self.db_cursor.execute("CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY, datetime TIMESTAMP unique, comment TEXT)")
		self.db.commit()

	def log_entry_at_time(self,timestamp,comment):
		"""
		Inserts the specified comment with the specified timestamp into the log table.

		Timestamp should be standard datetime object.
		"""

		self.db_cursor.execute("INSERT INTO log(datetime,comment) VALUES (?,?)",(timestamp,comment))
		self.db.commit()

	def log_entry(self,comment):
		"""
		Inserts the specified comment with the current timestamp into the log table.
		"""

		self.log_entry_at_time(dt.datetime.now(),comment)

	def log_validation(self):
		"""
		Inserts a validation entry into the log table (shortcut method).
		"""

		self.log_entry(self.Logs.VALIDATION_SUCCESS.value)

	def log_reset(self):
		"""
		Inserts a patron database reset entry into the log table (shortcut method).
		"""

		self.log_entry(self.Logs.PATRONS_RESET.value)

	def log_admin(self):
		"""
		Inserts an admin mode active entry into the log table (shortcut method).
		"""

		self.log_entry(self.Logs.ADMIN_MODE.value)

	def log_fail(self):
		"""
		Inserts a validation failed entry into the log table (shortcut method).
		"""

		self.log_entry(self.Logs.VALIDATION_FAIL.value)

	def drop_log_table(self,run=False):
		"""
		Drop the log table.

		CAUTION: be sure you really want to execute this since it could remove a lot of records!
		"""

		if not run:
			return

		try:
			self.db_cursor.execute("DROP TABLE log")
			self.db.commit()
		except:
			print("table doesn't exist!")

	def get_log_size(self):
		"""
		Gets the number of records in the log table as an integer.
		"""

		self.db_cursor.execute("SELECT Count(*) FROM log")
		return int(self.db_cursor.fetchone()[0])

	def get_last_reset(self):
		"""
		Get the last time a patron database reset entry was made in the log table.

		Note: could be None if no entry exists (if the table was just made)
		"""

		self.db_cursor.execute("SELECT datetime from log where comment = ? order by datetime desc",(SQLite3Database.Logs.PATRONS_RESET.value,))
		reset=self.db_cursor.fetchone()
		if reset is None:
			return None
		else:
			return reset[0]

	def get_data_type_between(self,datetime1,datetime2,data_type=None):
		"""
		Get all the entries of the specified type between the specified timestamps.

		Returns a list of datetime.datetime objects
		"""

		if data_type is None:
			data_type=SQLite3Database.Logs.VALIDATION_SUCCESS.value

		self.db_cursor.execute("SELECT datetime FROM log where comment = ? AND datetime BETWEEN ? AND ?",(data_type,datetime1,datetime2))
		records=[]
		for record in self.db_cursor.fetchall():
			records.append(record[0])
		return records


	def get_num_validations_between(self,datetime1,datetime2):
		"""
		Get the number of validation entries between the specified timestamps.

		Returns an integer
		"""

		self.db_cursor.execute("SELECT Count(*) FROM log where comment = ? AND datetime BETWEEEN ? AND ?",(SQLite3Database.Logs.VALIDATION_SUCCESS.value,datetime1,datetime2))
		return int(self.db_cursor.fetchone()[0])

	def get_validations_between(self,datetime1,datetime2):
		"""
		Get all the validation entries between the specified timestamps.

		Returns a list of datetime.datetime objects
		"""

		return self.get_data_type_between(datetime1,datetime2,data_type=SQLite3Database.Logs.VALIDATION_SUCCESS.value)

	def get_failed_between(self,datetime1,datetime2):
		"""
		Get all the failed entries between the specified timestamps.

		Returns a list of datetime.datetime objects
		"""

		return self.get_data_type_between(datetime1,datetime2,data_type=SQLite3Database.Logs.VALIDATION_FAIL.value)

	def get_admin_between(self,datetime1,datetime2):
		"""
		Get all the admin entries between the specified timestamps.

		Returns a list of datetime.datetime objects
		"""

		return self.get_data_type_between(datetime1,datetime2,data_type=SQLite3Database.Logs.ADMIN_MODE.value)

	def get_num_validations_since(self,datetime):
		"""
		Get the number of validation entries between now and the specified timestamp.

		Returns an integer
		"""

		return self.get_num_validations_between(datetime,dt.datetime.now())

	def get_num_validations_since_reset(self):
		"""
		Get the number of validation entries between now and the last reset timestamp.

		Returns an integer
		"""

		return self.get_num_validations_since(self.get_last_reset())

	def get_validations_since(self,datetime):
		"""
		Get all the validation entries between now and the specified timestamp.

		Returns a list of datetime.datetime objects
		"""

		return self.get_validations_between(datetime,dt.datetime.now())

	def get_validations_since_reset(self):
		"""
		Get all the validation entries between now and the last reset timestamp.

		Returns a list of datetime.datetime objects
		"""

		return self.get_validations_since(self.get_last_reset())

	def hist_between(self,date1=dt.datetime(2020,11,1),date2=dt.datetime(2020,12,1),data_type="validation",start_hour=6,end_hour=21):
		"""
		Generates CSV file with one histogram per line, in the reports directory (hardcoded to "reports" for now)

		Histogram is of specified data for a given day between the specified starting and ending hours

		Data range is between the two input dates, not including the end date

		Returns the total number of instances of the specified data as well as the filename

		"""
		days=(date2-date1).days
		total=0

		csv_file=f"reports/{data_type}-{date1:%Y-%m-%d}-to-{date2-dt.timedelta(days=1):%Y-%m-%d}.csv"
		with open(csv_file,"w+",newline='') as fpw:
			csvwriter=csv.writer(fpw,delimiter=',')
			csvwriter.writerow(["day\\hour"]+list(range(start_hour,end_hour)))

			for day in range(0,days):
				start_date=date1+dt.timedelta(days=day)
				end_date=date1+dt.timedelta(days=day+1)

				#print(start_date,end_date)

				# get data from database
				if data_type=="validation":
					data=self.get_validations_between(start_date,end_date)
				elif data_type=="admin":
					data=self.get_admin_between(start_date,end_date)
				else:
					data=self.get_failed_between(start_date,end_date)

				# keep track of the total entries
				total+=len(data)

				# extract hour
				hours=np.zeros(len(data))

				for k,entry in enumerate(data):
					hours[k]=entry.hour

				# returns frequencies and bin edges
				hist=np.histogram(hours,range(start_hour,end_hour+1))

				# write line to csv file
				csvwriter.writerow([start_date.strftime("%Y-%m-%d")]+list(hist[0]))

		return total,csv_file
