import SocketServer
import select
import socket
import struct
from socksChain import getChain




class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class Socks5Server(SocketServer.StreamRequestHandler):
    @staticmethod
    def handle_tcp(sock, remote):
        fdset = [sock, remote]
        while True:
            r, w, e = select.select(fdset, [], [])
            if sock in r:
                if remote.send(sock.recv(4096)) <= 0: break
            if remote in r:
                if sock.send(remote.recv(4096)) <= 0: break

    def handle(self):
        try:
            pass  # print 'from ', self.client_address nothing to do.
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send("\x05\x00")
            # 2. Request
            data = self.rfile.read(4)
            mode = ord(data[1])
            addrtype = ord(data[3])
            if addrtype == 1:  # IPv4
                addr = socket.inet_ntoa(self.rfile.read(4))
            elif addrtype == 3:  # Domain name
                addr = self.rfile.read(ord(sock.recv(1)[0]))
            port = struct.unpack('>H', self.rfile.read(2))[0]

            if mode == 1:  # 1. Tcp connect
                chain = getChain()
                remote, reply = chain.buildSocksTrain(addr, port, addrtype)
            else:
                reply = "\x05\x07\x00\x01"  # Command not supported
            sock.send(reply)
            # 3. Transferring
            if reply[1] == '\x00':  # Success
                if mode == 1:  # 1. Tcp connect
                    self.handle_tcp(sock, remote)
        except socket.error:
            print 'socket error while listen'
        except IndexError:
            print 'IndexError error while listen'

