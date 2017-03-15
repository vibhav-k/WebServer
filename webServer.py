#!/usr/bin/env python 

import socket 
import threading 
import os
import select
import _thread

class Server: 
    def __init__(self): 
        self.host = '' 
        try:
            self.port = int(config['ListenPort'])
        except ValueError:
            print("Enter a number for the port in the Config file (ws.conf)")
            os._exit(1)
        self.backlog = 5 
        self.size = 1024 
        self.server = None
        self.threads = [] 

    def openSocket(self): 
        try: 
            if self.port < 1024 or self.port > 65536 :
                raise AssertionError
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.host,self.port)) 
            self.server.listen(5) 
            print("The webserver has started. Listening on port "+ str(self.port) +"...")
        except AssertionError:
            print("Port number cannot be less than 1024 or greater than 65535")
            os._exit(1)
        except Exception as errors:
            if self.server: 
                self.server.close() 
            print ("Could not open socket: " + errors) 
            os._exit(1) 

    def run(self): 
        try:
            self.openSocket() 
            running = 1
            inputSock = [self.server]
            while running: 
                inputready,outputready,exceptready = select.select(inputSock,[],[])
                for s in inputready:                
                    # handle the server socket 
                    c = Client(self.server.accept())
                    #if a client connection is established, serve the requests in a new thread
                    c.start()
                    self.threads.append(c)
                    for t in self.threads:
                        if hasattr(t, "stopped"):
                            t.join()
        except KeyboardInterrupt as err:
                print("Keyboard Interrupt")
                os._exit(1)
        except Exception as err:
            # close all threads 
            print("Closing server")
            print("Error - ", err)
            self.server.close() 
            for c in self.threads: 
                c.join()
            os._exit(1)

class Client(threading.Thread): 
    def __init__(self, clientAddr):
        (client, address) = clientAddr
        threading.Thread.__init__(self, name = address)
        self.client = client 
        self.address = address 
        self.size = 1024
        self.requestHeaders = {}
        self.responseHeaders = []
        self.timeout = config['KeepaliveTime']
        self.rootDocument = config['DocumentRoot']

    def run(self):
        running = 1 
        while running:
            try:
                #receive the request from the client
                data = self.client.recv(self.size)
                print("Client - ", self.client)
                print("Address - ", self.address)
                print(data)
                if not data:
                    break
                del self.responseHeaders[:]
                #resolve the request headers
                self.resolveHeaders(data.decode())
                #check the HTTP protocol and connection flag to decide if it is a persistent connection or not 
                if self.checkProtocol(data.decode()):
                    if (not self.persistentConnection()):
                        running = 0
                        self.responseHeaders.append("Connection: close")
                    else:
                        self.responseHeaders.append("Connection: keep-alive")
                else:
                    running = 0
                    self.responseHeaders.append("Connection: close")
                file = self.decodeRequest(data.decode())
                self.constructResponseHeaders()
                self.sendResponse(file)
                #set a timeout for persistent connection
                self.client.settimeout(float(self.timeout))
                
            except ConnectionAbortedError as err:
                print ("Error - Connection aborted by client.\n", err)
                break
            except ConnectionResetError as err:
                print ("Error - Connection reset by client.\n", err)
                break
            except socket.timeout as err:
