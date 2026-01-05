#!/usr/bin/env python3
"""Create inventory tables"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from app.db.session import engine
from app.db.base import Base

def create_tables():
    try:
        print("Creating inventory tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Inventory tables created successfully!")
        
        # List tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Current tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()