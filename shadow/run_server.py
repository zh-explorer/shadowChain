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
import logging
from functools import partial
import sys

from shadow import context
from shadow.log import logger
from shadow.protocols import Socks5Client, Socks5Server, in_protocol_chains, SCBase, SCSProxyClient, ReverseFinalServer, \
    connection

from shadow.unit import load_conf_file


def init(loop, filename):
    context.logger = logger
    context.main_loop = loop
    load_conf_file(filename)


def main_start():
    if len(sys.argv) <= 1:
        print('must have conf file')
        exit(-1)

    filename = sys.argv[1]
    loop = asyncio.get_event_loop()
    init(loop, filename)

    loop.set_debug(enabled=True)
    logging.getLogger('asyncio').setLevel(logging.INFO)

    if context.is_reverse_server:
        get_server_proto2 = partial(ReverseFinalServer, loop, context.sock_pool)
        coro2 = loop.create_server(get_server_proto2, context.target_host, context.target_port)
        server2 = loop.run_until_complete(coro2)

    if context.is_reverse_client:
        connection(loop, 50)
    else:
        get_server_proto = partial(in_protocol_chains, loop)
        coro = loop.create_server(get_server_proto, context.server_host, context.server_port)
        server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

        # Close the server
    if not context.is_reverse_client:
        server.close()
    if context.is_reverse_server:
        server2.close()
    loop.run_until_complete(server.wait_closed())
    loop.shutdown_asyncgens()
    loop.stop()
    loop.close()

if __name__ == '__main__':
    main_start()
