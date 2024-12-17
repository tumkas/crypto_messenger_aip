'''
This module contains main socket logic and its main handlers
'''

import socket
import threading
from utils import logger
import zlib

log = logger.Logger("sockets")


class P2PSocket:
    '''
    The main socket class

    :ivar host: Local peer host
    :type host: str
    :ivar port: Local peer port
    :type port: int
    :ivar blockchain: Local peer's blockchain
    :type blockchain: Blockchain
    :ivar max_connections: Maximum connections peer allows to connect
    :type max_connections: int
    :ivar socket: Main socket instance that used to send and accept connections
    :type socket: Socket
    :ivar connections: Peers active connections
    :type connections: List[(conn, addr)]
    :ivar sync_manager: Syncronization manager instance that handles every blockchain action
    :type sync_manager: SyncManager
    :ivar signature_manager: Signature manager that handles every action with signing messages and transactions
    :type signature_manager: DigitalSignature
    '''
    def __init__(self, host: str, port: int, blockchain, sync_manager,
                 signature_manager, max_connections: int = 5):
        """
        P2PSocket intialization.

        :param host: Local peer host
        :type host: str
        :param port: Local peer port
        :type port: int
        :param blockchain: Local peer's blockchain
        :type blockchain: Blockchain
        :param max_connections: Maximum connections peer allows to connect
        :type max_connections: int
        :param sync_manager: Syncronization manager instance that handles every blockchain action
        :type sync_manager: SyncManager
        :param signature_manager: Signature manager that handles every action with signing messages and transactions
        :type signature_manager: DigitalSignature

        """
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connections = []  # Active connection list
        self.blockchain = blockchain
        self.sync_manager = sync_manager
        self.signature_manager = signature_manager



    def start_server(self):
        '''Starting server to accept connections'''
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_connections)
            log.debug(f"Server started at {self.host}:{self.port}")
        except socket.error as e:
            log.error(f"Could not bind socket: {e}")
            return

        while True:
            try:
                conn, addr = self.socket.accept()
                if len(self.connections) >= self.max_connections:
                    log.warning(
                        f"Maximum connections reached. Connection from {addr} rejected"
                    )
                    conn.close()
                    continue
                self.connections.append((conn, addr))
                log.info(f"Connection established with {addr}")
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            except socket.error as e:
                log.error(f"Error accepting connection: {e}")
                return

    def handle_client(self, conn, addr):
        '''
        Client handler.

        :param conn: Connection that needs to be handled
        :type conn: socket.connection
        :param addr: Connection's address that needs to be handled
        :type addr: Tuple(str, int)
        '''
        try:
            while True:
                try:
                    chunks = []
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break  # Connection closed
                        chunks.append(chunk)
                        if len(chunk) < 4096:
                            break # Last chunk
                    if not chunks:
                        break # Leaving handle cycle if no data

                    data = b"".join(chunks)
                    print(data)

                    data = zlib.decompress(data)

                    log.debug(f"Received from {addr}: {data[:100].decode()}")

                    if data.startswith(b"NEW_BLOCK"):
                        block_data = data[len(b"NEW_BLOCK") :]
                        self.sync_manager.handle_new_block(block_data, conn)

                    elif data.startswith(b"REQUEST_CHAIN"):
                        log.info("Sending blockchain")
                        self.sync_manager.broadcast_chain()
                        log.debug(f"Sent blockchain to {addr}")

                    elif data.startswith(b"BLOCKCHAIN"):
                        blockchain = data[len(b"BLOCKCHAIN") :]
                        self.sync_manager.handle_blockchain(blockchain, conn)


                    elif data.startswith(b"NEW_TRANSACTION"):
                        transaction_data = data[len(b"NEW_TRANSACTION") :]
                        self.sync_manager.handle_new_transaction(transaction_data, conn)

                    elif data.startswith(b"NEW_MESSAGE"):
                        pass

                    else:  # Simple message
                        self.broadcast(data, conn)

                except ConnectionResetError as e:
                    break # Leaving handler cycle
                except socket.error as e:
                    log.error(f"Error receiving data from {addr}: {e}")
                    break

        except Exception as e:
            log.error(f"Error with client {addr}: {e}")
        finally:
            self.connections.remove((conn, addr))
            log.info(f"Connection closed with {addr}")
            conn.close()

    def broadcast(self, message: bytes, sender_conn):
        """
        Broadcastin message to everyone, except sender.

        :param message: Message that needs to be broadcasted
        :type message: bytes
        :param sender_conn: Connection of sender
        :type sender_conn: socket.connection
        """
        for conn, _ in self.connections:
            if conn != sender_conn:
                try:
                    conn.sendall(zlib.compress(message))
                except socket.error as e:
                    log.error(f"Error broadcasting to a connection: {e}")

    def connect_to_peer(self, peer_host: str, peer_port: int):
        '''
        Connecting to another peer

        :param peer_host: Another peer's host
        :type peer_host: str
        :param peer_port: Another peer's port
        :type peer_port: int
        :return: Another peer's connection or None
        :rtype: socket.connection or None
        '''
        try:
            conn = socket.create_connection((peer_host, peer_port))
            if len(self.connections) >= self.max_connections:
                log.warning(
                    f"Maximum connections reached. Connection to {peer_host}:{peer_port} rejected"
                )
                conn.close()
                return None
            self.connections.append((conn, (peer_host, peer_port)))
            threading.Thread(
                target=self.handle_client, args=(conn, (peer_host, peer_port))
            ).start()
            log.info(f"Connected to peer {peer_host}:{peer_port}")
            return conn
        except socket.error as e:
            log.error(f"Error connecting to peer {peer_host}:{peer_port}: {e}")
            return None

    def get_connection(self, peer_host: str):
        '''
        Returns existing connection or None if there is no one.

        :param peer_host: Another peer's host
        :type peer_host: str
        :return: Another peer's socket connection or none
        :rtype: socket.connection or None
        '''
        for conn, addr in self.connections:
            if addr[0] == peer_host:
                return conn
        return None
