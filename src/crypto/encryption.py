"""
    This module represents message encryption / decryption.\
    In project dh shared key will be used with this module \
    to encrypt / decrypt messages.
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from typing import Optional


class SymmetricEncryption:
    """
    Encryption class

    :ivar key: key that will be used to encrypt message
    :type key: bytes
    """

    def __init__(self, key: bytes, algorithm="AES", mode="CBC"):
        """
        Initiates with the given key

        :param key: key that will be used to encrypt message
        :type key: bytes
        :param algorithm: algotithm to encrypt
        :type algorithm: str
        :param mode: work mode of encrypt algorithm
        :type mode: str
        """
        self.key = key
        self.algorithm = algorithm
        self.mode = mode

    def encrypt(self, plaintext: str) -> Optional[bytes]:
        """
        Encrypts the message

        :param plaintext: message to be encrypted
        :type plaintext: str
        :return: encrypted message
        :rtype: bytes
        """
        if not plaintext:
            return None

        plaintext_bytes = plaintext.encode()

        if self.algorithm == "AES" and self.mode == "CBC":
            iv = os.urandom(16)
            cipher = Cipher(
                algorithms.AES(self.key), modes.CBC(iv), backend=default_backend()
            )
            encryptor = cipher.encryptor()

            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(plaintext_bytes) + padder.finalize()

            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            return iv + ciphertext
        else:
            print("Unsupported algorithm or mode")
            return None


if __name__ == "__main__":

    key = os.urandom(32)

    encryptor = SymmetricEncryption(key, algorithm="AES", mode="GCM")
    plaintext = "This is a secret message."

    encrypted = encryptor.encrypt(plaintext)
    print("Encrypted:", encrypted.hex() if encrypted else "None")
