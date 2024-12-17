import hashlib
import json5 as json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from typing import Dict, Any
from utils.logger import Logger
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    Encoding,
    PublicFormat,
)

log = Logger("transaction")


class Transaction:

    def __init__(
        self,
        sender: bytes = None,
        recipient: bytes = None,
        amount: float = 0,
        content: Any = "",
        sign_public_key: bytes = None,
        signature: bytes = None
    ):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.content = content
        self.sign_public_key = sign_public_key
        self.signature = signature

    def to_dict(self) -> Dict[str, str]:
        return {
            "sender": (
                self.sender.hex()
                if self.sender
                else None
            ),
            "recipient": (
                self.recipient.hex()
                if self.recipient
                else None
            ),
            "amount": self.amount,
            "content": str(self.content),
            "signature": (
                self.signature.hex()
                if self.signature
                else None
            ),
            "sign_public_key": self.sign_public_key.hex()
            if self.sign_public_key
            else None,
        }

    def calculate_hash(self) -> str:
        transaction_dict = self.to_dict()
        transaction_dict.pop("signature", None)
        transaction_string = json.dumps(transaction_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(transaction_string.encode()).hexdigest()

    def sign_transaction(self, signer: rsa.RSAPrivateKey) -> None:
        if not self.sender or not self.recipient:
            raise ValueError("Transaction must include sender and recipient")

        hash_bytes = self.calculate_hash().encode()
        self.signature = signer.sign(hash_bytes, padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256() )

    def is_valid(self, public_key: bytes) -> bool:
        if not self.signature:
            log.debug("No signature in this transaction")
            return False
        if not public_key:
            log.debug("No public key provided")
            return False

        public_key = load_pem_public_key(public_key)
        try:
            public_key.verify(
                self.signature,
                self.calculate_hash().encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            log.error(f"Signature verification failed: {e}")
            return False


if __name__ == "__main__":
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        )

    transaction = Transaction(sender=b"Alice", recipient=b"Bob", amount=100, sign_public_key=public_key)
    print("Transaction hash before signing:", transaction.calculate_hash())

    transaction.sign_transaction(private_key)
    print("Transaction signed.")

    is_valid = transaction.is_valid(public_key)
    print("Is transaction valid?:", is_valid)