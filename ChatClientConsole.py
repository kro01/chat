""" 2 socketa - za prastane i za poluchawane
 purvo se prasta 0 za poluchawane ili 1 za 1 izprastane ot klienta
 sled towa se izprasta username
 wsichki saobstebia sa po 32 byte
 servera ima dwa spisaka sus socketi - edin za poluchawane i edin za prastane
 pri swarzwane na socket se chete parvi byte - ako e 0, znachi klienta ste poluchawa - t.e. e za prastane
"""

import wx
import os
import threading
import logging
import socket
import time
import sys


evt_result_id = wx.NewId()

def evt_result(win, func):
    """Define Result Event."""
    win.Connect(-1, -1, evt_result_id, func)

   
class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""
    def __init__(self, data):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(evt_result_id)
        self.data = data

def make_length(msg, length):
    if(len(msg) > length):
        msg = msg[:length]    
    else:
        while(len(msg) < length):
            msg += ' '
    return msg

  
class ChatTransfer(object):
    messages = list()
    def __init__(self):
         self.msg_lock = threading.Lock()
        
    def add_message(self, msg):
        self.messages.append(msg)
        logging.warn("Adding message:" + msg)
        logging.warn("Number messages: %s", len(self.messages))            
    
    def get_message(self):
        msg = self.messages.pop(0)
        return msg
    
    def is_empty(self):
            r = len(self.messages) == 0
            logging.warn("is empty number msg: %s Returning %s", len(self.messages), r)   
            return r

            
class ChatReceiveThread(threading.Thread):
    def __init__(self, ChatTransfer, receive_event, sock, notify_win):
        logging.warn('ChatReceiveThread init')
        super(ChatReceiveThread,self).__init__()
        self.ChatTransfer = ChatTransfer
        self.receive_event = receive_event
        self.should_run = True
        self.sock = sock
        self._notify_window = notify_win
    
    def signal_end(self):
        self.should_run = False
    
    def run(self):
        logging.warn('ChatReceiveThread started, Should run:%d', self.should_run)
        while(self.should_run):
            logging.warn('Callign recv')
            msg = self.sock.recv(32)
            logging.warn('Recv result:' + msg)
            if(msg.strip() == ''):
                continue
            logging.warn("Received msg: %s", msg)
            self.receive_event.set()
            wx.PostEvent(self._notify_window, ResultEvent(msg))
        
class ChatSendThread(threading.Thread):
    def __init__(self, ChatTransfer, send_event, sock):
        super(ChatSendThread,self).__init__()
        self.ChatTransfer = ChatTransfer
        self.send_event = send_event
        self.should_run = True
        self.sock = sock
        self.sock.setblocking(1)
       
    def run(self):
        logging.warn("ChatSendThread started")
        while(self.should_run):
            if(self.send_event.wait(5)):
                logging.warn("send event fired")
                msg = "Test Message"
                if not self.ChatTransfer.is_empty():
                    msg = self.ChatTransfer.get_message()
                logging.warn("start sending message: <%s>", msg)
                
                if(self.sock.sendall(msg) == None):
                    logging.warn("Successfuly sent:" + msg)
                else:
                    logging.warn("Error sending sent")
                self.send_event.clear()

    def signal_end(self):
        self.should_run = False
        
    def set_should_stop(self):
        self.should_run = False
    
