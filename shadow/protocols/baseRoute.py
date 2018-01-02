import asyncio
from functools import partial

from shadow.log import logger


class BaseRoute(asyncio.Protocol):
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
        self.transport.close()
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
        self.close(None)


class BaseRouteClient(BaseRoute):
    def __init__(self, loop, peer_proto, peer_transport):
        super().__init__(loop)
        self.peer_proto = peer_proto
        self.peer_transport = peer_transport


async def out_protocol_chains(host, port, loop, in_protocol, in_transport):
    proto_func = partial(BaseRouteClient, loop, in_protocol, in_transport)
    return await loop.create_connection(proto_func, host, port)


# the two class below if just for test and example. useless
# TODO delete this
class BaseRouteServer(BaseRoute):
    def __init__(self, loop, host, port):
        super().__init__(loop)
        self.target_host = host
        self.target_port = port

    def connection_made(self, transport):
        logger.info("get conn")
        self.transport = transport
        logger.debug(transport)

        # the register if reading is after the call of connection_made. So must use a call back to stop the reading
        self.loop.call_soon(self.transport.pause_reading)

        logger.debug("pause")
        proto_func = partial(BaseRouteClient, self.loop, self, self.transport)
        task = asyncio.ensure_future(self.loop.create_connection(proto_func, self.target_host, self.target_port),
                                     loop=self.loop)

        def conn_complete(future):
            exc = future.exception()
            if exc is not None:
                logger.info("conn error")
                self.is_abort = True
                self.transport.abort()
            logger.debug("conn complete")
            self.peer_transport, self.peer_proto = future.result()
            self.transport.resume_reading()

        task.add_done_callback(conn_complete)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    get_server_proto = partial(BaseRouteServer, loop, "45.32.238.193", "3343")
    coro = loop.create_server(get_server_proto, '0.0.0.0', 3333)

    server = loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
