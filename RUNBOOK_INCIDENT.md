# INCIDENT RESPONSE RUNBOOK

## 🚨 **INCIDENT CLASSIFICATION & RESPONSE**

### **Severity Levels**

#### **🔥 CRITICAL (P1) - Response: 15 minutes**

- **Definition:** Complete system outage, data corruption, security breach
- **Examples:** Database down, authentication failing, data loss
- **Response Team:** All hands on deck
- **Communication:** Immediate stakeholder notification

#### **⚠️ HIGH (P2) - Response: 1 hour**

- **Definition:** Major feature degradation, performance issues
- **Examples:** Slow reports, export jobs failing, partial outages
- **Response Team:** Technical lead + on-call
- **Communication:** Hourly updates to stakeholders

#### **📝 MEDIUM (P3) - Response: 4 hours**

- **Definition:** Minor feature issues, non-critical bugs
- **Examples:** UI glitches, minor data inconsistencies
- **Response Team:** Assigned developer
- **Communication:** Daily progress updates

#### **📋 LOW (P4) - Response: 1 business day**

- **Definition:** Enhancement requests, cosmetic issues
- **Examples:** Typos, nice-to-have features
- **Response Team:** Product backlog
- **Communication:** Sprint planning updates

---

## 📞 **INCIDENT RESPONSE TEAM**

### **Roles & Responsibilities**

#### **🎯 Incident Commander**

- **Primary:** Technical Lead
- **Backup:** IT Manager
- **Responsibilities:**
  - Declare incident severity
  - Coordinate response team
  - Communicate with stakeholders
  - Make go/no-go decisions

#### **🔧 Technical Response**

- **Primary:** Senior Developer
- **Backup:** IT Manager
- **Responsibilities:**
  - Investigate root cause
  - Implement fixes/workarounds
  - Monitor system recovery
  - Document technical details

#### **📢 Communications Lead**

- **Primary:** Business Owner
- **Backup:** Office Manager
- **Responsibilities:**
  - Update internal stakeholders
  - Manage customer communications
  - Coordinate with external vendors
  - Document business impact

#### **📊 Support & Documentation**

- **Primary:** Any available team member
- **Backup:** External contractor
- **Responsibilities:**
  - Gather logs and evidence
  - Execute runbook procedures
  - Coordinate with vendors
  - Maintain incident timeline

---

## ⚡ **QUICK REFERENCE - COMMON INCIDENTS**

### **🗄️ Database Issues**

#### **Database Connection Failures**

```bash
# Quick diagnosis
sudo docker-compose logs postgres | tail -50
sudo docker-compose exec postgres psql -c "SELECT 1;"

# If postgres down:
sudo docker-compose restart postgres

# If connection limit hit:
sudo docker-compose exec postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Emergency rollback point
sudo docker-compose exec postgres pg_dump sme_erp > emergency_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### **Read-Replica Down**

```bash
# Check replica status
curl http://localhost:8000/health/database | jq '.read_replica'

# Manual failover to primary
# Update config: READ_REPLICA_URL -> DATABASE_URL
sudo docker-compose restart app

# Verify failover
curl http://localhost:8000/health/database
```

#### **Database Corruption**

```bash
# STOP application immediately
sudo docker-compose stop app

# Assess damage
sudo docker-compose exec postgres pg_dump sme_erp > corruption_assessment.sql

# Contact: Database specialist or restore from backup
# DO NOT attempt repairs without expert consultation
```

---

### **🖥️ Application Issues**

#### **Application Won't Start**

```bash
# Check logs
sudo docker-compose logs app | tail -100

# Common fixes:
# 1. Configuration issue
sudo docker-compose exec app cat /app/.env

# 2. Database migration needed
sudo docker-compose exec app alembic upgrade head

# 3. Permission issues
sudo docker-compose exec app ls -la /app

# 4. Dependency conflicts
sudo docker-compose exec app pip list
```

#### **Memory/Performance Issues**

```bash
# Check resource usage
sudo docker stats

# Check application metrics
curl http://localhost:8000/health | jq '.metrics'

# Emergency restart (if critical)
sudo docker-compose restart app

# Scale horizontally (if configured)
sudo docker-compose -f docker-compose.scale.yml up -d --scale app=3
```

#### **Authentication Failing**

```bash
# Check JWT configuration
curl -H "Authorization: Bearer invalid_token" http://localhost:8000/api/v1/auth/verify

# Check user database
sudo docker-compose exec postgres psql sme_erp -c "SELECT id, username, is_active FROM users LIMIT 5;"

# Reset admin password (emergency access)
sudo docker-compose exec app python -c "
from app.core.auth.password import hash_password
print('Admin reset hash:', hash_password('TempPassword123!'))
"
```

---

### **🌐 Infrastructure Issues**

#### **Load Balancer Down**

```bash
# Check nginx status
sudo systemctl status nginx

# Check configuration
sudo nginx -t

# Emergency direct access
curl http://localhost:8000/health

