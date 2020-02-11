import os

ASANA_API_KEY = os.getenv("ASANA_API_KEY")
GITHUB_API_KEY = os.getenv("GITHUB_API_KEY")
ENV = os.getenv("ENV", "dev")
LOCK_TABLE = os.getenv("LOCK_TABLE", "sgtm-lock")
OBJECTS_TABLE = os.getenv("OBJECTS_TABLE", "sgtm-objects")
USERS_TABLE = os.getenv("USERS_TABLE", "sgtm-users")
