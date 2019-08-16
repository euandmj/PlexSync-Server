import server
from multiprocessing import Process


if __name__ == "__main__":
    server_process = Process(target=server.runServer)
    updater_process = Process(target=server.autoUpdater)
    server_process.start()
    updater_process.start()