import sys
sys.path.append('.')
from app.db.session import engine
from app.db.base import Base

print("Creating inventory tables...")
Base.metadata.create_all(bind=engine)
print("✅ Done!")
