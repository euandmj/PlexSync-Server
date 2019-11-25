import configparser
import datetime
import os
import re
import socket
import sys
import threading
import time
from ast import literal_eval
from json import loads
from multiprocessing import Process
from urllib.parse import unquote

from plexapi import myplex
from plexapi.library import Library
from plexapi.server import PlexServer
from qbittorrent import Client

import logger

class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"

global DEFAULT_DOWNLOADED_FILE_PATH
global plex_directories
global prefixes
global client
global initTime
global config

# load below globals via .config
config = configparser.ConfigParser()
try:
    with open("config.ini") as f:
        config.read_file(f)

        # validate all data exists
        try:
            config.get("Server", "name")
            config.get("Server", "host")
            config.get("Server", "port")
            config.get("Plex", "server")
            config.get("Plex", "username")
            config.get("Plex", "password")
            config.get("Plex", "directories")
            config.get("qBittorrent", "host")
            config.get("qBittorrent", "username")
            config.get("qBittorrent", "password")
            config.get("General", "savepath")

            # verify directories
            dirs = literal_eval(config.get("Plex", "directories"))
            for d in dirs:
                if not os.path.exists(d):
                    raise PathNotFound
            dirs = config.get("General", "savepath")
            if not os.path.exists(dirs):
                raise PathNotFound
            
        except (configparser.NoOptionError, configparser.NoSectionError) as e:
            print("Error validating config.ini: \n%s" % e)
            raise
        except PathNotFound as e:
            print(e)
            raise
except IOError:
    print("the config.ini file is not found")
    raise
finally:
    myPlex = myplex.MyPlexAccount(username=config.get("Plex", "username"), password=config.get("Plex", "password"))
    client = Client(config.get("qBittorrent", "host"))
    client.login(config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))
    log = logger.logger(filename="server_log", user=config.get("Server", "name"))    
    DEFAULT_DOWNLOADED_FILE_PATH = config.get("General", "savepath")
    plex_directories = literal_eval(config.get("Plex", "directories"))
    initTime = datetime.datetime.now()

def getDownloadedList():
    # list all downloaded folders
    paths = [f for f in os.listdir(DEFAULT_DOWNLOADED_FILE_PATH)]
    
    return ','.join(paths)

def getServerTime():
    return str(initTime)[:-7]

def getPlexDirectories():
    # ? is a protected character
    return '?'.join(plex_directories)

def updateLibrary():
    src = myPlex.resource(config.get("Plex", "server")).connect()
    src.library.update()

def getTorrentlist():
    torrents = []

    for t in client.torrents():
        torrents.append(str(t["hash"]) + "~" + t["name"] + "~" + str(t["progress"]) + "~" + t["state"])

    return '\n'.join(torrents)

def checkForUpdate():
    # no completed torrents. skip. 
    if not client.torrents(filter="completed"):
        return
    
    for torrent in client.torrents(filter="completed"):
        print("removing ", torrent["name"])
        log.log("COMPLETED %s" % torrent["name"])
        client.delete(torrent["hash"])
    
    print("updating library...")

    updateLibrary()
    

def autoUpdater():
    from twisted.internet import task, reactor
    
    # schedule a function to check if any of the hashes are now completed
    f = task.LoopingCall(checkForUpdate)
    
    f.start(interval=15)
    reactor.run()


