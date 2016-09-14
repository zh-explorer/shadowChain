import re
import socket
import struct


def getChain():
    return chain


class shadowChain(object):
    def __init__(self):
        self.buildChainList()

    def buildSocksTrain(self, addr, port, addrtype):
        iplist = list(self.iplist)
        iplist.append((addr, port, addrtype))
        try:
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect(iplist.pop(0)[:2])
        except socket.error:
            return None, '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
        replay = self.sockNext(remote, iplist)
        if replay[1] != '\x00':
            remote = None
        return remote, replay

    def getAddrType(self, addr):
        pattern = r"\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        if re.match(pattern, addr):
            return 1
        else:
            return 3

    def buildChainList(self):
        fp = open('list')
        self.iplist = []
        for line in fp:
            addr, port = line.strip().split(':')
            addrtype = self.getAddrType(addr)
            self.iplist.append((addr, int(port), addrtype))

        iplist = list(self.iplist)

        while True:
            self.uselist = []
            remote = self.testConnect(iplist)
            if remote == None:
                print "can't find"
                exit(1)
            while True:
                if len(iplist) == 0:
                    try:
                        remote.send('\x05\x01\x00')
                        if remote.recv(2) == '\x05\x00':
                            self.uselist.append(self.last)
                    except:
                        pass
                    if len(self.uselist) == 0:
                        print "can't find"
                        exit(1)
                    self.iplist = self.uselist
                    print len(self.iplist)
                    print self.iplist
                    return
                addr, port, addrtype = iplist.pop(0)
                if self.testSock(remote, addr, port, addrtype) == False:
                    iplist = self.uselist + iplist
                    break

    def testSock(self, remote, addr, port, addrtype):
        try:
            remote.send('\x05\x01\x00')
            if remote.recv(2) == '\x05\x00':
                self.uselist.append(self.last)
                print "try sock " + addr + ':' + str(port)
                if addrtype == 1:
                    data = '\x05\x01\x00\x01' + socket.inet_aton(addr) + struct.pack(">H", port)
                elif addrtype == 3:
                    data = '\x05\x01\x00\x03' + chr(len(addr)) + addr + struct.pack(">H", port)
                remote.send(data)
                data = remote.recv(4)

                if data[1] != '\x00':
                    return False
                else:
                    if data[3] == '\x01':
                        remote.recv(4+2)
                    elif data[3] == '\x03':
                        remote.recv(ord(remote.recv(1)[0])+2)
                    self.last = addr, port, addrtype
                    return True
        except:
            return False

    def testConnect(self, iplist):
        while True:
            try:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                t = len(self.uselist)+2
                t /= 2
                remote.settimeout(t)
                if len(iplist) == 0:
                    return None
                addr, port, addrtype = iplist.pop(0)
                self.last = addr, port, addrtype
                print "try connect " + addr + ':' + str(port)
                remote.connect((addr, port))
                break
            except:
                pass
        return remote

    def sockNext(self, sock, iplist):
        sock.send('\x05\x01\x00')
        if sock.recv(2) == '\x05\x00':
            try:
                ip, port, addrtype = iplist.pop(0)
                if addrtype == 1:
                    data = '\x05\x01\x00\x01' + socket.inet_aton(ip) + struct.pack(">H", port)
                elif addrtype == 3:
                    data = '\x05\x01\x00\x03' + chr(len(ip)) + ip + struct.pack(">H", port)
                sock.send(data)
                data = sock.recv(4 + 4 + 2)
            except socket.error:
                return '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'

            if data[1] != '\x00':
                return '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
            if len(iplist) == 0:
                return data
            else:
                return self.sockNext(sock, iplist)


chain = shadowChain()