#                 print("Client connection timed out.")
                break
            except ValueError as err:
                print ("KeepaliveTime Value in the configuration file is not an integer or a float")
                break
            except KeyboardInterrupt as err:
                print("Keyboard Interrupt")
                _thread.exit()
                break
            except socket.error as err:
                print ("Error - Socket Error.\n", err)
                running = 0 
            except:
                running=0
        self.client.close()
        
    #Function to check which protocol client is using to communicate with the server
    def checkProtocol(self, request):
        proto = request.split("\n")[0].split()[2]
        if (float(proto.split('/')[1]) < 1.0 or float(proto.split('/')[1]) < 1.0):
            self.responseHeaders.append("HTTP/1.1")
        else:
            self.responseHeaders.append(proto)
        if (proto == "HTTP/1.1"):
            return True
        else:
            return False
        
    #Resolve the headers of the client request
    def resolveHeaders(self, request):
        if (len(request) < 1):
            return
        lines = request.split("\r\n")
        for element in lines:
            if (len(element.split(": ")) > 1):
                key, value = element.split(": ")
                self.requestHeaders[key] = value.split("\r")[0]
    
    #Check Connection flag for persistent connections
    def persistentConnection(self):
        if "keep-alive" in self.requestHeaders.values():
            return True
        else:
            return False
    
    #Function to construct the headers to be sent in the response
    def constructResponseHeaders(self):
        header = ''
        for head in self.responseHeaders:
            header += head + "\r\n"
        header += "\r\n"
        del self.responseHeaders[:]
        self.responseHeaders.append(header)
    
    #Function to send the response to the client for the request resource            
    def sendResponse(self, file):
        if os.path.exists(file):
            response = self.responseHeaders[0].encode() + open(file, mode='rb').read()
        else:
            response = self.responseHeaders[0].encode() + file.encode()
        self.client.send(response)
    
    #Function to check what resource is requested by the client. If the resource is available or not
    def decodeRequest(self, request):
        req = request.split(sep="\n")[0].split(" ")[0]
        #Check if the http protocol is supported by browser
        if (request.split(sep="\n")[0].split(" ")[2] not in ("HTTP/1.0\r", "HTTP/1.1\r", "HTTP/1.0", "HTTP/1.1")):
            headers = "501 Not Implemented"
            response = self.errorResponse(request, headers)
        #If http protocol is supported then check if it is a GET or a POST request
        elif (req == "GET" or req == "POST"):
            resource = request.split(sep="\n")[0].split(" ")[1]
            if (resource.endswith('/')):
                for res in config['DirectoryIndex']:
                    resource = self.rootDocument + "/" + res
                    if os.path.exists(resource):
                        break
            else:
                resource = self.rootDocument + resource
            #Check if the request resource is found or not
            if (not os.path.exists(resource)):
                headers = "404 Not Found"
                response = self.errorResponse(request, headers)
            else:
                response = resource
                ext = os.path.basename(resource).split(".")[-1]
                #Check if the requested content is supported. This is controlled through the ws.conf file
                if ("."+ext) not in config['ContentType'].keys():
                    headers = "501 Not Implemented"
                    response = self.errorResponse(request, headers)
                else:
                    headers = "200 OK"
                    self.responseHeaders.append("Content-Type: " + config['ContentType']['.' + ext])
            #if the request is POST, get the form data and send it back to the client in the respose along with the request resource
            if req=="POST":
                response = open(resource).read()
                response = self.processPOSTRequest(response, request) 
        #Check for bad requests or malformed requests
        else:
            headers = "400 Bad Request"
            response = self.errorResponse(request, headers) 
        self.responseHeaders[0] = self.responseHeaders[0] + " " + headers
        
        #create the content-type and content-type headers
        if (os.path.exists(response)):
            length = len(open(response, mode = 'rb').read())
        else:
            length = len(response)
        self.responseHeaders.append("Content-Length: " + str(length))
        return response
    
    #Construct the body for the responses other than 200 OK
    def errorResponse(self, request, code):
        response = ("<html><h1>" + code + "</h1>" + "<body>Error " + request + " </body></html>")
        return response
        
    #Function to process the POST request. The html to be sent to the client is to be modified to include the post data as well
    def processPOSTRequest(self, data, request):
        res = request.split("\r\n")[-1]
#         res = unquote_plus(request.split("\r\n")[-1])
        res = "<h1>Post Data</h1><pre>" + res + "</pre>\n"
        if ("<html>" in data):
            ch = data.split("<html>\n")
        ch[-1] = res + ch[-1] 
        response = ch[0] + ch[1]
        return response

#Function to be run in a thread to check for keyboard interrupt - Ctrl+C
def checkInterrupt():
    while 1:
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            os._exit(1)

#Function to get the values from the config file. The values in the ws.conf need to be separated by a TAB character
def setConfigs(file):
    fh = open (file)
    conf = {}
    for line in fh:
        line = line.split("\n")[0]
        if not line.startswith('#'):
            if (len(line.split("\t")) == 2):
                key, value = line.split("\t")
                if (value.startswith('"')):
                    value = value[1:-1]
                if (value.endswith('/') or value.endswith('\\')):
                    value = value[:-1]
                config[key] = value.split("\n")[0]
            elif (len(line.split("\t")) == 3 and line.split("\t")[1].startswith(".")):
                key1, key2, value2 = line.split("\t")
                if (value2[1:] == '\"' and value2[:-1] == '\"'):
                    value2 = value2[1:-1]
                conf[key2] = value2
            else:
                lines = line.split("\t")
                key = lines[0]
                del lines[0]
                value = lines
                config[key] = lines
    config[key1] = conf
    config['DocumentRoot'] = config['DocumentRoot'].replace("\\", "/")
    fh.close()

if __name__ == "__main__":
    try:
        file = "./ws.conf"
        global config
        config = {}
        threading.Thread(target=checkInterrupt).start()
        setConfigs(file)
        s = Server()
        s.run()
    except FileNotFoundError as err:
        print("Configuration file now found.")
        os._exit(1)
    except PermissionError:
        print("Python does not have permission to read ws.conf file")
        os._exit(1)
    except (KeyboardInterrupt, SystemExit) as err:
        print("Closing program")
        s.server.close()
        os._exit(1)