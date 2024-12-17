import time
from typing import List
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    Encoding,
    PublicFormat,
)


class ProofOfWork:
    def __init__(self, difficulty: int):
        self.difficulty = difficulty

    def mine(self, block) -> str:
        target = self.get_target()

        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()
        print(f"Block mined: {block.hash}")
        return block.hash

    def validate(self, block) -> bool:
        target = self.get_target()
        return block.hash.startswith(target)

    def get_target(self) -> str:
        return "0" * self.difficulty


class Validator:

    def validate_blockchain(self, blockchain) -> bool:
        for i in range(1, len(blockchain.chain)):
            current_block = blockchain.chain[i]
            previous_block = blockchain.chain[i - 1]
            if not self.validate_block(current_block, previous_block):
                return False

        return True

    def validate_block(self, current_block, previous_block) -> bool:
        if current_block.hash != current_block.calculate_hash():
            print(f"Block {current_block.index} has invalid hash.")
            return False

        if current_block.previous_hash != previous_block.hash:
            print(f"Block {current_block.index} has invalid previous hash.")
            return False

        if current_block.timestamp <= previous_block.timestamp:
            print(f"Block {current_block.index} has invalid timestamp")
            return False

        return True


if __name__ == "__main__":
    from transaction import Transaction
    from blockchain import Blockchain, Block

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        )


    blockchain = Blockchain(difficulty=4)
    pow = ProofOfWork(difficulty=4)

    transaction1 = Transaction(b"Alice", b"Bob", 0, "Hi", sign_public_key=public_key)
    transaction1.sign_transaction(private_key)

    transaction2 = Transaction(b"Charlie", b"Dave", 0, "Hello", sign_public_key=public_key)
    transaction2.sign_transaction(private_key)

    blockchain.add_transaction(transaction1)
    blockchain.add_transaction(transaction2)

    new_block = Block(
        index=len(blockchain.chain),
        previous_hash=blockchain.get_latest_block().hash,
        timestamp=time.time(),
        transactions=blockchain.pending_transactions,
    )

    pow.mine(new_block)

    blockchain.chain.append(new_block)

    validator = Validator()
    print("Blockchain valid:", validator.validate_blockchain(blockchain))