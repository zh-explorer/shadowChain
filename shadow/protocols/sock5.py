from .baseProtocol import BaseProtocol, BaseServerTop, out_protocol_chains, BaseProtocolError
from shadow import context
import asyncio
import socket
import struct
from shadow.unit.misc import check_host_type


class Socks5Error(BaseProtocolError): pass


class Socks5Server(BaseServerTop):
    def __init__(self, loop):
        super().__init__(loop)
        self.cmd = None
        self.address_type = None
        self.target_host = None
        self.target_port = None

    def made_connection(self):
        pass

    def received_data(self):
        data = yield from self.read(2)
        if data[0] != 5:
            context.logger.info("get a no sock5 connection")
            self.close(None)
            return True
        data = yield from self.read(data[1])
        if b"\x00" not in data:
            self.next_proto.write(b"\x05\xff")
            self.close(None)
            return True
        self.next_proto.write(b'\x05\x00')
        data = yield from self.read(4)
        if data[0] != 5 or data[2] != 0:
            self.replies_error(1)
            return True
        elif data[1] != 1:
            self.replies_error(1)
            return True
        elif data[3] != 1 and data[3] != 3:
            self.replies_error(3)
            return True
        self.cmd = data[1]
        self.address_type = data[3]
        if self.address_type == 3:
            data = yield from self.read(1)
            data = yield from self.read(data[0] + 2)
            self.target_host = bytes(data[:-2])
            self.target_port = struct.unpack(b"!H", data[-2:])[0]
        elif self.address_type == 1:
            data = yield from self.read(6)
            self.target_host = socket.inet_ntoa(data[:4])
            self.target_port = struct.unpack(b"!H", data[4:])[0]

        self.connection(self.target_host, self.target_port)
        result = yield from self.read(-1)
        if not result:
            self.replies_error(5)
            return True

        host, port = self.transport.get_extra_info("sockname")
        addr_raw = socket.inet_aton(host)
        port_raw = struct.pack(b"!H", port)
        self.next_proto.write(b"\x05\x00\x00\x01" + addr_raw + port_raw)
        while True:
            data = yield from self.read(0)
            self.peer_proto.write(data)

    def replies_error(self, errno):
        reply = bytearray(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        reply[1] = errno
        self.next_proto.write(bytes(reply))
        self.close(None)

    def connection(self, host, port):
        context.logger.info("a new sock5 request to %s:%d" % (self.target_host, self.target_port))

        def conn_complete(future):
            exc = future.exception()
            if exc is not None:
                context.logger.info("sock5 conn error %s" % str(exc))
                self.exc = exc
                try:
                    self.request_size = self.receive_iter.send(False)
                except StopIteration as e:
                    if not e.value:
                        raise e
            else:
                context.logger.debug("conn complete")
                self.peer_proto, self.peer_transport = future.result()
                try:
                    self.request_size = self.receive_iter.send(True)
                except StopIteration as e:
                    if not e.value:
                        raise e

        task = asyncio.ensure_future(out_protocol_chains(host, port, self.loop, self),
                                     loop=self.loop)
        task.add_done_callback(conn_complete)


class Socks5Client(BaseProtocol):
    def __init__(self, loop, prev_proto, origin_host, origin_port, target_host=None, target_port=None):
        if type(origin_host) == str:
            origin_host = origin_host.encode()
        if type(target_host) == str:
            target_host = target_host.encode()
        super().__init__(loop, prev_proto, origin_host, origin_port)

        if target_host is None and target_port is None:
            self.target_host = origin_host
            self.target_port = origin_port
        else:
            assert target_port is not None and target_host is not None
            self.target_host = target_host
            self.target_port = target_port

        self.host_type = check_host_type(self.target_host)
        if self.host_type == 4:
            raise Socks5Error("The ipv6 is not support now")
        self.peer_host = None
        self.peer_port = None

    def made_connection(self):
        self.next_proto.write(b"\x05\x01\x00")

    def received_data(self):
        data = yield from self.read(2)
        if data != b'\x05\x00':  # this mean some error is happened
            self.close()
            self.connection_complete.set_result(False)
            raise Socks5Error("no method support")
        request = bytearray(b"\x05\x01\x00")
        request.append(self.host_type)  # the host_type is the same in RFC1928
        if self.host_type == 1:
            request += socket.inet_aton(str(self.target_host, encoding='ascii'))
        elif self.host_type == 3:
            request.append(len(self.target_host))
            request += self.target_host
        request += struct.pack(b'!H', self.target_port)
        self.next_proto.write(request)
        data = yield from self.read(4)

        if data[0] != 5:
            self.close()
            self.connection_complete.set_result(False)
            raise Socks5Error("socks5 version check error")
        elif data[1] != 0:
            self.close()
            self.connection_complete.set_result(False)
            raise Socks5Error("The error code is %d" % data[1])
        elif data[2] != 0:
            context.logger.error("the RSV is not zero")

        if data[3] == 1:
            data = yield from self.read(6)
            self.peer_host = socket.inet_ntoa(data[:4])
            self.peer_port = struct.unpack(b"!H", data[4:])[0]
        elif data[3] == 3:
            data = yield from self.read(1)
            data = yield from self.read(data[0] + 2)
            self.peer_host = bytes(data[:-2])
            self.peer_port = struct.unpack(b"!H", data[-2:])[0]
        elif data[3] == 4:
            data = yield from self.read(18)
            self.peer_host = socket.inet_ntop(socket.AF_INET6, data[:16])
            self.peer_port = struct.unpack(b"!H", data[16:])[0]
        else:
            self.close()
            self.connection_complete.set_result(False)
            raise Socks5Error("unknown addr type")

        self.connection_complete.set_result(True)
        while True:
            data = yield from self.read(0)
            self.prev_proto.data_received(data)
