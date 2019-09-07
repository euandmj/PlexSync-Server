from serv import Server
from ast import literal_eval

import os
import configparser
import logger


class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"


if __name__ == "__main__":
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
    l = logger.logger(filename="server_log", user=config.get("Server", "name"))
    s = Server(config, l)
    s.start()