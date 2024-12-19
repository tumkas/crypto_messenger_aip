import unittest
from unittest.mock import patch, MagicMock
import os
import sys

parent_dir = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.append(parent_dir)

from src.network import discovery, p2p, sockets, sync
from src.blockchain import blockchain, consensus, transaction
from src.crypto import diffie_hellman, encryption, signatures
from src.utils import logger, config

class TestDiscovery(unittest.TestCase):
    @patch('src.network.discovery.socket')
    @patch('src.network.discovery.logger.log_info')
    @patch('src.crypto.signatures.DigitalSignature.verify', return_value=True)
    def test_discover_peers(self, mock_verify_signature, mock_log_info, mock_socket):
        # Setup mock objects
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Mock UDP socket behavior
        mock_socket_instance.recvfrom.return_value = (b'{"port": 12345, "signature": "valid_sig"}', ("127.0.0.1", 12345))

        # Mock zlib decompression and JSON loading
        with patch('src.network.discovery.zlib.decompress', return_value=b'{"port": 12345, "signature": "valid_sig"}'):
            with patch('src.network.discovery.json.loads', return_value={"port": 12345, "signature": "valid_sig"}):
                peers = discovery.discover_peers(
                    local_host="127.0.0.1",
                    local_port=8000,
                    broadcast_port=8001,
                    username="test_user",
                    public_key="public_key",
                    broadcast_interval=1
                )

        # Assertions
        self.assertIn(("127.0.0.1", 12345), peers)
        mock_socket_instance.bind.assert_called_once_with(("", 8001))
        mock_verify_signature.assert_called_once_with("valid_sig", "public_key")

class TestP2P(unittest.TestCase):
    @patch('src.network.p2p.P2PNetwork')
    @patch('src.utils.logger.Logger')
    @patch('src.crypto.encryption.SymmetricEncryption', return_value="encrypted_message")
    def test_p2p_connection(self, mock_encrypt_message, mock_log_info, mock_socket):
        # Setup mock objects
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Example mock for a P2P connection establishment
        mock_socket_instance.connect.return_value = None
        result = p2p.connect_to_peer("127.0.0.1", 8000)

        # Assertions
        mock_socket_instance.connect.assert_called_once_with(("127.0.0.1", 8000))
        self.assertTrue(result)
        mock_encrypt_message.assert_not_called()  # No encryption during connection setup

    @patch('src.crypto.encryption.encrypt_message', return_value="encrypted_message")
    @patch('src.crypto.encryption.decrypt_message', return_value="decrypted_message")
    def test_send_and_receive_message(self, mock_decrypt_message, mock_encrypt_message):
        # Mock send and receive
        with patch('src.network.p2p.send_message', return_value=True) as mock_send, \
             patch('src.network.p2p.receive_message', return_value="decrypted_message") as mock_receive:

            # Simulate sending a message
            send_result = p2p.send_message("127.0.0.1", 8000, "test_message")

            # Simulate receiving a message
            received_message = p2p.receive_message("127.0.0.1", 8000)

        # Assertions
        mock_send.assert_called_once_with("127.0.0.1", 8000, "encrypted_message")
        mock_receive.assert_called_once_with("127.0.0.1", 8000)
        self.assertTrue(send_result)
        self.assertEqual(received_message, "decrypted_message")

class TestSockets(unittest.TestCase):
    @patch('src.network.sockets.socket')
    @patch('src.utils.logger.log_info')
    def test_socket_creation(self, mock_log_info, mock_socket):
        # Setup mock objects
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Example mock for socket creation
        result = sockets.create_socket()

        # Assertions
        mock_socket.assert_called_once()
        self.assertEqual(result, mock_socket_instance)
        mock_log_info.assert_called_once_with("Socket created successfully")

class TestSync(unittest.TestCase):
    @patch('src.network.sync.logger.log_info')
    @patch('src.blockchain.blockchain.validate_block', return_value=True)
    @patch('src.crypto.encryption.decrypt_message', return_value={"data": "test_data"})
    def test_sync_data(self, mock_decrypt_message, mock_validate_block, mock_log_info):
        # Mock the sync function behavior
        with patch('src.network.sync.fetch_data_from_peer', return_value="encrypted_data") as mock_fetch:
            result = sync.synchronize_data("127.0.0.1", 8000)

        # Assertions
        mock_fetch.assert_called_once_with("127.0.0.1", 8000)
        mock_decrypt_message.assert_called_once_with("encrypted_data")
        mock_validate_block.assert_called_once_with({"data": "test_data"})
        self.assertEqual(result, {"data": "test_data"})

if __name__ == "__main__":
    unittest.main()

