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
        """Инициализация P2P сети."""
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


    def start(self):
        self.node.blockchain = self.blockchain  # Добавляем blockchain в node
        threading.Thread(target=self.node.start_server, daemon=True).start()
        log.info(f"Node started at {self.host}:{self.port}")

    def connect_to_peer(self, peer_host: str, peer_port: int):
        """Подключение к новому узлу."""
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
        """Рассылка сообщения всем подключенным узлам."""
        log.debug(f"Broadcasting message: {message}")
        print(message)
        self.node.broadcast(message, conn)

    def broadcast_transaction(self, transaction: Transaction, conn):
        """Рассылает транзакцию всем подключенным узлам."""
        transaction_data = json.dumps(
            transaction.to_dict(), ensure_ascii=False
        ).encode()
        log.debug(f"Broadcasting transaction: {transaction.calculate_hash()}")
        self.broadcast_message(b"NEW_TRANSACTION" + transaction_data, conn)

    def discover_peers(self):
        """Механизм обнаружения новых узлов."""
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
        """Синхронизация данных с подключенными узлами."""
        self.sync_manager.start_sync_loop()
