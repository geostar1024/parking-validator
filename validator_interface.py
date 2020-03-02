import tkinter as tk
import datetime as dt

class Header(tk.Frame):
	"""
	Contains title and clock for UI.
	"""

	def __init__(self,master,title_text="",font=None,label_font=None,fg=None,label_fg=None,width=None,**kw):
		super().__init__(master,**kw)
		self.master=master
		kw['fg']=fg
		self.title2=TimeClock(master,font=label_font,label_font=font,label_fg=label_fg,**kw)
		kw['relief']=None
		self.title1=tk.Label(self,text=title_text,font=font,width=width,**kw)
		self.title1.grid(row=0)
		self.title2.grid(row=1)

class LabeledBox(tk.LabelFrame):
	"""
	Generic label in a labeled frame, with direct text insertion method.

	Note that the interior label's font can be different than the frame's font
	"""

	def __init__(self,master,title="default",text="default",label_font=None,label_fg=None,**kw):
		super().__init__(master,text=title,**kw)
		self.master=master
		kw['relief']=None
		if label_font is not None:
			kw['font']=label_font
		if label_fg is not None:
			kw['fg']=label_fg
		self.label=tk.Label(self,text=text,**kw)
		self.label.pack()

	def title(self,new_title=None):
		if new_title is not None:
			self.config(text=new_title)
		else:
			return self.cget('text')

	def text(self,new_text):
		if new_text is not None:
			self.label.config(text=new_text)
		else:
			return self.label.cget('text')

class LabeledSplitBox(tk.LabelFrame):
	"""
	Two labels side-by-side in a labeled frame, with direct text insertion methods.

	Note that the interior labels' font can be different than the frame's font
	"""

	def __init__(self,master,title="default",text_left="default",text_right="default",label_font=None,label_fg=None,**kw):
		super().__init__(master,text=title,**kw)
		self.master=master
		kw['relief']=None
		if label_font is not None:
			kw['font']=label_font
		if label_fg is not None:
			kw['fg']=label_fg

		# left label is right-justified, right label is left-justified
		self.label_left=tk.Label(self,text=text_left,anchor='e',justify='right',**kw)
		self.label_right=tk.Label(self,text=text_right,anchor='w',justify='left',**kw)
		self.label_left.pack(side=tk.LEFT,fill=tk.BOTH,expand=1,padx=2)
		self.label_right.pack(side=tk.LEFT,fill=tk.BOTH,expand=1,padx=2)

	def title(self,new_title=None):
		if new_title is not None:
			self.config(text=new_title)
		else:
			return self.cget('text')

	# set text in left label
	def text_left(self,new_text):
		self.label_left.config(text=new_text)

	# set text in right label
	def text_right(self,new_text):
		self.label_right.config(text=new_text)

	# takes a list and splits it into two halves to display in the two labels
	def text(self,new_text_list):
		self.text_left(':\n'.join(new_text_list[::2])+':')
		self.text_right('\n'.join(new_text_list[1::2]))

class TimeClock(LabeledBox):
	"""
	Simple widget to show the current time.

	Update tick is 200 ms by default
	"""

	def __init__(self,master,**kw):
		super().__init__(master,title="Current Time",**kw)
		self.tick()

	def tick(self):
		self.text(f"{dt.datetime.now():%H:%M:%S}")
		self.after(200,self.tick)

class KeyInput(LabeledBox):
	"""
	Handles keyboard input, whether from physical keyboard or hand scanner.

	<BackSpace> is bound, so that simple editing can take place
	"""

	def __init__(self,master,callback=None,keybinds=None,title_prefix="raw input",**kw):
		super().__init__(master,title=title_prefix,**kw)
		self.master=master
		self.input=""
		self.keybinds=keybinds
		self.callback=callback
		self.title_prefix=title_prefix
		self.update()

		if self.keybinds is not None:
			for key in self.keybinds.keys():
				self.bind_all(key, self.get_key)

		if self.callback is not None:
			self.bind_all('<Return>',self.cust_callback)
			self.bind_all('<KP_Enter>',self.cust_callback)

		self.bind_all('<BackSpace>',self.del_key)

	def del_key(self,event):
		if len(self.input)>0:
			self.input=self.input[:-1]
			self.update()

	def get_key(self,event):
		if f'<{event.keysym}>' in self.keybinds:
			self.input+=self.keybinds[f'<{event.keysym}>']
			self.update()
		elif event.keysym in self.keybinds:
			self.input+=self.keybinds[event.keysym]
			self.update()
		else:
			print("error!")

	def cust_callback(self,event):
		data=self.input
		self.input=""
		self.callback(data)
		self.update()

	def update(self):
			self.title(f"{self.title_prefix} ({len(self.input)})")
			self.text(self.input)

