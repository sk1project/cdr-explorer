import sys, struct, zlib


def load_file(file):
	f = open(file, 'rb')
	buf = f.read()
	f.close()
	riff = RiffChunk()
	riff.load(buf)
	return riff
	
class RiffChunk:
	fourcc = '????'
	hdroffset = 0
	rawsize = 0
	data = ''
	contents = []
	fullname= ''
	chunkname= ''
	chunksize= ''
	compression = False
	infocollector=None
	number=0
	
	def __init__(self, infocollector=None):
		if infocollector:
			self.infocollector=infocollector
		else:
			self.infocollector=InfoCollector()
			self.infocollector.image=None
			self.infocollector.bitmap=None
			
	def load_pack(self):
		self.compression=True
		self.infocollector.compression=True
		decomp = zlib.decompressobj()
		self.uncompresseddata = decomp.decompress(self.data[12:])
		chunk = RiffChunk(infocollector=self.infocollector)
		offset = 0
		self.contents = []
		while offset < len(self.uncompresseddata):
			chunk = RiffChunk(infocollector=self.infocollector)
			chunk.parent = self
			chunk.load(self.uncompresseddata, offset)
			self.contents.append(chunk)
			offset += 8 + chunk.rawsize

	def loadcompressed(self):
		if self.data[0:4] != 'cmpr':
			raise Exception("can't happen")
		self.compression=True
		self.infocollector.compression=True
		[compressedsize] = struct.unpack('<I', self.data[4:8])
		[uncompressedsize] = struct.unpack('<I', self.data[8:12])
		[blocksizessize] = struct.unpack('<I', self.data[12:16])
		# 16:20 unknown (seen 12, 1096)
		assert(self.data[20:24] == 'CPng')
		assert(struct.unpack('<H', self.data[24:26])[0] == 1)
		assert(struct.unpack('<H', self.data[26:28])[0] == 4)
		if (20 + compressedsize + blocksizessize + 1) & ~1 != self.rawsize:
			raise Exception('mismatched blocksizessize value (20 + %u + %u != %u)' % (compressedsize, blocksizessize, self.rawsize))
		decomp = zlib.decompressobj()
		self.uncompresseddata = decomp.decompress(self.data[28:])
		if len(decomp.unconsumed_tail):
			raise Exception('unconsumed tail in compressed data (%u bytes)' % len(decomp.unconsumed_tail))
		if len(decomp.unused_data) != blocksizessize:
			raise Exception('mismatch in unused data after compressed data (%u != %u)' % (len(decomp.unused_data), bytesatend))
		if len(self.uncompresseddata) != uncompressedsize:
			raise Exception('mismatched compressed data size: expected %u got %u' % (uncompressedsize, len(self.uncompresseddata)))
		chunk = RiffChunk(infocollector=self.infocollector)
		blocksizesdata = zlib.decompress(self.data[28+compressedsize:])
		blocksizes = []
		for i in range(0, len(blocksizesdata), 4):
			blocksizes.append(struct.unpack('<I', blocksizesdata[i:i+4])[0])
		offset = 0
		self.contents = []
		while offset < len(self.uncompresseddata):
			chunk = RiffChunk(infocollector=self.infocollector)
			chunk.parent = self
			chunk.load(self.uncompresseddata, offset, blocksizes)
			self.contents.append(chunk)
			offset += 8 + chunk.rawsize

	def load(self, buf, offset=0, blocksizes=()):
		import PIL.Image,PIL.ImageTk, StringIO
		#import StringIO

		self.hdroffset = offset
		self.fourcc = buf[offset:offset+4]
		self.chunksize = buf[offset+4:offset+8]
		[self.rawsize] = struct.unpack('<I', buf[offset+4:offset+8])
		if len(blocksizes):
			self.rawsize = blocksizes[self.rawsize]
		self.data = buf[offset+8:offset+8+self.rawsize]
		if self.rawsize & 1:
			self.rawsize += 1
		self.number=self.infocollector.numcount
		self.infocollector.numcount+=1
		if self.fourcc == 'DISP':
			[bitmapoffset] = struct.unpack('<I',buf[offset+32:offset+36])
			bitmapoffset = self.rawsize + 8 - bitmapoffset
			bitmapoffset = struct.pack('>I', bitmapoffset)
			self.image_buf = 'BM'+buf[offset+4:offset+7]+'\x00\x00\x00\x00'+bitmapoffset[2:3]+'\x00\x00'+buf[offset+10:offset+8+self.rawsize]
			self.image = PIL.Image.open(StringIO.StringIO(self.image_buf ))
			self.image.load()
			self.infocollector.image= PIL.ImageTk.PhotoImage(self.image)
#                       result = open('disp.bmp', 'wb')
#                       result.write(self.image_buf)
#                       result.close()

		if self.fourcc == 'vrsn':
			[version] = struct.unpack('<H', self.data)
			self.infocollector.cdr_version=version/100

		self.contents = []
		self.fullname = self.full_name()        
		self.chunkname = self.chunk_name()
		if self.fourcc == 'pack':	
			self.load_pack()
		if self.fourcc == 'RIFF' or self.fourcc == 'LIST':
			self.listtype = buf[offset+8:offset+12]
			self.fullname = self.full_name()
			self.chunkname = self.chunk_name()
			
			if self.listtype == 'page':
				self.infocollector.pages+=1
			if self.listtype == 'layr':
				self.infocollector.layers+=1
			if self.listtype == 'obj ':
				self.infocollector.objects+=1
			if self.listtype == 'bmpt':
				self.infocollector.bitmaps+=1   
			if self.listtype == 'grp ':
				self.infocollector.groups+=1
				
			if self.listtype == 'stlt':
				self.chunkname = '<stlt>'
				#pass     # dunno what's up with these, but they're not lists
			elif self.listtype == 'cmpr':
				self.loadcompressed()
			else:
				offset += 12
				while offset < self.hdroffset + 8 + self.rawsize:
					chunk = RiffChunk(infocollector=self.infocollector)
					chunk.parent = self
					chunk.load(buf, offset, blocksizes)
					self.contents.append(chunk)
					offset += 8 + chunk.rawsize
		
	
	def full_name(self):
		if hasattr(self, 'parent'):
			name = self.parent.fullname + '.'
			if hasattr(self, 'listtype'):
				return name + self.listtype
			return name + self.fourcc
		else:
			return self.fourcc
		
	def chunk_name(self):
		if self.fourcc == 'RIFF':
			return '<'+self.fourcc+'>'
		if hasattr(self, 'listtype'):
			return '<'+self.listtype+'>'
		return '<'+self.fourcc+'>'
	
