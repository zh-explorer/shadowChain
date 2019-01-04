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
import types
from functools import partial
from .NATTraversal import re_out_protocol_chains
from shadow import context
import traceback

NEXT = 1
PREV = 2
PEER = 3


class BaseProtocolError(Exception): pass


class BaseProtocol(object):
    def __init__(self, loop, prev_proto):
        self.loop = loop
        self.prev_proto = prev_proto
        self.next_proto = None
        self.notify_ignore = False
        self.transport = None
        self.receive_iter = None
        self.connection_complete = None

        self.cache_data = bytearray()
        self.cache_size = 0

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.receive_iter = self.received_data()
        assert isinstance(self.receive_iter, types.GeneratorType)

        # def made_connection_complete(future):
        #     exc = future.exception()
        #     if exc is not None:
        #         context.logger.warning("connection is not complete")
        #         context.logger.warning(str(exc))
        #         self.close(False)
        #     elif future.result():
        #         self.prev_proto.connection_made(self.transport, self)
        #     else:
        #         context.logger.warning("connection failed")
        #         self.close(False)

        self.connection_complete = self.loop.create_future()
        self.connection_complete.add_done_callback(self.made_connection_complete)
        self.made_connection()

    def made_connection_complete(self, future):
        exc = future.exception()
        if exc is not None:
            context.logger.warning("connection is not complete")
            context.logger.warning(str(exc))
            self.close(False)
        elif future.result():
            self.prev_proto.connection_made(self.transport, self)
        else:
            context.logger.warning("connection failed")
            self.close(False)

    def data_received(self, data=None):
        # context.logger.debug("get data")
        # context.logger.debug(data)
        try:
            self.receive_iter.send(data)
        except StopIteration as e:
            if not e.value:  # normal stop, close the protocol
                raise e  # not normal, throw it

    def read(self, size):
        if size == 0:
            if self.cache_size != 0:
                data = self.cache_data
                self.cache_size = 0
                self.cache_data = bytearray()
                return data
            else:
                data = yield None
                return data
        elif size == -1:
            self.transport.pause_reading()
            while True:
                data = yield None
                if not isinstance(data, bytes):
                    self.transport.resume_reading()
                    return data
                self.cache_data += data
                self.cache_size += len(data)

        while size > self.cache_size:
            data = yield None
            self.cache_data += data
            self.cache_size += len(data)

        data = self.cache_data[:size]
        self.cache_data = self.cache_data[size:]
        self.cache_size -= size
        # context.logger.debug(data)
        return data

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.prev_proto.notify_close(result, NEXT)
        else:
            self.next_proto.notify_close(result, PREV)
        self.handle_close_notify(result)

    def close(self, result=None):
        self.notify_ignore = True
        self.next_proto.notify_close(result, PREV)
        self.prev_proto.notify_close(result, NEXT)
        self.raw_close(result)

    def raw_close(self, result):
        pass

    def received_data(self):
        while True:
            data = yield from self.read(0)
            self.prev_proto.data_received(data)

    def write(self, data):
        self.next_proto.write(data)

    def made_connection(self):
        self.start_recevice()
        self.connection_complete.set_result(True)

    def start_recevice(self):
        try:
            self.receive_iter.send(None)
        except StopIteration:
            raise BaseProtocolError("can't start received_data generator")

    def handle_close_notify(self, result):
        self.raw_close(result)


class BaseProtocolFinal(asyncio.Protocol):
    def __init__(self, loop, prev_proto):
        self.loop = loop
        self.prev_proto = prev_proto
        self.transport = None
        self.is_abort = False
        self.notify_ignore = False

    def connection_made(self, transport):
        self.transport = transport
        self.prev_proto.connection_made(transport, self)

    def connection_lost(self, exc):
        context.logger.debug("conn lost")
        result = None
        if exc is not None:
            result = str(exc)
            context.logger.info("conn exception %s" % result)
        if not self.is_abort:  # the conn is close by some one. not close again
            self.close(result)

    def data_received(self, data):
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

    # do nothing but close. Should use for a exc close
    # def about(self):
    #     self.transport.abort()
    #     self.prev_proto.notify_close("about", NEXT)

    def notify_close(self, result, from_where=None):
        if self.notify_ignore:
            return
        self.raw_close(result)


