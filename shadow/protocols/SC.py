from .baseProtocol import BaseProtocol, BaseServerTop, out_protocol_chains, BaseProtocolError
from shadow import context
from shadow.unit import crypto_tools
import time
import struct

logger = context.logger


class SCError(BaseProtocolError):
    pass


class SCBase(BaseProtocol):
    def __init__(self, loop, prev_proto):
        """
        This protocol not need target host and target host, it just a verify and crypto protocol
        """
        super().__init__(loop, prev_proto)
        self.aes = None
        self.token = None
        self.timestamp = None
        self.noise = None
        self.hash_sum = None
        self.main_version = None
        self.data_len = None
        self.subtype = None
        self.random_len = None

        self.noise_list = [[i] for i in range(60)]
        self.all_data = b""

    def received_data(self):
        while True:
            data = yield from self.read(32)
            self.all_data += data
            self.token = data[:16]
            self.aes = crypto_tools.AES(self.token)
            data = self.aes.decrypt(data[16:])
            self.timestamp = crypto_tools.unpack_timestamp(data[:8])
            self.noise = data[8:]
            if abs(self.timestamp - time.time()) > 30:
                context.logger.info("time error")
                self.close(None)
                return True
            token_v = crypto_tools.sha256(context.password + data)[:16]
            if token_v != self.token:
                context.logger.info("token error")
                self.close(None)
                return True
            if not self.check_noise(self.noise, self.timestamp):
                self.close(None)
                context.logger.error("get a noise repetitive")
                return True

            data = yield from self.read(48)
            self.all_data += data
            self.aes.decrypt(data)
            self.hash_sum = data[:32]
            self.main_version = data[32]
            self.data_len = struct.unpack(b'!L', data[33:37])[0]
            self.random_len = data[37]

            data = yield from self.read(self.data_len)
            data = data[:-self.random_len]
            self.all_data += data

            self.all_data[32:64] = b'\x00' * 32
            if crypto_tools.sha256(self.all_data) != self.hash_sum:
                context.logger.error("hash sun check error")
                self.close(None)
                return True

            data = self.aes.decrypt(data)
            self.prev_proto.data_received(data)

    def check_noise(self, noise, timestamp):
        index = timestamp % 60
        if self.noise_list[index][0] != timestamp:
            self.noise_list[index] = [timestamp]
        else:
            if noise in self.noise_list[index]:
                return False
        self.noise_list[index].append(noise)
        return True

    def write(self, data):

        timestamp = crypto_tools.packed_timestamp()
        noise = crypto_tools.random_byte(8)
        token = crypto_tools.sha256(context.password + timestamp + noise)[:16]
        random_len = crypto_tools.random_byte(1)[0]
        random_len = random_len % 40

        data_len = random_len + len(data) + 80

        data_buf = bytearray()
        data_buf += token + timestamp + noise + b'\x00' * 32
        data_buf.append(1)
        data_buf += struct.pack(b'!L', data_len)
        data_buf.append(random_len)
        data_buf += crypto_tools.random_byte(10)
        data_buf += data
        data_buf += crypto_tools.random_byte(random_len)

        hash_sum = crypto_tools.sha256(bytes(data_buf))
        data_buf[32:64] = hash_sum

        data_buf = bytes(data_buf)[16:]

        aes = crypto_tools.AES(token)
        data_buf = token + aes.encrypt(data_buf)

        self.next_proto.write(data_buf)
