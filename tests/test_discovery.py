import unittest
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import zlib
import json5 as json
import time
parent_dir = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.append(parent_dir)
from src.network.discovery import discover_peers


class TestDiscoverPeers(unittest.TestCase):
    @patch("socket.socket")
    def test_discover_peers_adds_new_peer(self, mock_socket):
        """Test that discover_peers adds new peers correctly."""

        # Mock сокет
        mock_udp_socket = MagicMock()
        mock_socket.return_value = mock_udp_socket

        # Параметры для discover_peers
        local_host = "127.0.0.1"
        local_port = 5000
        broadcast_port = 5001
        username = "test_user"
        public_key = "abcdef123456"

        # Получаем множество пиров
        peers = discover_peers(
            local_host, local_port, broadcast_port, username, public_key
        )

        # Фейковые данные от нового пира
        fake_peer_data = {
            "port": 6000,
            "username": "peer_user",
            "public_key": "fedcba654321",
        }
        fake_peer_address = ("127.0.0.2", 6000)

        # Сжимаем сообщение как это делает код
        compressed_data = zlib.compress(json.dumps(fake_peer_data).encode())

        # Имитируем получение сообщения
        def fake_recvfrom(buffer_size):
            return compressed_data, fake_peer_address

        mock_udp_socket.recvfrom.side_effect = fake_recvfrom

        # Ждем, пока поток обработает сообщение
        time.sleep(2)

        # Проверяем, что новый пир добавлен
        expected_peer = (
            fake_peer_address[0],
            fake_peer_data["port"],
            fake_peer_data["username"],
            bytes.fromhex(fake_peer_data["public_key"]),
        )
        self.assertIn(expected_peer, peers)

    @patch("socket.socket")
    def test_discover_peers_ignores_self(self, mock_socket):
        """Test that discover_peers ignores its own broadcast."""

        # Mock сокет
        mock_udp_socket = MagicMock()
        mock_socket.return_value = mock_udp_socket

        # Параметры для discover_peers
        local_host = "127.0.0.1"
        local_port = 5000
        broadcast_port = 5001
        username = "test_user"
        public_key = "abcdef123456"

        # Получаем множество пиров
        peers = discover_peers(
            local_host, local_port, broadcast_port, username, public_key
        )

        # Фейковые данные от себя
        fake_self_data = {
            "port": local_port,
            "username": username,
            "public_key": public_key,
        }
        fake_self_address = (local_host, local_port)

        # Сжимаем сообщение
        compressed_data = zlib.compress(json.dumps(fake_self_data).encode())

        # Имитируем получение сообщения
        def fake_recvfrom(buffer_size):
            return compressed_data, fake_self_address

        mock_udp_socket.recvfrom.side_effect = fake_recvfrom

        # Ждем, пока поток обработает сообщение
        time.sleep(2)

        # Проверяем, что "свой" пир не добавился
        self.assertEqual(len(peers), 0)

    @patch("socket.socket")
    def test_broadcast_sends_correct_message(self, mock_socket):
        """Test that the broadcast message is sent correctly."""

        # Mock сокет
        mock_udp_socket = MagicMock()
        mock_socket.return_value = mock_udp_socket

        # Параметры для discover_peers
        local_host = "127.0.0.1"
        local_port = 5000
        broadcast_port = 5001
        username = "test_user"
        public_key = "abcdef123456"

        # Запускаем discover_peers
        discover_peers(
            local_host, local_port, broadcast_port, username, public_key
        )

        # Ждем отправки сообщений
        time.sleep(2)

        # Проверяем, что сокет отправил сжатое сообщение
        expected_message = {
            "host": local_host,
            "port": local_port,
            "public_key": public_key,
            "username": username,
        }
        expected_compressed = zlib.compress(json.dumps(expected_message).encode())

        mock_udp_socket.sendto.assert_called_with(
            expected_compressed, ("<broadcast>", broadcast_port)
        )


if __name__ == "__main__":
    unittest.main()

