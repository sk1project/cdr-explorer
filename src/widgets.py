import Tkinter, TreeWidget, chunks, struct


class WebIconButton:
	def __init__(self, master, imagefile='openfolder', command=None, **opts):
		self.master = master
		self.imagefile=imagefile
		self.command=command
		self.image = Tkinter.PhotoImage(file='icons/'+self.imagefile+'.gif', master=self.master)
		self.frame = Tkinter.Frame(self.master, border=1, relief='flat', bg='#595D61')
		self.button=Tkinter.Button(self.frame, image=self.image, command=self.command, 
							border=0, bg='#EDEDED', width=20, activebackground='#EDEDED', **opts)
		self.button.pack(side='top',fill='both', expand=1)
		
class WebButton:
	def __init__(self, master, command=None, **opts):
		self.master = master
		self.command=command
		self.frame = Tkinter.Frame(self.master, border=1, relief='flat', bg='#595D61')
		self.button=Tkinter.Button(self.frame, command=self.command, 
							border=0, bg='#EDEDED', width=20, activebackground='#EDEDED', **opts)
		self.button.pack(side='top',fill='both', expand=1)
		
class WebEntry:
	def __init__(self, master, textvariable=None, **opts):
		self.master = master
		self.textvariable=textvariable
		self.frame = Tkinter.Frame(self.master, border=1, relief='flat', bg='#595D61')
		self.entry=Tkinter.Entry(self.frame, textvariable=self.textvariable)    
		self.entry.pack(side='top', fill='x', expand=1)
		
class PreviewPanel:
	def __init__(self, master):
		self.master = master
		self.no_image=Tkinter.PhotoImage(file='icons/no_preview.gif', master=self.master)
		self.frame = Tkinter.Frame(self.master, border=5, relief='flat')
		borderframe = Tkinter.Frame(self.frame, border=1, relief='flat', bg='#595D61')
		borderframe.pack(side='top')
		inner_frame = Tkinter.Frame(borderframe, border=5, relief='flat')
		inner_frame.pack(side='top')
		self.image=Tkinter.Label(inner_frame, image=self.no_image)
		self.image.pack(side='top', expand=1, fill='x')
		self.label=Tkinter.Label(inner_frame, text='No info', justify='left')
		self.label.pack(side='top')
		
	def processFile(self, fileName):                
		self.riff=chunks.load_file(fileName)
		text=''
		if self.riff.infocollector.cdr_version>0:
			text+='CorelDRAW ver.%u'%self.riff.infocollector.cdr_version+'          \n'
			text+='   Pages: %u'%(self.riff.infocollector.pages-1)+'\n'
			text+='   Layers: %u'%(self.riff.infocollector.layers/self.riff.infocollector.pages)+'\n'
			text+='   Groups: %u'%self.riff.infocollector.groups+'\n'
			text+='   Objects: %u'%self.riff.infocollector.objects+'\n'
			text+='   Bitmaps: %u'%self.riff.infocollector.bitmaps+'\n'
			if self.riff.infocollector.compression:
				text+='   COMPRESSED'
		else:
			text+='Corel Presentation\nExchange ver. CMX1      '
		self.label['text']=text
		if self.riff.infocollector.image:
			self.image['image']=self.riff.infocollector.image                               
		else:
			self.image['image']=self.no_image

	
	def clearPreview(self):
		self.image['image']=self.no_image
		self.label['text']='No info'
		
		
