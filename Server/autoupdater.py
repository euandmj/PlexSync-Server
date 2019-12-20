from exceptions import WebAPIStart

import requests
from plexapi import myplex
from qbittorrent import Client as qbittorrentClient
from twisted.internet import reactor, task

import logger


class AutoUpdater:

    def __str__(self):
        return \
            "Scheduler for removing downloaded torrents from qbittorrent and consequently updating Plex"

    def __init__(self, config, _logger, interval=30, ):
        self.config = config
        self.interval = interval
        self.logger = _logger

        # login to the various clients
        self.login()

    def start(self):
        f = task.LoopingCall(self.checkForUpdate)

        f.start(interval=self.interval)
        reactor.run()

    def login(self):
        self.myPlex = myplex.MyPlexAccount(username=self.config.get(
            "Plex", "username"), password=self.config.get("Plex", "password"))
        self.client = qbittorrentClient(self.config.get("qBittorrent", "host"))

        self.client.login(self.config.get("qBittorrent", "username"),
                          self.config.get("qBittorrent", "password"))

    def checkForUpdate(self):
        # there are no torrents marked as completed. skip.
        try:
            if not self.client.torrents(filter="completed"):
                return
                
            # log and delete from client the completed torrents
            for torrent in self.client.torrents(filter="completed"):
                self.logger.log("COMPLETED %s" % torrent["name"])
            self.client.delete(torrent["hash"])
        except requests.exceptions.ConnectionError:
            self.startQbt()

        # update the plex library
        self.updateLibrary()

    def updateLibrary(self):
        res = self.myPlex.resource(self.config.get("Plex", "server")).connect()
        res.library.update()

    def startQbt(self):
        from os import startfile
        # qbittorrent was likely killed by vpn. restart qbt
        try:
            startfile(self.config.get("General", "qbt_savepath"))
        except WebAPIStart as e:
            self.logger.log(e)
