import os
import sys
import unittest

pdir = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.append(pdir)

import src.crypto.diffie_hellman as dh


class TestDiffieHellman(unittest.TestCase):
	dhc = dh.DiffieHellmanKeyExchange()

	def test_generate_shared_key_success(self):
		test_key = self.dhc.get_public_key()

		self.assertEqual(type(self.dhc.generate_shared_key(test_key)), bytes)

	def test_generate_shared_key_fail(self):
		with self.assertRaises(AssertionError):
			self.assertEqual(type(self.dhc.generate_shared_key("123")), bytes)



if __name__ == '__main__':
	unittest.main()