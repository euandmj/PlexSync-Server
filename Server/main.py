if __name__ == "__main__":
    import os
    import difflib
    a = 'magnet:?xt=urn:btih:19bb5835ebdf6ab5edc7ae1ba96ebb41f9f9e5ae&dn=South.Park.S22E07.WEB.h264-TBS&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969'
    b = 'magnet:?xt=urn:btih:19bb5835ebdf6ab5edc7ae1ba96ebb41f9f9e5ae&dn=South.Park.S22E07.WEB.h264-TBS%5brarbg%5d&tr=udp%3a%2f%2ftracker.leechers-paradise.org%3a6969&tr=udp%3a%2f%2ftracker.openbittorrent.com%3a80&tr=udp%3a%2f%2fopen.demonii.com%3a1337&tr=udp%3a%2f%2ftracker.coppersurfer.tk%3a6969&tr=udp%3a%2f%2fexodus.desync.com%3a6969'

    print(difflib.SequenceMatcher(None, "abc", "abcd").ratio())