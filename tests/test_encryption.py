import os
import sys
import unittest

pdir = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.append(pdir)

import src.crypto.encryption as enc


class TestEncryption(unittest.TestCase):
	exe = enc.SymmetricEncryption(os.urandom(32), )

	def test_encrypt_success(self):
		self.assertEqual(type(self.exe.encrypt("Test String.")), bytes)

	def test_encrypt_fail(self):
		with self.assertRaises(AssertionError):
			self.assertEqual(type(self.exe.encrypt("")), bytes)


	def test_decrypt_success(self):
		self.assertEqual(self.exe.decrypt(self.exe.encrypt("Test String.")), "Test String.")

	def test_decrypt_fail(self):
		with self.assertRaises(AssertionError):
			self.assertEqual(self.exe.decrypt(b'123'), "321")



if __name__ == '__main__':
	unittest.main()