class InfoCollector:
	image=None
	cdr_version=0
	objects=0
	pages=0
	layers=0
	groups=0
	bitmaps=0
	compression=False
	numcount=0

class Analyser:

	def __init__(self, master, viewer, viewer_obj, lister, dump):
		self.viewer = viewer
		self.lister = lister
		self.viewer_obj = viewer_obj
		self.master = master
		self.imagetk = None
		self.dump=dump

#       def loda_null(self,chunk,type,offset):
#               return ''
	def fildoutl_clr(self,col0,col1,col2,col3,clrmode):
		rgbcol = ''
		i = 0
		if clrmode == 3 or clrmode == 0x11: # CMYK255
			R = (255 - col0)*(255 - col3)/255
			G = (255 - col1)*(255 - col3)/255
			B = (255 - col2)*(255 - col3)/255
			i = 1
		if clrmode == 2:                                                        # CMYK100
			R = (100 - col0)*(100 - col3)*255/10000
			G = (100 - col1)*(100 - col3)*255/10000
			B = (100 - col2)*(100 - col3)*255/10000
			i = 1
		if clrmode == 5:                                                        # RGB
			R = col2
			G = col1
			B = col0
			i = 1
		if clrmode == 9:                                                        # Gray
			R = col0
			G = col0
			B = col0
			i = 1
		if i == 1:                                      
			rgbcol = "#%02x%02x%02x"% (R, G, B)
		return rgbcol

	def txsm_fnum(self,chunk,offset):
		fontnum=ord(chunk.data[offset])
		encnum =ord(chunk.data[offset+2])
		return 'Font: %u/%x '%(fontnum, encnum)

	def txsm_fstyle(self,chunk,offset):
		strikes = ('Custom ','StrkSnglTn ',\
		'StrkSnglTnW ','StrkSnglTk ','StrkSnglTkW ','StrkDbllTn ','StrkDbllTnW ')			
		overstrikes = ('Custom ','OverSnglTn ',\
		'OverSnglTnW ','OverSnglTk ','OverSnglTkW ','OverDbllTn ','OverDbllTnW ')			
		understrikes = ('Custom ','UnderSnglTn ',\
		'UnderSnglTnW ','UnderSnglTk ','UnderSnglTkW ','UnderDbllTn ','UnderDbllTnW ')			
 
		b1 = ord(chunk.data[offset])
		b2 = ord(chunk.data[offset+1])
		b3 = ord(chunk.data[offset+2])
		b4 = ord(chunk.data[offset+3])
		# need to use dict_of_func for stf
		stf =''
		if b2&0x10 == 0x10:
			stf = 'B '
		if b2&0x20 == 0x20:
			stf = 'BI '
		if b1&0x80 == 0x80:
			stf = 'I '
		if b4&0x8 == 0x8:
			stf = stf+'Sup '
		if b4&0x10 == 0x10:
			stf = stf+'Sub '
		if b4&7 > 0:
			stf = stf+strikes[b4&7]
		if b3&0x1c > 0:
			stf = stf+understrikes[(b3&0x1c)/4]
		if b3&0xE0 > 0:
			stf = stf+overstrikes[(b3&0xe0)/32]
		if b1&0x40 == 0x40 and b3 == 0 and b4 == 0:
			stf = stf+'CstmStrk'

		return 'Flags: %02x %02x %02x %02x '%(b1,b2,b3,b4)+stf
		
	def txsm_xoffs(self,chunk,offset):
		[x]=struct.unpack('<L', chunk.data[offset:offset+4])
		if x > 0x7FFFFFFF:
			x = x - 0x100000000
		return 'XOffs: %u '%x
		
	def txsm_yoffs(self,chunk,offset):
		[x]=struct.unpack('<L', chunk.data[offset:offset+4])
		if x > 0x7FFFFFFF:
			x = x - 0x100000000
		return 'YOffs: %u '%x
	def txsm_rotate(self,chunk,offset):
		[x]=struct.unpack('<L', chunk.data[offset:offset+4])
		if x > 0x7FFFFFFF:
			x = x - 0x100000000
		return 'Rotate: %u '%(x/1000000)
	
	
	def txsm_fild(self,chunk,offset):
		b1 = ord(chunk.data[offset])
		b2 = ord(chunk.data[offset+1])
		b3 = ord(chunk.data[offset+2])
		b4 = ord(chunk.data[offset+3])
		return 'fild_id: %02x %02x %02x %02x '%(b1,b2,b3,b4)
	
	def txsm_outl(self,chunk,offset):
		b1 = ord(chunk.data[offset])
		b2 = ord(chunk.data[offset+1])
		b3 = ord(chunk.data[offset+2])
		b4 = ord(chunk.data[offset+3])
		return 'outl_id: %02x %02x %02x %02x '%(b1,b2,b3,b4)
	
	def loda_outl(self,chunk,type,offset,version):
		return 'Outl_ID:\t'+'%02X '%ord(chunk.data[offset])+'%02X '%ord(chunk.data[offset+1])+\
				'%02X '%ord(chunk.data[offset+2])+'%02X '%ord(chunk.data[offset+3])

	def loda_stlt(self,chunk,type,offset,version):
		return 'Stlt_ID:\t'+'%02X '%ord(chunk.data[offset])+'%02X '%ord(chunk.data[offset+1])+\
					'%02X '%ord(chunk.data[offset+2])+'%02X '%ord(chunk.data[offset+3])
				
	def loda_fild(self,chunk,type,offset,version):
		return 'Fild_ID:\t'+'%02X '%ord(chunk.data[offset])+'%02X '%ord(chunk.data[offset+1])+\
					'%02X '%ord(chunk.data[offset+2])+'%02X '%ord(chunk.data[offset+3])

	def loda_rot(self,chunk,type,offset,cdr_version):
		[rot] = struct.unpack('<L', chunk.data[offset:offset+4])
		return '\nRotate:\t\t%u'%round(rot/1000000.0,2)
		 
	def loda_name(self,chunk,type,offset,cdr_version):
		if cdr_version == 13 or cdr_version == 12:
			layrname = unicode(chunk.data[offset:],'utf-16').encode('utf-8')
		else:
			layrname = chunk.data[offset:]
		return '\nLayer name:\t%s'%layrname

	def loda_polygone(self,chunk,type,offset,version):
		[numofgones] = struct.unpack('<L', chunk.data[offset+4:offset+8])
		st = '# of angles:\t%u\n'%numofgones
		for i in range(4):
			[varX] = struct.unpack('<L', chunk.data[offset+0x10+i*8:offset+0x14+i*8])
			[varY] = struct.unpack('<L', chunk.data[offset+0x14+i*8:offset+0x18+i*8])
			if varX > 0x7FFFFFFF:
				varX = varX - 0x100000000
			if varY > 0x7FFFFFFF:
				varY = varY - 0x100000000
			st = st+'X%u/Y%u:\t\t%u/%u mm\n'%(i,i,round(varX/10000.0,2),round(varY/10000.0,2))
		return st
	
	def loda_coords(self,chunk,type,offset,version):
		if type == 1 or type == 2 or type == 4:  # rectangle or ellipse or text
			[CoordX2] = struct.unpack('<L', chunk.data[offset:offset+4])                            
			[CoordY2] = struct.unpack('<L', chunk.data[offset+4:offset+8])
			if CoordX2 > 0x7FFFFFFF:
				CoordX2 = CoordX2 - 0x100000000
			if CoordY2 > 0x7FFFFFFF:
				CoordY2 = CoordY2 - 0x100000000
			st = 'X1/Y1:\t\t0/0 mm\nX2/Y2:\t\t%u/'%round(CoordX2/10000.0,2)+'%u mm'%round(CoordY2/10000.0,2)
			if type == 1:
				[R1] = struct.unpack('<L', chunk.data[offset+8:offset+12])                              
				[R2] = struct.unpack('<L', chunk.data[offset+12:offset+16])
				[R3] = struct.unpack('<L', chunk.data[offset+16:offset+20])
				[R4] = struct.unpack('<L', chunk.data[offset+20:offset+24])
				st=st+'\nR1:\t\t%u mm'%round(R1/10000.0,2)+\
						'\nR2:\t\t%u mm'%round(R2/10000.0,2)+\
						'\nR3:\t\t%u mm'%round(R3/10000.0,2)+\
						'\nR4:\t\t%u mm'%round(R4/10000.0,2)
					
			if type == 2:
				[startangle] = struct.unpack('<L', chunk.data[offset+8:offset+12])                              
				[endangle] = struct.unpack('<L', chunk.data[offset+12:offset+16])
				[rotangle] = struct.unpack('<L', chunk.data[offset+16:offset+20])
				st=st+'\nStart Angle:\t%u'%round(startangle/1000000.0,2)+\
						'\nEnd Angle:\t%u'%round(endangle/1000000.0,2)+\
						'\nRot. Angle:\t%u'%round(rotangle/1000000.0,2)
			return st

		if type == 3 or type == 5: # line/curve and bitmap
			st = ''
			if type == 5:
				bmp_color_models = ('Invalid','Pal1','CMYK255','RGB','Gray','Mono','Pal6','Pal7','Pal8')
					#'Invalid', 'RGB', 'CMY', 'CMYK255', 'HSB', 'Gray', 'Mono','HLS', 'PAL8', 'Unknown9', 'RGB', 'LAB')                                       

				for i in range(4):
					[varX] = struct.unpack('<L', chunk.data[offset+i*8:offset+4+i*8])
					[varY] = struct.unpack('<L', chunk.data[offset+4+i*8:offset+8+i*8])
					if varX > 0x7FFFFFFF:
						varX = varX - 0x100000000
					if varY > 0x7FFFFFFF:
						varY = varY - 0x100000000

					st = st+'X%u/Y%u:\t\t%u/%u mm\n'%(i,i,round(varX/10000.0,2),round(varY/10000.0,2))

				bmp_clrmode = ord(chunk.data[offset+0x30])
				clrdepth = ord(chunk.data[offset+0x22])
				[width] = struct.unpack('<L', chunk.data[offset+0x24:offset+0x28])
				[height] = struct.unpack('<L', chunk.data[offset+0x28:offset+0x2c])
				[idx1] = struct.unpack('<L', chunk.data[offset+0x2c:offset+0x30])
				numbmp = ord(chunk.data[offset+0x20])
				[idx2] = struct.unpack('<L', chunk.data[offset+0x34:offset+0x38])
				[idx3] = struct.unpack('<L', chunk.data[offset+0x38:offset+0x3c])
				st = st+'\nColor model:\t%s'%bmp_color_models[bmp_clrmode]+'\nColor depth:\t%u'%clrdepth+' bits\n'
				st = st+'Width*Height:\t%u/%u\n'%(width,height)
				st = st+'Bmp number:\t%u\n'%numbmp
				#idx1..idx3 aren't show
				#ver7 - 2, ver8 - 3, ver9..13 - 5
				if version == 7:
					shift = 0x3c
				if version == 8:
					shift = 0x40
				if version > 8:
					shift = 0x48    
				offset = offset + shift
			[pointnum] = struct.unpack('<L', chunk.data[offset:offset+4])
			for i in range (pointnum):
				[CoordX] = struct.unpack('<L', chunk.data[offset+4+i*8:offset+8+i*8])                           
				[CoordY] = struct.unpack('<L', chunk.data[offset+8+i*8:offset+12+i*8])
				Type = ord(chunk.data[offset+4+pointnum*8+i])
				NodeType = ''
				# FIXME! Lazy to learn dictionary right now, will fix later
				if Type&2 == 2:
					NodeType = '    Char. start'                                                                                                                                                                    
				if Type&4 == 4:
					NodeType = NodeType+'  Can modify'                                                                                                                                                                      
				if Type&8 == 8:
					NodeType = NodeType+'  Closed path'
				if Type&0x10 == 0 and Type&0x20 == 0:
					NodeType = NodeType+'  Discontinued'
				if Type&0x10 == 0x10:
					NodeType = NodeType+'  Smooth'
				if Type&0x20 == 0x20:
					NodeType = NodeType+'  Symmetric'
				if Type&0x40 == 0 and Type&0x80 == 0:                                                                           
					NodeType = NodeType+'  START'
				if Type&0x40 == 0x40 and Type&0x80 == 0:
					NodeType = NodeType+'  Line'                                                    
				if Type&0x40 == 0 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Curve'                                                   
				if Type&0x40 == 0x40 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Arc'                                                     

				if CoordX > 0x7FFFFFFF:
					CoordX = CoordX - 0x100000000
				if CoordY > 0x7FFFFFFF:
					CoordY = CoordY - 0x100000000

				st = st+'X%u/'%(i+1)+'Y%u'%(i+1)+':  \t%u/'%round(CoordX/10000.0,2)+\
						'%u mm'%round(CoordY/10000.0,2)+NodeType+'\n'

		if type == 20: # polygone
			[diameter] = struct.unpack('<L', chunk.data[offset:offset+4])
			st = 'Diameter:\t%u\n'%round(diameter/10000.0,2)
