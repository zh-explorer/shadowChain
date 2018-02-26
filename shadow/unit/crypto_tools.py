from Crypto.Cipher import AES as aes
from hashlib import sha256 as sha
from Crypto import Random
from shadow.context import context
import time
import struct

rand = Random.new()


def random_byte(size):
    return rand.read(size)


def sha256(byte):
    a = sha(byte)
    return a.digest()


class AES(object):
    def __init__(self, token):
        token = bytes(token)
        s = sha256(context.password + token)
        self.key = s[:16]
        self.iv = s[16:]

        self.aes_object = aes.new(self.key, aes.MODE_CFB, self.iv)

    def encrypt(self, data):
        data = bytes(data)
        return self.aes_object.encrypt(data)

    def decrypt(self, data):
        data = bytes(data)
        return self.aes_object.decrypt(data)


def packed_timestamp():
    t = time.time()
    t = int(t)
    return struct.pack(b"!Q", t)


def unpack_timestamp(data):
    return struct.unpack(b'!Q', data)[0]
