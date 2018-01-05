import asyncio
from functools import partial
from shadow import context

logger = context.logger
NEXT = 1
PREV = 2


class BaseProtocolError(Exception): pass


class BaseServer(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.peer_transport = None
        self.peer_proto = None
        self.notify_ignore = False
        self.is_abort = False

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        logger.debug("conn lost")
        result = None
        if exc is not None:
            result = str(exc)
            logger.info("conn exception %s" % result)
        if not self.is_abort:  # the conn is close by some one. not close again
            self.close(result)

    def data_received(self, data):
        self.peer_proto.write(data)

    def write(self, data):
        # logger.debug(data)
        self.transport.write(data)

    def close(self, result):
        self.is_abort = True
        self.notify_ignore = True
        if self.peer_proto is not None:
            self.peer_proto.notify_close(result)

    # do nothing but close. Should use for a exc close
    def about(self):
        self.is_abort = True
        self.transport.abort()

    def notify_close(self, result):
        if self.notify_ignore:
            return
        self.handle_peer_close(result)

    def handle_peer_close(self, result):
        self.raw_close(result)

    def raw_close(self, result):
        self.transport.close()


class BaseClient(object):
    def __init__(self, loop, prev_proto, origin_host, origin_port):
        self.loop = loop
        self.prev_proto = prev_proto
        self.next_proto = None
        self.notify_ignore = False
        self.origin_host = origin_host
        self.origin_port = origin_port
        self.transport = None

    def connection_made(self, transport, next_proto):
        self.next_proto = next_proto
        self.transport = transport
        self.prev_proto.connection_made(transport, self)

    def data_received(self, data):
        self.prev_proto.data_received(data)

    def write(self, data):
        self.next_proto.write(data)

    def close(self, result=None):
        self.notify_ignore = True
        self.next_proto.notify_close(result, PREV)
        self.prev_proto.notify_close(result, NEXT)
        self.raw_close(result)

    def raw_close(self, result=None):
        pass

    def notify_close(self, result, from_where):
        if self.notify_ignore:
            return
        if from_where == NEXT:
            self.prev_proto.notify_close(result, NEXT)
        else:
            self.next_proto.notify_close(result, PREV)
        self.handle_peer_close(result)

    def handle_peer_close(self, result):
        self.raw_close(result)


class BaseClientTop(object):
    def __init__(self, loop, peer_proto, future):
        self.loop = loop
        self.peer_proto = peer_proto
        self.next_proto = None
        self.notify_ignore = False
        self.result_future = future
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

    def notify_close(self, result, from_where=None):
        if self.notify_ignore:
            return
        self.peer_proto.notify_close(result)
        self.handle_peer_close(result)

    def handle_peer_close(self, result):
        pass


class BaseClientFinal(asyncio.Protocol):
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
        self.is_abort = True
        self.notify_ignore = True
        self.raw_close(result)
        if self.prev_proto is not None:
            self.prev_proto.notify_close(result, NEXT)

    def raw_close(self, result=None):
        self.transport.close()

    # do nothing but close. Should use for a exc close
    def about(self):
        self.is_abort = True
        self.transport.abort()
        self.prev_proto.notify_close("about", NEXT)

    def notify_close(self, result, from_where=None):
        if self.notify_ignore:
            return
        self.handle_close(result)

    def handle_close(self, result):
        self.raw_close(result)


async def out_protocol_chains(host, port, loop, in_protocol):
    f = loop.create_future()
    ret = None
    transport = None
    try:
        top = BaseClientTop(loop, in_protocol, f)
        prev = top
        for protocol in context.protocol_chains:
            proto = protocol(loop, prev, host, port)
            prev = proto

        protocol_func = partial(BaseClientFinal, loop, prev)
        protocol, transport = await loop.create_connection(protocol_func, context.out_host, context.out_port)

        ret = await f
    except BaseProtocolError as e:
        # This error mean some protocol get a error. throw it and clean the conn
        logger.error("The protocol get ad error %s" % e)
        if transport is not None and not transport.is_closing():
            transport.close()
        # throw it to peer
        raise e
    return ret

# # the two class below if just for test and example. useless
# # TODO delete this
# class BaseRouteServer(BaseRoute):
#     def __init__(self, loop, host, port):
#         super().__init__(loop)
#         self.target_host = host
#         self.target_port = port
#
#     def connection_made(self, transport):
#         logger.info("get conn")
#         self.transport = transport
#         logger.debug(transport)
#
#         # the register if reading is after the call of connection_made. So must use a call back to stop the reading
#         self.loop.call_soon(self.transport.pause_reading)
#
#         logger.debug("pause")
#         proto_func = partial(BaseRouteClient, self.loop, self, self.transport)
#         task = asyncio.ensure_future(self.loop.create_connection(proto_func, self.target_host, self.target_port),
#                                      loop=self.loop)
#
#         def conn_complete(future):
#             exc = future.exception()
#             if exc is not None:
#                 logger.info("conn error")
#                 self.is_abort = True
#                 self.transport.abort()
#             logger.debug("conn complete")
#             self.peer_transport, self.peer_proto = future.result()
#             self.transport.resume_reading()
#
#         task.add_done_callback(conn_complete)
#
#
# if __name__ == '__main__':
#     loop = asyncio.get_event_loop()
#
#     get_server_proto = partial(BaseRouteServer, loop, "45.32.238.193", "3343")
#     coro = loop.create_server(get_server_proto, '0.0.0.0', 3333)
#
#     server = loop.run_until_complete(coro)
#     try:
#         loop.run_forever()
#     except KeyboardInterrupt:
#         pass
#
#     # Close the server
#     server.close()
#     loop.run_until_complete(server.wait_closed())
#     loop.close()
