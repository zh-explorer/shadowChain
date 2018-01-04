import asyncio
import logging
import socket
import struct
from functools import partial

from shadow import context
from shadow.log import logger
from shadow.protocols.baseRoute import BaseServer, out_protocol_chains, BaseClient, BaseProtocolError
from shadow.unit.misc import check_host_type

SOCK_SERVER_START = 1
SOCK_SERVER_GET_METHODS = 2
SOCK_SERVER_REQUEST = 3
SOCK_SERVER_DOMAIN_LEN = 4
SOCK_SERVER_DOMAIN = 5
SOCK_SERVER_IPV4 = 6
SOCK_SERVER_CONN = 7
SOCK_SERVER_ROUTE = 8
SOCK_SERVER_CONN_ERROR = 9


class Sock5Error(BaseProtocolError): pass


class Sock5Server(BaseServer):
    def __init__(self, loop):
        super().__init__(loop)
        self.cache_data = bytearray()
        self.cache_size = 0
        self.request_size = None
        self.sock_status = None
        self.n_methods = None
        self.cmd = None
        self.address_type = None
        self.target_host = None
        self.target_port = None
        self.request_all = False

    def connection_made(self, transport):
        self.transport = transport
        self.request_size = 2
        self.sock_status = SOCK_SERVER_START

        peername = transport.get_extra_info('peername')
        logger.info('Connection from {}'.format(peername))

    def data_received(self, data):
        # logger.debug("get data")
        # logger.debug(data)
        self.cache_data += data
        self.cache_size += len(data)
        if self.request_all:
            # logger.debug("here")
            data = self.cache_data
            self.cache_data = bytearray()
            self.cache_size = 0
            self.sock_decode(data)
            return

        while self.cache_size >= self.request_size != -1 and not self.request_all:  # decode until no enough data remain
            data = self.cache_data[:self.request_size]
            self.cache_data = self.cache_data[self.request_size:]
            self.cache_size -= self.request_size
            self.request_size = -1
            self.sock_decode(data)

    def sock_decode(self, data):
        # logger.debug(self.sock_status)
        if self.sock_status == SOCK_SERVER_START:
            if data[0] != 5:
                logger.info("get a no sock5 connection")
                self.close(None)
                return
            self.request_size = data[1]
            self.sock_status = SOCK_SERVER_GET_METHODS

        elif self.sock_status == SOCK_SERVER_GET_METHODS:
            if b"\x00" not in data:
                self.transport.write(b"\x05\xff")
                self.close(None)
                return
            self.transport.write(b'\x05\x00')
            self.request_size = 4
            self.sock_status = SOCK_SERVER_REQUEST

        elif self.sock_status == SOCK_SERVER_REQUEST:
            if data[0] != 5 or data[2] != 0:
                self.replies_error(1)
                return
            elif data[1] != 1:
                self.replies_error(1)
                return
            elif data[3] != 1 and data[3] != 3:
                self.replies_error(3)
                return
            self.cmd = data[1]
            self.address_type = data[3]
            if self.address_type == 3:
                self.sock_status = SOCK_SERVER_DOMAIN_LEN
                self.request_size = 1
            elif self.address_type == 1:
                self.sock_status = SOCK_SERVER_IPV4
                self.request_size = 6

        elif self.sock_status == SOCK_SERVER_IPV4:
            self.target_host = socket.inet_ntoa(data[:4])
            self.target_port = struct.unpack(b"!H", data[4:])[0]
            self.sock_status = SOCK_SERVER_CONN
            self.request_size = -1

            self.connection(self.target_host, self.target_port)

        elif self.sock_status == SOCK_SERVER_DOMAIN_LEN:
            self.request_size = data[0] + 2
            self.sock_status = SOCK_SERVER_DOMAIN

        elif self.sock_status == SOCK_SERVER_DOMAIN:
            self.target_host = bytes(data[:-2])
            self.target_port = struct.unpack(b"!H", data[-2:])[0]
            self.sock_status = SOCK_SERVER_CONN
            self.request_size = -1
            self.connection(self.target_host, self.target_port)

        elif self.sock_status == SOCK_SERVER_CONN:
            assert data is None
            host, port = self.transport.get_extra_info("sockname")
            addr_raw = socket.inet_aton(host)
            port_raw = struct.pack(b"!H", port)
            self.transport.write(b"\x05\x00\x00\x01" + addr_raw + port_raw)
            self.sock_status = SOCK_SERVER_ROUTE
            self.request_all = True

        elif self.sock_status == SOCK_SERVER_ROUTE:
            # logger.debug("here2")
            # logger.debug(data)
            self.peer_proto.write(bytes(data))

        elif self.sock_status == SOCK_SERVER_CONN_ERROR:
            self.replies_error(5)  # TODO need replies by exc

        else:
            raise Sock5Error("sock5 decode status error")

    def replies_error(self, errno):
        reply = bytearray(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        reply[1] = errno
        self.transport.write(bytes(reply))
        self.close(None)

    def connection(self, host, port):
        logger.info("a new sock5 request to %s:%d" % (self.target_host, self.target_port))
        self.transport.pause_reading()

        def conn_complete(future):
            exc = future.exception()
            if exc is not None:
                logger.info("sock5 conn error %s" % str(exc))
                self.exc = exc
                self.sock_status = SOCK_SERVER_CONN_ERROR
                self.sock_decode(None)
            else:
                logger.debug("conn complete")
                self.peer_proto, self.peer_transport = future.result()
                self.transport.resume_reading()
                self.sock_decode(None)

        task = asyncio.ensure_future(out_protocol_chains(host, port, self.loop, self),
                                     loop=self.loop)
        task.add_done_callback(conn_complete)


SOCK_CLIENT_METHOD_REPLY = 17
SOCK_CLIENT_WAIT_REPLIES = 18
SOCK_CLIENT_GET_IPV4 = 19
SOCK_CLIENT_GET_NDOAMIN = 20
SOCK_CLIENT_GET_IPV6 = 21
SOCK_CLIENT_GET_DOMAIN = 22
SOCK_CLIENT_ROUTE = 0


class Sock5Client(BaseClient):
    def __init__(self, loop, prev_proto, origin_host, origin_port, target_host=None, target_port=None):
        super().__init__(loop, prev_proto, origin_host, origin_port)
        if type(origin_host) == str:
            origin_host = origin_host.encode()
        if type(target_host) == str:
            target_host = target_host.encode()

        if target_host is None and target_port is None:
            self.target_host = origin_host
            self.target_port = origin_port
        else:
            assert target_port is not None and target_host is not None
            self.target_host = target_host
            self.target_port = target_port

        self.host_type = check_host_type(self.target_host)
        if self.host_type == 4:
            raise Sock5Error("The ipv6 is not support now")
        self.sock_status = None
        self.request_size = None
        self.cache_data = bytearray()
        self.cache_size = 0
        self.request_all = False
        self.peer_host = None
        self.peer_port = None

        # do not throw connection event. until the conn is finish

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.sock_status = SOCK_CLIENT_METHOD_REPLY
        self.next_proto.write(b"\x05\x01\x00")
        self.request_size = 2

    def data_received(self, data):
        self.cache_data += data
        self.cache_size += len(data)
        if self.request_all:
            # logger.debug("here")
            data = self.cache_data
            self.cache_data = bytearray()
            self.cache_size = 0
            self.sock_decode(data)
            return

        while self.cache_size >= self.request_size != -1 and not self.request_all:  # decode until no enough data remain
            data = self.cache_data[:self.request_size]
            self.cache_data = self.cache_data[self.request_size:]
            self.cache_size -= self.request_size
            self.request_size = -1
            self.sock_decode(data)

    def sock_decode(self, data):
        if self.sock_status == SOCK_CLIENT_METHOD_REPLY:
            if data != b'\x05\x00':  # this mean some error is happened
                raise Sock5Error("no method support")
            request = bytearray(b"\x05\x01\x00")
            request.append(self.host_type)  # the host_type is the same in RFC1928
            if self.host_type == 1:
                request += socket.inet_aton(str(self.target_host, encoding='ascii'))
            elif self.host_type == 3:
                request.append(len(self.target_host))
                request += self.target_host
            request += struct.pack(b'!H', self.target_port)
            self.next_proto.write(request)
            self.sock_status = SOCK_CLIENT_WAIT_REPLIES
            self.request_size = 4
        elif self.sock_status == SOCK_CLIENT_WAIT_REPLIES:
            if data[0] != 5:
                raise Sock5Error("socks5 version check error")
            elif data[1] != 0:
                raise Sock5Error("The error code is %d" % data[1])
            elif data[2] != 0:
                logger.error("the RSV is not zero")

            if data[3] == 1:
                self.sock_status = SOCK_CLIENT_GET_IPV4
                self.request_size = 6
            elif data[3] == 3:
                self.sock_status = SOCK_CLIENT_GET_NDOAMIN
                self.request_size = 1
            elif data[3] == 4:
                self.sock_status = SOCK_CLIENT_GET_IPV6
                self.request_size = 18
            else:
                raise Sock5Error("unknown addr type")

        elif self.sock_status == SOCK_CLIENT_GET_IPV4:
            self.peer_host = socket.inet_ntoa(data[:4])
            self.peer_port = struct.unpack(b"!H", data[4:])[0]
            self.sock_status = SOCK_CLIENT_ROUTE
            self.request_all = True
            self.prev_proto.connection_made(self.transport, self)

        elif self.sock_status == SOCK_CLIENT_GET_NDOAMIN:
            self.request_size = data[0] + 2
            self.sock_status = SOCK_CLIENT_GET_DOMAIN

        elif self.sock_status == SOCK_CLIENT_GET_DOMAIN:
            self.peer_host = bytes(data[:-2])
            self.peer_port = struct.unpack(b"!H", data[-2:])[0]
            self.sock_status = SOCK_CLIENT_ROUTE
            self.request_all = True
            self.prev_proto.connection_made(self.transport, self)

        elif self.sock_status == SOCK_CLIENT_GET_IPV6:
            self.peer_host = socket.inet_ntop(socket.AF_INET6, data[:16])
            self.peer_port = struct.unpack(b"!H", data[16:])[0]
            self.sock_status = SOCK_CLIENT_ROUTE
            self.request_all = True
            self.prev_proto.connection_made(self.transport, self)

        elif self.sock_status == SOCK_CLIENT_ROUTE:
            self.prev_proto.data_received(bytes(data))
        else:
            raise Sock5Error("sock5 decode status error")

    def write(self, data):
        self.next_proto.write(data)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_debug(enabled=True)
    logging.getLogger('asyncio').setLevel(logging.DEBUG)
    get_server_proto = partial(Sock5Server, loop)
    coro = loop.create_server(get_server_proto, '0.0.0.0', 3333)

    context.protocol_chains = [Sock5Client]
    logger.debug(context.protocol_chains)
    server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.shutdown_asyncgens()
    loop.stop()
    loop.close()