class MainWindow(wx.Frame):
    def __init__(self, parent, title, user):
        self.dir_name=''
        self.set_user(user)
        wx.Frame.__init__(self, parent, title=title, size=(1600,400))
        self.control = wx.TextCtrl(self)
        self.chat_text = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE)
        
        self.CreateStatusBar() 

        file_menu= wx.Menu()
        menu_open = file_menu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
        menu_about= file_menu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menu_exit = file_menu.Append(wx.ID_EXIT,"&Exit"," Terminate the program")

        # Creating the menubar.
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menu_bar)  # Adding the MenuBar to the Frame content.

        # Events.
        self.Bind(wx.EVT_MENU, self.on_open, menu_open)
        self.Bind(wx.EVT_MENU, self.on_exit, menu_exit)
        self.Bind(wx.EVT_MENU, self.on_about, menu_about)

        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = []
        
        logging.warn("Start connecting")
        host = 'localhost'    # The remote host
        port = 8182              # The same port as used by the server
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.recv_sock.connect((host, port))
            self.recv_sock.sendall('0')
            self.recv_sock.sendall(self.user)
            logging.info("Receive Socket connected")
            
            self.send_sock.connect((host, port))
            self.send_sock.sendall('1')
            self.send_sock.sendall(self.user)
            logging.info("send Socket connected")
            
        
        except socket.error:
            self.should_run = False
            return
        
            
        logging.warn('connected')   
        
        self.chat_transfer = ChatTransfer()
        self.chat_transfer_recv = ChatTransfer()
        self.send_event = threading.Event()
        self.recv_event = threading.Event()
        self.chat_lock = threading.Lock()
        logging.warn("Init receive thread")
        self.recv_thread = ChatReceiveThread(self.chat_transfer_recv,
                                             self.recv_event,
                                             self.recv_sock, self)
        self.chat_thread = ChatSendThread(self.chat_transfer,
                                          self.send_event,
                                          self.send_sock)

        self.chat_thread.start()
        self.recv_thread.start()
        
        self.buttons.append(wx.Button(self, -1, "&Send"))
        self.buttons.append(wx.Button(self, -1, "&Send File"))
        
        self.sizer2.Add(self.buttons[0], 1, wx.EXPAND)
        self.sizer2.Add(self.buttons[1], 1, wx.EXPAND)
        
        self.buttons[0].SetDefault()
        
        self.Bind(wx.EVT_BUTTON, self.on_send, self.buttons[0])
        self.Bind(wx.EVT_BUTTON, self.on_send_file, self.buttons[1])
        
        evt_result(self,self.on_result)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.chat_text, 1, wx.EXPAND)
        self.sizer.Add(self.control, 2, wx.EXPAND)
        
        self.sizer.Add(self.sizer2, 0, wx.EXPAND)

        #Layout sizers
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.sizer.Fit(self)
        self.Show()
        
    def on_result(self, event):
        """Show Result status."""
       
        logging.warn("On result: event.data: %s", event.data)
        complete_chat = self.chat_text.GetValue()
        complete_chat += "\n" +  event.data
        complete_chat = complete_chat[-100:]
        self.chat_text.SetValue(event.data)
    
    def on_send(self,e):
        msg = self.control.GetValue()
        logging.warn(msg)
        self.chat_transfer.add_message(make_length('0' + msg, 32))
        self.control.Clear()
        logging.warn("Setting send event for:" + msg)
        self.send_event.set()
    
    def on_send_file(self,e):
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.OPEN)
        file_contents = ""
        if dlg.ShowModal() == wx.ID_OK:
            file_name = dlg.GetFilename()
            dir_name = dlg.GetDirectory()
            f = open(os.path.join(dir_name, file_name), 'r')
            file_contents = f.read()
            f.close()
        dlg.Destroy()
        file_length = len(file_contents)
        self.chat_transfer.add_message('1' + make_length(str(file_length), 8) + make_length(file_name, 64)  + file_contents)
        self.control.Clear()

        self.send_event.set()
    
    def on_about(self,e):
        # Create a message dialog box
        dlg = wx.MessageDialog(self, "Chat client", "About FMI CHAT", wx.OK)
        dlg.ShowModal() # Shows it
        dlg.Destroy() # finally destroy it when finished.

    def on_exit(self,e):
        self.chat_thread.set_should_stop()
        self.Close(True)  # Close the frame.

    def on_open(self,e):
        """ Open a file"""
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.file_name = dlg.GetFilename()
            self.dir_name = dlg.GetDirectory()
            f = open(os.path.join(self.dir_name, self.file_name), 'r')
            self.control.SetValue(f.read())
            f.close()
        dlg.Destroy()
    
    def set_user(self, user):
        self.user = make_length(user, 32)
    

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
