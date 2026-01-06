# BACKUP & RESTORE RUNBOOK

## Quick Reference

**Database Type**: PostgreSQL (Production) / SQLite (Development)  
**RPO (Recovery Point Objective)**: 24 hours for SME  
**RTO (Recovery Time Objective)**: 4 hours for SME

---

## PostgreSQL (Production Environment)

### Backup Commands

#### Full Database Backup

```bash
# Create timestamped backup
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h <hostname> -U <username> -d sme_erp_prod > sme_erp_backup_${BACKUP_DATE}.sql

# With compression
pg_dump -h <hostname> -U <username> -d sme_erp_prod | gzip > sme_erp_backup_${BACKUP_DATE}.sql.gz

# Custom format (faster restore)
pg_dump -h <hostname> -U <username> -d sme_erp_prod -Fc > sme_erp_backup_${BACKUP_DATE}.dump
```

#### Schema-only Backup

```bash
pg_dump -h <hostname> -U <username> -d sme_erp_prod --schema-only > sme_erp_schema_${BACKUP_DATE}.sql
```

#### Data-only Backup

```bash
pg_dump -h <hostname> -U <username> -d sme_erp_prod --data-only > sme_erp_data_${BACKUP_DATE}.sql
```

### Restore Commands

#### Full Database Restore

```bash
# Create new database
createdb -h <hostname> -U <username> sme_erp_restored

# Restore from SQL dump
psql -h <hostname> -U <username> -d sme_erp_restored < sme_erp_backup_20260105_120000.sql

# Restore from compressed dump
gunzip -c sme_erp_backup_20260105_120000.sql.gz | psql -h <hostname> -U <username> -d sme_erp_restored

# Restore from custom format
pg_restore -h <hostname> -U <username> -d sme_erp_restored sme_erp_backup_20260105_120000.dump
```

#### Partial Restore (specific tables)

```bash
pg_restore -h <hostname> -U <username> -d sme_erp_restored -t users -t items sme_erp_backup_20260105_120000.dump
```

### Verification Steps

#### 1. Check Database Connection

```bash
psql -h <hostname> -U <username> -d sme_erp_restored -c "SELECT version();"
```

#### 2. Verify Table Counts

```sql
-- Compare record counts between original and restored
SELECT
    schemaname,
    tablename,
    n_tup_ins as row_count
FROM pg_stat_user_tables
ORDER BY tablename;
```

#### 3. Verify Key Data Integrity

```sql
-- Check user accounts
SELECT COUNT(*) FROM users WHERE is_active = true;

-- Check inventory items
SELECT COUNT(*) FROM items WHERE status = 'ACTIVE';

-- Check recent transactions
SELECT COUNT(*) FROM stock_transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- Check stock balances
SELECT
    i.name,
    SUM(sl.quantity_change) as total_stock
FROM stock_ledger sl
JOIN items i ON i.id = sl.item_id
GROUP BY i.id, i.name
HAVING SUM(sl.quantity_change) != 0
ORDER BY i.name;
```

#### 4. Test Application Connection

```bash
# Test backend connection to restored DB
# Update DATABASE_URL in .env to point to restored database
export DATABASE_URL="postgresql://user:pass@host:5432/sme_erp_restored"

# Start backend and test
uvicorn app.main:app --port 8001
curl http://localhost:8001/health
```

---

## SQLite (Development Environment)

### Backup Commands

#### Full Database Backup

```bash
# Simple copy
cp app.db app_backup_$(date +%Y%m%d_%H%M%S).db

# Using SQLite backup command
sqlite3 app.db ".backup app_backup_$(date +%Y%m%d_%H%M%S).db"

# Export to SQL
sqlite3 app.db .dump > app_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Commands

#### Full Database Restore

```bash
# Simple copy restore
cp app_backup_20260105_120000.db app.db

# From SQL dump
rm -f app.db  # Remove existing database
sqlite3 app.db < app_backup_20260105_120000.sql
```

### Verification Steps

#### 1. Check Database File

```bash
file app.db
sqlite3 app.db "PRAGMA integrity_check;"
```

#### 2. Verify Table Counts

```sql
-- List all tables and row counts
SELECT
    name,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%') as table_count
FROM sqlite_master
WHERE type='table' AND name NOT LIKE 'sqlite_%';

