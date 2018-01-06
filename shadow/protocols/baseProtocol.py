import asyncio
from functools import partial
from shadow import context
import types

logger = context.logger

NEXT = 1
PREV = 2
PEER = 3


class BaseProtocolError(Exception): pass


class BaseProtocol(object):
    def __init__(self, loop, prev_proto, target_host=None, target_port=None):
        self.loop = loop
        self.target_host = target_host
        self.target_port = target_port
        self.prev_proto = prev_proto
        self.next_proto = None
        self.notify_ignore = False
        self.transport = None
        self.receive_iter = None
        self.connection_complete = None

        self.cache_data = bytearray()
        self.cache_size = 0
        self.request_size = None
        self.request_all = False

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.receive_iter = self.received_data()
        assert isinstance(self.receive_iter, types.GeneratorType)
        try:
            self.receive_iter.send(None)
        except StopIteration:
            raise BaseProtocolError("can't start received_data generator")

        def made_connection_complete(future):
            exc = future.exception()
            if exc is not None:
                logger.info("connection is not complete")
            elif future.result():
                self.prev_proto.connection_made(self.transport, self)

        self.connection_complete = self.loop.create_future()
        self.connection_complete.add_done_callback(made_connection_complete)
        self.made_connection()

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
            try:
                self.receive_iter.send(data)
            except StopIteration as e:
                if e.value:  # normal stop, close the protocol
                    self.close(None)
                else:
                    raise e  # not normal, throw it

            return

        while self.cache_size >= self.request_size != -1 and not self.request_all:  # decode until no enough data remain
            data = self.cache_data[:self.request_size]
            self.cache_data = self.cache_data[self.request_size:]
            self.cache_size -= self.request_size
            self.request_size = -1
            try:
                self.receive_iter.send(data)
            except StopIteration as e:
                if e.value:  # normal stop, close the protocol
                    self.close(None)
                else:
                    raise e  # not normal, throw it

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.prev_proto.notify_close(result, NEXT)
        else:
            self.next_proto.notify_close(result, PREV)
        self.handle_peer_close(result)

    def close(self, result=None):
        self.notify_ignore = True
        self.next_proto.notify_close(result, PREV)
        self.prev_proto.notify_close(result, NEXT)
        self.raw_close(result)

    def raw_close(self, result=None):
        pass

    def received_data(self):
        yield True
        while True:
            data = yield None
            self.prev_proto.data_received(data)

    def write(self, data):
        self.next_proto.write(data)

    def made_connection(self):
        self.connection_complete.set_result(True)

    def handle_peer_close(self, result):
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
        logger.debug("conn lost")
        result = None
        if exc is not None:
            result = str(exc)
            logger.info("conn exception %s" % result)
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

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.receive_iter = self.received_data()
        assert isinstance(self.receive_iter, types.GeneratorType)
        try:
            self.receive_iter.send(None)
        except StopIteration:
            raise BaseProtocolError("can't start received_data generator")
        self.made_connection()

    def close(self, result=None):
        self.next_proto.notify_close(result, PREV)
        self.peer_proto.notify_close(result, PEER)
        self.close(result)

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.peer_proto.notify_close(result)
        elif from_where == PEER:
            self.next_proto.notify_close(result)
        else:
            raise BaseProtocolError("should not from other")

    def received_data(self):
        yield True
        while True:
            data = yield None
            self.peer_proto.data_received(data)

    def made_connection(self):
        raise BaseProtocolError("The virtual function should not be called")


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
        self.peer_proto.write(data)

    def write(self, data):
        self.next_proto.write(data)

    def close(self, result=None):
        self.next_proto.notify_close(result, PREV)
        self.peer_proto.notify_close(result, PEER)

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.peer_proto.notify_close(result)
        elif from_where == PEER:
            self.next_proto.notify_close(result)
        else:
            raise BaseProtocolError("should not from other")


async def out_protocol_chains(host, port, loop, in_protocol):
    f = loop.create_future()
    transport = None
    try:
        prev = BaseClientTop(loop, in_protocol, f)
        for protocol in context.protocol_chains:
            prev = protocol(loop, prev, host, port)

        protocol_func = partial(BaseProtocolFinal, loop, prev)
        protocol, transport = await loop.create_connection(protocol_func, context.out_host, context.out_port)

        return await f
    except BaseProtocolError as e:
        # This error mean some protocol get a error. throw it and clean the conn
        logger.error("The protocol get ad error %s" % e)
        if transport is not None and not transport.is_closing():
            transport.close()
        # throw it to peer
        raise e


def in_protocol_chains(loop):
    prev = BaseServerTop(loop)
    for protocol in context.in_protocol_chains:
        prev = protocol(loop, prev)

    return BaseProtocolFinal(loop, prev)
