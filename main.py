import sys
from server import ThreadingTCPServer,Socks5Server

def main():
    filename = sys.argv[0]
    if len(sys.argv) < 2:
        print 'usage: ' + filename + ' port'
        sys.exit()
    socks_port = int(sys.argv[1])

    server = ThreadingTCPServer(('', socks_port), Socks5Server)
    print 'bind port: %d' % socks_port + ' ok!'
    server.serve_forever()


if __name__ == '__main__':
    main()