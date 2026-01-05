# SME ERP Operational Runbooks

## Phase 7 - Operational Excellence

### 📚 Complete Runbook Collection

---

## 1. 🔄 BACKUP & RESTORE Runbook

### Daily Backup Procedure

**Frequency:** Automated daily at 2:00 AM  
**RTO:** < 5 minutes  
**RPO:** < 24 hours

#### Automated Backup

```bash
# Run manual backup
cd /workspaces/sme_erp/backend
python3 ops/backup.py

# Check backup status
ls -la backups/
```

#### Backup Verification

```bash
# Verify latest backup integrity
python3 ops/restore.py
```

#### Emergency Restore Procedure

**When:** Database corruption, accidental deletion, disaster recovery

1. **Identify backup to restore**

   ```bash
   python3 ops/restore.py  # List available backups
   ```

2. **Stop application**

   ```bash
   ./ops/deploy.sh cleanup
   ```

3. **Restore database**

   ```bash
   python3 -c "
   from app.core.restore import RestoreManager
   restore_manager = RestoreManager('/workspaces/sme_erp/backend/backups')
   restore_manager.restore_backup('TIMESTAMP', '/path/to/restore')
   "
   ```

4. **Verify restore**

   ```bash
   # Test database connectivity
   python3 -c "import sqlite3; conn = sqlite3.connect('sme_erp_dev.db'); print('✅ Database OK')"
   ```

5. **Restart application**
   ```bash
   ./ops/deploy.sh deploy
   ```

#### Backup Troubleshooting

- **Backup fails:** Check disk space, permissions
- **Restore fails:** Verify backup file integrity, check target path
- **Performance issues:** Monitor backup duration, consider compression

---

## 2. 🚀 DEPLOYMENT Runbook

### Blue-Green Deployment Procedure

**Downtime:** Zero downtime  
**Rollback time:** < 2 minutes

#### Pre-deployment Checklist

- [ ] CI/CD pipeline passes all gates
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Health checks functional
- [ ] Rollback plan confirmed

#### Standard Deployment

```bash
cd /workspaces/sme_erp/backend

# 1. Pre-deployment checks
./ops/deploy.sh status

# 2. Execute blue-green deployment
DEPLOYMENT_MODE=blue-green ./ops/deploy.sh deploy

# 3. Verify deployment
./ops/deploy.sh status
curl http://localhost:$(cat ops/active_port.txt)/health/ready
```

#### Rolling Deployment (Alternative)

```bash
# For minimal downtime scenarios
DEPLOYMENT_MODE=rolling ./ops/deploy.sh deploy
```

#### Emergency Rollback

```bash
# Immediate rollback to previous version
./ops/deploy.sh rollback

# Verify rollback success
./ops/deploy.sh status
```

#### Post-deployment Verification

1. Health checks pass: `curl /health/ready`
2. Authentication works: Test login
3. Core features functional: CRUD operations
4. Performance acceptable: Response times < 2s
5. Logs clean: No error spikes

#### Deployment Troubleshooting

- **Health check fails:** Check logs, database connectivity
- **Port conflicts:** Kill existing processes, check port availability
- **Permission errors:** Verify file permissions, user context
- **High error rates:** Monitor logs, consider rollback

---

## 3. 🚨 INCIDENT RESPONSE Runbook

### Severity Levels

- **Critical:** Application down, security breach
- **High:** Major feature broken, performance degraded
- **Medium:** Minor feature issues, warnings
- **Low:** Informational, maintenance needed

### Incident Response Process

#### 1. DETECTION (First 2 minutes)

```bash
# Check application status
curl http://localhost:8000/health/ready

# Check active alerts
python3 -c "
import sqlite3
conn = sqlite3.connect('ops/alerts.db')
alerts = conn.execute('SELECT * FROM alerts WHERE resolved=0').fetchall()
print(f'Active alerts: {len(alerts)}')
"

# Check recent logs
tail -50 ops/deploy.log
```

#### 2. ASSESSMENT (Next 3 minutes)

```bash
# Determine scope
./ops/deploy.sh status
python3 ops/backup.py  # Verify backup capability

# Check system resources
df -h  # Disk space
ps aux | grep python  # Process status
```

#### 3. IMMEDIATE RESPONSE (Next 5 minutes)

**If Application Down:**

```bash
# Quick restart attempt
./ops/deploy.sh cleanup
./ops/deploy.sh deploy

# If restart fails, rollback
./ops/deploy.sh rollback
```

