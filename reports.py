import numpy as np
import datetime as dt
import csv
from database import SQLite3Database
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText



def send_report_email(validations=0,failures=0,admin=0,date1=dt.datetime(2020,11,1),date2=dt.datetime(2020,12,1),source_email=None,destination_emails=None,email_password=None,attachments=None):
	"""
	Sends an email reporting on the parking validation statistics

	This requires a gmail account with 2FA set up so that app passwords can be used
	The app password should be encrypted by running

		python crypto.py passwd_email

	(this will insert the encrypted password into the config file as well)

	TODO: clean this up a bit and rework the function arguments; maybe should be a proper class?
	"""

	if source_email is None or destination_emails is None or email_password is None:
		print("Failed to send email; one or more required emails and/or passwords was invalid!")
		return

	# body of the email
	mail_content = f"This is your monthly automated parking validation report.\n\ntotal successful validations: {validations}\ntotal failed attempts: {failures}\ntotal admin mode activations: {admin}\n\nDetailed hourly data is attached."

	# setup the MIME
	msg = MIMEMultipart()

	# fill out the fields
	msg['From'] = source_email
	msg['To'] = f"{','.join(destination_emails)}"
	msg['Subject'] = f"Parking Validation Report for {date1:%Y-%b}"

	# insert the body of the email
	msg.attach(MIMEText(mail_content, 'plain'))

	# go through the specified attachments and attach them
	# strictly speaking, this is a bit overkill for simply attaching CSV files, but it can handle other attachment types too
	if attachments is not None:
		for filename in attachments:

			ctype, encoding = mimetypes.guess_type(filename)
			if ctype is None or encoding is not None:
				ctype = "application/octet-stream"

			maintype, subtype = ctype.split("/", 1)

			if maintype == "text":
				fp = open(filename)
				# Note: we should handle calculating the charset
				attachment = MIMEText(fp.read(), _subtype=subtype)
				fp.close()
			elif maintype == "image":
				fp = open(filename, "rb")
				attachment = MIMEImage(fp.read(), _subtype=subtype)
				fp.close()
			elif maintype == "audio":
				fp = open(filename, "rb")
				attachment = MIMEAudio(fp.read(), _subtype=subtype)
				fp.close()
			else:
				fp = open(filename, "rb")
				attachment = MIMEBase(maintype, subtype)
				attachment.set_payload(fp.read())
				fp.close()

			attachment.add_header("Content-Disposition", "attachment", filename=filename)
			msg.attach(attachment)

	#Create SMTP session for sending the mail
	session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
	session.starttls() #enable security
	session.login(source_email, email_password) #login with mail_id and password
	session.sendmail(source_email, f"{','.join(destination_emails)}", msg.as_string())
	session.quit()
	print(f"report email for {date1:%Y-%b} sent!")



# functions to work on a dummy database to test report generation (actual function in database class)

def custom_db(db_file="test.db"):
	"""
	Create custom test db

	"""
	db=SQLite3Database(db_file)
	db.open_db()

	# create log table
	db.create_log_table()
	return db

def generate_random_log(db,num_start=15,num_end=75,hour_start=8,hour_end=18,day_start=1,day_end=30):
	"""
	Generate random log entries for custom db

	"""
	rng=np.random.default_rng()
	for j in range(day_start,day_end+1):
		for k in range(rng.integers(num_start,num_end)):
			h=rng.normal(hour_start+(hour_end-hour_start)/2,(hour_end-hour_start)/2/4)
			hour=int(h)
			minute=int((h-hour)*60)
			second=int((h-hour-minute/60)*60)
			date=dt.datetime(2020,11,j,hour,minute,second,rng.integers(0,9999))
			db.log_entry_at_time(date,db.Logs.VALIDATION_SUCCESS.value)


if __name__ == "__main__":
	db=custom_db()

	reset=False

	if reset:
		db.drop_log_table(run=True)
		db.create_log_table()
		generate_random_log(db)

	date1=dt.datetime(2020,11,1)
	date2=dt.datetime(2020,12,1)

	validations=db.hist_between(date1=date1,date2=date2,data_type="validation")
	failures=db.hist_between(date1=date1,date2=date2,data_type="failed")
	admin=db.hist_between(date1=date1,date2=date2,data_type="admin")
