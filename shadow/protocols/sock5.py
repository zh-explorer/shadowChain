from shadow.log import logger
from shadow.protocols.baseRoute import BaseRoute, out_protocol_chains
import socket
import struct
import asyncio
from functools import partial
import logging

SOCK_START = 1
SOCK_GET_METHODS = 2
SOCK_REQUEST = 3
SOCK_DOMAIN_LEN = 4
SOCK_DOMAIN = 5
SOCK_IPV4 = 6
SOCK_CONN = 7
SOCK_ROUTE = 8
SOCK_CONN_ERROR = 9


class Sock5Server(BaseRoute):
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
        self.sock_status = SOCK_START

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
        if self.sock_status == SOCK_START:
            if data[0] != 5:
                logger.info("get a no sock5 connection")
                self.close(None)
                return
            self.request_size = data[1]
            self.sock_status = SOCK_GET_METHODS

        elif self.sock_status == SOCK_GET_METHODS:
            if b"\x00" not in data:
                self.transport.write(b"\x05\xff")
                self.close(None)
                return
            self.transport.write(b'\x05\x00')
            self.request_size = 4
            self.sock_status = SOCK_REQUEST

        elif self.sock_status == SOCK_REQUEST:
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
                self.sock_status = SOCK_DOMAIN_LEN
                self.request_size = 1
            elif self.address_type == 1:
                self.sock_status = SOCK_IPV4
                self.request_size = 6

        elif self.sock_status == SOCK_IPV4:
            self.target_host = socket.inet_ntoa(data[:4])
            self.target_port = struct.unpack(b"!H", data[4:])[0]
            self.sock_status = SOCK_CONN
            self.request_size = -1
            self.transport.pause_reading()
            self.connection(self.target_host, self.target_port)

        elif self.sock_status == SOCK_DOMAIN_LEN:
            self.request_size = data[0] + 2
            self.sock_status = SOCK_DOMAIN

        elif self.sock_status == SOCK_DOMAIN:
            self.target_host = bytes(data[:-2])
            self.target_port = struct.unpack(b"!H", data[-2:])[0]
            self.sock_status = SOCK_CONN
            self.request_size = -1
            self.transport.pause_reading()
            self.connection(self.target_host, self.target_port)

        elif self.sock_status == SOCK_CONN:
            assert data is None
            host, port = self.transport.get_extra_info("sockname")
            addr_raw = socket.inet_aton(host)
            port_raw = struct.pack(b"!H", port)
            self.transport.write(b"\x05\x00\x00\x01" + addr_raw + port_raw)
            self.sock_status = SOCK_ROUTE
            self.request_all = True

        elif self.sock_status == SOCK_ROUTE:
            # logger.debug("here2")
            # logger.debug(data)
            self.peer_proto.write(bytes(data))

        elif self.sock_status == SOCK_CONN_ERROR:
            self.replies_error(5)  # TODO need replies by exc

        else:
            raise Exception("sock5 decode status error")

    def replies_error(self, errno):
        reply = bytearray(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        reply[1] = errno
        self.transport.write(bytes(reply))
        self.close(None)

    def connection(self, host, port):
        logger.info("a new sock5 request to %s:%d" % (self.target_host, self.target_port))

        def conn_complete(future):
            exc = future.exception()
            if exc is not None:
                logger.info("sock5 conn error %s" % str(exc))
                self.exc = exc
                self.sock_status = SOCK_CONN_ERROR
                self.sock_decode(None)
            else:
                logger.debug("conn complete")
                self.peer_transport, self.peer_proto = future.result()
                self.transport.resume_reading()
                self.sock_decode(None)

        task = asyncio.ensure_future(out_protocol_chains(host, port, self.loop, self, self.transport),
                                     loop=self.loop)
        task.add_done_callback(conn_complete)

    # def write(self, data):
    #     logger.debug("write data")
    #     logger.debug(data)
    #     self.transport.write(data)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_debug(enabled=True)
    logging.getLogger('asyncio').setLevel(logging.WARN)
    get_server_proto = partial(Sock5Server, loop)
    coro = loop.create_server(get_server_proto, '0.0.0.0', 3333)

    server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.stop()
    loop.close()
