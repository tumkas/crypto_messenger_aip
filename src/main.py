# main.py
import sys
import socket

from network.p2p import P2PNetwork
from blockchain.blockchain import Blockchain
from network.sockets import P2PSocket
from blockchain.transaction import Transaction
from crypto.diffie_hellman import DiffieHellmanKeyExchange
from crypto.signatures import DigitalSignature
from crypto.encryption import SymmetricEncryption
from ui.messenger_window import MessengerApp
from utils.logger import Logger
from utils.config import DEFAULT_DH_PARAMETERS, DEFAULT_PORT, BROADCAST_PORT
from network.sync import SyncManager
from PyQt5.QtWidgets import QApplication


log = Logger("main")


def generate_keys():
    """Generates keys for both DH and signature."""
    dh_key_exchange = DiffieHellmanKeyExchange(DEFAULT_DH_PARAMETERS)
    dh_public_key = dh_key_exchange.get_public_key()

    signer = DigitalSignature()
    private_key_pem = signer.get_private_key()
    public_key_pem = signer.get_public_key()
    public_key = signer.public_key

    return dh_key_exchange, signer, private_key_pem, public_key, dh_public_key


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(("10.254.254.254", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def main():
    username = input("Enter your username (default=guest): ") or "guest"
    host = input(f"Enter your host (default={get_ip()}): ") or get_ip()
    try:
        port = int(input(f"Enter your port (default={DEFAULT_PORT}): "))
    except Exception:
        port = DEFAULT_PORT

    broadcast_port = BROADCAST_PORT
    sync_interval = 5
    max_connections = 5
    broadcast_interval = 2

    print("Generating keys...")
    dh_key_manager = DiffieHellmanKeyExchange(DEFAULT_DH_PARAMETERS)
    signature_manager = DigitalSignature()
    dh_public_key = dh_key_manager.get_public_key()

    blockchain = Blockchain()
    p2p_network = P2PNetwork(
        host,
        port,
        P2PSocket,
        SyncManager,
        blockchain,
        broadcast_port,
        username,
        dh_public_key.hex(),
        signature_manager,
        sync_interval,
        broadcast_interval,
        max_connections
    )
    p2p_network.start()
    # p2p_network.sync_with_peers()
    p2p_network.discover_peers() # <--- кривовато работает

    log.info(f"Your public key: {dh_public_key}")
    shared_keys = {}

    def get_shared_key(peer_public_key):
        """Retrieves existing shared key or generates new one."""
        if peer_public_key in shared_keys:
            return shared_keys[peer_public_key]
        else:
            shared_key = dh_key_manager.generate_shared_key(peer_public_key)
            if shared_key:
                shared_keys[peer_public_key] = shared_key
                return shared_key

    def connect_by_username(username):
        peer = ()
        if len(p2p_network.peers):
            for p in p2p_network.peers:
                if p[2] == username:
                    peer = p
                    break
                else:
                    log.info("No such user")
                    return False

            p2p_network.connect_to_peer(peer[0], peer[1])
            return True
        else:
            log.error("Couldnt find user")
            return False


    def get_messages(peer1, peer2):
        messages = []
        for block in blockchain.chain:
            for transaction in block.transactions:
                if (transaction.sender == peer1[3] and \
                    transaction.recipient == peer2[3]) or \
                    (transaction.sender == peer2[3] and \
                    transaction.recipient == peer1[3]):
                    messages.append(transaction)
        for transaction in blockchain.pending_transactions:
            if (transaction.sender == peer1[3] and \
                transaction.recipient == peer2[3]) or \
                (transaction.sender == peer2[3] and \
                transaction.recipient == peer1[3]):
                messages.append(transaction)

        return messages

    def send_message(username, content, app):
        recipient = None
        for peer in p2p_network.peers:
            if peer[2] == username:
                recipient = peer
                break
        if recipient is None:
            print(f"User {username} not found")

        shared_key = get_shared_key(recipient[3])
        if shared_key:
            encryptor = SymmetricEncryption(shared_key, algorithm="AES", mode="CBC")
            encrypted_content = encryptor.encrypt(content)
            if encrypted_content:
                log.debug("Creating signed encrypted transaction")
                transaction = Transaction(dh_public_key, recipient[3], 0, encrypted_content.hex(), signature_manager.get_public_key())
                transaction.sign_transaction(signature_manager)
                blockchain.add_transaction(transaction)
                p2p_network.broadcast_transaction(transaction, None)
                app.handle_messages(dh_public_key,
                    get_messages((host, port, username, dh_public_key), recipient))
            else:
                log.error("Message was not encrypted")
        else:
               log.warning("No shared key")

    def remove_connection(username):
        peer = None
        for p in p2p_network.peers:
            if p[2] == username:
                peer = p
                break
        if peer is None:
            print(f"User {username} not found")

        conn = p2p_network.node.get_connection(peer[0])
        p2p_network.node.connections.remove(conn, (peer[0], peer[1]))
        conn.close()


    app = QApplication(sys.argv)

    with open("src/ui/styles.qss", "r") as file:
        style_sheet = file.read()
        app.setStyleSheet(style_sheet)

    window = MessengerApp(username, connect_by_username, send_message, peers=p2p_network.peers)
    window.show()
    sys.exit(app.exec_())

#    while True:
#        command = input(
#            "Enter command (connect, message, send, mine, balance, peers, chain, sync, exit): "
#        )
#        if command == "connect":
#            while True:
#                index = input("Enter peer index or username: ")
#
#                try:
#                    index = int(index)
#                    peers = list(p2p_network.peers)
#                    p2p_network.connect_to_peer(peers[index][0], peers[index][1])
#                    break
#                except (ValueError, IndexError, TypeError):
#                    try:
#                        for p in p2p_network.peers:
#                            if p[2] == index:
#                                p2p_network.connect_to_peer(p[0], p[1])
#                                break
#                    except Exception as e:
#                        print(f"Error connecting to peer: {e}")
#
#        elif command == "message":
#            recipient_username = input("Enter recipient username: ")
#            recipient = None
#            for peer in list(p2p_network.peers):
#                if peer[2] == recipient_username:
#                    recipient = peer[3]
#                    break
#            if recipient is None:
#                print(f"User {recipient_username} not found")
#                continue
#
#            content = input("Enter message content: ")
#
#            shared_key = get_shared_key(recipient)
#
#            if shared_key:
#                encryptor = SymmetricEncryption(shared_key, algorithm="AES", mode="CBC")
#                encrypted_content = encryptor.encrypt(content)
#                if encrypted_content:
#                    log.debug("Creating signed encrypted transaction")
#                    transaction = Transaction(dh_public_key, recipient, 0, encrypted_content.hex(), signature_manager.get_public_key())
#                    transaction.sign_transaction(signature_manager)
#                    blockchain.add_transaction(transaction)
#                    p2p_network.broadcast_transaction(transaction, None)
#                else:
#                    log.error("Message was not encrypted")
#            else:
#                log.warning("No shared key")
#
#        elif command == "send":
#            recipient_username = input("Enter recipient username: ")
#            recipient = None
#            for peer in list(p2p_network.peers):
#                if peer[2] == recipient_username:
#                    recipient = peer[3]
#                    break
#            if recipient is None:
#                print(f"User {recipient_username} not found")
#                continue
#            amount = float(input("Enter amount to send (MEM): "))
#            transaction = Transaction(dh_public_key, recipient, amount, "", signature_manager.get_public_key())
#            transaction.sign_transaction(signature_manager)
#            blockchain.add_transaction(transaction)
#            p2p_network.broadcast_transaction(transaction, None)
#        elif command == "mine":
#            new_block, reward_transaction = blockchain.mine_pending_transactions(ProofOfWork, dh_public_key)
#            if new_block is None or reward_transaction is None:
#                continue
#            p2p_network.sync_manager.broadcast_block(new_block, None)
#            p2p_network.broadcast_transaction(reward_transaction, None)
#
#
#        elif command == "balance":
#            balance = blockchain.get_balance(dh_public_key)
#            print(f"Your balance: {balance} MEM")
#        elif command == "peers":
#            peers = list(p2p_network.peers)
#            for peer in peers:
#                print(f"ID: {peers.index(peer)}     HOST: {peer[0]}     PORT: {peer[1]}     USERNAME: {peer[2]}     PUBLIC KEY: {peer[3].hex()}")
#        elif command == "chain":
#            for block in blockchain.chain:
#                print(block.to_dict())
##         elif command == "sync":
##             p2p_network.sync_with_peers()
#            print("Syncing...")
#        elif command == "exit":
#            print("Exiting...")
#            sys.exit()
#        else:
#            print("Unknown command.")


if __name__ == "__main__":
    main()

