
class PathNotFound(Exception):
    def __str__(self):
        return "Directory not found"
class WebAPIStart(Exception):
    def __str__(self):
        return "error trying to open qBittorrent\n \
                    Please check that 'qbt_savepath' under '[General]' is configured with the correct install path."
class ServerRequestError(Exception):
    def __init__(self, innerexcept : Exception, methodname: str):
        self.innerexception = innerexcept
        self.method = methodname
    def __str__(self):
        return f"{type(self.innerexception)} occured in {self.method}:\n{str(self.innerexception)}"