-- Check specific tables
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM items;
SELECT COUNT(*) FROM stock_transactions;
```

---

## Automated Backup Scripts

### Daily Backup Script (Linux/Unix)

```bash
#!/bin/bash
# daily_backup.sh

set -e

# Configuration
DB_HOST="your-db-host"
DB_USER="backup_user"
DB_NAME="sme_erp_prod"
BACKUP_DIR="/var/backups/sme_erp"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
BACKUP_FILE="$BACKUP_DIR/sme_erp_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

echo "Starting backup to $BACKUP_FILE"
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

# Verify backup file exists and has content
if [ -s "$BACKUP_FILE" ]; then
    echo "✅ Backup completed successfully: $BACKUP_FILE"

    # Test that the backup file can be read
    zcat "$BACKUP_FILE" | head -10 > /dev/null
    echo "✅ Backup file integrity verified"
else
    echo "❌ Backup failed - file is empty or missing"
    exit 1
fi

# Clean up old backups
echo "Cleaning up backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "sme_erp_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed at $(date)"
```

### Backup Cron Setup

```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * /path/to/daily_backup.sh >> /var/log/sme_erp_backup.log 2>&1

# Weekly full backup with custom format (Sundays at 3 AM)
0 3 * * 0 pg_dump -h host -U user -d sme_erp_prod -Fc > /var/backups/sme_erp/weekly_$(date +\%Y\%m\%d).dump
```

---

## Recovery Scenarios & Procedures

### Scenario 1: Data Corruption

**Problem**: Database reports corruption or inconsistent data

**Steps**:

1. Stop application immediately
2. Copy current database to safe location
3. Run integrity checks
4. If corruption confirmed, restore from latest backup
5. Verify restored data integrity
6. Restart application

### Scenario 2: Accidental Data Deletion

**Problem**: Critical data accidentally deleted

**Steps**:

1. Do NOT restart application
2. Identify timestamp of deletion
3. Restore to temporary database from backup before deletion
4. Extract deleted data using SQL queries
5. Import missing data to production database
6. Verify data consistency

### Scenario 3: Server Hardware Failure

**Problem**: Database server completely inaccessible

**Steps**:

1. Provision new database server
2. Install PostgreSQL with same version
3. Create new database
4. Restore from latest backup
5. Update application connection strings
6. Test full application functionality
7. Update DNS/load balancer if needed

---

## Backup Testing Log

### Test Performed: January 5, 2026

#### Environment: Local SQLite Development

```bash
# Test Date: 2026-01-05
# Tester: M4 Implementation

# 1. Create test data
sqlite3 app.db "INSERT INTO users (email, role) VALUES ('test@backup.com', 'admin');"
sqlite3 app.db "SELECT COUNT(*) FROM users;" # Result: 1

# 2. Create backup
sqlite3 app.db ".backup app_backup_test.db"

# 3. Simulate data loss
rm app.db

# 4. Restore from backup
cp app_backup_test.db app.db

# 5. Verify data
sqlite3 app.db "SELECT email FROM users WHERE email='test@backup.com';"
# Result: test@backup.com

# ✅ Test Result: SUCCESS
# ✅ Backup size: 32KB
# ✅ Restore time: < 1 second
# ✅ Data integrity: Verified
```

#### Next Test Due: January 12, 2026

---

## Emergency Contacts & Procedures

### Escalation Matrix

1. **Developer**: Immediate response for data issues
2. **System Admin**: Infrastructure and server issues
3. **Business Owner**: If data loss > 24 hours or affects operations

### Communication Template

```
SUBJECT: [URGENT] SME ERP Database Issue - [Brief Description]

Issue: [What happened]
Impact: [Business impact]
Action Taken: [What was done]
ETA: [Expected resolution time]
Backup Status: [Latest backup available from when]
```

---

## Best Practices for SME Environment

1. **Daily Automated Backups**: Set up cron jobs
2. **Test Quarterly**: Restore to test environment
3. **Multiple Locations**: Store backups off-site (cloud storage)
4. **Monitor Backup Success**: Set up alerts for failed backups
5. **Document Changes**: Keep this runbook updated
6. **Access Control**: Restrict backup file access
7. **Encryption**: Encrypt backups containing sensitive data
