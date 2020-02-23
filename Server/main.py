import configparser
import os
import sys
from ast import literal_eval
from exceptions import PathNotFound, WebAPIStart

import requests

import logger
from server import Server

config = configparser.ConfigParser()

def openQbittorrent(path):
    os.startfile(path)

def verifyPaths(*args):
    for paths in args:
        if [d for d in paths if not os.path.exists(d)]:
            raise PathNotFound

def main(args):           
    l = logger.logger(filename="server_log", user=config.get("Server", "name"))
    Server(config, l).start()


if __name__ == "__main__":
    # load below globals via .config    try:
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
            verifyPaths(literal_eval(config.get("Plex", "directories")), [config.get("General", "savepath")])

            main(sys.argv)
            
        except (configparser.NoOptionError, configparser.NoSectionError) as e:
            print("Error validating config.ini: \n%s" % e)
            raise
        except PathNotFound as e:
            print(e)
            raise
        except requests.ConnectionError:
            try:
                openQbittorrent(config.get("General", "qbt_savepath"))
                main(sys.argv)
            except WebAPIStart as e:
                print(e)
            except (KeyboardInterrupt, SystemExit):
                raise
        except IOError:
            print("the config.ini file is not found")
        except (KeyboardInterrupt, SystemExit):
            os.kill(pid=os.getpid())
        except Exception as e:
            print("Critical error occurred:\n%s" % e)
