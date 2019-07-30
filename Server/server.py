import socket
import time
import datetime
import re
import configparser
import os
import sys

from multiprocessing import Process

from plexapi import myplex
from plexapi.server import PlexServer
from plexapi.library import Library
from qbittorrent import Client
import logger


global DEFAULT_FILE_PATH
global initTime

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
            config.get("qBittorrent", "host")
            config.get("qBittorrent", "username")
            config.get("qBittorrent", "password")
        except (configparser.NoOptionError, configparser.NoSectionError) as e:
            print("Error validating config.ini: \n%s" % e)
            raise
            # raise Exception("Error validating config.ini: \n%s" % e)
except IOError:
    print("the config.ini file is not found")
    raise
finally:
    myPlex = myplex.MyPlexAccount(username=config.get("Plex", "username"), password=config.get("Plex", "password"))
    log = logger.logger(filename="server_log", user=config.get("Server", "name"))
    DEFAULT_FILE_PATH = config.get("General", "savepath")
    initTime = datetime.datetime.now()

def getDownloadedList():
    # list all downloaded folders
    paths = [f for f in os.listdir(DEFAULT_FILE_PATH)]# if not os.path.isfile(os.path.join(DEFAULT_FILE_PATH, f))]
    
    return ','.join(paths)

def getServerTime():
    return str(initTime)[:-7]

def updateLibrary():
    src = myPlex.resource(config.get("Plex", "server")).connect()
    src.library.update()

def getTorrentlist():
    client = Client("http://127.0.0.1:8080")
    client.login(config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))

    torrents = []

    for t in client.torrents():
        torrents.append(str(t["hash"]) + "~" + t["name"] + "~" + str(t["progress"]) + "~" + t["state"])

    # if not torrents:
    #     return "ree"
    return '\n'.join(torrents)

def checkForUpdate():
    client = Client("http://127.0.0.1:8080")
    client.login(config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))
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

# a crude way of finding most appropriate directory.
def getAppropriateFilePath(torrent):
    import difflib
    def getSeasonSubDir(torrentName, path, dir):
        # usual syntax is SXXEXX
        # group1- name
        # group2 - season (value)
        # group3 - episode (value)
        # group4 - rest
        regex = re.match(r'(.*?)\.S?(\d{1,2})E?(\d{2})\.(.*)', torrentName)
        
        # no regex match, return worker
        if not regex:
            return path
        else:           
            season = regex.group(2)

            dirs = [f for f in os.listdir(path) if not os.path.isfile(os.path.join(path, f))]

            for d in dirs:
                if ("s" + season).lower() in d.lower() or \
                    ("season " + season).lower() in d.lower():
                    return path + "\\" + d
            
            # directory doesnt exist, create and return
            newdir = path + "\\" + (regex.group(1) + " ") + ("S" + season)
            newdir = newdir.replace('.', ' ')
            os.mkdir(newdir)
            return newdir                

    # the directories for which folders for individual media are stored
    top_paths = [r"I:\Movies\Anime", r"I:\Movies\Documentaries", r"I:\Movies\TV", r"I:\Movies\Movies"]
    #fname = torrent["name"].replace('.', ' ')

    # for up to s01e02 regex
    if '.' in torrent['name']:
        t_name_split = torrent['name'].split('.')
    elif ' ' in torrent['name']:
        t_name_split = torrent['name'].split(' ')


    for i, st in enumerate(t_name_split):
        if re.match(r"[Ss](\d{1,2})[Ee](\d{1,2})", st) \
            or st.lower() in "season":
            # presume name is up to this point, compare torrent 'name'
            # with folder name
            media_name = ' '.join(t_name_split[:i])
    
    # for each directorry, analyze the subdirectories to find the most fitting match.
    try:
        for path in top_paths:
            # get all folders
            dirs = [f for f in os.listdir(path) if not os.path.isfile(os.path.join(path, f))]

            for d in dirs:
                # if the directory contains a part of the name, assume a fit match
                # if d in media_name:
                # -- new --
                # if the ratio is acceptable
                if difflib.SequenceMatcher(None, a=media_name, b=d).ratio() >= 0.77:
                    # if the dir is tv or anime; we should try to find the right season folder
                    if path == top_paths[0] or path == top_paths[2]:
                        tv_dir = getSeasonSubDir(torrent["name"], path + "\\" + d, d)
                        return tv_dir

                    # if the dir is documentaries or movies we can just plonk into root
                    return path + "\\" + d

        return DEFAULT_FILE_PATH
    except NameError:
        return DEFAULT_FILE_PATH
    except Exception as e:
        print(e)
        return DEFAULT_FILE_PATH

