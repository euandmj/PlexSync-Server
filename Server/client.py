import socket

host = "192.168.0.2"
port = 54000

# magnet:?xt=urn:btih:4bf843445b1a19a42dd884f20a5931e42d107b35&dn=South.Park.S22E01.Dead.Kids.720p.WEBRip.AAC2.0.H.264.mkv&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969
#
magnetlink = "magnet:?xt=urn:btih:ae3cee7faf0512e5d3bef237e8f93681a5562adf&dn=Parks+and+Recreation+-+Season+1+%5B720p%5D&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969"
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    s.sendall(bytes(magnetlink, encoding="utf-8"))
    data = s.recv(1024)

print("received: ", repr(data))
