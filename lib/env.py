from dotenv import find_dotenv, load_dotenv
import os

if not load_dotenv(find_dotenv()):
	raise FileNotFoundError('Could not find .env')

cfg = os.environ