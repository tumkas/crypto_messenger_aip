'''This module contains main P2P network handler'''

import threading
import utils.logger as logger
from .sockets import P2PSocket
from blockchain.transaction import Transaction
import json5 as json
from network.discovery import discover_peers
import traceback
from blockchain.blockchain import Blockchain

log = logger.Logger("p2p")


class P2PNetwork:
    '''
    That class of P2P network where peers corroze

    :ivar host: Local peer's host
    :type host: str
    :ivar port: Local peer's port
    :type port: int
    :ivar blockchain: Peer's local blockchain
    :type blockchain: Blockchain
    :ivar username: Local peer's username
    :type username: str
    :ivar public_key: Local peer's DH public key
    :type public_key: str
    :ivar broadcast_port: Local peer's broadcast port
    :type broadcast_port: int
    :ivar peers: Set of knows peers
    :type peers: set
    :ivar sync_interval: Blockchain syncronization interval
    :type sync_interval: int
    :ivar broadcast_interval: Broadcast interval
    :type broadcast_interval: int
    :ivar sync_manager: Syncronization manager that handles blockchain operations
    :type sync_manager: SyncManager
    :ivar signature_manager: Sugnature manager that handles operations with signatures
    :type DigitalSignature:
    :ivar node: Node server of peer
    :type node: P2PSocket
    '''
    def __init__(
        self,
        host: str,
        port: int,
        node: P2PSocket,
        sync_manager,
        blockchain: Blockchain,
        broadcast_port: int,
        username: str,
        public_key: str,
        signature_manager,
        sync_interval: int = 5,
        broadcast_interval: int = 1,
        max_connections: int = 5
    ):
        '''
        P2P Network initialization


        :param host: Local peer's host
        :type host: str
        :param port: Local peer's port
        :type port: int
        :param blockchain: Peer's local blockchain
        :type blockchain: Blockchain
        :param username: Local peer's username
        :type username: str
        :param public_key: Local peer's DH public key
        :type public_key: str
        :param broadcast_port: Local peer's broadcast port
        :type broadcast_port: int
        :param sync_interval: Blockchain syncronization interval
        :type sync_interval: int
        :param broadcast_interval: Broadcast interval
        :type broadcast_interval: int
        :param sync_manager: Syncronization manager that handles blockchain operations
        :type sync_manager: SyncManager
        :param signature_manager: Sugnature manager that handles operations with signatures
        :type signature_manager: DigitalSignature
        :param node: Node server of peer
        :type node: P2PSocket
        '''
        self.blockchain = blockchain
        self.host = host
        self.port = port
        self.username = username
        self.public_key = public_key
        self.broadcast_port = broadcast_port
        self.peers = set()  # Список известных узлов
        self.sync_interval = sync_interval
        self.broadcast_interval = broadcast_interval
        self.sync_manager = sync_manager(self, self.blockchain, self.sync_interval)
        self.signature_manager = signature_manager
        self.node = node(self.host, self.port, self.blockchain, self.sync_manager, self.signature_manager, max_connections)
        self.ui_app = None


    def start(self):
        '''Starting P2P network'''
        self.node.blockchain = self.blockchain  # Добавляем blockchain в node
        threading.Thread(target=self.node.start_server, daemon=True).start()
        log.info(f"Node started at {self.host}:{self.port}")

    def connect_to_peer(self, peer_host: str, peer_port: int):
        '''
        Connecting to new peer

        :param peer_host: Peer's host
        :type peer_host: str
        :param peer_port: Peer's port
        :type peer_port: int
        :return: Peer connection or None
        :rtype: socket.connection or None
        '''
        try:
            if (
                self.host == peer_host or peer_host == "127.0.0.1"
            ) and self.port == peer_port:
                log.warning("Cannot connect to self")
                raise Exception("Cannot connect to self")
            conn = self.node.connect_to_peer(peer_host, peer_port)
            return conn
        except Exception as e:
            log.error(f"Error connecting to peer: {e}")
            print(traceback.format_exc())

    def broadcast_message(self, message: str, conn):
        '''
        Broadcasting message to all peers

        :param message: Message to broadcast
        :type message: str
        :param conn: Sender connection
        :type conn: socket.connection
        '''
        log.debug(f"Broadcasting message: {message}")
        self.node.broadcast(message, conn)

    def broadcast_transaction(self, transaction: Transaction, conn):
        '''
        Broadcasting transaction

        :param transaction: Transaction to broadcast
        :type transaction: Transaction
        :param conn: Sender connection
        :type conn: socket.connection
        '''
        transaction_data = json.dumps(
            transaction.to_dict(), ensure_ascii=False
        ).encode()
        log.debug(f"Broadcasting transaction: {transaction.calculate_hash()}")
        self.broadcast_message(b"NEW_TRANSACTION" + transaction_data, conn)

    def discover_peers(self):
        '''Peers discovery mechainsm'''
        self.peers = discover_peers(
            self.host,
            self.port,
            self.broadcast_port,
            self.username,
            self.public_key,
            self.broadcast_interval,
        )
        log.info(f"Discovered peers: {list(self.peers)}")

    def sync_with_peers(self):
        '''Syncronization with connected peers'''
        self.sync_manager.start_sync_loop()
