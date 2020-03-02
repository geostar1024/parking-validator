import hid
import time

class PowerUSB():
	"""
	Implements simple interface to PowerUSB devices

	Currently only turning sockets on and off and retrieving socket status is supported

	"""
	SLEEP_DURATION=0.02
	SOCKET_ON=[b'A',b'C',b'E']
	SOCKET_OFF=[b'B',b'D',b'F']
	SOCKET_STATUS=[0xa1,0xa2,0xac]

	def __init__(self,vendor=0x04d8,device=0x003f):
		"""
		Initialize the `PowerUSB` object and try to make a connection

		"""

		self.vendor=vendor
		self.device=device
		self.hiddev=hid.device()
		try:
			self.hiddev.open(self.vendor,self.device)
		except(OSError):
			print("Failed to open PowerUSB device!")

	def write(self,bytes):
		"""
		Write a series of bytes to the PowerUSB device

		If the device becomes disconnected after the initial connection was made,
		  a ValueError error will be raised and caught.
		"""

		try:
			self.hiddev.write(bytes)
		except(ValueError):
			print("Failed to write to PowerUSB device!")
		time.sleep(PowerUSB.SLEEP_DURATION)

	def read(self,num_bytes):
		"""
		Read a series of bytes from the PowerUSB device

		If the device becomes disconnected after the initial connection was made,
		  either an OSError or a ValueError error will be raised and caught.

		"""

		try:
			return self.hiddev.read(num_bytes)
		except(OSError, ValueError):
			print("Failed to read from PowerUSB device!")


	def socket(self,num_socket=1,operation="status"):
		"""
		Main method for working with PowerUSB sockets

		With default arguments, this method returns the status of socket 1

		If passed an out-of-range socket, num_socket is silently corrected to socket 1

		Parameters
		----------
		:num_socket: The socket number to operate on
		:operation: The type of operation to perform

		Returns
		-------
		:status: The status of the socket if the status operation was selected

		"""

		if num_socket<1 or num_socket>3:
			num_socket=1
		if operation=="status":
			self.write([0,PowerUSB.SOCKET_STATUS[num_socket-1]])
			result=self.read(1)
			if result is not None:
				return result[0]==1

		if operation=="on":
			self.write(PowerUSB.SOCKET_ON[num_socket-1])
			return
		if operation=="off":
			self.write(PowerUSB.SOCKET_OFF[num_socket-1])
			return

	def status(self,num_socket=1):
		"""
		Shorthand method to get the status of a socket

		"""

		return self.socket(num_socket=num_socket)

	def on(self,num_socket=1):
		"""
		Shorthand method to turn on a socket

		"""

		return self.socket(num_socket=num_socket,operation="on")

	def off(self,num_socket=1):
		"""
		Shorthand method to turn off a socket

		"""

		return self.socket(num_socket=num_socket,operation="off")

	def close(self):
		"""
		Closes the USB HID device.

		May not strictly be necessary given python's intelligent resource handling, but good to call anyway

		"""

		self.hiddev.close()

if __name__ == "__main__":
	"""
	Test the code in this file
	"""
	a=PowerUSB()
	time.sleep(3)
	print(a.status(1))