class CDRViewer:

	"""CDR Viewer Window"""

	def __init__(self, master, pathToFile=None):
		self.master=master
		self.pathToFile=pathToFile              
		self.build_window()

	def open_file(self):
			oname = tkFileDialog.askopenfilename(filetypes=[('All CorelDRAW files', '*.cdr *.cmx'),
																							('CorelDRAW Graphics files', '*.cdr'),
																							('Corel Presentation Exchange files', '*.cmx')])
			if oname:
				self.processFile(oname)
		
	def build_window(self):
		self.root = Tkinter.Toplevel(self.master)
		self.root.title('Parsed file: '+self.pathToFile)
		#self.root.transient(self.master)
		
		self.root.geometry('850x600+300+200')           
		
		self.fileName=Tkinter.StringVar(self.root)
		
		pFrame = Tkinter.PanedWindow(self.root, relief='flat', border=5)                
		frame2 = Tkinter.Frame(pFrame, border=0, relief='flat')
		pFrame2 = Tkinter.PanedWindow(frame2, relief='flat', border=5, orient='vertical')               
		ldFrame = Tkinter.Frame(frame2, relief='flat', border=3)
		
		self.fileEntry = WebEntry(ldFrame, textvariable=self.fileName)          
		self.openFile=WebButton(ldFrame, command=self.open_file)
		
		treeFrame = Tkinter.Frame(pFrame, border=1, relief='flat', bg='#595D61')
		
		self.tree = TreeWidget.ScrolledCanvas(treeFrame, bg='#EDEDED', highlightthickness=0, takefocus=1, width=200)            
		self.info=InfoViewer(pFrame2)
		self.dump=DumpViewer(pFrame2)
		
		pFrame.pack(side='top', expand=1, fill='both')
		
		pFrame.add(treeFrame)
		pFrame.add(frame2)
		
		self.tree.frame.pack(side='bottom', expand=1, fill='both')
		#ldFrame.pack(fill='x', anchor='n')
		
		pFrame2.pack(side='bottom', expand=1, fill='both')
		pFrame2.add(self.info.root_frame)
		pFrame2.add(self.dump.frame)
		
		self.analyser=chunks.Analyser(self.root,self.info.viewer,self.info, self.info.lister, self.dump.viewer)
		
		#self.fileEntry.frame.pack(side='left', fill='x', expand=1, padx=3)
		if self.pathToFile == None:
			self.openFile.frame.pack(side='right', fill='y')
		else:
			self.processFile(self.pathToFile)
		
		
	def processFile(self, oname):
		self.fileName.set(oname)
		self.riff=chunks.load_file(oname)
		self.item = TreeWidget.ObjectTreeItem(self.riff, self.dump, self.info, self.analyser)
		self.node = TreeWidget.TreeNode(self.tree.canvas, None, self.item)
		self.node.expand()              
		
class DumpViewer:
	def __init__(self, master, **opts):
		self.master = master
		self.frame = Tkinter.Frame(master, border=1, relief='flat', bg='black')
		self.frame2 = Tkinter.Frame(master, border=1, relief='flat', bg='black', height = 1)

		self.header = Tkinter.Text(self.frame, borderwidth=2, wrap=Tkinter.NONE, state=Tkinter.DISABLED,  bg='#595D61', height=1)
		str='         00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E OF'
		self.header['state']=Tkinter.NORMAL
		self.header.insert(Tkinter.END, str+'\n')
		self.header['state']=Tkinter.DISABLED
		
		
#               self.numviewer= Tkinter.Text(self.frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED, bg='#595D61', width=9)
#               self.viewer= Tkinter.Text(self.frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED,fg='black', bg='#C0C0C0', width=50)
		self.numviewer= Tkinter.Text(self.frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED, width=9)
		self.viewer= Tkinter.Text(self.frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED, width=50)
		self.viewer.bind("<ButtonRelease-1>", self.mouse_select)
		self.asciiviewer= Tkinter.Text(self.frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED)
		self.infoline= Tkinter.Text(self.frame, borderwidth=1, wrap=Tkinter.NONE, state=Tkinter.DISABLED, fg='#0000CC',bg='#c0c0c0', height=1)
		self.sb=Tkinter.Scrollbar(self.frame)
		self.infoline.pack(side='bottom', fill='x')
		self.header.pack(side='top', fill='x')
		self.sb.pack(side='right', fill='y')
		self.numviewer.pack(side='left', fill='y')
		self.viewer.pack(side='left', fill='y')
		self.asciiviewer.pack(side='left', fill='both', expand=1)
		self.frame.pack(side='top', fill='x')
		self.sb.config(command=self.scroll)             
		self.numviewer.config(yscrollcommand=self.sb.set)
		self.asciiviewer.config(yscrollcommand=self.sb.set)
		self.viewer.config(yscrollcommand=self.sb.set)
	
	def mouse_select(self, event):
		if self.viewer.tag_ranges('sel')!=():
			textline = self.viewer.get('sel.first', 'sel.last') 
			self.infoline['state']=Tkinter.NORMAL
			self.infoline.delete(1.0, Tkinter.END)
			self.infocalc(textline)
			self.infoline['state']=Tkinter.DISABLED

	def infocalc(self, textline):
		import os, string
		
		slen = len(textline)
		start = 0
		bytes = ''
		if slen < 2:
			return ''
		if slen > 25:
			slen = 25 # calc no more than 8 bytes values
		if textline[0] == ' ':
			start = 1
		if textline[1] == ' ':
			start = 2
		if slen - start < 2:
			return ''
		num = (slen - start + 1)/3
		rnum = num*3 - 1
		test = string.split(textline[start:start+rnum])
		test.reverse()
		hex = int(string.join(test,''),16)