def downloadTorrent(uri, client):
    #print("qBittorrent Version: %s" % client.app_version())

    hard_coded_save_path = DEFAULT_FILE_PATH
    client.login(config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))

    #softlier_coded_save_path = getAppropriateFilePath()
    client.download_from_link(uri, savepath=hard_coded_save_path)

    log.log("TORRENT ADDED: %s" % uri)


    t = next((x for x in client.torrents() if x["magnet_uri"].lower() == uri.lower()), None)

    # magnet uri may not useful to fetch torrents 100%

    if t is not None:
        #kinda bugs me how this call is here
        new_save_path = getAppropriateFilePath(t)

        # override file path. 
        # function lost??
        #     
        def overrideFilePath(): 
            from qbittorrentapi import Client as xClient
            xc = xClient(config.get("qBittorrent", "host"), config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))
            xt = next((x for x in xc.torrents.info.downloading() if x["magnet_uri"].lower() == uri.lower()), None) 
            
            if xt is not None:
                print("suitable location for %s %s" % (xt["name"], new_save_path))
                log.log("WRITING %s TO %s" % (xt["name"], new_save_path))
                xt.set_location(new_save_path)

            # [s["magnet_uri"].lower() == uri.lower() for s in xc.torrents.info.downloading()]
            # #for xt in xc.torrents.info.downloading():
            # if xt["magnet_uri"].lower() == uri.lower():
            #     print("suitable location for %s:\n%s" % (xt["name"], new_save_path))
            #     xt.set_location(new_save_path)

        
        # use old api in overrideFilePath()
        overrideFilePath()

def runServer():
    client = Client("http://127.0.0.1:8080")
    client.login(config.get("qBittorrent", "username"), config.get("qBittorrent", "password"))
   

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("listening...")
        
        s.bind((config.get("Server", "host"), config.getint("Server", "port")))
        s.listen()

        while 1:
            cnn, addr = s.accept()
            with cnn:
                try:                    
                    while 1:
                        data = cnn.recv(1024)
                        decoded = data.decode()
                        print("connection received by %s: %s" % (str(addr), decoded))                        
                        log.log("connection received by %s: %s" % (str(addr), decoded))

                        if not data:
                            break
                        if re.match(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*", decoded):
                            downloadTorrent(decoded, client)
                            cnn.sendall(b"sucessfully added torrent")
                        elif decoded == "__listdownloaded__":
                            cnn.sendall(bytes(getDownloadedList(), encoding="utf-8"))
                        elif decoded == "__listtorrents__":
                            cnn.sendall(bytes(getTorrentlist(), encoding="utf-8"))
                        elif decoded == "__refreshplex__":
                            updateLibrary()
                            cnn.sendall(bytes("updated plex library", encoding="utf-8"))
                        elif decoded == "__gettime__":
                            cnn.sendall(bytes(getServerTime(), encoding="utf-8"))
                        else:
                            cnn.sendall(b"invalid request")
                except Exception as e:
                    print(e)
                    cnn.sendall(b"an error has occurred")
                    log.log(str(e))
                    break                    




if __name__ == "__main__":
    # server_process = Process(target=runServer)
    # updater_process = Process(target=autoUpdater)
    # server_process.start()
    # updater_process.start()

    # run for debugging.
    runServer()

    # autoUpdater()