#it's copy-paste part from type4/5
			pointnum = 3
			for i in range (pointnum):
				[CoordX] = struct.unpack('<L', chunk.data[offset+4+i*8:offset+8+i*8])                           
				[CoordY] = struct.unpack('<L', chunk.data[offset+8+i*8:offset+12+i*8])
				Type = ord(chunk.data[offset+4+pointnum*8+i])
				NodeType = ''
				# FIXME! Lazy to learn dictionary right now, will fix later
				if Type&2 == 2:
					NodeType = '    Char. start'                                                                                                                                                                    
				if Type&4 == 4:
					NodeType = NodeType+'  Can modify'                                                                                                                                                                      
				if Type&8 == 8:
					NodeType = NodeType+'  Closed path'
				if Type&0x10 == 0 and Type&0x20 == 0:
					NodeType = NodeType+'  Discontinued'
				if Type&0x10 == 0x10:
					NodeType = NodeType+'  Smooth'
				if Type&0x20 == 0x20:
					NodeType = NodeType+'  Symmetric'
				if Type&0x40 == 0 and Type&0x80 == 0:                                                                           
					NodeType = NodeType+'  START'
				if Type&0x40 == 0x40 and Type&0x80 == 0:
					NodeType = NodeType+'  Line'                                                    
				if Type&0x40 == 0 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Curve'                                                   
				if Type&0x40 == 0x40 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Arc'                                                     

				if CoordX > 0x7FFFFFFF:
					CoordX = CoordX - 0x100000000
				if CoordY > 0x7FFFFFFF:
					CoordY = CoordY - 0x100000000

				st = st+'X%u/'%(i+1)+'Y%u'%(i+1)+':  \t%u/'%round(CoordX/10000.0,2)+\
						'%u mm'%round(CoordY/10000.0,2)+NodeType+'\n'
		return st               

	def analyse(self, chunk):
		import os, Tkinter, string
		import PIL.Image,PIL.ImageTk, StringIO, PIL.ImageDraw
		#import StringIO
		cdr_version=chunk.infocollector.cdr_version
		self.viewer_obj.add('Chunk No.: %u'%(chunk.number))
		loda_type = {0:'Layer',1:'Rectangle',2:'Ellipse',3:'Line', 4:'Text',5:'Bitmap', 20:'Polygone'}
		color_models = ('Invalid', 'Pantone', 'CMYK', 'CMYK255', 'CMY', 'RGB',
							'HSB', 'HLS', 'BW', 'Gray', 'YIQ255', 'LAB','Unknown0xc',
							'Unknown0xd','Unknown0xe','Unknown0xf','Unknown0x10',
							'CMYK255','Unknown0x12','Unknown0x13','Registration Color',)
		bmp_clr_models = ('Invalid', 'RGB', 'CMY', 'CMYK255', 'HSB', 'Gray', 'Mono',
								'HLS', 'PAL8', 'Unknown9', 'RGB', 'LAB')                                       
		outl_corn_type =('Normal', 'Rounded', 'Cant')
		outl_caps_type =('Normal', 'Rounded', 'Out Square')
		fild_pal_type = {0:'Transparent', 1:'Solid', 2:'Gradient',6:'Postscript',7:'Pattern', 0xb:'Texture'} # FIXME! names are guessed by frob
		fild_grad_type = ('Unknown', 'Linear', 'Radial', 'Conical', 'Squared') #FIXME! gussed
		loda_type_func = {0xa:self.loda_outl,0x14:self.loda_fild,0x1e:self.loda_coords,
						0x68:self.loda_stlt, 0x2af8:self.loda_polygone,0x3e8:self.loda_name,
						0x2efe:self.loda_rot}
						#, 0x7d0:loda_palt, 0x1f40:loda_lens, 0x1f45:loda_contnr}
