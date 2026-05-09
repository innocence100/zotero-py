import os

DATABASE_URL = os.environ.get("ZOTERO_DATABASE_URL", "sqlite+aiosqlite:///./zotero.db")
API_VERSION = 3
KEY_CHARS = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
KEY_LENGTH = 8
SECRET_KEY = os.environ.get("ZOTERO_SECRET_KEY", "change-me-in-production")
