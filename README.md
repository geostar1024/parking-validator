``parking-validator`` is designed to operate a parking validation kiosk for Princeton Public Library. It works by turning on a validation machine that is plugged into a USB-controlled power strip (currently a PowerUSB model) when a user presents a valid library card; the account is checked for validity by a look-up in the PPL Sierra database via the REST API. A record of validation attempts (successful and unsuccessful), distinguished by library card number only, are maintained in a local sqlite database, which is cleared every day by default. A second table in the database also stores long-term statistics, and a module in the program sends monthly reports to specified email addresses via a dedicated Gmail account.

# Running the validator

Use a desktop shortcut or run

	python3 parkingvalidator.py

## Keyboard commands

The interface is designed to be navigable with only the numpad

* ``[*]`` cancels the current validation in progress (and exits admin/debug mode)
* ``[/]`` or ``[ESC]`` exits the validator program (only in admin/debug mode)
* ``[+]`` manually starts a validation (not needed in touchless mode)
* ``[-]`` resets daily number of allowed validations (only in admin/debug mode)

# Configuration

## Change encrypted data

### Change encrypted API key:

	python3 crypto.py passwd_token

### Change encrypted email password:

	python3 crypto.py passwd_email

**NOTE: use the same encryption password for both!**


## Switch between touchless and button-press validation mode:

Set "touchless validation delay" in the "validation" section to an integer larger than zero

## Configure admin/debug barcodes:

Set "admin"/"debug" in the "admin barcodes" section to the desired cardnumbers. These should be input as a list of strings:

	[ "<barcode_1>", "<barcode_2>" ]
