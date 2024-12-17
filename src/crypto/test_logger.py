class Logger:
	module = ""


	def __init__(self, module):
		self.module = module


	def debug(self, text):
		print("TESTS_MODE [" + self.module + "] - debug - " + str(text))

	def error(self, text):
		print("TESTS_MODE [" + self.module + "] - error - " + str(text))