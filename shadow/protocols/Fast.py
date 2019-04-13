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


class Fast(BaseProtocol):
    def __init__(self, loop, prev_proto):
        """
        This protocol not need target host and target host, it just a verify and crypto protocol
        """
        super().__init__(loop, prev_proto)
        self.key = context.password
        self.rc4 = crypto_tools.rc4(self.key)

    def received_data(self):
        while True:
            data = yield from self.read(0)
            data = self.rc4.encrypt(data)
            self.prev_proto.data_received(data)

    def write(self, data):
        # context.logger.info("write")
        # context.logger.info(data)
        data_buf = self.rc4.encrypt(data)
        self.next_proto.write(data_buf)
