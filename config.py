# config.py

import os
from dotenv import load_dotenv
from langchain_xai import ChatXAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

llm = ChatXAI(model="grok-4-1-fast-reasoning")
