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
import asyncio
from shadow import context
from ..unit.crypto_tools import sha256, random_byte
from . import baseProtocol
from functools import partial
import time

NEXT = 1
PREV = 2
PEER = 3

start_conn = 0x10
suspend = 0x11
awaken = 0x12
fin = 0x13


class ReverseProtocolError(Exception): pass


class ReverseFinalServer(asyncio.Protocol):
    def __init__(self, loop, queue):
        self.loop = loop
        self.prev_proto = None
        self.awaken_finish = None
        self.transport = None
        self.is_abort = False
        self.notify_ignore = False
        self.cache_data = b""
        self.status = start_conn
        self.sock_pool = queue
        self.available = True

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        context.logger.debug("conn lost")
        if self.status == suspend:
            self.available = False
        if self.status == awaken:
            self.awaken_finish.set_result(False)
        result = None
        if exc is not None:
            result = str(exc)
            context.logger.info("conn exception %s" % result)
        if not self.is_abort:  # the conn is close by some one. not close again
            self.close(result)

    def awaken(self, prev, future):
        self.prev_proto = prev
        self.awaken_finish = future
        self.status = awaken
        self.write(b'\x00')

    def data_received(self, data):
        if self.status == start_conn:
            self.cache_data += data
            if len(self.cache_data) >= 40:
                salt = self.cache_data[:8]
                pass_hash = self.cache_data[8:40]
                if sha256(context.password + salt) != pass_hash:
                    context.logger.info("get a unknown connection")
                    self.close()
                else:
                    coro = self.sock_pool.put(self)
                    asyncio.ensure_future(coro, loop=self.loop)
            self.status = suspend
        elif self.status == suspend:
            context.logger.warning("get data when suspend")
        elif self.status == awaken:
            if data == b'\x01':
                self.status = fin
                self.awaken_finish.set_result(True)
                self.prev_proto.connection_made(self.transport, self)
        elif self.status == fin:
            self.prev_proto.data_received(data)
        else:
            raise ReverseProtocolError("unknown status code")

    def write(self, data):
        self.transport.write(data)

    def close(self, result=None):
        self.notify_ignore = True
        self.is_abort = True
        self.raw_close(result)
        if self.prev_proto is not None:
            self.prev_proto.notify_close(result, NEXT)

    def raw_close(self, result=None):
        self.transport.close()

    def notify_close(self, result, from_where=None):
        if self.notify_ignore:
            return
        self.raw_close(result)


class ReverseFinalClient(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop
        self.prev_proto = None
        self.transport = None
        self.is_abort = False
        self.notify_ignore = False
        self.wait_conn = True

    def connection_made(self, transport):
        context.pool_size += 1
        self.transport = transport
        salt = random_byte(8)
        pass_hash = sha256(context.password + salt)
        self.write(salt + pass_hash)

    def connection_lost(self, exc):
        context.logger.debug("conn lost")
        if self.wait_conn:
            expand_pool(self.loop)
        result = None
        if exc is not None:
            result = str(exc)
            context.logger.info("conn exception %s" % result)
        if not self.is_abort:  # the conn is close by some one. not close again
            self.close(result)

    def data_received(self, data):
        if self.wait_conn:
            if data[0] != 0:
                context.logger.warning("get a unknown data when wait conn")
                self.close()
            else:
                self.write(b'\x01')
                self.wait_conn = False
                self.prev_proto = re_in_protocol_chains(self.loop)
                self.prev_proto.connection_made(self.transport, self)
            expand_pool(self.loop)
        else:
            self.prev_proto.data_received(data)

    def write(self, data):
        self.transport.write(data)

    def close(self, result=None):
        self.notify_ignore = True
        self.is_abort = True
        self.raw_close(result)
        if self.prev_proto is not None:
            self.prev_proto.notify_close(result, NEXT)

    def raw_close(self, result=None):
        self.transport.close()

    def notify_close(self, result, from_where=None):
        if self.notify_ignore:
            return
        self.raw_close(result)


def re_in_protocol_chains(loop):
    prev = context.in_protocol_stack[0](loop) if len(context.in_protocol_stack) != 0 else baseProtocol.BaseServerTop(
        loop)
    for protocol in context.in_protocol_stack[1:]:
        prev = protocol(loop, prev)
    return prev


async def re_out_protocol_chains(loop, prev):
    while True:
        rs = await context.sock_pool.get()
        if rs.available:
            f = loop.create_future()
            rs.awaken(prev, f)
            result = await f
            if result:
                return rs, rs.transport


last_time = 0
conn_speed = 0


def expand_pool(loop):
    global last_time, conn_speed
    conn_speed += 1
    context.pool_size -= 1
    if context.pool_size < context.pool_max_size:
        connection(loop, 1)
    if time.time() - last_time > 1:
        if time.time() - last_time > 2:
            conn_speed = 0
        last_time = time.time()
        context.pool_max_size = (conn_speed // 10) * 20 + 50
        conn_speed = 0
        context.logger.info("+" * 80)
        context.logger.info("Poll max size: %d" % context.pool_max_size)
        context.logger.info("Poll size: %d" % context.pool_size)
        if context.pool_max_size - context.pool_size > 0:
            connection(loop, context.pool_max_size - context.pool_size)


def connection(loop, size):
    coro = coro_connection(loop, size)
    asyncio.ensure_future(coro, loop=loop)


async def coro_connection(loop, size):
    for i in range(size):
        while True:
            protocol_func = partial(ReverseFinalClient, loop)
            try:
                await loop.create_connection(protocol_func, context.server_host, context.server_port)
                break
            except OSError as exc:
                context.logger.warning("conn error %s" % str(exc))
                context.logger.warning("wait for 5s and retry")
                time.sleep(5)
