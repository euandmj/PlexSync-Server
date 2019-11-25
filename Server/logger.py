import os
import re
import datetime
from enum import Enum


# file io mode enum
# txt, json
class FileMode(Enum):
    txt = 0
    json = 1
    xml = 2

REGEX_SYMBOL_OR_SPACE = r"[-!$%^&*()_+|~=`{}\[\]: \";'<>?,.\/]"



class logger:
    _defaultPath_ = str(os.path.dirname(os.path.abspath(__file__)))
    SIGNATURE_REGEX_RULE = r"([dthmsu][-!$%^&*()_+|~=`{}\[\]: \";'<>?,.\/]*){1,5}"

    def __init__(self, filename, filepath=_defaultPath_, user="non-user", encoding="utf-8"):
        

        self.user = user
        self.filepath = filepath + "\\" + filename + ".txt"
        self.sign = "ud h:m:s:"
        self.encoding = encoding




    
    # to format input to the following rule:
    # {<identifier>}
    # i.e. {d}/{t}::{u} = date/time::user
    # d = date
    # t = time -> HH:MM:SS
    # h = hour
    # m = minute
    # s = second
    # u = user
    def setSignature(self, sign):
        # function takes in a formatted string like above and 
        # sets the message always printed on a log accordingly

        # does input match the regex
        assert re.match(self.SIGNATURE_REGEX_RULE, sign), "input sign is not correct expression."

        self.sign = sign

    def getSignString(self):
        worker = self.sign

        signstr = ""

        for s in worker:
            if s == '':
                continue
            if s == 'd':
                signstr += str(datetime.date.today())
            elif s == 't':
                signstr += str(datetime.datetime.now().time())
            elif s == 'h':
                signstr += str(datetime.datetime.now().hour)
            elif s == 'm':
                signstr += str(datetime.datetime.now().minute)
            elif s == 's':
                signstr += str(datetime.datetime.now().second)
            elif s == 'ms':
                signstr
            elif s == 'u':
                signstr += "(%s)" % self.user            

            # if the character is exactly 1 of any symbol or space
            if re.match(REGEX_SYMBOL_OR_SPACE, s):
                signstr += s

        return signstr        


    def open(self, mode="w", encoding="utf-8"):
        self.activeFile = open(file=self.filepath, mode=mode, encoding=encoding)

    def close(self):
        self.activeFile.close()

    def log(self, logmsg):
        with open(file=self.filepath, mode='a', encoding=self.encoding) as f:
            f.write("%s %s\n" % (self.getSignString(), logmsg))


    
        