#               print 'num: ',num,' rnum: ',rnum,'start: ',start,' test: ',test,' hex: ',hex
							
		if num == 2:
			bytes=bytes+'\t\t%u'%hex
			self.infoline.insert(1.0, bytes)        
		if num == 3:
			rgbcol = "#%02x%02x%02x"% (int(test[2],16),int(test[1],16),int(test[0],16))
			bgrcol = "#%02x%02x%02x"% (int(test[0],16),int(test[1],16),int(test[2],16))
			bytes='RGB:     BGR:     '
			self.infoline.insert(1.0, bytes)                        
			self.infoline.tag_add('color_rgb', '1.5', '1.8')
			self.infoline.tag_config('color_rgb', background=rgbcol)
			self.infoline.tag_add('color_bgr', '1.14', '1.17')
			self.infoline.tag_config('color_bgr', background=bgrcol)
		
		if num == 4:
			if hex > 2147483647:
				hex = hex - 4294967295
			hex = round(hex/10000.0,4)
			bytes=bytes+'\t%.4f'%hex
			self.infoline.insert(1.0, bytes)
			col0 = int(test[3],16)
			col1 = int(test[2],16)
			col2 = int(test[1],16)
			col3 = int(test[0],16)
			rgbcol = "#%02x%02x%02x"% (col2,col1,col0)
			bgrcol = "#%02x%02x%02x"% (col0,col1,col2)
			R = (100 - col0)*(100 - col3)*255/10000
			G = (100 - col1)*(100 - col3)*255/10000
			B = (100 - col2)*(100 - col3)*255/10000
			if col0 > 100 or col1 > 100 or col2 > 100 or col3 > 100:
				R = (255 - col0)*(255 - col3)/255
				G = (255 - col1)*(255 - col3)/255
				B = (255 - col2)*(255 - col3)/255
			cmykcol ="#%02x%02x%02x"% (R,G,B)
			bytes='RGB:     BGR:     CMYK:     '
			self.infoline.insert(1.0, bytes)                        
			self.infoline.tag_add('color_rgb', '1.5', '1.8')
			self.infoline.tag_config('color_rgb', background=rgbcol)
			self.infoline.tag_add('color_bgr', '1.14', '1.17')
			self.infoline.tag_config('color_bgr', background=bgrcol)
			self.infoline.tag_add('color_cmyk', '1.24', '1.27')
			self.infoline.tag_config('color_cmyk', background=cmykcol)
			
		
		if num == 8:
			tstr = ''
			for i in range(8):
				tstr = tstr + chr(int(test[i],16))
			[hex] = struct.unpack('>d', tstr[0:8])
			bytes=bytes+'\t\t%u'%int(hex)+'  [%.4f mm]'%round(int(hex)/10000.0,2)
			self.infoline.insert(1.0, bytes)                
			
		
	def scroll(self, value1, value2):
		self.viewer.yview(value1, value2)
		self.asciiviewer.yview(value1, value2)
		self.numviewer.yview(value1, value2)
		
	def add_num(self, str): 
		self.numviewer['state']=Tkinter.NORMAL
		self.numviewer.insert(Tkinter.END, str+'\n')
		self.numviewer['state']=Tkinter.DISABLED
		
	def add_ascii(self, str):       
		self.asciiviewer['state']=Tkinter.NORMAL
		self.asciiviewer.insert(Tkinter.END, str+'\n')
		self.asciiviewer['state']=Tkinter.DISABLED
		
	def add(self, str):     
		self.viewer['state']=Tkinter.NORMAL
		self.viewer.insert(Tkinter.END, str+'\n')
		self.viewer['state']=Tkinter.DISABLED
		
	def clear(self):
		self.viewer['state']=Tkinter.NORMAL
		self.viewer.delete(1.0, Tkinter.END)
		self.viewer['state']=Tkinter.DISABLED
		self.numviewer['state']=Tkinter.NORMAL
		self.numviewer.delete(1.0, Tkinter.END)
		self.numviewer['state']=Tkinter.DISABLED
		self.asciiviewer['state']=Tkinter.NORMAL
		self.asciiviewer.delete(1.0, Tkinter.END)
		self.asciiviewer['state']=Tkinter.DISABLED
		
	def process(self, obj):
		if obj.path.compression:
			data=obj.path.uncompresseddata
		else:
			data=obj.path.data
		data=obj.path.fourcc+obj.path.chunksize+data
		strng=''
		self.clear()
		i=1
		for line in range(0, len(data), 16):
			self.add_num("%07x: " % line)
			strng= ''
			end = min(16, len(data) - line)
			for byte in range(0, 15):
				if (byte & 3) == 0:
					strng+= ''
				if byte < end:
					strng+="%02x " % ord(data[line + byte])
			if end > 15:                    
				strng+="%02x" % ord(data[line + 15])

			str = ''
			for byte in range(0, end):
				if ord(data[line + byte]) < 32 or 126<ord(data[line + byte])<160:
					str += '.'
				else:
					str += data[line + byte]
			#strng=strng+" "+str
			self.add(strng)
			self.add_ascii(str)     
			
			#self.viewer.tag_add('linenum', '%u.0'%i, '%u.8'%i)
			#self.viewer.tag_add('ascii', '%u.59'%i, '%u.91'%i)
			i+=1
		#self.viewer.tag_config('linenum', foreground='white')
		#self.viewer.tag_config('ascii', foreground='yellow')
		#self.viewer.tag_add('header_hex', '1.10', '1.33')
		#self.viewer.tag_add('header_acsii', '1.59', '1.67')
		#self.viewer.tag_config('header_hex', foreground='black', background='#B2B2B2')
		#self.viewer.tag_config('header_acsii', foreground='black', background='#B2B2B2')
		
