import os
from dotenv import load_dotenv

load_dotenv(".env")


OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
