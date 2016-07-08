import threading
import socket
import logging
import time
#import sleep
import select
import os

s_list = dict()
r_list = dict()

class ServerState(object):
    #sendList = dict()
    #recvList = dict()
    #sendListLock = threading.Lock()
    def __init(self):
        #self.sendList = list()
        #self.sendListLock = threading.lock()
        return
        
    def add_client(self, socket):
    
        type = socket.recv(1)
        user = socket.recv(32).strip()
        logging.warn("Type: %s, User: %s", type, user)
        if(type == '0'):
            #self.sendList[user] = socket
            s_list[user] = socket
            logging.warn("Added client. Current number: %d", len(s_list.keys()))
        if(type == '1'):
            #self.recvList[user] = socket
            r_list[user] = socket
        #with self.sendListLock:
            #self.sendList.append(socket)
        
        socket.setblocking(1)
    
    #def getSendList(self):
    #    return dict(self.sendList)
    
    #def getRecvList(self):
    #    return dict(self.recvList)
    
    
    def has_send_list(self):
        #with self.sendListLock:
        logging.warn("hassendList s_list: %d", len(s_list.keys()))
        if s_list is None:
            return False
        if len(s_list.keys()) > 0:
            return True
        
        return False

class ClientThread(threading.Thread):
    def __init__(self, serverState):
        super(ClientThread,self).__init__()
        self.server_state = ServerState()
        self.should_run = True
        return
    
    def signal_end(self):
        self.should_run = False
        return
    
    def run(self):
        logging.warn("Start")   
        while self.should_run:
            logging.warn("will call has_send_list")
            if not self.server_state.has_send_list():
                logging.warn("no cients, sleeping")
                time.sleep(5)
            else:
                logging.warn("has clients, process")
                recv_list = r_list # self.serverState.getRecvList()
                send_list = s_list # self.serverState.getSendList()
                if(len(recv_list) == 0 and len(send_list) == 0):
                    logging.warn("empty list continue")
                    continue
                #msg = rList.values()[0].recv(32)
                #logging.warn("Received: %s", msg)

                #sList.values()[0].sendall("test")
                logging.warn("call select")
                ready_to_read, ready_to_write, in_error = select.select(recv_list.itervalues(), [], [])
                received_messages = list()
                    
                logging.warn("Number messages to receive: %d %d %d",
                             len(ready_to_read),
                             len(ready_to_write),
                             len(in_error))
                for s in ready_to_read:
                        user_name = recv_list.keys()[recv_list.values().index(s)]
                    #if recvList.values()[i] in ready_to_read:
                #for s in rList.values():
                        try:
                            type = s.recv(1)
                            if(type == '0') : # message
                                data = s.recv(32)
                                data = user_name + '> ' + data # append user name to message
                                received_messages.append(data)
                                logging.warn("Client received msg: %s",  data)
                            if(type == '1') : #file
                                file_length = int(s.recv(8))
                                file_name = s.recv(64).strip()
                                file_contents = s.recv(file_length)
                                directory = 'recv.files'
                                if not os.path.exists(directory):
                                    os.makedirs(directory)
                                full_name = os.path.join(directory, user_name
                                                         + '_' + file_name)
                                if os.path.exists(full_name):
                                    data = user_name
                                    + """ wants send you a file named:"""
                                    + file_name
                                    + """. You aleady have received file
                                    with such name from this user.
                                    To receive new file with the same name
                                    - please delete existing file at:"""
                                    + full_name
                                else:
                                    with open(full_name, "w") as text_file:
                                        text_file.write(file_contents)
                                    data = user_name 
                                    + ' have sent a file written to:'
                                    + full_name
                                received_messages.append(data)
                        except socket.error:
                            recv_list.pop(user_name, s)
                            continue
                
                #ready_to_read, ready_to_write, in_error = select.select([], sockets, [], 5)
                ready_to_read, ready_to_write, in_error = select.select([], send_list.itervalues(), [], [])
                
                logging.warn("Number messages to send: %d %d %d",
                             len(ready_to_read),
                             len(ready_to_write),
                             len(in_error))
                for s in ready_to_write:
                    #if ready_to_write[j]:
                        for msg in received_messages:
                            s.sendall(msg)
                            logging.warn("sending msg back")
                
                #time.sleep(5)
                #sleep(200)
            #msg = sock.recv(4096)
            #msg = sock.recv(4096)
        

class AcceptringThread(threading.Thread):
    def __init__(self, port, serverState):
        super(AcceptringThread,self).__init__()
        self.should_run = True
        self.port = port
        self.send_list = []
        self.server_state = ServerState()
        return
    
    def signal_end(self):
        self.should_run = False
        logging.warn("AcceptringThread signal_end called")
        return
    
    def run(self):
        #socket.setdefaulttimeout(60.0) # seconds
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #bind the socket to a public host,
        # and a well-known port
        server_socket.bind(('localhost', self.port))
        #become a server socket
        server_socket.listen(20) # number of chat sendList
        logging.warn("Server socket created")
        while self.should_run:
            try:
                #accept connections from outside
                (send_list_socket, address) = server_socket.accept()
                logging.warn("connection received")
                self.server_state.add_client(send_list_socket)
            except socket.timeout:
                logging.warn("no connection - timeout")
                pass
        
        logging.warn("AcceptringThread will end")
        #socket.close
        
def start_server():
    port = 8182
    print("Starting server at port {0}", port)
   
    server_state = ServerState()
    logging.warning(server_state.has_send_list())
    client_thread = ClientThread(server_state)
    accepting_thread = AcceptringThread(port, server_state)
    accepting_thread.start()
    client_thread.start()
    
    input("Press Enter to stop\n")
    logging.warn("Signalling end\n")
    
    accepting_thread.signal_end()
    client_thread.signal_end()

start_server()
