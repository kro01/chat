import threading
import socket
import logging
import time
#import sleep
import select

sList = dict()
rList = dict()

class ServerState(object):
    sendList = dict()
    recvList = dict()
    sendListLock = threading.Lock()
    def __init(self):
        #self.sendList = list()
        #self.sendListLock = threading.lock()
        return
        
    def addClient(self, socket):
        type = socket.recv(1)
        user = socket.recv(32).strip()
        logging.warn("Type: %s, User: %s", type, user)
        if(type == '0'):
            self.sendList[user] = socket
            sList[user] = socket
        if(type == '1'):
            self.recvList[user] = socket
            rList[user] = socket
        #with self.sendListLock:
        #    self.sendList.append(socket)
        
        socket.setblocking(1)
    
    def getSendList(self):
        return dict(self.sendList)
    
    def getRecvList(self):
        return dict(self.recvList)
    
    
    def hassendList(self):
        with self.sendListLock:
            if self.sendList is None:
                return False
            if len(self.sendList) > 0:
                return True
        
        return False

class ClientThread(threading.Thread):
    def __init__(self, serverState):
        super(ClientThread,self).__init__()
        self.serverState = serverState
        self.shouldRun = True
        return
    
    def signalEnd(self):
        self.shouldRun = False
        return
    
    def run(self):
        logging.warn("Start")   
        while self.shouldRun:
            if not self.serverState.hassendList():
                logging.warn("no cients, sleeping")
                time.sleep(5)
            else:

                recvList = rList # self.serverState.getRecvList()
                sendList = sList # self.serverState.getSendList()
                #logging.warn("Recv List: %d, Send List : %d", len(recvList), len(sendList))
                if(len(recvList) == 0 and len(sendList) == 0):
                    continue
                #msg = rList.values()[0].recv(32)
                #logging.warn("Received: %s", msg)

                #sList.values()[0].sendall("test")
                ready_to_read, ready_to_write, in_error  = select.select(recvList.itervalues(), [], [], 60)
                receivedMessages = list()
                
                logging.warn("Number messages to receive: %d %d %d",   len(ready_to_read), len(ready_to_write), len(in_error))
                for s in ready_to_read:
                    #if recvList.values()[i] in ready_to_read:
                #for s in rList.values():
                        data = s.recv(32)
                        data = '> ' + data # append user name to message
                        receivedMessages.append(data)
                        logging.warn("Client received msg: %s",  data)
                
                #ready_to_read, ready_to_write, in_error = select.select([], sockets, [], 5)
                ready_to_read, ready_to_write, in_error  = select.select([], sendList.itervalues(), [], 60)
                
                logging.warn("Number messages to send: %d %d %d",  len(ready_to_read), len(ready_to_write), len(in_error))
                for s in ready_to_write:
                    #if ready_to_write[j]:
                        for msg in receivedMessages:
                            s.sendall(msg)
                            logging.warn("sending msg back")
                
                #time.sleep(5)
                #sleep(200)
            #msg = sock.recv(4096)
            #msg = sock.recv(4096)
        

class AcceptringThread(threading.Thread):
    def __init__(self, port, serverState):
        super(AcceptringThread,self).__init__()
        self.shouldRun = True
        self.port = port
        self.sendList = []
        self.serverState = serverState
        return
    
    def signalEnd(self):
        self.shouldRun = False
        return
    
    def run(self):
        logging.warn("Accepting thread start")
        socket.setdefaulttimeout(60) # seconds
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #bind the socket to a public host,
        # and a well-known port
        serversocket.bind(('localhost', self.port))
        #become a server socket
        serversocket.listen(20) # number of chat sendList
        logging.warn("Server socket created")
        while self.shouldRun:
            try:
                #accept connections from outside
                (sendListocket, address) = serversocket.accept()
                logging.warn("connection received")
                #now do something with the sendListocket
                #in this case, we'll pretend this is a threaded server
                self.serverState.addClient(sendListocket)
            except socket.timeout:
                logging.warn("no connection - timeout")
                pass
        
        #socket.close
        
def start_server():
    port = 8182
    print("Starting server at port {0}", port)
   
    serverState = ServerState()
    logging.warning(serverState.hassendList())
    clientThread = ClientThread(serverState)
    acceptingThread = AcceptringThread(port, serverState)
    acceptingThread.start()
    clientThread.start()
    
    input =  raw_input("Press Enter to stop")
    acceptingThread.signalEnd()
    clientThread.signalEnd()

start_server()