#		txsm_flag_func = {1:self.txsm_fnum,2:self.txsm_fstyle,0x10:self.txsm_xoffs,0x20:self.txsm_yoffs,
#								0x40:self.txsm_fild, 0x80:self.txsm_outl}                                           
				
		flgs_layer = {0x0a:'Guides',0x08:'Desktop',0x00:'Layer',0x1a:'Grid'}
						
		if chunk.fourcc == 'DISP':
			self.viewer['state']=Tkinter.NORMAL
			self.viewer.insert(Tkinter.END, 'Thumbnail:     ')
			self.viewer.image_create(Tkinter.END, image=chunk.infocollector.image)
			self.viewer['state']=Tkinter.DISABLED
			
		if chunk.fourcc == 'vrsn':                      
			self.viewer_obj.add('\nCorelDRAW version: %u'%(cdr_version))              
				
#############################################################################################
# TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD TRFD #
#############################################################################################
		if chunk.fourcc == 'trfd':
			ieeestart = 32
			if cdr_version == 13:
				ieeestart = 40
			if cdr_version == 5:
				ieeestart = 18
				
			[CoordX0] = struct.unpack('<d', chunk.data[ieeestart+16:ieeestart+24])
			[CoordY0] = struct.unpack('<d', chunk.data[ieeestart+40:ieeestart+48])
			self.viewer_obj.add('Shift X/Y:\t\t%u/'%(CoordX0/10000)+'%u mm'%(CoordY0/10000))

			i=0                     
			[var] = struct.unpack('<d', chunk.data[ieeestart+i*8:ieeestart+8+i*8]) 
			self.viewer_obj.add('\nVar%u'%(i+1)+' [0x%X:'%(ieeestart+i*8)+'0x%X]:'%(ieeestart+8+i*8)+' %f'%var)
			i=1
			[var] = struct.unpack('<d', chunk.data[ieeestart+i*8:ieeestart+8+i*8]) 
			self.viewer_obj.add('Var%u'%(i+1)+' [0x%X:'%(ieeestart+i*8)+'0x%X]:'%(ieeestart+8+i*8)+' %f'%var)
			i=3                     
			[var] = struct.unpack('<d', chunk.data[ieeestart+i*8:ieeestart+8+i*8]) 
			self.viewer_obj.add('Var%u'%(i+1)+' [0x%X:'%(ieeestart+i*8)+'0x%X]:'%(ieeestart+8+i*8)+' %f'%var)
			i=4
			[var] = struct.unpack('<d', chunk.data[ieeestart+i*8:ieeestart+8+i*8]) 
			self.viewer_obj.add('Var%u'%(i+1)+' [0x%X:'%(ieeestart+i*8)+'0x%X]:'%(ieeestart+8+i*8)+' %f'%var)

