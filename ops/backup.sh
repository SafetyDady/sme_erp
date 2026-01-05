#!/bin/bash
# SME ERP Database Backup - Docker/Kubernetes Ready
# Phase 7 - Operational Excellence

set -euo pipefail

# Configuration (override with environment variables)
BACKUP_DIR=${BACKUP_DIR:-"/app/backups"}
DATABASE_URL=${DATABASE_URL:-"sqlite:///app/sme_erp.db"}
RETENTION_DAYS=${RETENTION_DAYS:-"30"}
ENCRYPT_BACKUPS=${ENCRYPT_BACKUPS:-"true"}
S3_BUCKET=${S3_BUCKET:-""}
BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${BACKUP_DIR}/backup.log"
}

# Create backup directory
mkdir -p "${BACKUP_DIR}"

log "🔄 Starting SME ERP backup: ${BACKUP_TIMESTAMP}"

# Health check before backup
log "🏥 Pre-backup health check..."
if ! python3 -c "
from app.db.session import engine
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT 1').fetchone()
    print('✅ Database connection OK')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"; then
    log "❌ Pre-backup health check failed"
    exit 1
fi

# Extract database path from DATABASE_URL
if [[ $DATABASE_URL == sqlite* ]]; then
    DB_PATH=$(echo $DATABASE_URL | sed 's/sqlite:\/\/\///')
    log "📊 SQLite database detected: $DB_PATH"
    
    # Create SQLite backup
    BACKUP_FILE="${BACKUP_DIR}/sme_erp_backup_${BACKUP_TIMESTAMP}.db"
    
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$BACKUP_FILE"
        log "✅ Database backup created: $BACKUP_FILE"
    else
        log "❌ Database file not found: $DB_PATH"
        exit 1
    fi
    
elif [[ $DATABASE_URL == postgresql* ]]; then
    log "🐘 PostgreSQL database detected"
    
    # Extract connection details
    BACKUP_FILE="${BACKUP_DIR}/sme_erp_backup_${BACKUP_TIMESTAMP}.sql"
    
    # Create PostgreSQL dump
    if pg_dump "$DATABASE_URL" > "$BACKUP_FILE"; then
        log "✅ PostgreSQL dump created: $BACKUP_FILE"
    else
        log "❌ PostgreSQL backup failed"
        exit 1
    fi
else
    log "❌ Unsupported database type: $DATABASE_URL"
    exit 1
fi

# Compress backup
log "🗜️  Compressing backup..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"
log "✅ Backup compressed: $BACKUP_FILE"

# Encrypt backup if enabled
if [ "$ENCRYPT_BACKUPS" = "true" ]; then
    log "🔐 Encrypting backup..."
    
    if [ -n "${BACKUP_ENCRYPTION_KEY:-}" ]; then
        # Use symmetric encryption with provided key
        openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" -out "${BACKUP_FILE}.enc" -pass env:BACKUP_ENCRYPTION_KEY
        rm "$BACKUP_FILE"  # Remove unencrypted file
        BACKUP_FILE="${BACKUP_FILE}.enc"
        log "✅ Backup encrypted: $BACKUP_FILE"
    else
        log "⚠️  Encryption requested but BACKUP_ENCRYPTION_KEY not set"
    fi
fi

# Generate backup metadata
METADATA_FILE="${BACKUP_DIR}/sme_erp_backup_${BACKUP_TIMESTAMP}.metadata.json"
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
BACKUP_HASH=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)

cat > "$METADATA_FILE" << EOF
{
  "timestamp": "$BACKUP_TIMESTAMP",
  "created_at": "$(date -Iseconds)",
  "file_name": "$(basename "$BACKUP_FILE")",
  "file_size": $BACKUP_SIZE,
  "sha256_hash": "$BACKUP_HASH",
  "database_url_type": "$(echo $DATABASE_URL | cut -d':' -f1)",
  "compressed": true,
  "encrypted": $ENCRYPT_BACKUPS,
  "retention_until": "$(date -d "+${RETENTION_DAYS} days" -Iseconds)"
}
EOF

log "📋 Metadata created: $METADATA_FILE"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log "☁️  Uploading to S3: $S3_BUCKET"
    
    if command -v aws &> /dev/null; then
        aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/backups/$(basename "$BACKUP_FILE")"
        aws s3 cp "$METADATA_FILE" "s3://${S3_BUCKET}/backups/$(basename "$METADATA_FILE")"
        log "✅ Backup uploaded to S3"
    else
        log "⚠️  AWS CLI not found, skipping S3 upload"
    fi
fi

# Cleanup old backups
log "🧹 Cleaning up old backups..."
find "$BACKUP_DIR" -name "sme_erp_backup_*.db*" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "sme_erp_backup_*.sql*" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "sme_erp_backup_*.metadata.json" -mtime +$RETENTION_DAYS -delete
log "✅ Cleanup completed"

# Verify backup integrity
log "🔍 Verifying backup integrity..."
EXPECTED_HASH="$BACKUP_HASH"
ACTUAL_HASH=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)

if [ "$EXPECTED_HASH" = "$ACTUAL_HASH" ]; then
    log "✅ Backup integrity verified"
else
    log "❌ Backup integrity check failed!"
    exit 1
fi

# Success notification
log "🎉 Backup completed successfully!"
log "📦 File: $BACKUP_FILE"
log "📏 Size: $(numfmt --to=iec $BACKUP_SIZE)"
log "🔢 Hash: $BACKUP_HASH"

# Optional: Send notification to monitoring system
if [ -n "${WEBHOOK_URL:-}" ]; then
    curl -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"✅ SME ERP Backup Completed\",
            \"backup_timestamp\": \"$BACKUP_TIMESTAMP\",
            \"backup_size\": $BACKUP_SIZE,
            \"status\": \"success\"
        }" || log "⚠️  Failed to send notification"
fi