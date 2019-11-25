from logger import logger

class loggingService:


    def __init__(self, filename, filepath=_defaultPath_, user="non-user", encoding="utf-8"):
        self.logger = logger(filename, filepath=filepath, user=user, encoding=encoding)

    def log(self):
        pass
