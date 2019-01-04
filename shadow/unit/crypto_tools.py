from Crypto.Cipher import AES as aes
from Crypto.Cipher import ARC4

# from pyaes import AESModeOfOperationCFB as aes
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


key = ''  # key


def crypto(string):
    sbox = []
    for i in range(256):
        sbox.append(i)
    j = 0
    for i in range(256):
        j = (sbox[i] + j + ord(key[i % 16])) % 0x100
        sbox[i], sbox[j] = sbox[j], sbox[i]


class rc4(object):
    def __init__(self, key):
        key = bytes(key)
        tempkey = sha256(key)
        self.cipher = ARC4.new(tempkey)

    def encrypt(self, data):
        return self.cipher.encrypt(data)


class AES(object):
    def __init__(self, token):
        token = bytes(token)
        s = sha256(context.password + token)
        self.key = s[:16]
        self.iv = s[16:]

        self.aes_object = aes.new(self.key, aes.MODE_CFB, self.iv)
        # self.aes_object = aes(self.key, iv=self.iv)

    def encrypt(self, data):
        data = bytes(data)
        # data = self.pkcs5_pad(data)
        return self.aes_object.encrypt(data)

    def decrypt(self, data):
        data = bytes(data)
        # data = self.pkcs5_pad(data)
        return self.aes_object.decrypt(data)

    @staticmethod
    def pkcs5_pad(data):
        print("+" * 80)
        pad_len = 16 - len(data) % 16
        data += bytes([pad_len]) * pad_len
        return data


def packed_timestamp():
    t = time.time()
    t = int(t)
    return struct.pack(b"!Q", t)


def unpack_timestamp(data):
    return struct.unpack(b'!Q', data)[0]
