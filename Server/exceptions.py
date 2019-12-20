
class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"
class WebAPIStart(Exception):
    def __str__(self):
        return "error trying to open qBittorrent\n \
                    Please check that 'qbt_savepath' under '[General]' is configured with the correct install path."