def downloadTorrentFromUri(uri, pathIndex):
    def downloadTorrent():
        client.download_from_link(uri, savepath=DEFAULT_DOWNLOADED_FILE_PATH)

        # return the extracted hash from the uri
        # hash appears before the name in the uri and is wrapped in identifiable tags

        # parse out any http uri syntax
        magnet = unquote(uri)

        magnet = re.sub(r'magnet:\?xt=urn:btih:', '', magnet)
        magnet = magnet[:magnet.index('&dn=')]

        # if the string now matches a hash regex
        if re.match('[a-zA-Z0-9]*', magnet):
            return magnet
        else:
            return None
    def getAppropriateFilePath(torrent, pathIndex):
        import difflib
        def getSeasonSubDir(name, season, path):
            dirs = [f for f in os.listdir(path) if not os.path.isfile(os.path.join(path, f))]

            # find existing season subfolder
            for d in dirs:
                if ("s" + season).lower() in d.lower() or \
                    ("season " + season).lower() in d.lower():
                    return path + "\\" + d
            
            # directory doesnt exist, create and return
            newdir = "%s\\%s Season %s" % (path, name, season)
            os.mkdir(newdir)
            return newdir

        client_path = plex_directories[pathIndex]

        try:
            if '.' in torrent['name']:
                t_split = torrent['name'].split('.')
            elif ' ' in torrent['name']:
                t_split = torrent['name'].split(' ')

            # find if torrent has seasons. 
            # usual syntax is SXXEXX
            # group1- name
            # group2 - season (value)
            # group3 - episode (value)
            # group4 - rest
            regex = re.match(r'(.*?)\.S?(\d{1,2})E?(\d{2})\.(.*)', torrent['name'].replace(' ', '.'))
            
            if regex:
                # find the best fitting season folder                
                # gets the media name
                for i, st in enumerate(t_split):
                    if re.match(r"[Ss](\d{1,2})[Ee](\d{1,2})", st) or st.lower() == "season":
                        # presume name is up to this index
                        media_name = ' '.join(t_split[:i])
                        break
                
                # get all folders
                dirs = [f for f in os.listdir(client_path) if not os.path.isfile(os.path.join(client_path, f))]

                for d in dirs:
                    # if the ratio is acceptable
                    if difflib.SequenceMatcher(None, a=media_name.lower(), b=d.lower()).ratio() >= 0.77:
                        # we should try to find the right season folder
                        tv_dir = getSeasonSubDir(media_name, regex.group(2), client_path + "\\" + d)
                        return tv_dir

            return client_path + "\\" + torrent['name']
        except NameError:
            return DEFAULT_DOWNLOADED_FILE_PATH
        except Exception as e:
            log.log("getAppropiateFilePath ERROR: %s - %s" % (e, torrent["name"]))
            return DEFAULT_DOWNLOADED_FILE_PATH
    def overrideFilePath(hash):
        # use old api for torrent.set_location
        from qbittorrentapi import Client as xClient
        xc = xClient(config.get("qBittorrent", "host"), config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))
        
        xt = next((x for x in xc.torrents.info.downloading() if x["hash"].lower() == hash.lower()), None) 
        
        if xt is not None:
            print("suitable location for %s %s" % (xt["name"], new_save_path))
            log.log("WRITING %s TO %s" % (xt["name"], new_save_path))
            xt.set_location(new_save_path)

    torrent_hash = downloadTorrent()    
    log.log("TORRENT ADDED: %s" % uri)
    client.sync()
    
    # use the extracted hash to fetch the just added torrent
    t = next((x for x in client.torrents() if x["hash"].lower() == torrent_hash.lower()), None)
    
    if t is not None:
        #kinda bugs me how this call is here
        new_save_path = getAppropriateFilePath(t, int(pathIndex))

        # override file path. 
        overrideFilePath(torrent_hash)

def acceptClient(cnn, addr):
    with cnn:
        try:                    
            while 1:
                data = cnn.recv(1024)
                decoded = data.decode()                

                print("connection received by %s: %s" % (str(addr), decoded))                        
                log.log("connection received by %s: %s" % (str(addr), decoded))

                if not data:
                    break
                if re.match(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*", decoded[1:]):
                    downloadTorrentFromUri(decoded[1:], decoded[0])
                    cnn.sendall(b"sucessfully added torrent")
                elif decoded == "__listdownloaded__":
                    cnn.sendall(bytes(getDownloadedList(), encoding="utf-8"))
                elif decoded == "__listtorrents__":
                    cnn.sendall(bytes(getTorrentlist(), encoding="utf-8"))
                elif decoded == "__refreshplex__":
                    updateLibrary()
                    cnn.sendall(b"updated plex library")
                elif decoded == "__gettime__":
                    cnn.sendall(bytes(getServerTime(), encoding="utf-8"))
                elif decoded == "__getdirectories__":
                    cnn.sendall(bytes(getPlexDirectories(), encoding="utf-8"))
                else:
                    cnn.sendall(b"invalid request")
        except Exception as e:
            print(e)
            cnn.sendall(b"an error has occurred")
            log.log(str(e))

def runServer():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((config.get("Server", "host"), config.getint("Server", "port")))
        print("listening...")

        try:
            while 1:                
                s.listen()
                cnn, addr = s.accept()
                threading.Thread(target=acceptClient, args=(cnn, addr)).start()

        except ConnectionResetError as e:
            # occasional crash. 
            log.log(str(e))
            runServer()




if __name__ == "__main__":    
    server_process = Process(target=runServer)
    updater_process = Process(target=autoUpdater)
    server_process.start()
    updater_process.start()

    # run for debugging.
    # runServer()

    # autoUpdater()