class InfoViewer:
	def __init__(self, master, **opts):
		self.master = master
		self.root_frame = Tkinter.Frame(master, border=10, relief='flat', height=200)
		self.frame = Tkinter.Frame(self.root_frame, border=1, relief='flat', bg='#595D61')
		self.chunk_name = Tkinter.Label(self.frame, text='[Select chunk]', border=0, relief='flat', bg='#595D61', fg='white', font='Verdana 16')
		self.int_frame = Tkinter.Frame(self.frame, border=0, relief='flat')
		self.int_frame0 = Tkinter.Frame(self.frame, border=0, relief='flat')
		self.viewer= Tkinter.Text(self.int_frame, wrap=Tkinter.NONE, state=Tkinter.DISABLED, bg='#EBEBEB', fg='black')
		self.lister= Tkinter.Text(self.int_frame0, wrap=Tkinter.NONE, state=Tkinter.NORMAL, bg='#EDEDED', fg='black', width = 22) #             
		self.sb=Tkinter.Scrollbar(self.int_frame)
		self.sbl=Tkinter.Scrollbar(self.int_frame0) #

		self.frame.pack(fill='both', expand=1)
		#self.chunk_name.pack(side='top', fill='x')
		self.int_frame0.pack(side='left', fill='both', expand=1)
		self.int_frame.pack(side='left', fill='both', expand=1)
		self.sb.pack(side='right', fill='y')
		self.sbl.pack(side='right', fill='y')
		self.lister.pack(side='left', fill='both', expand=1)  #
		self.viewer.pack(side='left', fill='both', expand=1)
		self.sbl.config(command=self.lister.yview)
		self.sb.config(command=self.viewer.yview)
		self.viewer.config(yscrollcommand=self.sb.set)
		self.lister.config(yscrollcommand=self.sbl.set)
		
	def getInfo(self, obj):
		self.chunk_name['text'] = 'Chunk '+obj.path.chunkname
		lines=''
		lines+='Full name:     '+ obj.path.fullname+'\n'
		lines+='Fourcc:        '+ obj.path.fourcc+'\n'
		lines+='Header offset: %u'%obj.path.hdroffset+'\n'
		lines+='Raw size:      %u'%obj.path.rawsize+' (0x%X)'%obj.path.rawsize+'\n'
		if obj.path.compression:
			lines+='Compression:   Yes'+'\n'
		else:
			lines+='Compression:   No'+'\n'
		return lines
		
	def process(self, obj):
		self.chunk_name['text'] = 'Chunk '+obj.path.chunkname
		self.viewer['state']=Tkinter.NORMAL
		self.viewer.delete(1.0, Tkinter.END)
		self.viewer.insert(Tkinter.END, self.getInfo(obj))
		self.viewer['state']=Tkinter.DISABLED
		
	def add(self, str):
		if (str):
			self.viewer['state']=Tkinter.NORMAL
			self.viewer.insert(Tkinter.END, str+'\n')
			self.viewer['state']=Tkinter.DISABLED


	
