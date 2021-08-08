
# Running the validator

Use the desktop shortcut or run

	python3 parkingvalidator.py

### Admin mode

'/' exits the validator program (only in admin/debug mode)

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

Set "admin"/"debug" in the "admin barcodes" section to the desired cardnumbers. These should be input as a list of strings: [ "<barcode_1>", "<barcode_2>" ]
