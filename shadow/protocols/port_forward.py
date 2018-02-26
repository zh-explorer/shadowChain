from shadow import context
from .baseProtocol import BaseServerTop


class PFServer(BaseServerTop):
    def __init__(self, loop, target_host, target_port):
        super().__init__(loop)
        self.target_host = target_host
        self.target_port = target_port

    def made_connection(self):
        host, port = self.transport.get_extra_info('peername')
        context.logger.info("a new port forward from %s:%d" % (host, port))
        self.connection(self.target_host, self.target_port)

    def received_data(self):
        result = yield from self.read(-1)
        if not result:
            context.logger.info("connection to remote if fail")
            return True

        while True:
            data = yield from self.read(0)
            self.peer_proto.write(data)
