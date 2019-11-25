import sys
import re
import socket
import argparse

# parser = argparse.ArgumentParser(description="supply magnet link and directory ordinal")
# parser.add_argument(name_or_flags="-m", type=str)
# parser.add_argument(name_or_flags="-o", type=str)

# args = parser.parse_args()




if __name__ == "__main__":
    if not len(sys.argv) > 1:
        uri = input("paste the magnet")
    else:
        uri = sys.argv[1]
        
        # if not re.match(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*", uri) or \
        #     len(dir) != 1:
        #     print("invalid uri/dir")
        #     exit()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(("192.168.1.11", 54000))
        client.send(bytes(uri, encoding="utf-8"))
        resp = client.recv(1024)

        print(resp)
        input("press any key to exit")
