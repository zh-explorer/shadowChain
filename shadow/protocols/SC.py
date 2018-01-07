# from shadow.protocols.baseRoute import BaseServer, out_protocol_chains, BaseClient, BaseProtocolError
# from shadow import context
# from shadow.unit import crypto_tools
# import time
# import struct
#
# logger = context.logger
#
#
# class SCError(BaseProtocolError): pass
#
#
# SC_SERVER_GET_TOKEN = 1
# SC_SERVER_VERIFY_TOKEN = 2
# SC_SERVER_GET_HEAD = 3
# SC_SERVER_GET_ALL = 4
#
#
# class SCBase(BaseServer):
#     def __init__(self, loop):
#         super().__init__(loop)
#         self.sc_status = None
#         self.aes = None
#         self.token = None
#         self.timestamp = None
#         self.noise = None
#         self.hash_sum = None
#         self.main_version = None
#         self.data_len = None
#         self.subtype = None
#         self.random_len = None
#
#     def proto_decode(self, data):
#         if self.sc_status == SC_SERVER_GET_TOKEN:
#             self.token = data
#             self.aes = crypto_tools.AES(data)
#             self.sc_status = SC_SERVER_VERIFY_TOKEN
#             self.request_size = 16
#         elif self.sc_status == SC_SERVER_VERIFY_TOKEN:
#             data = self.aes.decrypt(data)
#             self.timestamp = crypto_tools.unpack_timestamp(data[:8])
#             self.noise = data[8:]
#             if abs(self.timestamp - time.time()) > 30:
#                 self.close("time out")
#                 return
#             token_v = crypto_tools.sha256(context.password + data)
#             if token_v != self.token:
#                 self.close("error token")
#                 return
#             self.sc_status = SC_SERVER_GET_HEAD
#             self.request_size = 48
#         elif self.sc_status == SC_SERVER_GET_HEAD:
#             data = self.aes.decrypt(data)
#             self.hash_sum = data[:32]
#             self.main_version = data[32]
#             self.data_len = struct.unpack(b'!L', data[33:37])[0]
#             self.subtype = data[37]
#             self.random_len = data[38]
#             self.sc_status = SC_SERVER_GET_ALL
#             self.request_size = self.data_len
#         elif self.sc_status == SC_SERVER_GET_ALL:
#             data = self.aes.decrypt(data)
#             data = data[:-self.random_len]
#             self.request_all = True
#             self.sub_decode(data)
#         else:
#             raise SCError("sc decode status error")
#
#     def sub_decode(self, data):
#         self.peer_proto.write(data)
#
#
# class SCServer(SCBase):
#     def __init__(self, loop):
#         super().__init__(loop)
#
#     def connection_made(self, transport):
#         self.transport = transport
#         self.request_size = 16
#         self.sc_status = SC_SERVER_GET_TOKEN
#
#         peername = transport.get_extra_info('peername')
#         logger.info('Connection from {}'.format(peername))
#
#     def sub_decode(self, data):
#         pass