# Restart load balancer
sudo systemctl restart nginx
```

#### **Disk Space Full**

```bash
# Quick space check
df -h

# Emergency cleanup
sudo docker system prune -f
sudo rm -rf /tmp/*
sudo journalctl --vacuum-time=1d

# Find large files
du -sh /* | sort -hr | head -10
```

#### **Network Issues**

```bash
# Check external connectivity
curl -I https://google.com

# Check internal connectivity
curl -I http://localhost:8000/health

# Check DNS resolution
nslookup google.com

# Check port availability
netstat -tulpn | grep :8000
```

---

## 🔍 **TROUBLESHOOTING TOOLS**

### **Log Collection**

```bash
# Application logs
sudo docker-compose logs app --tail=200 > incident_app_logs.txt

# Database logs
sudo docker-compose logs postgres --tail=200 > incident_db_logs.txt

# System logs
sudo journalctl -u docker --since="1 hour ago" > incident_system_logs.txt

# nginx logs (if applicable)
sudo tail -200 /var/log/nginx/error.log > incident_nginx_logs.txt
```

### **System Diagnostics**

```bash
# Resource usage snapshot
sudo docker stats --no-stream > incident_resources.txt
free -h >> incident_resources.txt
df -h >> incident_resources.txt

# Network connectivity
netstat -tulpn > incident_network.txt
ss -tulpn >> incident_network.txt

# Process status
ps aux | head -20 > incident_processes.txt
```

### **Database Diagnostics**

```bash
# Database status
sudo docker-compose exec postgres psql sme_erp -c "
SELECT
    datname as database,
    numbackends as connections,
    xact_commit as commits,
    xact_rollback as rollbacks
FROM pg_stat_database
WHERE datname = 'sme_erp';
" > incident_db_status.txt

# Table sizes
sudo docker-compose exec postgres psql sme_erp -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
" > incident_table_sizes.txt
```

---

## 📋 **INCIDENT RECORD TEMPLATE**

```
INCIDENT ID: INC-YYYY-MM-DD-XXX
SEVERITY: [ ] P1 [ ] P2 [ ] P3 [ ] P4
START TIME: _____________
END TIME: _____________
DURATION: _____________

DESCRIPTION:
_________________________________

IMPACT:
□ System down completely
□ Features degraded
□ Performance issues
□ Data integrity concerns
□ Security implications

AFFECTED SERVICES:
□ Authentication
□ Inventory Management
□ Reporting
□ Data Exports
□ Database
□ Load Balancer

ROOT CAUSE:
_________________________________

RESOLUTION ACTIONS:
1. _____________________________
2. _____________________________
3. _____________________________

WORKAROUNDS USED:
_________________________________

INCIDENT COMMANDER: _____________
TECHNICAL LEAD: _________________
COMMUNICATIONS: _________________

POST-INCIDENT ACTIONS:
□ Root cause analysis completed
□ Prevention measures identified
□ Documentation updated
□ Team retrospective scheduled
```

---

## 🔄 **INCIDENT DRILL SCENARIOS**

### **Drill #1: Database Replica Failure**

#### **Scenario Setup**

```bash
# Simulate read-replica failure
sudo docker-compose stop postgres-replica
```

#### **Expected Response**

1. **Detection:** Health check alerts (< 5 minutes)
2. **Assessment:** Identify replica down via monitoring
3. **Response:** Failover to primary database
4. **Communication:** Internal team notification
5. **Recovery:** Restore replica service

#### **Success Criteria**

- [ ] Incident detected within 5 minutes
- [ ] Failover completed within 15 minutes
- [ ] Export functionality maintained
- [ ] No data loss occurred
- [ ] Incident properly documented

### **Drill #2: Application Memory Exhaustion**

#### **Scenario Setup**

```bash
# Simulate memory leak
sudo docker-compose exec app python -c "
data = []
for i in range(1000000):
    data.append('memory_leak_simulation' * 1000)
"
```

#### **Expected Response**

1. **Detection:** High memory alerts
2. **Assessment:** Identify resource exhaustion
3. **Response:** Restart application containers
4. **Communication:** User notification of brief downtime
5. **Recovery:** Monitor for recurrence

#### **Success Criteria**

- [ ] Memory issue detected via monitoring
- [ ] Service restored within 10 minutes
- [ ] Root cause investigation initiated
- [ ] Prevention measures discussed

---

## 📞 **EMERGENCY CONTACT LIST**

**Technical Lead:** xxx-xxxx (Primary)  
**IT Manager:** xxx-xxxx (Secondary)  
**Business Owner:** xxx-xxxx (Stakeholder)  
**Office Manager:** xxx-xxxx (Communications)

**External Support:**

- **ISP Support:** xxx-xxxx
- **Cloud Provider:** xxx-xxxx (if applicable)
- **Database Specialist:** xxx-xxxx (consultant)

**Last Updated:** January 2026  
**Next Review:** April 2026  
**Next Drill Date:** February 2026
