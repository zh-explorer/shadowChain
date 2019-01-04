# Copyright [2018] [zh_explorer]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import socket
import struct

from shadow import context
from shadow.unit.misc import check_host_type
from .baseProtocol import BaseServerTop, BaseProtocolError, BaseClient


class SCSError(BaseProtocolError): pass


class SCSProxyServer(BaseServerTop):
    def __init__(self, loop):
        super().__init__(loop)
        self.target_host = None
        self.target_port = None

    def made_connection(self):
        self.start_recevice()

    def received_data(self):
        data = yield from self.read(3)
        if data[0] != 1:
            context.logger.info("This is not a scs proxy protocol")
            self.next_proto.write(b"\xff")
            self.close(None)
            return True

        if data[1] != 1:
            context.logger.info("get a invalid cmd")
            self.replies_error(2)
            return True

        if data[2] == 1:
            data = yield from self.read(6)
            addr = data[:4]
            port = data[4:]
            self.target_host = socket.inet_ntoa(addr)
            self.target_port = struct.unpack(b'!H', port)[0]
        elif data[2] == 3:
            data = yield from self.read(1)
            addr_len = data[0]
            data = yield from self.read(addr_len + 2)
            self.target_host = bytes(data[:-2])
            self.target_port = struct.unpack(b'!H', data[-2:])[0]
        else:
            context.logger.info("unknown addr type")
            self.replies_error(3)
            return True

        context.logger.info("a new scs proxy request to %s:%d" % (self.target_host, self.target_port))
        self.connection(self.target_host, self.target_port)
        result = yield from self.read(-1)
        if not result:
            self.replies_error(1)
            return True

        host, port = self.peer_transport.get_extra_info("sockname")
        addr_raw = socket.inet_aton(host)
        port_raw = struct.pack(b'!H', port)
        self.next_proto.write(b'\x02\x00\x01' + addr_raw + port_raw)

        while True:
            data = yield from self.read(0)
            self.peer_proto.write(data)

    def replies_error(self, errno):
        reply = bytearray(b'\x02\x00\x01' + b'\x00' * 6)  # do not have address, so use \x00 pad
        reply[1] = errno
        self.next_proto.write(bytes(reply))
        self.close(None)


class SCSProxyClient(BaseClient):
    def __init__(self, loop, prev_proto, target_host, target_port):
        if type(target_host) == str:
            target_host = target_host.encode()

        super().__init__(loop, prev_proto, target_host, target_port)

        self.host_type = check_host_type(self.target_host)
        if self.host_type == 4:
            raise SCSError("The ipv6 is not support now")

        self.peer_host = None
        self.peer_port = None

    def made_connection(self):
        self.start_recevice()
        request = bytearray()
        request += b'\x01\x01'
        request.append(self.host_type)
        if self.host_type == 1:
            request += socket.inet_aton(str(self.target_host, encoding='ascii'))
        elif self.host_type == 3:
            request.append(len(self.target_host))
            request += self.target_host

        request += struct.pack(b'!H', self.target_port)
        self.next_proto.write(bytes(request))

    def received_data(self):
        data = yield from self.read(1)
        if data[0] != 2:
            self.close()
            self.connection_complete.set_result(False)
            raise SCSError("The protocol type is not right: %d", data[0])

        data = yield from self.read(2)
        if data[0] != 0:
            self.close()
            self.connection_complete.set_result(False)
            raise SCSError("The connection is failed: %d", data[0])

        if data[1] == 1:
            data = yield from self.read(6)
            self.peer_host = socket.inet_ntoa(data[:4])
            self.peer_port = struct.unpack(b'!H', data[4:])[0]
        elif data[1] == 3:
            data = yield from self.read(1)
            data = yield from self.read(data[0] + 2)
            self.peer_host = bytes(data[:-2])
            self.peer_port = struct.unpack(b'!H', data[-2:])[0]
        else:
            self.close()
            self.connection_complete.set_result(False)
            raise SCSError("The connection is failed: %d", data[0])

        self.connection_complete.set_result(True)
        while True:
            data = yield from self.read(0)
            self.prev_proto.data_received(data)
