import configparser
import os
import sys
from ast import literal_eval

import requests

import logger
from server import Server

config = configparser.ConfigParser()


class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"
class WebAPIStart(Exception):
    def __str__(self):
        return "error trying to open qBittorrent\n \
                    Please have qBitTorrent running with WebAPI on %s" % config.get("qBittorrent", "host")

def openQbittorrent(path):
    os.startfile(path)

def main(args):           
    l = logger.logger(filename="server_log", user=config.get("Server", "name"))
    s = Server(config, l)
    s.start()


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
            dirs = literal_eval(config.get("Plex", "directories"))
            for d in dirs:
                if not os.path.exists(d):
                    raise PathNotFound
            dirs = config.get("General", "savepath")
            if not os.path.exists(dirs):
                raise PathNotFound

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
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
        except IOError:
            print("the config.ini file is not found")
            raise
        except (KeyboardInterrupt, SystemExit):
            os.kill(pid=os.getpid())
            raise
        except Exception as e:
            print("Critical error occurred:\n%s" % e)

       

