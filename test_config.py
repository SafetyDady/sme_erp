#!/usr/bin/env python3

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, '/workspace/backend')

try:
    from app.core.config import settings
    from app.core.db import engine
    from sqlalchemy import text
    
    print("=" * 50)
    print("SME ERP Configuration Test")
    print("=" * 50)
    print(f"APP_NAME: {settings.APP_NAME}")
    print(f"APP_VERSION: {settings.APP_VERSION}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print()
    
    print("Testing database connection...")
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();")).fetchone()
        print("✅ Database connected successfully!")
        if result:
            version_info = result[0]
            print(f"PostgreSQL version: {version_info.split(',')[0]}")
    
    # Test basic query
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database();")).fetchone()
        if result:
            print(f"Connected to database: {result[0]}")
    
    print("\n🎉 All tests passed! System is ready.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)