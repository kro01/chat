# 2 socketa - za prastane i za poluchawane
# purvo se prasta 0 za poluchawane ili 1 za 1 izprastane ot klienta
# sled towa se izprasta username
# wsichki saobstebia sa po 32 byte
# servera ima dwa spisaka sus socketi - edin za poluchawane i edin za prastane
# pri swarzwane na socket se chete parvi byte - ako e 0, znachi klienta ste poluchawa - t.e. e za prastane


import wx
import os
import threading
import logging
import socket
import time
import sys
#import win32event

EVT_RESULT_ID = wx.NewId()

def EVT_RESULT(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, EVT_RESULT_ID, func)
    
class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data

def makeLength(msg, length):
    if(len(msg) > length):
        msg = msg[:length]    
    else:
        while(len(msg) < length):
            msg += ' '
    return msg
    
class ChatTransfer(object):
    messages = list()
    def __init__(self):
         self.msglock = threading.Lock() # send lock is used for sending
        
    def addMessage(self, msg):
         #with self.msglock:
            self.messages.append(msg)
            logging.warn("Adding message:" + msg)
            logging.warn("Number messages: %s", len(self.messages))            
    
    def getMessage(self):
        #with self.msglock:
            msg = self.messages.pop(0)
            #self.messages.remove(msg)
            return msg
    
    def isEmpty(self):
        #with self.msglock:
            r = len(self.messages) == 0
            logging.warn("isEmpty number msg: %s Returning %s", len(self.messages), r)   
            return r

            
class ChatReceiveThread(threading.Thread):
    def __init__(self, chatTransfer, receiveEvent, sock, notify_win):
        super(ChatReceiveThread,self).__init__()
        self.chatTransfer = chatTransfer
        self.receiveEvent = receiveEvent
        self.shouldRun = True
        self.sock = sock
        self._notify_window = notify_win
    
    def signalEnd(self):
        self.shouldRun = False
    
    def run(self):
        while(self.shouldRun):
            msg = self.sock.recv(32)
            if(msg.strip() == ''):
                continue
            #self.chatTransfer.addMessage(msg)
            logging.warn("Received msg: %s", msg)
            self.receiveEvent.set()
            wx.PostEvent(self._notify_window, ResultEvent(msg))
        
class ChatSendThread(threading.Thread):
    def __init__(self, chatTransfer, sendEvent, sock):
        super(ChatSendThread,self).__init__()
        self.chatTransfer = chatTransfer
        self.sendEvent = sendEvent
        self.shouldRun = True
        self.sock = sock
        self.sock.setblocking(1)
       
    def run(self):
        logging.warn("ChatSendThread started")
        while(self.shouldRun):
            if(self.sendEvent.wait(5)):
                logging.warn("send event fired")
                msg = "Test Message"
                if not self.chatTransfer.isEmpty():
                    msg = self.chatTransfer.getMessage()
                logging.warn("start sending message: <%s>", msg)
                
                if(self.sock.sendall(msg) == None):
                    logging.warn("Successfuly sent")
                else:
                    logging.warn("Error sending sent")
                self.sendEvent.clear()
            else:
                logging.warn("send event time out")
            
    def signalEnd(self):
        self.shouldRun = False
        
    def setShouldStop(self):
        self.shouldRun = False
    
class MainWindow(wx.Frame):
    def __init__(self, parent, title, user):
        self.dirname=''
        self.setUser(user)
        # A "-1" in the size parameter instructs wxWidgets to use the default size.
        # In this case, we select 200px width and the default height.
        wx.Frame.__init__(self, parent, title=title, size=(1600,400))
        self.control = wx.TextCtrl(self)
        self.chatText = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE)
        
        self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
        menuAbout= filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Events.
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)

        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = []
        
        logging.warn("Start connecting")
        HOST = 'localhost'    # The remote host
        PORT = 8182              # The same port as used by the server
        self.recvSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sendSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.recvSock.connect((HOST, PORT))
            self.recvSock.sendall('0')
            self.recvSock.sendall(self.user)
            
            self.sendSock.connect((HOST, PORT))
            self.sendSock.sendall('1')
            self.sendSock.sendall(self.user)
        
        except socket.error:
            self.shouldRun = False
            return
        
            
        logging.warn('connected')   
        
        self.chatTransfer = ChatTransfer()
        self.chatTransferRecv = ChatTransfer()
        self.sendEvent = threading.Event()
        self.recvEvent = threading.Event()
        self.chatLock = threading.Lock()
        self.chatThread = ChatSendThread(self.chatTransfer, self.sendEvent, self.sendSock)
        self.recvThread = ChatReceiveThread(self.chatTransferRecv, self.recvEvent, self.recvSock, self)
        self.chatThread.start()
        self.recvThread.start()
        
        #self.buttons.append(wx.Button(self, -1, "&Send")
        #self.sizer2.Add(self.buttons[0], 1, wx.EXPAND)
        self.buttons.append(wx.Button(self, -1, "&Send"))
        self.sizer2.Add(self.buttons[0], 1, wx.EXPAND)
        self.buttons[0].SetDefault()
        
        self.Bind(wx.EVT_BUTTON, self.OnSend, self.buttons[0])
        EVT_RESULT(self,self.OnResult)
        #for i in range(1, 7):
        #    self.buttons.append(wx.Button(self, -1, "Button &"+str(i)))
        #    self.sizer2.Add(self.buttons[i], 1, wx.EXPAND)

        # Use some sizers to see layout options
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.chatText, 1, wx.EXPAND)
        self.sizer.Add(self.control, 2, wx.EXPAND)
        
        self.sizer.Add(self.sizer2, 0, wx.EXPAND)

        #Layout sizers
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.sizer.Fit(self)
        self.Show()
        
    def OnResult(self, event):
        """Show Result status."""
        #if event.data is None:
            # Thread aborted (using our convention of None return)
            #self.status.SetLabel('Computation aborted')
        #else:
        logging.warn("OnResult: event.data: %s", event.data)
        completeChat = self.chatText.GetValue()
        completeChat += "\n" +  event.data
        completeChat = completeChat[-100:]
        self.chatText.SetValue(event.data)
            # Process results here
            #self.status.SetLabel('Computation Result: %s' % event.data)
            # In either event, the worker is done
            #self.worker = None
    
    def OnSend(self,e):
        msg = self.control.GetValue()
        logging.warn(msg)
        self.chatTransfer.addMessage(makeLength(msg, 32))
        self.control.Clear()
        logging.warn("Setting send event")
        self.sendEvent.set()
    
    def OnAbout(self,e):
        # Create a message dialog box
        dlg = wx.MessageDialog(self, "Chat client", "About FMI CHAT", wx.OK)
        dlg.ShowModal() # Shows it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self,e):
        self.chatThread.setShouldStop()
        self.Close(True)  # Close the frame.

    def OnOpen(self,e):
        """ Open a file"""
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            f = open(os.path.join(self.dirname, self.filename), 'r')
            self.control.SetValue(f.read())
            f.close()
        dlg.Destroy()
    
    def setUser(self, user):
        self.user = makeLength(user, 32)
    
#logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.info("Info")
logging.warn("warn")
logging.debug("debug")
if(len(sys.argv) < 2):
    logging.warn("No arguments. Usage: python ChatClientConsole <user>")
    exit()
else:
    user = sys.argv[1]
    
app = wx.App(False)
frame = MainWindow(None, "Chat Client FMI", user)
app.MainLoop()