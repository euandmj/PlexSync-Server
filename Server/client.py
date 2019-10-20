import sys
import re
import socket

if __name__ == "__main__":
    if not sys.argv:
        print("need magnet uri as first and only arg")
        exit()
    else:
        uri = sys.argv[0]
        dir = sys.argv[1]
        
        # if not re.match(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*", uri) or \
        #     len(dir) != 1:
        #     print("invalid uri/dir")
        #     exit()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(("localhost", 5400))
        client.send(uri)
        resp = client.recv(1024)

        print(resp)