"""Crypto Helper Functions"""

import hashlib
import os
from base64 import b64encode, b64decode
from random import SystemRandom
from string import punctuation, ascii_letters, digits

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def random_string(length: int = 64, p: bool = False) -> str:
    """Generate a random string."""
    allowed_chars = ascii_letters + digits
    if p:
        allowed_chars += punctuation
    token = "".join(SystemRandom().choice(allowed_chars) for i in range(length))
    return token


def random_words(length: int = 2, sep: str = '-') -> str:
    adjectives = [
        "absurd",
        "amusing",
        "astonishing",
        "bizarre",
        "bouncing",
        "comical",
        "dapper",
        "daring",
        "delightful",
        "eccentric",
        "elated",
        "fantastic",
        "goofy",
        "hilarious",
        "incredible",
        "jaunty",
        "jovial",
        "kooky",
        "laughable",
        "ludicrous",
        "magnificent",
        "marvellous",
        "peculiar",
        "quizzical",
        "ridiculous",
        "silly",
        "stupendous",
        "wacky",
        "zany"
    ]

    nouns = [
        "blackcap",
        "canary",
        "chaffinch",
        "cockatoo",
        "Common",
        "linnet",
        "grosbeak",
        "koel",
        "lyrebird",
        "magpie",
        "mockingbird",
        "nightingale",
        "oriole",
        "passerine",
        "robin",
        "skylark",
        "sparrow",
        "tanager",
        "thrush",
        "wagtail",
        "warbler",
        "woodpecker",
    ]
    return sep.join([SystemRandom().choice(adjectives) for i in range(length-1)] + [SystemRandom().choice(nouns)])


def generate_salt(key_size: int = 256):
    """generate a random salt."""
    return b64encode(AESGCM.generate_key(key_size)).decode('utf-8')


class CryptoHelper:
    """CryptoHelper Class"""
    def __init__(self, salt: str):
        self.salt = b64decode(salt.encode('utf-8'))
        self.associated_data = b"aad"
        self.aesgcm = AESGCM(self.salt)

    def hash(self, password: str) -> str:
        """generate hashed password"""
        return hashlib.sha512(password.encode('utf-8') + self.salt).hexdigest()

    def hash_verify(self, password: str, hashed_password: str) -> bool:
        """verify hashed password"""
        return self.hash(password) == hashed_password

    def encrypt(self, data: str) -> [str, str]:
        """encrypt data"""
        nonce = os.urandom(12)
        ct = self.aesgcm.encrypt(nonce, data.encode('utf-8'), self.associated_data)
        return b64encode(nonce).decode(), b64encode(ct).decode()
        # return {'nonce': b64encode(nonce).decode(), 'ciphertext': b64encode(ct).decode()}

    def decrypt(self, nonce: str, ciphertext: str) -> str:
        """decrypt data"""
        return self.aesgcm.decrypt(b64decode(nonce),
                                   b64decode(ciphertext),
                                   self.associated_data).decode('utf-8')


if __name__ == '__main__':
    print("random string ", random_string())
    print("random string ", random_string(True))

    print("random word ", random_words())
    print("random word ", random_words(3))

    _salt = generate_salt()
    print("salt ", _salt)

    CH = CryptoHelper(_salt)

    nonce, enc = CH.encrypt("string")
    print("encrypted ", enc)

    dec = CH.decrypt(nonce, enc)
    print("decrypted ", dec)

    HASHED = CH.hash('string')
    print("hashed ", HASHED)
    print("verified ", CH.hash_verify('string', HASHED))
