# WebServer

## Version
Python version - 3.4.4 

Files included:
  - webserver.py
  - ws.conf (configuration file)

## Usage
How to run the webserver script
1. To run the script trigger below command from the directory where webserver.py is present 
      - python webserver.py
2. Webserver can be run on ports between 1024 and 65536, which is set in the ws.conf file
3. Make sure the ws.conf is present in the same directory as the script. Also make sure document root directory, where the html and other files are present, is updated in the ws.conf.
4. To test the Performance Evaluation of the webserver, run the client.py program.

## Design
webserver.py
1. Webserver can handle "GET" and "POST" requests from the client
2. For other methods, server will respond with a "501 Not Implemented"
3. For GET request, the server will check if the requested resource is available at servers end. If not found, then it will send a "404 Not Found" back to the client.
4. If found, then server will check if the content-type is supported (from the ws.conf). If not supported then server will respond back to the client with a "501 Not Implemented"
5. If content-type is supported then the server will respond back to the client with a "200 OK" and the requested resource.
6. If the request is using HTPP/1.0 protocol, then the server will close the client connection after sending the response. In the response, it will put "Connection: close" header.
7. If the request is using HTTP/1.1 protocol, server will check if the client has request a persistent connection in the header through "Connection: keep-alive" flag. If this is set then server will also respond back to the client with a "Connection: keep-alive" in the response header.
8. After sending a request, the server will start a timeout of a time specified in the ws.conf file.
9. The webserver uses a multithreaded approach, to create a thread to serve each client connection.
10. The server is also capable of handling pipelined requests, when client sends requests to the server one after the other without waiting for a response for each of them.
11. Server will then send a response to each of the requests in the order in which it was received.
