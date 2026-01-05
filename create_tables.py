#!/usr/bin/env python3
"""
Create initial migration for users table
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.db.base import Base

def create_tables():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

if __name__ == "__main__":
    create_tables()