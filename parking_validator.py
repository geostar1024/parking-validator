import sys

assert sys.version_info >= (3,6)

import tkinter as tk
import os
import re
import datetime as dt
from enum import Enum
import toml
import getpass
import time
#import configparser

from validator_interface import Header,LabeledBox,LabeledSplitBox,KeyInput,KeyInput2,TimerClock,ValidatorClock
from library_card import PPLibraryCard
from patron import Patron
from database import SQLite3Database
from rest_api import RestAPI
from powerusb import PowerUSB
from crypto import Crypto

class ParkingValidator(tk.Frame):
	"""
	Parking validation application

	Configurable variables are found at the top of __init__
	"""

	class ErrorMsgs(Enum):
		"""
		Predefined error strings, intended for the status box.
		"""
		ERROR="ERROR:"
		STAFF="Please see a staff member at the Checkout Desk"
		GET_HELP="Please ask circulation for assistance."
		EXPIRED_CARD=f"{ERROR} Card Expired.\n\n{STAFF} to renew your card."
		NONEXISTENT_CARD=f"{ERROR} Card Not in System.\n\n{STAFF}."
		MAXIMUM_VALIDATIONS=f"{ERROR} Already Validated Today.\n\n{STAFF} if further assistance is needed."
		COMM_ERROR=f"{ERROR} Unable to contact remote patron database!\n\n{GET_HELP}"
		UNSPECIFIED_CARD=f"{ERROR} unspecified card problem!\n\n{GET_HELP}"
		ACCOUNT_HOLD=f"{ERROR} Account Has a Block.\n\n{GET_HELP}"
		UNSPECIFIED_ACCOUNT=f"{ERROR} unspecified account problem!\n\n{GET_HELP}"
		BARCODE=f"{ERROR} Invalid barcode characters/length!"
		CONSECUTIVE_FAILURES=f"{ERROR} Too many scanning errors!\n\n{GET_HELP}"
		TOO_SOON=f"{ERROR} Previous parking validation has not yet expired!\n\nPlease try again at:"
		NO_ERROR="No errors detected.\n"

		def __str__(self):
			return self.value

	class Messages(Enum):
		"""
		Predefined message strings, mostly for status and patron display boxes.
		"""

		TITLE="Princeton Public Library Parking Validation System"
		ABBREVIATION="PPLPVS"
		SCAN_CARD="READY: Please scan card."
		BLANK="\n\n\n\n"
		VALIDATION_ALLOWED="SUCCESS: valid patron account detected!\n\nPress [+] to validate."
		INSERT_TICKET="Validation process started.\n\nPlease insert ticket into validation machine."
		VALIDATION_SUCCESS="SUCCESS: parking validation successful!\n\nHave a nice day!"
		ADMIN_MODE="Admin mode active!\n\n[+] to run validation machine.\n\n[-] to reset daily validations for current card.\n\n[*] to exit admin mode."
		DEBUG_MODE="Debug mode active!\n"

		def __str__(self):
			return self.value

	def __init__(self,root,**kw):
		"""
		Initialize parking validator; top-level object is a tkinter Frame.
		"""
		super().__init__(root,**kw)
		self.version=0.14
		self.updated=dt.datetime(2020,11,14)

		###############################
		# user-configurable variables #
		###############################

		# sensible defaults are given in case a config file can't be found
		# though, note that the REST API client key and secret are not hardcoded here

		# database file name (will be created if it doesn't exist)
		self.db_file="parking_validator.db"

		# maximum values:
		# 2 validations per day
		# 2 hours between validations
		# 5 consecutive card scan failures
		# 5 seconds between scan attempts after lockout
		self.max_validations=2
		self.validation_interval=2*3600
		self.failures_threshold=5
		self.lockout_time=5

		# time interval values:
		# 24 hours between local database patron clears
		# 5 seconds between maintenance ticks
		# 30 seconds between input clears
		self.db_reset_interval=24*3600
		self.maintenance_interval=5*1000
		self.scan_interval=30
		self.validate_interval=20

		# admin and debug barcodes; none by default
		self.admin_barcodes=[]
		self.debug_barcodes=[]

		# debug mode enables various extra fields and buttons for testing
		self.debug_mode=False
		self.admin_mode=False
		self.fullscreen=True
		self.widget_bg="#F3F3F3"
		self.window_bg="#272727"
		self.widget_fg="#000"

		# REST API values
		self.rest_api_url=""
		self.rest_api_key=""
		self.crypted_key=""
		self.crypted_secret=""
		self.salt=""

		# update config values from config file
		self.load_config()

		# decrypt REST API client key and secret
		self.decrypt_api_key(root)

		###############################
		# internal instance variables #
		###############################

		# API variable
		self.api=None

		# patron and card variables
		self.card=None
		self.patron=None

		# status variables
		self.consecutive_failures=0
		self.last_scan_time=dt.datetime.now()
		self.validator_button_visible=False

		# UI defaults
		self.title_font=('Helvetica',25,'bold')
		self.default_font=('Helvetica',14)
		self.default_geom_kw={'sticky':'WENS','padx':5,'pady':20}
		self.default_style_kw={'borderwidth':5,'fg':self.widget_fg,'bg':self.widget_bg,'label_fg':self.widget_fg,'relief':tk.FLAT,}
		self.keybinds={'0':"0",'1':"1",'2':"2",'3':"3",'4':"4",'5':"5",'6':"6",'7':"7",'8':"8",'9':"9", '<KP_0>':"0",'<KP_1>':"1",'<KP_2>':"2",'<KP_3>':"3",'<KP_4>':"4", '<KP_5>':"5",'<KP_6>':"6",'<KP_7>':"7",'<KP_8>':"8",'<KP_9>':"9", '<KP_Insert>':"0",'<KP_End>':"1",'<KP_Down>':"2",'<KP_Next>':"3",'<KP_Left>':"4", '<KP_Begin>':"5",'<KP_Right>':"6",'<KP_Home>':"7",'<KP_Up>':"8",'<KP_Prior>':"9"}

		# barcode hide
		self.hide_len=3

		####################
		# begin setup code #
		####################

		# open PowerUSB device
		self.powerusb=PowerUSB()

		# create the UI
		self.create_widgets()

		# turn off debug mode at start
		#self.debug_mode_on()
		self.reset_interface()
		self.debug_mode_off()
		#self.debug_mode_on()

		# make sure we can quit using the keyboard
		root.bind_all('<KP_Divide>',self.admin_quit)
		root.bind_all('<Escape>',self.quit)

		# keybinds for admin/debug mode
		root.bind_all('<plus>',self.do_validation_callback)
		root.bind_all('<KP_Add>',self.do_validation_callback)
		root.bind_all('<minus>',self.admin_reset_validation)
		root.bind_all('<KP_Subtract>',self.admin_reset_validation)
		root.bind_all('<asterisk>',self.debug_mode_off_callback)
		root.bind_all('<KP_Multiply>',self.debug_mode_off_callback)

		# make a REST API connection
		self.api=RestAPI(url=self.rest_api_url,secret=self.rest_api_key)


		# turn off validator
		#self.powerusb.off()

		# open database file and get a cursor
		self.db=SQLite3Database(self.db_file)
		self.db.open_db()

		# create log table
		self.db.create_log_table()
		if self.db.get_last_reset() is None:
			# do a reset of the patron table if the log table was empty
			self.db.insert_reset_entry()
			self.db.drop_patron_table(run=True)

		# initialize the patron table if it's not there already
		self.db.create_patron_table()
		self.reset_interface()
		self.maintenance_tick()

	def decrypt_api_key(self,root):
		"""
		Obtain the REST API encryption password from the user and run decryption.

		"""

		# first hide the main window so that the password can be entered
		root.withdraw()

		# prompt for the password with echoing turned off
		password=getpass.getpass("password for REST API key: ")

		# get Crypto object
		crypto=Crypto(crypted_key_secret=self.crypted_key_secret,password="password",salt=self.salt)

		# attempt decryption; display error and exit upon any failure
		# most likely failure is incorrect password
		try:
			self.rest_api_key=crypto.decrypt()
		except:
			print("Decryption of REST API client key and secret failed!")
			exit()

		# if decryption succeeded, restore the main window
		root.update()
		root.deiconify()

	def load_config(self,config_file="parking_validator.conf"):
		"""
		Loads configuration settings.
		"""

		config=toml.load(config_file)


		# load validation config values
		self.max_validations=int(config['validation']['max validations per day'])
		self.validation_interval=int(config['validation']['hours between validations']*3600)
		self.scan_interval=int(config['validation']['interface timeout in seconds'])
		self.validate_interval=int(config['validation']['validate timeout in seconds'])

		# load general config values
		self.maintenance_interval=int(config['general']['maintenance interval in seconds']*1000)
		self.fullscreen=config['general']['fullscreen']
		self.widget_bg=config['general']['widget background color']
		self.window_bg=config['general']['window background color']
		self.widget_fg=config['general']['widget text color']

		# load failure config values
		self.failures_threshold=config['failures']['threshold']
		self.lockout_time=config['failures']['lockout time']

		# load database config values
		self.db_file=config['database']['filename']
		self.db_reset_interval=int(config['database']['reset interval']*3600)

		# load admin barcodes
		self.admin_barcodes=config['admin barcodes']['admin']
		if self.admin_barcodes==[""]:
			self.admin_barcodes=[]
		self.debug_barcodes=config['admin barcodes']['debug']
		if self.debug_barcodes==[""]:
			self.debug_barcodes=[]

		# load REST API config values
		self.rest_api_url=config['sierra rest api']['url']
		self.crypted_key_secret=config['sierra rest api']['crypted_key_secret'].encode('utf-8')
		#self.crypted_key=config['sierra rest api']['crypted_key'].encode('utf-8')
		#self.crypted_secret=config['sierra rest api']['crypted_secret'].encode('utf-8')
		self.salt=config['sierra rest api']['salt'].encode('utf-8')

	def maintenance_tick(self):
		"""
		Runs tasks periodically; interval determined by maintenance_interval above.

		Current tasks:
			-drop and recreate patron table every day
			-reset UI every so often for security
		"""

		# drop and recreate patron table when enough time has elapsed; disabled if interval is zero
		if (dt.datetime.now()-self.db.get_last_reset()).total_seconds()>self.db_reset_interval and self.db_reset_interval>0:
			self.db.drop_patron_table()
			self.db.create_patron_table()
			self.db.insert_reset_entry()

		# reset the interface for security every so often
		# the interval should be long enough for a patron to reasonably complete validation after scanning a card

		if (dt.datetime.now()-self.last_scan_time).total_seconds()>self.scan_interval:

			# disable debug/admin mode after timeout
			self.debug_mode_off()
			self.reset_interface()
			self.last_scan_time=dt.datetime.now()

		self.after(self.maintenance_interval,self.maintenance_tick)

	def create_widgets(self):
		"""
		Create all UI elements.
		"""

		gutter=30
		radius=30
		width=None
		if self.fullscreen is True:
			width=int(self.winfo_toplevel().winfo_screenwidth()/(self.title_font[1]-1.75))

		# toplevel canvas element to contain rounded-corner
		screen_width=1366
		screen_height=768
		self.canvas=tk.Canvas(root,bg=self.window_bg,relief=tk.FLAT,bd=0, highlightthickness=0, width=screen_width,height=screen_height)
		self.canvas.grid(sticky="NSEW")



		def round_rectangle(x, y, width, height, radius=radius, **kwargs):
			x1=x
			y1=y
			x2=x+width
			y2=y+height

			points = [	x1+radius, y1,
						x1+radius, y1,
						x2-radius, y1,
						x2-radius, y1,
						x2, y1,
						x2, y1+radius,
						x2, y1+radius,
						x2, y2-radius,
						x2, y2-radius,
						x2, y2,
						x2-radius, y2,
						x2-radius, y2,
						x1+radius, y2,
						x1+radius, y2,
						x1, y2,
						x1, y2-radius,
						x1, y2-radius,
						x1, y1+radius,
						x1, y1+radius,
						x1, y1]

			return self.canvas.create_polygon(points, **kwargs, smooth=True)

		self.logo_image=tk.PhotoImage(file='resources/logo.png')
		self.logo_image=self.logo_image.subsample(2)

		# section dimensions
		column_width=int((screen_width-3*gutter)/2)
		card_height=320
		status_height=screen_height-3*gutter-card_height
		info_height=screen_height-2*gutter

		# create section rectangles
		self.card_section=round_rectangle(gutter,gutter,column_width,card_height, fill=self.widget_bg)
		self.status_section=round_rectangle(gutter,gutter*2+card_height,column_width,status_height, fill=self.widget_bg)
		self.info_section=round_rectangle(gutter*2+column_width,gutter,column_width,screen_height-2*gutter, fill=self.widget_bg)

		# card section
		self.logo=self.canvas.create_image(column_width/2+gutter,gutter+radius, image=self.logo_image,anchor="n")

		self.card_text_var=tk.StringVar()
		self.card_text_var.set("Welcome.\n\nPlease scan your Princeton Public Library card,\nor enter your 14-digit barcode.")
		self.card_text_label=tk.Label(root,textvariable=self.card_text_var,bg=self.widget_bg, wraplength=column_width-2*radius,justify=tk.LEFT,font=self.default_font)
		self.card_text=self.canvas.create_window(gutter+radius,gutter+radius+80,anchor="nw", width=column_width-2*radius,window=self.card_text_label)

		self.status_title=self.canvas.create_text(gutter+radius,gutter*2+radius+card_height,text="Status Messages",font=self.default_font,anchor="nw")

		self.info_text_1=self.canvas.create_text(gutter*2+column_width+radius,gutter+radius,text="Parking Validation Instructions",font=('Helvetica',20,'bold'),anchor="nw")

		self.info_text_2=self.canvas.create_text(gutter*2+column_width+radius,gutter+radius+50,text="How to Validate Your Ticket for the Spring Street Garage",font=('Helvetica',15,'bold'),anchor="nw")

		self.info_text_3=self.canvas.create_text(gutter*2+column_width+radius,gutter+radius+80,text=f"1. Scan your Princeton Public Library card or enter your 14-digit barcode.\n\n2. If your library card is valid, the screen will say to press \"+\" (plus sign). Have your parking ticket ready before pressing the button. (If the card is invalid, you will receive an error message telling you why. Please see a staff member at the Checkout Desk.)\n\n3. Please wait a moment for the \"insert ticket\" instruction to appear.\n\n4. Insert your ticket for validation. You will have {self.validate_interval} seconds, indicated by the timer.\n\n5. Retrieve validated ticket. There should be a third barcode printed in the middle.\n\n6. Insert the ticket in one of the pay machines in the Spring Street Garage before you go to your car, to make sure the two hours were credited. For further help, see below.",font=('Helvetica',12),anchor="nw",width=column_width-2*radius)

		self.info_text_4=self.canvas.create_text(gutter*2+column_width+radius,gutter+radius+380, text="Things to Know",font=('Helvetica',15,'bold'),anchor="nw")

		self.info_text_5=self.canvas.create_text(gutter*2+column_width+radius,gutter+radius+410,text="● Validation gives Princeton Public Library cardholders one two-hour session of free parking per day in the Spring Street Garage, during library hours.\n\n● It does not matter when you validate. The stamp credits two hours from the time on the ticket.\n\n● Parking is free for anyone who is in and out of the garage within 30 minutes.\n\n● If a pay machine says you owe money when you shouldn’t, it didn’t read the stamped barcode. Try inserting the ticket a couple more times. If you still have trouble, please visit the Customer Service Office on the Spring Street side of the garage.",font=('Helvetica',12),anchor="nw",width=column_width-2*radius)

		# status section

		self.status_patron_var=tk.StringVar()
		self.status_patron_label=tk.Label(root,textvariable=self.status_patron_var,bg=self.widget_bg,wraplength=column_width-2*radius,justify=tk.LEFT,anchor="nw",font=('Helvetica',20,'bold'))
		self.status_patron=self.canvas.create_window(gutter+radius,gutter*2+radius+card_height+30,anchor="nw", width=column_width-2*radius,window=self.status_patron_label)

		# status text
		self.status_text_var=tk.StringVar()
		self.status_text_label=tk.Label(root,textvariable=self.status_text_var,bg=self.widget_bg,wraplength=column_width-2*radius,justify=tk.LEFT,anchor="nw",font=('Helvetica',20,'bold'))

		self.status_text_var.set(ParkingValidator.Messages.SCAN_CARD)

		self.status_text=self.canvas.create_window(gutter+radius,gutter*2+radius+card_height+80,anchor="nw", width=column_width-2*radius,window=self.status_text_label)

		#self.card_input_var=tk.StringVar()
		#self.card_input_entry=tk.Entry(root,textvariable=self.card_input_var, command=self.validate_barcode,keybinds=self.keybinds,exportselection=0)
		#self.card_input=canvas.create_window(gutter+radius,gutter+radius+160,anchor="nw", width=column_width-2*radius,window=self.card_input_entry)

		# set window title
		self.winfo_toplevel().title(ParkingValidator.Messages.TITLE.value)
		self.winfo_toplevel().config(bg=self.window_bg)

		# setup validator timer
		# note that this widget controls the powerusb device directly and manipulates the status box, and hence needs references to both
		self.validator_clock=ValidatorClock(root,label_font=('Helvetica',20,'bold'),label_bg=self.widget_bg,font=self.default_font,bg=self.widget_bg,relief=tk.FLAT,borderwidth=0,amount=1, powerusb=self.powerusb, status_var=self.status_text_var,status_start=ParkingValidator.Messages.INSERT_TICKET,status_end=ParkingValidator.Messages.VALIDATION_SUCCESS)
		self.validator=self.canvas.create_window(gutter+column_width-120,gutter*2+radius+card_height,anchor="nw",width=100,window=self.validator_clock)
		self.validator_clock.canvas=self.canvas
		self.validator_clock.canvas_id=self.validator
		self.validator_clock.hide()


		# title/header section

		#self.title=Header(root,f"{ParkingValidator.Messages.TITLE.value} ({ParkingValidator.Messages.ABBREVIATION.value})",font=self.title_font, label_font=self.default_font,width=width,**self.default_style_kw)
		#self.title.grid(row=0,columnspan=2,**self.default_geom_kw)

		# widget that has the keybindings; can effectively be typed in
		self.input_field=KeyInput2(root,callback=self.validate_barcode,keybinds=self.keybinds, font=('Helvetica',40),max_length=PPLibraryCard().barcode_length)
		#if self.debug_mode:

		self.input_field_canvas=self.canvas.create_window(gutter+column_width/2,gutter+radius+190, window=self.input_field, anchor="n")
		#self.input_field.grid(row=2,column=0,**self.default_geom_kw)

		# displays the last valid barcode
		#self.barcode_display_var=tk.StringVar()
		self.barcode_display = LabeledBox(root,title="Last valid barcode",text="<none>",font=self.default_font,**self.default_style_kw)
		self.barcode_display_canvas=self.canvas.create_window(gutter+column_width-200,screen_height-gutter-radius-40,anchor="nw",window=self.barcode_display)
		#self.barcode_display_var.set("<none>")
		self.canvas.itemconfig(self.barcode_display_canvas,state="hidden")
		#if self.debug_mode:
		#self.barcode_display.grid(row=2,column=1,**self.default_geom_kw)

		# displays patron information (merge of local and remote databases)
		#self.patron_display_left_var=tk.StringVar()
		#self.patron_display_right_var=tk.StringVar()
		self.patron_display=LabeledSplitBox(root,title="Patron Information",text_left="",text_right="",font=self.default_font, **self.default_style_kw)
		self.patron_display_canvas=self.canvas.create_window(gutter+radius,gutter*2+radius+card_height+120,anchor="nw", width=column_width-2*radius,window=self.patron_display)
		self.canvas.itemconfig(self.patron_display_canvas,state="hidden")
		#self.patron_display_right_var.set("")
		#self.patron_display_left_var.set("")
		#self.patron_display.grid(row=3,column=0,columnspan=2,**self.default_geom_kw)

		# displays status messages/errors
		#self.status=LabeledBox(root,title="Status",text=ParkingValidator.ErrorMsgs.NO_ERROR, font=self.default_font,**self.default_style_kw)
		#self.status.grid(row=4,column=0,columnspan=2,**self.default_geom_kw)

		# proxy for validation machine
		self.validator_button=tk.Button(root,text="run machine [+]",command=self.do_validation)
		#if self.debug_mode or self.admin_mode:
		#self.validator_button.grid(row=5,column=1,**self.default_geom_kw)

		# admin override to reset validation count
		self.reset_validation_button=tk.Button(root,text="admin reset [-]",command=self.reset_validation)
		#if self.debug_mode or self.admin_mode:
		#self.reset_validation_button.grid(row=5,column=0,**self.default_geom_kw)

		# version information
		self.footer_text=self.canvas.create_text(gutter+radius,screen_height-gutter-radius,text=f"{ParkingValidator.Messages.ABBREVIATION.value} version {self.version}; last updated {self.updated:%Y-%m-%d}",font=('Helvetica',10,'italic'),anchor="nw")


	def debug_mode_on(self):
		"""
		Turn on debug mode (turns on admin mode too).

		"""

		self.admin_mode_on()
		self.consecutive_failures=0
		self.debug_mode=True
		#self.barcode_display.grid()
		self.canvas.itemconfig(self.patron_display_canvas,state="normal")
		self.canvas.itemconfig(self.barcode_display_canvas,state="normal")
		#self.input_field.grid()
		self.status_text_var.set(ParkingValidator.Messages.DEBUG_MODE)

	def debug_mode_off(self):
		"""
		Turn off debug mode (turns off admin mode too).

		"""

		self.admin_mode_off()
		self.debug_mode=False
		#self.barcode_display.grid_remove()
		self.canvas.itemconfig(self.patron_display_canvas,state="hidden")
		self.canvas.itemconfig(self.barcode_display_canvas,state="hidden")
		#self.input_field.grid_remove()
		self.status_text_var.set(ParkingValidator.Messages.SCAN_CARD)

	def debug_mode_off_callback(self,event):
		"""
		Callback function to turn debug mode off via keypress.

		"""

		self.debug_mode_off()

	def admin_mode_on(self):
		"""
		Turn on admin mode

		"""

		self.consecutive_failures=0
		self.admin_mode=True
		self.validator_button_on()
		#self.reset_validation_button.grid()
		self.status_text_var.set(ParkingValidator.Messages.ADMIN_MODE)

	def admin_mode_off(self):
		"""
		Turn off admin mode.

		"""

		self.admin_mode=False
		self.validator_button_off()
		#self.reset_validation_button.grid_remove()
		self.status_text_var.set(ParkingValidator.Messages.SCAN_CARD)
		self.reset_interface()

	def validator_button_on(self):
		self.validator_button_visible=True
		#self.validator_button.grid()

	def validator_button_off(self):
		self.validator_button_visible=False
		#self.validator_button.grid_remove()



	def toggle_debug_mode(self):
		"""
		Toggles debug mode.
		"""

		if self.debug_mode:
			self.debug_mode_off()
		else:
			self.debug_mode_on()

	def toggle_admin_mode(self):
		"""
		Toggles admin mode, allowing access to only manual validation and reset buttons.
		"""

		if self.admin_mode:
			self.admin_mode_off()
		else:
			self.admin_mode_on()

	def reset_interface(self):
		"""
		Reset the UI and prompt to scan a card; usually called after a timeout.

		Return immediately if a lockout is in effect
		"""

		self.card=None
		self.patron=None

		if self.consecutive_failures>self.failures_threshold:
			return

		self.status_text_var.set(ParkingValidator.Messages.SCAN_CARD)
		self.status_patron_var.set("")
		#self.patron_display.text_left(ParkingValidator.Messages.SCAN_CARD)
		#self.patron_display.text_right("")

	def admin_quit(self,event):
		"""
		Quit if in admin/debug mode
		"""

		if self.admin_mode or self.debug_mode:
			self.quit(event)

	def quit(self,event=None):
		"""
		Clean-up code to run when application is exited.
		"""

		self.status_text_var.set("shutting down!")
		self.db.close_db()
		root.destroy()
		exit()

	def validate_barcode(self,barcode):
		"""
		Checks the entered barcode, and then attempts to look up patron record.

		The only input is the barcode string.
		After successfully running, there will be a valid patron object.
		Any errors generated during processing are displayed in the status box.
		"""

		# silently return if barcode is empty or None
		if barcode is None:
			return

		if len(barcode)==0:
			return

		# rate-limiting when there are too many consecutive errors
		if self.consecutive_failures>self.failures_threshold:
			if (dt.datetime.now()-self.last_scan_time).total_seconds()<self.lockout_time:
				return

		self.last_scan_time=dt.datetime.now()

		# first, check for debug barcodes (could be any length)
		if barcode in self.debug_barcodes:
			self.toggle_debug_mode()
			return

		# then, check for admin barcodes (could be any length)
		if barcode in self.admin_barcodes:
			self.toggle_admin_mode()
			return

		# lockout if too many failures (probably mostly innocuous, but could be someone looking for valid barcodes
		if self.consecutive_failures>self.failures_threshold:
			barcode=""

		# check the barcode to see if it could be valid (14 digits)
		self.card=PPLibraryCard(barcode=barcode)
		if self.card.has_valid_barcode():
			self.barcode_display.text(self.card.barcode)

			# the barcode is minimally valid; use it to look up the associated patron in Sierra
			# this process links the card and patron objects bi-directionally
			# also sets the limit on the number of and interval between validations
			# alternatively, if None is returned by the lookup, throw an error
			self.patron=self.remote_lookup_patron(self.card)
			if self.patron is None:
				self.display_error()
				return

			# now access the local database
			# either insert a new record or update an existing one
			self.db.insert_patron(self.patron)

			# retrieve the validations and last_validation fields for this patron from the local database
			self.db.retrieve_patron_validations(self.patron)

			# display the full record
			self.patron_display.text(self.patron.list_properties())
			self.last_scan_time=dt.datetime.now()

			hide_barcode=re.sub(f"^[0-9]{{{self.patron.card.barcode_length-self.hide_len}}}","*"*(self.patron.card.barcode_length-self.hide_len),self.patron.card.barcode)
			self.status_patron_var.set(f"Detected account: {hide_barcode}")

			# now we have enough information to determine if parking validation should proceed or not
			if self.patron.can_be_validated():
				# do the validation
				# or, at least, don't display an error message
				# and reset the failure counter
				self.consecutive_failures=0
				self.status_text_var.set(ParkingValidator.Messages.VALIDATION_ALLOWED)
				self.validator_button_on()

			else:
				# figure out exactly why validation can't happen

				self.display_error()
				return

		else:
			# card wasn't valid for some reason, prompt for rescan
			# keep track of number of consecutive failures

			self.barcode_display.text("<none>")
			self.consecutive_failures+=1
			if self.consecutive_failures>self.failures_threshold:
				self.status_text_var.set(ParkingValidator.ErrorMsgs.CONSECUTIVE_FAILURES)
				self.patron_display.text_left(ParkingValidator.Messages.BLANK)
				self.patron_display.text_right("")
			else:
				self.status_text_var.set(f"{ParkingValidator.ErrorMsgs.BARCODE}\n\n(last input: {barcode})")
				self.patron_display.text_left(ParkingValidator.Messages.SCAN_CARD)
				self.patron_display.text_right("")

			self.card=None

	def admin_do_validation(self,event):
		"""
		Do validation (probably triggered by keypress) if in admin/debug mode.
		"""

		if self.admin_mode or self.debug_mode:
			self.do_validation()

	def do_validation_callback(self,event):
		"""
		Do validation (probably triggered by keypress).
		"""

		if self.validator_button_visible:
			self.do_validation()

	def do_validation(self):
		"""
		Performs the validation, including database access.

		TODO: interface with validation machine, including error handling
		"""

		if self.patron is None:
			return
		if self.patron.can_be_validated():

			# reset interface timeout so that it doesn't trigger while the validator is on
			self.last_scan_time=dt.datetime.now()

			self.patron.validations+=1
			self.patron.last_validation=dt.datetime.now()
			# record in database
			self.db.do_patron_validation(self.patron)

			# display the updated patron object
			#self.patron_display.text(self.patron.list_properties())

			# turn on the validator clock, which controls the powerusb outlet itself
			# note that this runs in its own thread and doesn't block the main thread since it's a separate widget
			self.validator_clock.amount=self.validate_interval
			self.validator_clock.reset()

		else:
			self.display_error()

		# immediately disable the button to prevent double-pressing
		if not self.admin_mode and not self.debug_mode:
			self.validator_button_off()

	def admin_reset_validation(self,event):
		"""
		Reset validation (probably triggered by keypress) if in admin/debug mode.
		"""

		if self.admin_mode or self.debug_mode:
			self.reset_validation()

	def reset_validation(self):
		"""
		Validation reset function; admin tool.

		TODO: trigger function with specific library card numbers
		"""

		if self.patron is None:
			return

		self.patron.validations=0
		self.patron.last_validation=None

		# record in database
		self.db.reset_patron_validation(self.patron)
		self.patron_display.text(self.patron.list_properties())
		if self.patron.can_be_validated():
			self.status_text_var.set(ParkingValidator.Messages.VALIDATION_ALLOWED)
		else:
			self.display_error()

	def display_error(self,selector=None):
		"""
		Display one of several error messages in the status box.
		"""

		if selector == "COMM_ERROR":
			self.status_text_var.set(ParkingValidator.ErrorMsgs.COMM_ERROR)
			return
		if self.patron is None:
			# patron/card doesn't exist; return immediately
			self.status_text_var.set(ParkingValidator.ErrorMsgs.NONEXISTENT_CARD)
			self.patron_display.text(["",""])
			self.status_patron_var.set("")
			return
		elif self.patron.card.is_expired():
			# card expired
			self.status_text_var.set(ParkingValidator.ErrorMsgs.EXPIRED_CARD)
		elif not self.patron.card.has_no_blocks():
			# card has a mandatory block
			self.status_text_var.set(ParkingValidator.ErrorMsgs.ACCOUNT_HOLD)
		elif not self.patron.card.is_valid():
			# something weird happened
			self.status_text_var.set(ParkingValidator.ErrorMsgs.UNSPECIFIED_CARD)
		elif self.patron.validations>=self.patron.max_validations:
			# patron has already been validated the maximum number of times today
			self.status_text_var.set(ParkingValidator.ErrorMsgs.MAXIMUM_VALIDATIONS)
		elif (dt.datetime.now()-self.patron.last_validation).total_seconds()<self.patron.validation_interval:
			# validation attempted too soon
			#revalidate_time=.strftime("%H:%M:%S")
			self.status_text_var.set(f"{ParkingValidator.ErrorMsgs.TOO_SOON} {(self.patron.last_validation+dt.timedelta(seconds=self.patron.validation_interval)):%H:%M:%S}")
		else:
			# something weird happened
			self.status_text_var.set(ParkingValidator.ErrorMsgs.UNSPECIFIED_ACCOUNT)

		# reset barcode entry
		self.barcode=""

	def remote_lookup_patron(self,card):
		"""
		Remote lookup of patron using library card.
		"""

		# on occasion the request fails, so handle the exception
		try:
			data=self.api.get_patron(barcode=card.barcode)
		except:
			display_error("COMM_ERROR")
			return None

		# check if a valid patron record was retrieved
		if data is None:
			display_error("COMM_ERROR")
			return None
		if data.get('name')=="Record not found":
			return None
		name=data['names'][0].split(',')
		patron=Patron(first_name=name[1].strip(),last_name=name[0].strip(),card=card,max_validations=self.max_validations,validation_interval=self.validation_interval)
		card.patron=patron
		card.blocks=data['blockInfo']['code']
		card.expiration=dt.datetime.strptime(data['expirationDate'],"%Y-%m-%d")
		return patron

# execute main program
if __name__ == '__main__':
	root = tk.Tk()
	app = ParkingValidator(root)
	#app.config(bg='#272727')

	# change the icon in the titlebar
	root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file='resources/LibReader2014.png'))

	# no point in having the window be resizable
	root.resizable(width=False,height=False)

	# toggleable fullscreen
	if app.fullscreen:
		root.geometry("%dx%d+0+0" % (root.winfo_toplevel().winfo_screenwidth(), root.winfo_toplevel().winfo_screenheight()))
		root.attributes('-fullscreen', True)
	root.mainloop()
