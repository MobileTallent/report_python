import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
import os

cwd = Path().cwd()


login = os.getenv('login')
password = os.getenv('password')