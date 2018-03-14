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
import struct
import time

from shadow import context
from shadow.unit import crypto_tools
from .baseProtocol import BaseProtocol, BaseProtocolError
from functools import partial

logger = context.logger


def SCBase_factory(config_dict):
    if config_dict is None or 'timeout' not in config_dict:
        timeout = 300
    else:
        timeout = int(config_dict['timeout'])
        if timeout < 0:
            timeout = 0
    return partial(SCBase, timeout=timeout)


class SCError(BaseProtocolError):
    pass


class SCBase(BaseProtocol):
    def __init__(self, loop, prev_proto, timeout):
        """
        This protocol not need target host and target host, it just a verify and crypto protocol
        """
        super().__init__(loop, prev_proto)
        self.aes = None
        self.token = None
        self.timestamp = None
        self.noise = None
        self.hash_sum = None
        self.main_version = None
        self.data_len = None
        self.subtype = None
        self.random_len = None
        self.timeout = timeout
        if self.timeout != 0:
            self.noise_list = [[i] for i in range(self.timeout * 2)]

    def received_data(self):
        while True:
            data = yield from self.read(24)
            self.token = data[:8]
            self.aes = crypto_tools.AES(self.token)
            data = self.aes.decrypt(data[8:])
            self.timestamp = crypto_tools.unpack_timestamp(data[:8])
            self.noise = data[8:]
            if self.timeout != 0 and abs(self.timestamp - time.time()) >= self.timeout:
                context.logger.info("time error")
                self.close(None)
                return True
            token_v = crypto_tools.sha256(context.password + data)[:8]
            if token_v != self.token:
                context.logger.info("token error")
                self.close(None)
                return True
            if not self.check_noise(self.noise, self.timestamp):
                context.logger.error("get a noise repetitive")
                self.close(None)
                return True

            data = yield from self.read(8)
            data = self.aes.decrypt(data)
            self.main_version = data[0]
            self.data_len = struct.unpack(b'!L', data[1:5])[0]
            self.random_len = data[5]
            # print(self.data_len)
            # print(self.random_len)
            data = yield from self.read(self.data_len - 32)
            # print(data)
            data = data[:-self.random_len]
            data = self.aes.decrypt(data)
            # context.logger.info("get")
            # context.logger.info(self.token)
            # context.logger.info(self.noise)
            # context.logger.info(self.timestamp)
            # context.logger.info(self.main_version)
            # context.logger.info(self.data_len)
            # context.logger.info(self.random_len)
            # context.logger.info(data)
            self.prev_proto.data_received(data)

    def check_noise(self, noise, timestamp):
        if self.timeout == 0:
            return True
        index = timestamp % (self.timeout * 2)
        if self.noise_list[index][0] != timestamp:
            self.noise_list[index] = [timestamp]
        else:
            if noise in self.noise_list[index]:
                return False
        self.noise_list[index].append(noise)
        return True

    def write(self, data):
        # context.logger.info("write")
        # context.logger.info(data)
        timestamp = crypto_tools.packed_timestamp()
        noise = crypto_tools.random_byte(8)
        token = crypto_tools.sha256(context.password + timestamp + noise)[:8]
        random_len = crypto_tools.random_byte(1)[0]
        random_len = random_len % 40 + 1

        data_len = random_len + len(data) + 32

        data_buf = bytearray()
        data_buf += timestamp + noise
        data_buf.append(1)
        data_buf += struct.pack(b'!L', data_len)
        data_buf.append(random_len)
        data_buf += crypto_tools.random_byte(2)
        data_buf += data
        data_buf += crypto_tools.random_byte(random_len)

        aes = crypto_tools.AES(token)
        data_buf = token + aes.encrypt(bytes(data_buf))

        self.next_proto.write(data_buf)
