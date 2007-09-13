#! /usr/bin/python
import Tkinter, tkFileDialog, chunks, os, os_utils
from TreeWidget import FileTreeItem, TreeNode, TreeItem, ScrolledCanvas
from widgets import WebButton, WebEntry, PreviewPanel

class FileViewer:

	"""The file tree browser """

	def __init__(self, browsePath=os_utils.gethome()):
		self.browsePath=browsePath
		self.build_window()	
		
	def build_window(self):
		self.root = Tkinter.Tk()
		self.root.title('CDR/CMX/CDRX Explorer')
		
		if os.name == 'nt':
			self.root.option_readfile('tkDefaultsWin', 'interactive')
			self.browsePath='../../'
		else:
			self.root.option_readfile('tkDefaults', 'interactive')
		
		self.root.geometry('600x600+30+50')
		
		frame = Tkinter.Frame(self.root, border=5, relief='flat')
		frame.pack(side='top', expand=1, fill='both')
		
		treeFrame = Tkinter.Frame(frame, border=1, relief='flat', bg='#595D61')
		treeFrame.pack(side='left', expand=1, fill='both')
		
		self.preview=PreviewPanel(frame)
		self.preview.frame.pack(side='right', anchor='ne')
		
		self.refreshButton=WebButton(self.preview.frame, text='Refresh', command=self.build_tree)
		self.refreshButton.frame.pack(side='bottom', pady=10)
		
		self.tree = ScrolledCanvas(treeFrame, bg='#EDEDED', highlightthickness=0, takefocus=1)
		self.tree.frame.pack(side='top', expand=1, fill='both')
		self.build_tree()

	def build_tree(self):
		self.item = FileTreeItem(self.root, self.browsePath, filetypes=['cdr','cmx','ccx','CDR','CMX','CCX'], preview=self.preview)
		self.node = TreeNode(self.tree.canvas, None, self.item)
		self.node.expand()
		self.preview.clearPreview()
		
#Program entry point 

if __name__=='__main__':
	browser=FileViewer()
	browser.root.mainloop()
