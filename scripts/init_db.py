import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.database import init_db
from src.models import *

if __name__ == "__main__":
    print("Initializing database...")
    print("Registered tables:", Base.metadata.tables.keys())
    init_db()
    print("Database initialized.")
