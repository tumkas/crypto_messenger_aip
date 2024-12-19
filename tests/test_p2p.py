import threading
import unittest
import os
import sys
import zlib
parent_dir = os.path.dirname(os.path.relpath(__file__)) + "/.."
sys.path.append(parent_dir)
from src.network.sockets import P2PSocket
from src.network.p2p import P2PNetwork
from src.network.sync import SyncManager
from src.crypto.signatures import DigitalSignature
from src.blockchain.blockchain import Blockchain, Block
from src.crypto.diffie_hellman import DiffieHellmanKeyExchange
from src.utils.config import DEFAULT_DH_PARAMETERS

class TestSockets(unittest.TestCase):

    def setUp(self):
        self.dh_key_manager1 = DiffieHellmanKeyExchange(DEFAULT_DH_PARAMETERS)
        self.dh_public_key1 = self.dh_key_manager1.get_public_key()
        self.signature_manager1 = DigitalSignature()
        self.blockchain1 = Blockchain()
        self.network1 = P2PNetwork("127.0.0.1", 12345, P2PSocket,
                                  SyncManager, self.blockchain1, 5000,
                                  "Guest", self.dh_public_key1,
                                  self.signature_manager1)
        self.dh_key_manager2 = DiffieHellmanKeyExchange(DEFAULT_DH_PARAMETERS)
        self.dh_public_key2 = self.dh_key_manager2.get_public_key()
        self.signature_manager2 = DigitalSignature()
        self.blockchain2 = Blockchain()
        self.network2 = P2PNetwork("127.0.0.1", 12344, P2PSocket,
                                   SyncManager, self.blockchain2, 5000,
                                   "Guest2", self.dh_public_key2,
                                   self.signature_manager2)
        self.network1.node.start_server()
        self.network2.node.start_server()
        self.network1.discover_peers()


    def test_discover_peers(self):
        self.assertEqual(self.network1.peers, {("127.0.0.1", 12344, "Guest2", self.dh_public_key2)})


if __name__ == "__main__":
    unittest.main()
