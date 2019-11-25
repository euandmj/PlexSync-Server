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

import psutil
from plexapi import myplex
from qbittorrent import Client

from autoupdater import AutoUpdater


class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"

class Server:
    MAGNET_URI = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"
    COMMAND_GET_DLS = "__listdownloaded__"
    COMMAND_GET_TORRENTS = "__listtorrents__"
    COMMAND_GET_TIME = "__gettime__"
    COMMAND_GET_DIRECTORIES = "__getdirectories__"
    COMMAND_POST_REFRESH = "__refreshplex__"
    
    def __str__(self):
        return \
            "Handles TCP connections between this and client and manages downloads."
    
    def __init__(self, config, _logger, buffer=1024):
        self.config = config
        self.logger = _logger
        self.buffsize = buffer

        self.DEFAULT_DOWNLOADED_FILE_PATH = config.get("General", "savepath")
        self.plex_directories = literal_eval(config.get("Plex", "directories"))

        # set time as a property
        self._time = datetime.datetime.now()

        self.login()

        self.autoUpdater = AutoUpdater(config, _logger=self.logger)

    @property
    def time(self):
        return str(self._time)[:-7]
    @time.setter
    def time(self, value):
        self._time = value
    
    def start(self):
        # self.listen()
        # self.autoUpdater.start()

        server_prcs = Process(target=self.listen)
        updater_prcs = Process(target=self.autoUpdater.start)

        server_prcs.start()
        updater_prcs.start()

    def login(self):
        self.myPlex = myplex.MyPlexAccount(username=self.config.get("Plex", "username"), password=self.config.get("Plex", "password"))
        self.client = Client(self.config.get("qBittorrent", "host"))

        self.client.login(self.config.get("qBittorrent", "username"), self.config.get("qBittorrent", "password"))

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.config.get("Server", "host"), self.config.getint("Server", "port")))

            print("listening on %s:%i...." % (self.config.get("Server", "host"), self.config.getint("Server", "port")))
            self.logger.log("SERVER LISTENING")

            try:
                while 1:
                    s.listen()
                    cnn, addr = s.accept()
                    threading.Thread(target=self.acceptClient, args=(cnn, addr)).start()
            
            # occasional crash, restart the listen
            except ConnectionResetError as e:
                self.logger.log(str(e))
                # self.listen()
    
    def acceptClient(self, cnn, addr):
        try:
            while 1:
                data = cnn.recv(self.buffsize)
                decoded = data.decode()

                self.logger.log("CONNECTION: %s: %s" % (str(addr), decoded))

                if not data:
                    break
                if re.match(self.MAGNET_URI, decoded[1:]):
                    resp = self.downloadTorrent(decoded[1:], decoded[0])
                    encoding_resp = bytes(resp, encoding="utf-8")
                    cnn.sendall(encoding_resp)
                elif decoded == self.COMMAND_GET_DLS:
                    resp = bytes(self.getDownloadList, encoding="utf-8")
                    cnn.sendall(resp)
                elif decoded == self.COMMAND_GET_TORRENTS:
                    resp = bytes(self.getTorrentList, encoding="utf-8")
                    cnn.sendall(resp)
                elif decoded == self.COMMAND_POST_REFRESH:
                    self.updateLibrary()
                    cnn.sendall(b"updated plex library")
                elif decoded == self.COMMAND_GET_TIME:
                    resp = bytes(self.time, encoding="utf-8")
                    cnn.sendall(resp)
                elif decoded == self.COMMAND_GET_DIRECTORIES:
                    resp = bytes(self.getPlexDirectories, encoding="utf-8")
                    cnn.sendall(resp)
                else:
                    cnn.sendall(b"invalid request")
        except Exception as e:
            cnn.sendall(b"an error has occurred")
            self.logger.log(str(e))
            

    def downloadTorrent(self, uri, pathIndex):
        def download():
            self.client.download_from_link(uri, savepath=self.DEFAULT_DOWNLOADED_FILE_PATH)

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

            client_path = self.plex_directories[pathIndex]

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
                return client_path + "\\" + torrent['name']
            except Exception as e:
                self.logger.log("ERROR getAppropiateFilePath: %s - %s" % (e, torrent["name"]))
                return self.DEFAULT_DOWNLOADED_FILE_PATH
        def overrideFilePath(hash):
            # use old api for torrent.set_location
            from qbittorrentapi import Client as xClient
            xc = xClient(self.config.get("qBittorrent", "host"), self.config.get("qBittorrent", "username"), self.config.get("qBittorrent", "password"))
            
            xt = next((x for x in xc.torrents.info.downloading() if x["hash"].lower() == hash.lower()), None) 
            
            if xt is not None:
                # print("suitable location for %s %s" % (xt["name"], new_save_path))
                self.logger.log("WRITING %s TO %s" % (xt["name"], new_save_path))
                xt.set_location(new_save_path)        

        torrent_hash = download()    
        self.logger.log("TORRENT ADDED: %s" % uri)
        self.client.sync()
        
        # use the extracted hash to fetch the just added torrent
        t = next((x for x in self.client.torrents() if x["hash"].lower() == torrent_hash.lower()), None)
        
        if t is not None:
            #kinda bugs me how this call is here
            new_save_path = getAppropriateFilePath(t, int(pathIndex))

            # override file path. 
            overrideFilePath(torrent_hash)
        return "%s\n%s" % (t["name"], new_save_path)

    def updateLibrary(self):
        res = self.myPlex.resource(self.config.get("Plex", "server")).connect()
        res.library.update()
        
    @property
    def getDownloadList(self):
        # list all downloaded folders
        paths = [f for f in os.listdir(self.DEFAULT_DOWNLOADED_FILE_PATH)]
        
        return ','.join(paths)

    @property
    def getTorrentList(self):
        torrents = []


        try:
            _t = self.client.torrents()

        except Exception as e:
            # 403 forbiddent exception (cant find exception type)
            # try relogin
            self.logger.log(str(type(e)))
            self.login()
        finally:
            for t in _t:
                torrents.append(str(t["hash"]) + "~" + t["name"] + "~" + str(t["progress"]) + "~" + t["state"])
        
        return '\n'.join(torrents)        

    @property
    def getPlexDirectories(self):
        # ? is a protected char why not
        return '?'.join(self.plex_directories)


if __name__ == "__main__":
    pass
