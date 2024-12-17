import os
import sys
import unittest

pdir = os.path.dirname(os.path.realpath(__file__)) + "/.."
sys.path.append(pdir)

import src.crypto.signatures as sgn


class TestDiffieHellman(unittest.TestCase):
	ds = sgn.DigitalSignature()
	
	def test_sign_success(self):
		self.assertEqual(type(self.ds.sign(b'Test String.')), bytes)

	def test_sign_fail(self):
		with self.assertRaises(AssertionError):
			self.assertEqual(type(self.ds.sign('Test String.')), bytes)


	def test_verify_success(self):
		public_key = self.ds.get_public_key()
		test_string = "Test String."
		signature = self.ds.sign(bytes(test_string.encode()))

		self.assertEqual(self.ds.verify(public_key, test_string, signature), True)

	def test_verify_fail(self):
		public_key = self.ds.get_public_key()
		test_string = "Test String."
		fake_string = "Teest String."
		signature = self.ds.sign(bytes(fake_string.encode()))

		self.assertEqual(self.ds.verify(public_key, test_string, signature), False)


if __name__ == '__main__':
	unittest.main()