#############################################################################################
# TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM TXSM #
#############################################################################################
		if chunk.fourcc == 'txsm':
			for i in range(6):
				[var] = struct.unpack('<d', chunk.data[0x2c+i*8:0x34+i*8]) 
				self.viewer_obj.add('\nVar%u'%(i+1)+' [0x%X:0x'%(0x2c+i*8)+'%X]:'%(0x34+i*8)+'%u'%var)
			
			shift = 0
			enclen = 4
			desclen = 4
			txtshift = 0
			if cdr_version == 7:
				enclen = 3
			if cdr_version == 12 or cdr_version == 13:
				desclen = 8
				txtshift = 4
			if cdr_version == 13:
				shift = 1
					
			numofenc=ord(chunk.data[0x69+shift])
			for i in range(numofenc):
				st = ''
				txsm_offset = 0x6d+4+i*enclen	
				flag=ord(chunk.data[0x6d+2+shift+i*enclen])
				flag2=ord(chunk.data[0x6d+3+shift+i*enclen])
				txsm_offset = 0x6d+4+i*enclen
			#	print 'Flag: %x TxOffs: %x Shft: %x'%(flag,txsm_offset,shift) 
				if flag&1 == 1:
					st = st+self.txsm_fnum(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&2 == 2:
					st = st+self.txsm_fstyle(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&8 == 8:
					st = st+self.txsm_rotate(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&0x10 == 0x10:
					st = st+self.txsm_xoffs(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&0x20 == 0x20:
					st = st+self.txsm_yoffs(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&0x40 == 0x40:
					st = st+self.txsm_fild(chunk,txsm_offset+shift)
					shift = shift+4
				if flag&0x80 == 0x80:
					st = st+self.txsm_outl(chunk,txsm_offset+shift)
					shift = shift+4

				if flag > 0 and st == '':
					print 'WARNING! Flag == %x'%flag 
		
				if cdr_version > 7 and flag2 == 8:
					if cdr_version == 13:
						[elen] = struct.unpack('<L',chunk.data[0x71+shift+i*enclen:0x75+shift+i*enclen])
						encname = unicode(chunk.data[0x76:0x76+elen*2],'utf-16').encode('ascii')
						shift = shift + 4+elen*2
					else:						
						encname=chunk.data[0x71+shift+i*enclen:0x73+shift+i*enclen]
						shift = shift + 4
					self.viewer_obj.add('Enc.name: %s [%x]\t%s'%(encname, i*2,st))
				else:
					self.viewer_obj.add('Enc.: [%x]\t%s'%(i*2,st))
					
			[numchar] = struct.unpack('<L', chunk.data[0x6d+shift+enclen*numofenc:0x6d+shift+enclen*numofenc+4])
			txtoffset = 0x6d+shift+enclen*numofenc+4+numchar*desclen+txtshift
			txtoptions = 0x6d+shift+enclen*numofenc+4
			#print 'numch: %x, txtoff: %x'%(numchar, txtoffset)
			text = ''
			shift = 0 
			if cdr_version == 12 or cdr_version == 13:
				for i in range(numchar):
					if ord(chunk.data[txtoptions+i*8]) == 0:
						char = chunk.data[txtoffset+i+shift]
						if ord(char)== 0xd:
							char = '\n'
						text = text+char
					else:
						text = text+unicode(chunk.data[txtoffset+i+shift:txtoffset+i+2+shift],'utf-16').encode('utf-8')
						shift = shift+1
			else:
				text = chunk.data[txtoffset+shift:]
		
			self.viewer_obj.add('\nText:\n%s'%text)
			
#############################################################################################
# FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL FTIL # 
#############################################################################################
		if chunk.fourcc == 'ftil':
		# All chunk's data were used. Acknowledged with ver 13 and ver 9.
			[var] = struct.unpack('<d', chunk.data[0:8]) 
			self.viewer_obj.add('\nVar1 [0x0:0x8]: %u'%var)
			[var] = struct.unpack('<d', chunk.data[8:0x10]) 
			self.viewer_obj.add('Var2 [0x8:0x10]: %u'%var)
			[var] = struct.unpack('<d', chunk.data[0x10:0x18]) 
			self.viewer_obj.add('Var3 [0x10:0x18]: %u'%var)
			[var] = struct.unpack('<d', chunk.data[0x18:0x20]) 
			self.viewer_obj.add('Var4 [0x18:0x20]: %u'%var)
			[var] = struct.unpack('<d', chunk.data[0x20:0x28]) 
			self.viewer_obj.add('Var5 [0x20:0x28]: %u'%var)
			[var] = struct.unpack('<d', chunk.data[0x28:0x30]) 
			self.viewer_obj.add('Var6 [0x28:0x30]: %u'%var)                     

#############################################################################################
# OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL OUTL #
#############################################################################################
#  <outl> seems to be exactly the same for ver7 to ver12, slightly different for ver13 and ver5 (have no idea about ver6)
		if chunk.fourcc == 'outl' and cdr_version > 5:
			self.viewer_obj.add('\nOutline_Idx:\t%02X '%ord(chunk.data[0])+'%02X '%ord(chunk.data[1])+'%02X '%ord(chunk.data[2])+'%02X '%ord(chunk.data[3]))
			self.lister.insert(Tkinter.END,'Outl_Id '+'%02X '%ord(chunk.data[0])+'%02X '%ord(chunk.data[1])+'%02X '%ord(chunk.data[2])+'%02X\n'%ord(chunk.data[3]))
			ct_offset = 0x8
			lw_offset = 0xc
			lc_offset = 0x6
			offset = 0x1c
			dash_offset = 0x68
			arrw_offset = 0x80   
				
			if cdr_version == 13:
				ct_offset = 0x1c
				lw_offset = 0x1e
				lc_offset = 0x1a
				offset = 0x28
				dash_offset = 0x74
				arrw_offset = 0x8a
				
			self.viewer_obj.add('Caps Type:\t%s'%outl_caps_type[ord(chunk.data[lc_offset])])
			self.viewer_obj.add('Corner Type:\t%s'%outl_corn_type[ord(chunk.data[ct_offset])])
			[line_width] = struct.unpack('<L',chunk.data[lw_offset:lw_offset+4])
			self.viewer_obj.add('Line Width:\t%03.2F'%(line_width/10000.0)+' mm')
			self.viewer_obj.add('Arrw strt ID:\t%02x %02x %02x %02x'%(ord(chunk.data[arrw_offset]),ord(chunk.data[arrw_offset+1]),ord(chunk.data[arrw_offset+2]),ord(chunk.data[arrw_offset+3])))
			self.viewer_obj.add('Arrw end ID:\t%02x %02x %02x %02x\n'%(ord(chunk.data[arrw_offset+4]),ord(chunk.data[arrw_offset+5]),ord(chunk.data[arrw_offset+6]),ord(chunk.data[arrw_offset+7])))

						
			for i in range (6):
				[var] = struct.unpack('<d', chunk.data[offset+i*8:offset+i*8+8]) 
				self.viewer_obj.add('Var%u '%i+'[%X:'%(offset+i*8)+'%X]:\t'%(offset+i*8+8)+'%u'%var)
						
			clrmode = ord(chunk.data[offset+0x30])
			if clrmode < len(color_models):
				self.viewer_obj.add('\nColor model:\t%s'%color_models[clrmode])
			else:   
				self.viewer_obj.add('\nColor model:\tUnknown (%X)'%clrmode)
																# RGB           CMYK
			col0=ord(chunk.data[offset+0x38])               #       BB              CC
			col1=ord(chunk.data[offset+0x39])               #       GG              MM
			col2=ord(chunk.data[offset+0x3a])               #       RR              YY
			col3=ord(chunk.data[offset+0x3b])               #       ??              KK
			self.viewer_obj.add('Color:\t\t%02x'%col0+' %02x'%col1+' %02x'%col2+' %02x'%col3)
					
			rgbcol = self.fildoutl_clr(col0,col1,col2,col3,clrmode)
			if rgbcol != '':
				self.viewer['state']=Tkinter.NORMAL
				self.viewer.tag_add('color_rgb', '23.7')
				self.viewer.tag_config('color_rgb', background=rgbcol)
				self.viewer['state']=Tkinter.DISABLED                   

			[dashnum]= struct.unpack('<h', chunk.data[dash_offset:dash_offset+2])
			if dashnum > 0:
				st = ''
				sd = ''
				flag = 1
				for i in range(dashnum):
					[dash]= struct.unpack('<h', chunk.data[dash_offset+2+i*2:dash_offset+4+i*2])
					st = st+' '+str(dash)
					if flag:
						sd = sd + '-'*dash
						flag = 0
					else:
						sd = sd + ' '*dash
						flag = 1
				sd = sd + '|'		
				self.viewer_obj.add('\nDash:\t\t'+st+'\n'+sd)	

#############################################################################################
# BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  BMP  #
#############################################################################################
		if chunk.fourcc == 'bmp ':
			palflag = ord(chunk.data[0x36])
			if palflag < 12: # need to define more color_models for ver13?
				self.viewer_obj.add('\nColor model [0x36]: %s'%bmp_clr_models[palflag])
			[bmpsize] = struct.unpack('<L',chunk.data[42:46])
			[bmpstart] = struct.unpack('<L',chunk.data[50:54])
			numcol = (bmpstart - 82)/3
			if palflag == 5: # I will generate 'pallete' later
				numcol = 256    
			bmpstart2 = numcol*4 + 54
			bmpstart2 = struct.pack('<L',bmpstart2)
			self.bmpbuf = 'BM'+chunk.data[42:50]+bmpstart2[0:4]+'\x28\x00\x00\x00'
			self.bmpbuf = self.bmpbuf +chunk.data[62:72]+chunk.data[74:78]
			self.bmpbuf = self.bmpbuf+'\x00\x00'+chunk.data[82:90]+'\x00\x00\x00\x00'
			if numcol > 1:
				self.bmpbuf = self.bmpbuf+'\x00\x01\x00\x00\x00\x00\x00\x00'
				if palflag == 3:
					for i in range (numcol):
						C = ord(chunk.data[122+i*4])
						M = ord(chunk.data[123+i*4])
						Y = ord(chunk.data[124+i*4])
						K = ord(chunk.data[125+i*4])
						R = struct.pack('<h',(255 - C)*(255 - K)/255)
						G = struct.pack('<h',(255 - M)*(255 - K)/255)
						B = struct.pack('<h',(255 - Y)*(255 - K)/255)
						self.bmpbuf = self.bmpbuf+B[0]+G[0]+R[0]+'\x00'
				else:
					if palflag == 5:
						for i in range (numcol):
							clr = struct.pack('<h',i)
							self.bmpbuf = self.bmpbuf+clr[0]+clr[0]+clr[0]+'\x00'
					else:
						for i in range (numcol):
							self.bmpbuf = self.bmpbuf+chunk.data[122+i*3:125+i*3]+'\x00'
					
				self.bmpbuf = self.bmpbuf+chunk.data[bmpstart+40:]
			else:           
				if palflag == 3:
					for i in range (len(chunk.data[bmpstart+40:])/4):
						C = ord(chunk.data[bmpstart+40+i*4])
						M = ord(chunk.data[bmpstart+41+i*4])
						Y = ord(chunk.data[bmpstart+42+i*4])
						K = ord(chunk.data[bmpstart+43+i*4])
						R = struct.pack('<h',(255 - C)*(255 - K)/255)
						G = struct.pack('<h',(255 - M)*(255 - K)/255)
						B = struct.pack('<h',(255 - Y)*(255 - K)/255)
						self.bmpbuf = self.bmpbuf+B[0]+G[0]+R[0]+'\x00'
				if palflag == 6: #Mono
					self.bmpbuf = self.bmpbuf+'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
					self.bmpbuf = self.bmpbuf+chunk.data[bmpstart+40:]
				else:
					self.bmpbuf = self.bmpbuf+chunk.data[bmpstart+40:]
#                       result = open('result.bmp', 'wb')
#                       result.write(self.bmpbuf)
#                       result.close()
			
			self.bitmap = PIL.Image.open(StringIO.StringIO(self.bmpbuf ))
			self.bitmap.load()
			chunk.infocollector.bitmap = PIL.ImageTk.PhotoImage(self.bitmap)
			self.viewer['state']=Tkinter.NORMAL
			self.viewer.insert(Tkinter.END, 'Bitmap:     ')
			self.viewer.image_create(Tkinter.END, image=chunk.infocollector.bitmap)
			self.viewer['state']=Tkinter.DISABLED
			
#############################################################################################
# FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD FILD #
#############################################################################################
		if chunk.fourcc == 'fild':
			self.viewer_obj.add('\nFild_Id:\t%02X '%ord(chunk.data[0])+'%02X '%ord(chunk.data[1])+'%02X '%ord(chunk.data[2])+'%02X '%ord(chunk.data[3]))

			pal = ord(chunk.data[4])
			if cdr_version == 13:
				pal = ord(chunk.data[0xc])
			
			if fild_pal_type.has_key(pal):
				fild_type = fild_pal_type[pal]
			else:
				fild_type = 'Unknown (%X)'%pal
				
			self.viewer_obj.add('Pallete type:\t%s'%fild_type)
			self.lister.insert(Tkinter.END,'Fild_Id '+'%02X '%ord(chunk.data[0])+'%02X '%ord(chunk.data[1])+'%02X '%ord(chunk.data[2])+'%02X '%ord(chunk.data[3])+'%s\n'%fild_type[0])                      

			if fild_type == 'Solid':
				clr_offset = 0x8
				if cdr_version == 13:
					clr_offset = 0x1b
				
				clrmode = ord(chunk.data[clr_offset])
				if clrmode < len(color_models):
					self.viewer_obj.add('\nColor model:\t%s'%color_models[clrmode])
				else:   
					self.viewer_obj.add('\nColor model:\tUnknown (%X)'%clrmode)
				
				offset = 0x10
				if cdr_version == 13:
					offset =0x23
																	# RGB           CMYK
				col0=ord(chunk.data[offset])                    #       BB              CC
				col1=ord(chunk.data[offset+1])          #       GG              MM
				col2=ord(chunk.data[offset+2])          #       RR              YY
				col3=ord(chunk.data[offset+3])          #       ??              KK
				self.viewer_obj.add('Color:\t\t%02x'%col0+' %02x'%col1+' %02x'%col2+' %02x'%col3)
					
				rgbcol = self.fildoutl_clr(col0,col1,col2,col3,clrmode)
				if rgbcol != '':
					self.viewer['state']=Tkinter.NORMAL
					self.viewer.tag_add('color_rgb', '12.7')
					self.viewer.tag_config('color_rgb', background=rgbcol)
					self.viewer['state']=Tkinter.DISABLED

			if fild_type == 'Gradient':
				grd_offset = 0x8
				rot_offset = 0x20
				mid_offset = 0x32
				pal_len = 16
				pal_off = 0
				prcnt_off = 0
				if cdr_version == 13:
					grd_offset = 0x16
					mid_offset = 0x3c
					pal_len = 24
					pal_off = 3
					prcnt_off = 8
				grdmode = ord(chunk.data[grd_offset])
				midpoint = ord(chunk.data[mid_offset])
				pal_num = ord(chunk.data[mid_offset+2])								
				[rotation] = struct.unpack('<L', chunk.data[rot_offset:rot_offset+4])
				
				if grdmode < len(fild_grad_type):
					self.viewer_obj.add('\nGradient type:\t%s'%fild_grad_type[grdmode])
				else:   
					self.viewer_obj.add('\nGradient type:\tUnknown (%X)'%clrmode)	
				self.viewer_obj.add('Rotation:\t%u'%(rotation/1000000))
				self.viewer_obj.add('Midpoint:\t%u'%midpoint)
				for i in range(pal_num):
					clrmode = ord(chunk.data[mid_offset+6+pal_off+i*pal_len])
																	# RGB           CMYK
					col0=ord(chunk.data[mid_offset+14+pal_off+i*pal_len])                    #       BB              CC
					col1=ord(chunk.data[mid_offset+15+pal_off+i*pal_len])          #       GG              MM
					col2=ord(chunk.data[mid_offset+16+pal_off+i*pal_len])          #       RR              YY
					col3=ord(chunk.data[mid_offset+17+pal_off+i*pal_len])          #       ??              KK
					prcnt = ord(chunk.data[mid_offset+18+prcnt_off+i*pal_len])
					self.viewer_obj.add('Color:\t\t%02x'%col0+' %02x'%col1+' %02x'%col2+' %02x\t'%col3+'%u'%prcnt)
					
					rgbcol = self.fildoutl_clr(col0,col1,col2,col3,clrmode)
					if rgbcol != '':
						self.viewer['state']=Tkinter.NORMAL
						self.viewer.tag_add('color_rgb'+str(i), '%u.7'%(14+i))
						self.viewer.tag_config('color_rgb'+str(i), background=rgbcol)
						self.viewer['state']=Tkinter.DISABLED

			if fild_type == 'Pattern' or fild_type == 'Texture':
				#will be different for ver13
				bmpf_offs = 0x8
				coord_offset = 0xc
				if fild_type == 'Texture':
					bmpf_offs = 0x30
					coord_offset = 0x20
					
				self.viewer_obj.add('Bmp_ID: \t%02x %02x %02x %02x'%(ord(chunk.data[bmpf_offs]),ord(chunk.data[bmpf_offs+1]),ord(chunk.data[bmpf_offs+2]),ord(chunk.data[bmpf_offs+3])))
				[x]=struct.unpack('<L', chunk.data[coord_offset:coord_offset+4])
				[y]=struct.unpack('<L', chunk.data[coord_offset+4:coord_offset+8])
				if x > 0x7FFFFFFF:
					x = x - 0x100000000
				if y > 0x7FFFFFFF:
					y = y - 0x100000000
				self.viewer_obj.add('X/Y:\t\t%.2f/%.2f'%(x/10000.0,y/10000.0))

#############################################################################################
# LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA LODA #
#############################################################################################
		if chunk.fourcc == 'loda' and cdr_version > 6:                  

			[numofparms] = struct.unpack('<L', chunk.data[0x4:0x8])
			[startofparms] = struct.unpack('<L',chunk.data[0x8:0xC])
			[startoftypes] = struct.unpack('<L',chunk.data[0xC:0x10])
				
			type = ord(chunk.data[0x10])
			if loda_type.has_key(type):
				self.viewer_obj.add('\nObj.Type:\t%s'%loda_type[type])
			else:
				self.viewer_obj.add('\nObj.Type:\tUnknown (%u)'%type)
			for i in range(numofparms, 0, -1):
				[offset] = struct.unpack('<L',chunk.data[startofparms+i*4-4:startofparms+i*4])
				[argtype] = struct.unpack('<L',chunk.data[startoftypes + (numofparms-i)*4:startoftypes + (numofparms-i)*4+4])
				print 'Arg: %x'%argtype+'  Off: %x'%offset
				st = ''
				if loda_type_func.has_key(argtype) == 1:
					st = loda_type_func[argtype](chunk,type,offset,cdr_version)
				else:
					print 'Unknown argtype: %x'%argtype                             
				
				if st != '':
					self.viewer_obj.add(st)
					
#############################################################################################                            
# BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX BBOX OBBX #
#############################################################################################
		if (chunk.fourcc == 'bbox' or chunk.fourcc == 'obbx') and cdr_version > 6:
			num = 2
			if chunk.fourcc == 'obbx':
				num = 4
			for i in range(num):    
				[X] = struct.unpack('<L', chunk.data[i*8:i*8+4])
				[Y] = struct.unpack('<L', chunk.data[i*8+4:i*8+8])
				if X > 0x7FFFFFFF:
					X = X - 0x100000000
				if Y > 0x7FFFFFFF:
					Y = Y - 0x100000000
				self.viewer_obj.add('\nX%u'%i+'/Y%u:\t'%i+'%.2f/'%round(X/10000.0,2)+'%.2f mm'%round(Y/10000.0,2))

#############################################################################################                            
# FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS FLGS #
#############################################################################################
# WARNING! Guesses.
		if chunk.fourcc == 'flgs':
			self.viewer_obj.add('\nWARNING!!! It is a rougly guessed meaning of the flags!\n')
			b0 = ord(chunk.data[0])
			b1 = ord(chunk.data[1])
			b2 = ord(chunk.data[2])
			b3 = ord(chunk.data[3])
			if b3 == 0x98: # Layer
				if flgs_layer.has_key(b0):
					self.viewer_obj.add('Type:\t%s'%flgs_layer[b0])
				else:
					self.viewer_obj.add('Unknown:\t%x'%b0)
			if b3 == 0x90: # Page
				apx = ''
				if b0 == 0x40:
					apx = '(with lens or container)'
				self.viewer_obj.add('Type:\tPage #%u '%b2+apx)
			if b3 == 0x10: #Grp
				self.viewer_obj.add('Type:\tGroup')
			if b3 == 0x8: #Obj
				apx = ''
				if b1 == 0x0a:
					apx = '(Xparent outline?) '
				if b2 == 0x8:
					apx = apx + '(Has a lens?) '
				if b2 == 0x10:
					apx = apx + '(Container?) '
					
				self.viewer_obj.add('Type:\tObj. '+apx)

#############################################################################################                            
# BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF BMPF #  
#############################################################################################

		if chunk.fourcc == 'bmpf':
			bitmapoffset = 0x3e # will be right for Monochrome
			bmpsize = chunk.rawsize + 10
			bitmapoffset = struct.pack('<I', bitmapoffset)
			bmpsize = struct.pack('<I', bmpsize)
			self.bmpbuf = 'BM'+bmpsize[0:4]+'\x00\x00\x00\x00'+bitmapoffset[0:4]+chunk.data[4:]
#                       result = open('result.bmp', 'wb')
#                       result.write(self.bmpbuf)
#                       result.close()
			self.bitmap = PIL.Image.open(StringIO.StringIO(self.bmpbuf ))
			self.bitmap.load()
			chunk.infocollector.bitmap = PIL.ImageTk.PhotoImage(self.bitmap)
			self.viewer['state']=Tkinter.NORMAL
			self.viewer.insert(Tkinter.END, 'Bitmap:     ')
			self.viewer.image_create(Tkinter.END, image=chunk.infocollector.bitmap)
			self.viewer['state']=Tkinter.DISABLED

#############################################################################################                            
# ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW ARRW #  
#############################################################################################
		if chunk.fourcc == 'arrw':
			self.viewer_obj.add('\nArrw_Idx:\t%02X '%ord(chunk.data[0])+'%02X '%ord(chunk.data[1])+'%02X '%ord(chunk.data[2])+'%02X '%ord(chunk.data[3]))
			[numofcoords] = struct.unpack('<h', chunk.data[0x8:0xA])
			[coord_offset] = struct.unpack('<L', chunk.data[0xA:0xE])
			
			st = ''
			self.bitmap = PIL.Image.new('RGB',(200,200),'white')
			draw = PIL.ImageDraw.Draw(self.bitmap)
#			[X1] = struct.unpack('<L', chunk.data[coord_offset+8:coord_offset+0xC])
#			[Y1] = struct.unpack('<L', chunk.data[coord_offset+0xC:coord_offset+0x10])
#			if X1 > 0x7FFFFFFF:
#				X1 = X1 - 0x100000000
#			if Y1 > 0x7FFFFFFF:
#				Y1 = Y1 - 0x100000000
			linenodes = []			
			for i in range(numofcoords):
				[varX] = struct.unpack('<L', chunk.data[coord_offset+8+i*8:coord_offset+0xC+i*8])
				[varY] = struct.unpack('<L', chunk.data[coord_offset+0xC+i*8:coord_offset+0x10+i*8])
				if varX > 0x7FFFFFFF:
					varX = varX - 0x100000000
				if varY > 0x7FFFFFFF:
					varY = varY - 0x100000000
				linenodes.append(varX/10000)
				linenodes.append(varY/10000)

				Type = ord(chunk.data[0xE+i])
				NodeType = ''
				# FIXME! Lazy to learn dictionary right now, will fix later
				if Type&2 == 2:
					NodeType = '    Char. start'                                                                                                                                                                    
				if Type&4 == 4:
					NodeType = NodeType+'  Can modify'                                                                                                                                                                      
				if Type&8 == 8:
					NodeType = NodeType+'  Closed path'
				if Type&0x10 == 0 and Type&0x20 == 0:
					NodeType = NodeType+'  Discontinued'
				if Type&0x10 == 0x10:
					NodeType = NodeType+'  Smooth'
				if Type&0x20 == 0x20:
					NodeType = NodeType+'  Symmetric'
				if Type&0x40 == 0 and Type&0x80 == 0:                                                                           
					NodeType = NodeType+'  START'
				if Type&0x40 == 0x40 and Type&0x80 == 0:
					NodeType = NodeType+'  Line'                                                    
				if Type&0x40 == 0 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Curve'                                                   
				if Type&0x40 == 0x40 and Type&0x80 == 0x80:
					NodeType = NodeType+'  Arc'                                                     

				st = st+'X%u/Y%u:  \t%u/%u mm%s\n'%(i,i,round(varX/10000.0,2),round(varY/10000.0,2),NodeType)

			X = linenodes[0]
			Y = linenodes[1]
			for i in range(len(linenodes)/2-1):
				X1 = linenodes[i*2+2]
				Y1 = linenodes[i*2+3]
				draw.line((120+X,100+Y,120+X1,100+Y1),fill=0)
				X=X1
				Y=Y1

			self.viewer_obj.add(st)
			self.bitmap.load()
			chunk.infocollector.bitmap = PIL.ImageTk.PhotoImage(self.bitmap)
			self.viewer['state']=Tkinter.NORMAL
			self.viewer.insert(Tkinter.END, 'Bitmap:     ')
			self.viewer.image_create(Tkinter.END, image=chunk.infocollector.bitmap)
			self.viewer['state']=Tkinter.DISABLED