**If Database Issues:**

```bash
# Check database connectivity
python3 -c "import sqlite3; sqlite3.connect('sme_erp_dev.db').execute('SELECT 1')"

# If corrupt, restore from backup
python3 ops/restore.py
```

**If Performance Issues:**

```bash
# Check for resource constraints
top
iotop  # If available

# Review recent changes
./ops/deploy.sh status
```

#### 4. RESOLUTION & COMMUNICATION

- Update stakeholders on status
- Document incident timeline
- Fix root cause
- Update monitoring/alerting

#### 5. POST-INCIDENT REVIEW

- Create incident report
- Update runbooks based on learnings
- Improve monitoring/alerting
- Schedule preventive measures

### Common Incident Scenarios

#### Scenario: Application Won't Start

```bash
# 1. Check port conflicts
lsof -i :8000 :8001

# 2. Check file permissions
ls -la app/

# 3. Check environment
cat .env.dev

# 4. Check dependencies
pip list | grep fastapi

# 5. Manual startup for debugging
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Scenario: High Error Rate

```bash
# 1. Check recent deployments
./ops/deploy.sh status

# 2. Review error logs
grep ERROR ops/deploy.log

# 3. Check database connectivity
python3 -c "from app.db.session import engine; engine.connect()"

# 4. Consider rollback
./ops/deploy.sh rollback
```

#### Scenario: Database Corruption

```bash
# 1. Stop application immediately
./ops/deploy.sh cleanup

# 2. Assess damage
sqlite3 sme_erp_dev.db "PRAGMA integrity_check;"

# 3. Restore from backup
python3 ops/restore.py

# 4. Restart application
./ops/deploy.sh deploy
```

---

## 4. 📊 MONITORING & ALERTING Runbook

### Health Check Monitoring

```bash
# Manual health check
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/startup

# Check metrics
curl http://localhost:8000/health/metrics
```

### Log Analysis

```bash
# View structured logs
tail -f ops/app_port_*.log | grep ERROR

# Search for patterns
grep "rate_limit_exceeded" ops/*.log
grep "authentication" ops/*.log
```

### Performance Monitoring

```bash
# Response time check
time curl http://localhost:8000/health/ready

# Database performance
sqlite3 sme_erp_dev.db "EXPLAIN QUERY PLAN SELECT * FROM users LIMIT 1"
```

### Alert Management

```bash
# View active alerts
python3 -c "
import sqlite3
conn = sqlite3.connect('ops/alerts.db')
conn.row_factory = sqlite3.Row
alerts = conn.execute('SELECT * FROM alerts WHERE resolved=0').fetchall()
for alert in alerts:
    print(f'{alert[\"severity\"]}: {alert[\"title\"]}')
"

# Resolve alert
python3 -c "
from app.core.alerts import alert_manager
alert_manager.resolve_alert('ALERT_ID')
"
```

---

## 5. 🔧 MAINTENANCE Runbook

### Weekly Maintenance

- [ ] Review backup success/failures
- [ ] Check disk space usage
- [ ] Review error logs
- [ ] Update dependencies (if needed)
- [ ] Test disaster recovery

### Monthly Maintenance

- [ ] Backup retention cleanup
- [ ] Performance review
- [ ] Security review
- [ ] Update documentation
- [ ] Disaster recovery drill

### Quarterly Maintenance

- [ ] Full security audit
- [ ] Performance optimization
- [ ] Infrastructure review
- [ ] Business continuity testing
- [ ] Staff training updates

---

## 6. 📞 EMERGENCY CONTACTS

### Escalation Matrix

1. **Level 1:** Development Team
2. **Level 2:** Technical Lead
3. **Level 3:** Infrastructure Team
4. **Level 4:** Management

### Contact Information

```
Technical Lead: [contact info]
Infrastructure: [contact info]
Management: [contact info]
Vendor Support: [contact info]
```

### Communication Channels

- **Slack:** #sme-erp-alerts
- **Email:** alerts@company.com
- **Phone:** Emergency hotline
- **Status Page:** status.company.com

---

## 7. 📝 DOCUMENTATION UPDATES

### After Each Incident

- Update relevant runbook sections
- Add new troubleshooting steps
- Document lessons learned
- Review escalation procedures

### Monthly Review

- Check runbook accuracy
- Update contact information
- Review and test procedures
- Gather team feedback

---

**Last Updated:** January 4, 2026  
**Next Review:** February 1, 2026  
**Version:** 1.0  
**Owner:** SRE Team