class BaseServerTop(BaseProtocol):
    def __init__(self, loop):
        super().__init__(loop, None)
        self.peer_proto = None

    def made_connection_complete(self, future):
        '''
        Because the server top not need to notify to other protocol
        So overwrite it
        '''
        pass

    # def connection_made(self, transport, next_proto):
    #     self.next_proto = next_proto
    #     self.transport = transport
    #     self.receive_iter = self.received_data()
    #     assert isinstance(self.receive_iter, types.GeneratorType)
    #     self.made_connection()

    def close(self, result=None):
        self.next_proto.notify_close(result, PREV)
        if self.peer_proto is not None:
            self.peer_proto.notify_close(result, PEER)
        self.raw_close(result)

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            if self.peer_proto is not None:
                self.peer_proto.notify_close(result, PEER)
        elif from_where == PEER:
            self.next_proto.notify_close(result, PREV)
        else:
            raise BaseProtocolError("should not from other")

    def received_data(self):
        while True:
            data = yield from self.read(0)
            self.peer_proto.write(data)

    # def made_connection(self):
    #
    #     raise BaseProtocolError("The virtual function should not be called")
        # pass

    def connection(self, host, port):
        def conn_complete(future):
            exc = future.exception()
            if exc is not None:
                # raise exc
                context.logger.info("conn error %s" % str(exc))
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


class BaseClient(BaseProtocol):
    def __init__(self, loop, prev_proto, target_host, target_port):
        super().__init__(loop, prev_proto)
        self.target_host = target_host
        self.target_port = target_port


class BaseClientTop(object):
    def __init__(self, loop, peer_proto, future):
        self.loop = loop
        self.peer_proto = peer_proto
        self.result_future = future
        self.next_proto = None
        self.notify_ignore = False
        self.transport = None

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.result_future.set_result((self, transport))

    def data_received(self, data):
        # context.logger.debug(data)
        self.peer_proto.write(data)

    def write(self, data):
        # context.logger.debug(data)
        self.next_proto.write(data)

    def close(self, result=None):
        self.next_proto.notify_close(result, PREV)
        self.peer_proto.notify_close(result, PEER)

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.peer_proto.notify_close(result, PEER)
        elif from_where == PEER:
            self.next_proto.notify_close(result, PREV)
        else:
            raise BaseProtocolError("should not from other")


async def out_protocol_chains(host, port, loop, in_protocol):
    f = loop.create_future()
    transport = None
    try:
        if len(context.out_protocol_stack) >= 1:
            func = context.out_protocol_stack[context.first_client]
            func = partial(func, target_host=host, target_port=port)
            context.out_protocol_stack[0] = func
        prev = BaseClientTop(loop, in_protocol, f)
        for protocol in context.out_protocol_stack:
            prev = protocol(loop, prev)

        target_host = context.target_host if context.target_host is not None else host
        target_port = context.target_port if context.target_port is not None else port
        if context.is_reverse_server:
            protocol, transport = await re_out_protocol_chains(loop, prev)
        else:
            protocol_func = partial(BaseProtocolFinal, loop, prev)
            protocol, transport = await loop.create_connection(protocol_func, target_host, target_port)

        return await f
    except BaseProtocolError as e:
        # This error mean some protocol get a error. throw it and clean the conn
        context.logger.error("The protocol get ad error %s" % e)
        if transport is not None and not transport.is_closing():
            transport.close()
        # throw it to peer
        raise e


def in_protocol_chains(loop):
    prev = context.in_protocol_stack[0](loop) if len(context.in_protocol_stack) != 0 else BaseServerTop(loop)
    for protocol in context.in_protocol_stack[1:]:
        prev = protocol(loop, prev)

    return BaseProtocolFinal(loop, prev)
