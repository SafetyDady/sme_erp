from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ============= PRIMARY DATABASE (WRITE + CRITICAL READS) =============

# Create primary engine
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============= READ-REPLICA DATABASE (REPORTS + NON-CRITICAL READS) =============

read_replica_engine = None
ReadReplicaSessionLocal = None

if settings.READ_REPLICA_ENABLED and settings.READ_REPLICA_DATABASE_URL:
    try:
        if settings.READ_REPLICA_DATABASE_URL.startswith("sqlite"):
            read_replica_engine = create_engine(
                settings.READ_REPLICA_DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
        else:
            read_replica_engine = create_engine(settings.READ_REPLICA_DATABASE_URL)
        
        ReadReplicaSessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=read_replica_engine
        )
        
        logger.info(f"✅ Read-replica configured: {settings.READ_REPLICA_DATABASE_URL[:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Read-replica setup failed: {e}")
        if not settings.READ_REPLICA_FALLBACK:
            raise
        logger.warning("📌 Falling back to primary database for reads")

Base = declarative_base()

# ============= DATABASE SESSION DEPENDENCIES =============

def get_db():
    """
    Primary database session for writes and critical reads.
    Always uses primary database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    """
    Read-only database session for reports and non-critical reads.
    Uses read-replica when available, falls back to primary.
    """
    if ReadReplicaSessionLocal:
        try:
            db = ReadReplicaSessionLocal()
            # Test connection
            db.execute(text("SELECT 1"))
            yield db
            return
        except Exception as e:
            logger.warning(f"⚠️ Read-replica unavailable: {e}")
            db.close()
            if not settings.READ_REPLICA_FALLBACK:
                raise
            logger.info("📌 Falling back to primary database")
    
    # Fallback to primary database
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_db_with_fallback():
    """
    Read database with explicit fallback handling.
    Returns tuple (session, is_replica_used).
    """
    if ReadReplicaSessionLocal:
        try:
            db = ReadReplicaSessionLocal()
            # Test connection
            db.execute(text("SELECT 1"))
            return db, True
        except Exception as e:
            logger.warning(f"⚠️ Read-replica unavailable: {e}")
            try:
                db.close()
            except:
                pass
            
            if not settings.READ_REPLICA_FALLBACK:
                raise
    
    # Use primary database
    db = SessionLocal()
    return db, False

# ============= CONNECTION HEALTH CHECKS =============

def check_primary_health():
    """Check primary database connectivity."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Primary DB health check failed: {e}")
        return False

def check_replica_health():
    """Check read-replica database connectivity."""
    if not ReadReplicaSessionLocal:
        return False
    
    try:
        db = ReadReplicaSessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.warning(f"⚠️ Replica DB health check failed: {e}")
        return False

def get_db_status():
    """Get comprehensive database status."""
    return {
        "primary": check_primary_health(),
        "replica_enabled": settings.READ_REPLICA_ENABLED,
        "replica_configured": ReadReplicaSessionLocal is not None,
        "replica_healthy": check_replica_health(),
        "fallback_enabled": settings.READ_REPLICA_FALLBACK
    }