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

from .sock5 import Socks5Client, Socks5Server
from .baseProtocol import BaseServerTop, out_protocol_chains, in_protocol_chains, BaseProtocolError, BaseProtocol
from .SC import SCBase, SCBase_factory
from .SCS import SCSProxyServer, SCSProxyClient
from .NATTraversal import ReverseFinalClient, ReverseFinalServer, connection
from .port_forward import PFServer
from functools import partial

protocol_list = {
    "PFServer": {
        "type": "server",
        "protocol_factory": lambda config_dict: partial(PFServer, target_host=config_dict['host'],
                                                        target_port=config_dict['port'])
    },
    "SCBase": {
        "type": "base",
        "protocol_factory": SCBase_factory
    },
    "SCSProxyServer": {
        "type": "server",
        "protocol_factory": lambda config_dict: SCSProxyServer,
    },
    "SCSProxyClient": {
        "type": "client",
        "protocol_factory": lambda config_dict: SCSProxyClient,
    },
    "Socks5Server": {
        "type": "server",
        "protocol_factory": lambda config_dict: Socks5Server,
    },
    "Socks5Client": {
        "type": "client",
        "protocol_factory": lambda config_dict: Socks5Client,
    },
}

protocol_map = {
    "PF": {
        "server": "PFServer",
        "client": None
    },
    "SC": {
        "server": "SCBase",
        "client": "SCBase"
    },
    "SCSProxy": {
        "server": "SCSProxyServer",
        "client": "SCSProxyClient"
    },
    "Socks5": {
        "server": "Socks5Server",
        "client": "Socks5Client"
    }
}
