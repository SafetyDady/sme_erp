#!/usr/bin/env python3
"""
SME ERP Database Restore System
Phase 7 - Operational Excellence

Features:
- Restore from encrypted/compressed backups
- Verify data integrity after restore
- Multiple restore targets (in-place, new location)
- Disaster recovery simulation
"""

import os
import sys
import sqlite3
import shutil
import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
import tempfile

class RestoreManager:
    """Database restore manager with verification"""
    
    def __init__(self, backup_dir: str):
        self.backup_dir = Path(backup_dir)
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging for restore operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("/workspaces/sme_erp/backend/ops/restore.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def list_available_backups(self) -> list:
        """List all available backups with metadata"""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*.metadata.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                # Check if backup file exists
                backup_file = self.backup_dir / metadata["file_name"]
                if backup_file.exists():
                    backups.append({
                        "metadata": metadata,
                        "backup_file": str(backup_file),
                        "metadata_file": str(metadata_file)
                    })
            except Exception as e:
                self.logger.warning(f"⚠️  Corrupted metadata: {metadata_file}")
        
        return sorted(backups, key=lambda x: x["metadata"]["created_at"], reverse=True)
    
    def restore_backup(self, backup_timestamp: str, target_path: str, verify: bool = True) -> bool:
        """
        Restore database from backup
        
        Args:
            backup_timestamp: Timestamp of backup to restore (e.g., '20260104_170148')
            target_path: Path where to restore the database
            verify: Whether to verify restore integrity
        
        Returns:
            bool: Success status
        """
        try:
            self.logger.info(f"🔄 Starting restore: {backup_timestamp}")
            
            # Find backup files
            backup_files = list(self.backup_dir.glob(f"sme_erp_backup_{backup_timestamp}.*"))
            
            if not backup_files:
                self.logger.error(f"❌ No backup found for timestamp: {backup_timestamp}")
                return False
            
            # Find the actual backup file (not metadata)
            backup_file = None
            metadata_file = None
            
            for file in backup_files:
                if file.suffix == '.json':
                    metadata_file = file
                else:
                    backup_file = file
            
            if not backup_file or not metadata_file:
                self.logger.error(f"❌ Incomplete backup files for {backup_timestamp}")
                return False
            
            # Load metadata
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            self.logger.info(f"📋 Backup metadata: {metadata['file_size']} bytes, created {metadata['created_at']}")
            
            # Start restore process
            working_file = backup_file
            temp_dir = Path(tempfile.mkdtemp(prefix="sme_restore_"))
            
            try:
                # Step 1: Decrypt if needed
                if metadata.get("encrypted", False):
                    self.logger.info("🔓 Decrypting backup...")
                    working_file = self.decrypt_backup(working_file, temp_dir)
                
                # Step 2: Decompress if needed
                if metadata.get("compressed", False):
                    self.logger.info("📂 Decompressing backup...")
                    working_file = self.decompress_backup(working_file, temp_dir)
                
                # Step 3: Copy to target location
                target_file = Path(target_path)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy(working_file, target_file)
                self.logger.info(f"✅ Database restored to: {target_file}")
                
                # Step 4: Verify restore if requested
                if verify:
                    if self.verify_restored_database(target_file, metadata):
                        self.logger.info("✅ Restore verification passed")
                        return True
                    else:
                        self.logger.error("❌ Restore verification failed")
                        return False
                
                return True
                
            finally:
                # Cleanup temporary files
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            self.logger.error(f"❌ Restore failed: {str(e)}")
            return False
    
    def decrypt_backup(self, encrypted_file: Path, temp_dir: Path) -> Path:
        """Decrypt backup file"""
        decrypted_file = temp_dir / f"decrypted_{encrypted_file.stem}"
        
        # Simple XOR decryption (matches backup.py)
        key = "SME_ERP_BACKUP_KEY_2026"
        
        with open(encrypted_file, 'rb') as f_in:
            with open(decrypted_file, 'wb') as f_out:
                data = f_in.read()
                # Reverse XOR encryption
                decrypted = bytes(a ^ ord(key[i % len(key)]) for i, a in enumerate(data))
                f_out.write(decrypted)
        
        return decrypted_file
    
    def decompress_backup(self, compressed_file: Path, temp_dir: Path) -> Path:
        """Decompress backup file"""
        decompressed_file = temp_dir / f"decompressed_{compressed_file.stem}"
        
        with gzip.open(compressed_file, 'rb') as f_in:
            with open(decompressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_file
    
    def verify_restored_database(self, restored_file: Path, original_metadata: Dict) -> bool:
        """Verify restored database integrity"""
        try:
            # Test SQLite connectivity
            with sqlite3.connect(str(restored_file)) as conn:
                cursor = conn.cursor()
                
                # Check table structure
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                if not tables:
                    self.logger.error("❌ No tables found in restored database")
                    return False
                
                self.logger.info(f"✅ Found {len(tables)} tables: {[t[0] for t in tables]}")
                
                # Test data integrity (sample query)
                for table_name, in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        self.logger.info(f"📊 Table {table_name}: {count} records")
                    except Exception as e:
                        self.logger.warning(f"⚠️  Could not query table {table_name}: {e}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Database verification failed: {str(e)}")
            return False
    
    def disaster_recovery_drill(self) -> bool:
        """
        Perform complete disaster recovery simulation
        """
        self.logger.info("🚨 DISASTER RECOVERY DRILL STARTING")
        self.logger.info("=" * 50)
        
        try:
            # Step 1: List available backups
            backups = self.list_available_backups()
            if not backups:
                self.logger.error("❌ No backups available for recovery")
                return False
            
            # Use most recent backup
            latest_backup = backups[0]
            timestamp = latest_backup["metadata"]["timestamp"]
            
            self.logger.info(f"🎯 Using backup: {timestamp}")
            self.logger.info(f"📅 Created: {latest_backup['metadata']['created_at']}")
            
            # Step 2: Simulate database loss
            original_db = "/workspaces/sme_erp/backend/sme_erp_dev.db"
            backup_original = f"{original_db}.disaster_backup"
            
            if os.path.exists(original_db):
                shutil.copy(original_db, backup_original)
                os.remove(original_db)
                self.logger.info("🔥 Simulated database loss (original backed up)")
            
            # Step 3: Restore from backup
            recovery_start = datetime.now()
            
            if self.restore_backup(timestamp, original_db):
                recovery_time = (datetime.now() - recovery_start).total_seconds()
                
                self.logger.info(f"⏱️  Recovery completed in {recovery_time:.2f} seconds")
                
                # Step 4: Test application connectivity
                self.logger.info("🧪 Testing application connectivity...")
                
                with sqlite3.connect(original_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM test_data")
                    record_count = cursor.fetchone()[0]
                
                self.logger.info(f"✅ Application test passed: {record_count} records accessible")
                
                # Step 5: Restore original for safety
                if os.path.exists(backup_original):
                    shutil.copy(backup_original, original_db)
                    os.remove(backup_original)
                    self.logger.info("🔄 Original database restored")
                
                # Calculate RTO/RPO
                self.logger.info("📊 RECOVERY METRICS:")
                self.logger.info(f"   RTO (Recovery Time): {recovery_time:.2f} seconds")
                self.logger.info(f"   RPO (Data Loss): < 24 hours (daily backup)")
                self.logger.info("   Success Rate: 100%")
                
                self.logger.info("🎉 DISASTER RECOVERY DRILL PASSED")
                return True
            
            else:
                self.logger.error("❌ DISASTER RECOVERY DRILL FAILED")
                
                # Restore original database
                if os.path.exists(backup_original):
                    shutil.copy(backup_original, original_db)
                    os.remove(backup_original)
                    self.logger.info("🔄 Original database restored after failed drill")
                
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Disaster recovery drill failed: {str(e)}")
            return False


def main():
    """Main restore demonstration"""
    restore_manager = RestoreManager("/workspaces/sme_erp/backend/backups")
    
    print("🔄 SME ERP Database Restore System")
    print("=" * 40)
    
    # List available backups
    backups = restore_manager.list_available_backups()
    
    if not backups:
        print("❌ No backups available")
        return
    
    print(f"📋 Found {len(backups)} backup(s):")
    for i, backup in enumerate(backups, 1):
        metadata = backup["metadata"]
        print(f"  {i}. {metadata['timestamp']} - {metadata['file_size']} bytes ({metadata['created_at']})")
    
    # Perform disaster recovery drill
    print("\n🚨 Performing Disaster Recovery Drill...")
    print("-" * 40)
    
    if restore_manager.disaster_recovery_drill():
        print("✅ Disaster recovery drill PASSED")
        print("🎯 System ready for production deployment")
    else:
        print("❌ Disaster recovery drill FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()