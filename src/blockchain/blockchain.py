import hashlib
import time
from typing import List, Dict
from .consensus import ProofOfWork, Validator
from .transaction import Transaction
from cryptography.hazmat.primitives.asymmetric import rsa
import json5 as json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    Encoding,
    PublicFormat,
)


class Block:
    def __init__(
        self,
        index: int,
        previous_hash: str,
        timestamp: float,
        transactions: List[Transaction],
        nonce: int = 0,
        hash: str = None,
    ) -> None:
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.calculate_hash() if not hash else hash

    def calculate_hash(self) -> str:
        transactions = [transaction.to_dict() for transaction in self.transactions]
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}\
                         {transactions}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "timestamp": self.timestamp,
            "transactions": [
                transaction.to_dict() for transaction in self.transactions
            ],
            "nonce": self.nonce,
        }


class Blockchain:
    def __init__(self, difficulty: int = 4) -> None:
        self.chain: List[Block] = [self.create_genesis_block()]
        self.difficulty = difficulty
        self.pending_transactions: List[Transaction] = []
        self.validator = Validator()

    def __len__(self):
         return len(self.chain)

    def create_genesis_block(self) -> Block:
        return Block(0, "0", 0, [])

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> None:
        if self.is_transaction_valid(transaction):
            self.pending_transactions.append(transaction)
        else:
            print("Transaction is invalid")

    def is_transaction_valid(self, transaction: Transaction) -> bool:
        if transaction.sender:
            if not transaction.is_valid(transaction.sign_public_key):
                return False

            sender_balance = self.get_balance(transaction.sender)
            if sender_balance < transaction.amount:
                return False

        return True

    def get_balance(self, address: bytes) -> float:
        balance = 0
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.sender == address:
                    balance -= transaction.amount
                if transaction.recipient == address:
                    balance += transaction.amount
        return balance

    def mine_pending_transactions(self, miner, miner_address: str) -> tuple[Block, Transaction] | tuple[None, None]:
        if not self.pending_transactions:
            print("No transactions to mine.")
            return None, None

        new_block = Block(
            index=len(self.chain),
            previous_hash=self.get_latest_block().hash,
            timestamp=time.time(),
            transactions=self.pending_transactions,
        )

        reward_transaction = Transaction(None, miner_address, 1, "Mining Reward")

        miner(self.difficulty).mine(new_block)
        miner(self.difficulty).validate(new_block)

        if self.validator.validate_block(new_block, self.chain[-1]):
            self.chain.append(new_block)
            self.pending_transactions = [reward_transaction]
            return new_block, reward_transaction
        else:
            print("Invalid block. Block was not added to the chain")
            return None, None

    def is_chain_valid(self) -> bool:
        return self.validator.validate_blockchain(self)

    def contains_block(self, target_block: Block) -> bool:
        for block in self.chain:
            if block.hash == target_block.hash:
                return True
        return False



if __name__ == "__main__":
    blockchain = Blockchain(difficulty=4)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key().public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        )

    transaction = Transaction(b"Alice", b"Bob", 0, "", public_key)
    print("Transaction hash before signing:", transaction.calculate_hash())

    transaction.sign_transaction(private_key)
    print("Transaction signed.")

    blockchain.add_transaction(transaction)
    blockchain.mine_pending_transactions(ProofOfWork, miner_address="Miner1")

    print("Blockchain valid:", blockchain.is_chain_valid())
    for block in blockchain.chain:
        print(block.to_dict())