"""Module that handles blockchain syncronization"""

import json5 as json
from utils.logger import Logger
from blockchain.transaction import Transaction
from blockchain.blockchain import Block
from blockchain.consensus import ProofOfWork
import socket

log = Logger("sync")


class SyncManager:
    """
    Class that handles syncronization

    :ivar p2p_network: Peer's P2P Network
    :type p2p_network: P2PNetwork
    :ivar blockchain: Peer's local blockchain
    :type blockchain: Blockchain
    :ivar sync_interval: Syncronization interval
    :type sync_interval: int
    """

    def __init__(self, p2p_network, blockchain, sync_interval: int = 5):
        """
        Intialization of syncronization manager

        :ivar p2p_network: Peer's P2P Network
        :type p2p_network: P2PNetwork
        :ivar blockchain: Peer's local blockchain
        :type blockchain: Blockchain
        :ivar sync_interval: Syncronization interval
        :type sync_interval: int
        """
        self.p2p_network = p2p_network
        self.blockchain = blockchain  # Локальная копия блокчейна
        self.sync_interval = sync_interval

    def request_chain(self, peer_host: str, peer_port: int) -> None:
        """
        Requests blockchain copy from given peer

        :param peer_host: peer's host
        :type peer_host: str
        :param peer_port: peer's port
        :type peer_port: int
        """
        try:
            conn = self.p2p_network.node.get_connection(peer_host)
            if not conn:
                return
            self.p2p_network.broadcast_message(
                b"REQUEST_CHAIN", conn
            )  # Ensure all data is sent
            log.info(f"Requesting blockchain from {peer_host}:{peer_port}")

        except socket.error as e:
            log.error(f"Error requesting chain: {e}")
        except Exception as e:
            log.error(f"Error during chain request: {e}")

    def merge_chain(self, received_chain: list) -> None:
        """
        Updates local blockchain if recieved chain is longer and valid

        :param received_chain: Recieved chain
        :type received_chain: List[Block]
        """
        if not received_chain:
            log.info("Received empty chain")
            return

        if len(received_chain) > len(self.blockchain.chain):
            if self.blockchain.validator.validate_blockchain(self.blockchain):
                self.blockchain.chain = received_chain
                log.info("Local blockchain updated.")
            else:
                log.warning("Received blockchain is not valid")
        else:
            log.debug("Received chain is not longer than the local chain.")

    def broadcast_block(self, block: Block, conn) -> None:
        """
        Broadcast new block every known peer.

        :param block: New block to add to a chain
        :type block: Block
        :param conn: Sender connection
        :type conn: socket.connection or None
        """
        if not block:
            log.debug("Cannot broadcast empty block")
            return
        log.debug("Broadcasting new block...")

        block_bytes = json.dumps(block.to_dict(), ensure_ascii=False).encode()

        self.p2p_network.broadcast_message(b"NEW_BLOCK" + block_bytes, conn)

    def broadcast_chain(self, conn) -> None:
        """
        Broadcast chain to peer

        :param conn: Sender connection
        :type conn: socket.connection
        """
        if not self.blockchain.chain:
            log.debug("Cannot broadcast empty chain")
            return
        log.debug("Broadcasting chain...")

        chain_bytes = json.dumps(
            [block.to_dict() for block in self.blockchain.chain], ensure_ascii=False
        ).encode()
        self.p2p_network.broadcast_message(b"BLOCKCHAIN" + chain_bytes, conn)

    def start_sync_loop(self) -> None:
        """
        Automated syncronization cycle with known peers
        """

        log.debug("Starting synchronization loop...")
        if len(self.p2p_network.peers):
            for peer in self.p2p_network.peers:
                try:
                    self.request_chain(peer[0], peer[1])
                except Exception as e:
                    log.error(f"Error syncing with peer {peer}: {e}")

    def handle_new_block(self, block_data: bytes, conn) -> None:
        """
        Handles new block, recieved from other peer

        :param block_data: Block information
        :type block_data: bytes
        :param conn: Sender connection
        :type conn: socket.connection
        """
        try:
            block_dict = json.loads(block_data.decode())
            for transaction in block_dict["transactions"]:
                if transaction["signature"]:
                    transaction["signature"] = (
                        bytes.fromhex(transaction["signature"])
                        if transaction["signature"]
                        else None
                    )
                if transaction["sender"]:
                    transaction["sender"] = (
                        bytes.fromhex(transaction["sender"])
                        if transaction["sender"]
                        else None
                    )
                transaction["recipient"] = bytes.fromhex(transaction["recipient"])
                if transaction["sign_public_key"]:
                    transaction["sign_public_key"] = bytes.fromhex(
                        transaction["sign_public_key"]
                    )
            block_dict["transactions"] = [
                Transaction(**transaction) for transaction in block_dict["transactions"]
            ]
            block = Block(**block_dict)
            if self.blockchain.contains_block(block):
                return

            if self.blockchain.validator.validate_block(
                block, self.blockchain.get_latest_block()
            ):
                self.blockchain.chain.append(block)
                self.broadcast_block(block, conn)
                log.info(f"Added new block with index {block.index}")
            else:
                log.warning("Invalid block received")

        except Exception as e:
            log.error(f"Error during block handling: {e}")

    def handle_new_transaction(self, transaction_data: bytes, conn) -> None:
        """
        Handles new transaction, recieved from another peer.

        :param transaction_data: New transaction info
        :type transaction_data: bytes
        :param conn: Sender connection
        :type conn: socket.connection
        """
        try:
            transaction_string = transaction_data.decode()
            transaction_dict = json.loads(transaction_string)
            if transaction_dict["sender"]:
                transaction_dict["sender"] = (
                    bytes.fromhex(transaction_dict["sender"])
                    if transaction_dict["sender"]
                    else None
                )
            transaction_dict["recipient"] = bytes.fromhex(transaction_dict["recipient"])
            if transaction_dict["signature"]:
                transaction_dict["signature"] = (
                    bytes.fromhex(transaction_dict["signature"])
                    if transaction_dict["signature"]
                    else None
                )
            if transaction_dict["sign_public_key"]:
                transaction_dict["sign_public_key"] = bytes.fromhex(
                    transaction_dict["sign_public_key"]
                )
            transaction = Transaction(**transaction_dict)
            if transaction in self.blockchain.pending_transactions:
                return

            log.debug(f"Received transaction {transaction.calculate_hash()}")
            if self.blockchain.is_transaction_valid(transaction):
                self.blockchain.pending_transactions.append(transaction)
                dh_public_key = bytes.fromhex(self.p2p_network.public_key)
                if transaction.recipient == dh_public_key:
                    self.p2p_network.ui_app.handle_messages(self.p2p_network.public_key, transaction.sender)
                self.p2p_network.broadcast_transaction(transaction, conn)
                if len(self.blockchain.pending_transactions) >= 3:
                    new_block, reward_transaction = self.blockchain.mine_pending_transactions(ProofOfWork, dh_public_key)
                    if new_block is None or reward_transaction is None:
                        return
                    self.broadcast_block(new_block, None)
                    self.p2p_network.broadcast_transaction(reward_transaction, None)
                log.info(f"Added new transaction from network")
            else:
                log.warning("Invalid transaction received")
        except Exception as e:
            log.error(f"Error during transaction handling: {e}")

    def handle_blockchain(self, blockchain):
        """
        Handles new blockchain, recieved from another peer.

        :param blockchain: New blockchain
        :type blockchain: Blockchain
        """
        blockchain = json.loads(blockchain.decode())
        chain = []

        for block_data in blockchain:
            transactions = []
            for transaction_data in block_data["transactions"]:
                if transaction_data["signature"]:
                    transaction_data["signature"] = bytes.fromhex(
                        transaction_data["signature"]
                    )
                if transaction_data["sender"]:
                    transaction_data["sender"] = bytes.fromhex(
                        transaction_data["sender"]
                    )
                if transaction_data["recipient"]:
                    transaction_data["recipient"] = bytes.fromhex(
                        transaction_data["recipient"]
                    )
                if transaction_data["sign_public_key"]:
                    transaction_data["sign_public_key"] = bytes.fromhex(
                        transaction_data["sign_public_key"]
                    )
                transactions.append(Transaction(**transaction_data))
            block_data["transacti, connons"] = transactions
            chain.append(Block(**block_data))
        self.merge_chain(chain)
