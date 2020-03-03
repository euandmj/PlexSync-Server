import shutil
from shutil import disk_usage
import os
import sys

class Disk():
    folders = [str]

    def __init__(self, name : str, folders : list(str)):
        self.name = name[ : name.index('\\')]
        self.TotalGiB(disk_usage(self.name)[0])

        folders = folders


    @property
    def Free(self):
        return disk_usage(self.name)[3]

    @property
    def Used(self):
        return disk_usage(self.name)[2]
    
    @property 
    def TotalGiB(self):
        return self.total * 1e9
    @TotalGiB.setter
    def TotalGiB(self, value):
        self.total = value

class DiskUtil(object):
    self.disks = dict(string, Disk)


    def __init__(self):
        pass

    def addDrive(self, name : str):
        self.disks[name] = Disk(name)






