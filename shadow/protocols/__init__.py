from .sock5 import Socks5Client, Socks5Server
from .baseProtocol import BaseServerTop, out_protocol_chains, in_protocol_chains, BaseProtocolError, BaseProtocol
from .SC import SCBase
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
        "protocol_factory": lambda config_dict: SCBase,
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
