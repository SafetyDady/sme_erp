# DEPLOYMENT RUNBOOK

## 🚀 **PRODUCTION DEPLOYMENT PROCEDURES**

### **PRE-DEPLOYMENT CHECKLIST**

**📋 Required Before ANY Production Change:**

#### **1. Change Authorization**

- [ ] **Ticket ID:** <CHANGE_REQUEST_ID> (GitHub issue/internal ticket)
- [ ] **Business Justification:** Documented in ticket
- [ ] **Change Approver:** <APPROVER_NAME> (Name + Date)
- [ ] **Deployment Window:** <SCHEDULED_TIME> (Scheduled time)

#### **2. Code Quality Gates**

- [ ] **CI Build Status:** ✅ All checks passing
- [ ] **Code Review:** At least 1 approval from technical lead
- [ ] **Security Scan:** No high/critical vulnerabilities
- [ ] **Test Coverage:** Maintained or improved

#### **3. Database Safety (if applicable)**

- [ ] **Migration Dry-Run:** Tested on staging database
- [ ] **Data Backup:** Recent backup verified (< 24h old)
- [ ] **Rollback Script:** Prepared and tested
- [ ] **Migration Time:** Estimated duration documented

#### **4. Dependencies Check**

- [ ] **External Services:** Status confirmed healthy
- [ ] **Configuration:** Environment variables reviewed
- [ ] **Secrets:** Updated/rotated if needed
- [ ] **Resource Capacity:** CPU/Memory/Disk sufficient

---

## 🔄 **DEPLOYMENT EXECUTION**

### **Standard Deployment Steps**

#### **Phase 1: Preparation**

```bash
# 1. Connect to production environment
cd /workspaces/sme_erp/backend

# 2. Verify current system status
python -c "from app.api.health import health_check; print(health_check())"

# 3. Create deployment backup point
sudo docker-compose exec postgres pg_dump sme_erp > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### **Phase 2: Application Update**

```bash
# 1. Pull latest approved code
git fetch origin
git checkout <APPROVED_TAG>

# 2. Update dependencies
pip install -r requirements.txt

# 3. Run database migrations (if any)
alembic upgrade head

# 4. Restart services with health checks
sudo docker-compose restart app
```

#### **Phase 3: Verification**

```bash
# 1. Health check validation
curl -f http://localhost:8000/health || echo "❌ Health check failed"

# 2. Database connectivity test
curl -f http://localhost:8000/health/database || echo "❌ DB health failed"

# 3. Authentication test
curl -f http://localhost:8000/api/v1/auth/verify || echo "ℹ️ Auth endpoint check"

# 4. Key business function test
curl -f http://localhost:8000/api/v1/inventory/items?limit=1 || echo "❌ Business function failed"
```

---

## 🐳 **CONTAINER DEPLOYMENT**

### **Multi-Instance Deployment (Production)**

```bash
# 1. Deploy with scaling
sudo docker-compose -f docker-compose.scale.yml up -d

# 2. Verify all instances healthy
sudo docker-compose -f docker-compose.scale.yml ps

# 3. Load balancer health check
curl -f http://localhost/health || echo "❌ Load balancer failed"

# 4. Database replica status
curl -f http://localhost/health/database
```

### **Database Replica Deployment**

```bash
# 1. Deploy with read-replica
sudo docker-compose -f docker-compose.replica.yml up -d

# 2. Verify replica connectivity
curl -f http://localhost/health/database | jq '.read_replica'

# 3. Test export functionality (uses replica)
curl -X POST http://localhost/api/v1/exports/jobs \
     -H "Authorization: Bearer <ADMIN_TOKEN>" \
     -d '{"job_type": "csv_inventory_snapshot", "parameters": {}}'
```

---

## ❌ **ROLLBACK PROCEDURES**

### **Emergency Rollback**

#### **If Application Issues:**

```bash
# 1. Rollback to previous version
git checkout <PREVIOUS_STABLE_TAG>
sudo docker-compose restart app

# 2. Verify rollback success
curl -f http://localhost:8000/health
```

#### **If Database Issues:**

```bash
# 1. Stop application
sudo docker-compose stop app

# 2. Restore database backup
sudo docker-compose exec postgres psql sme_erp < backup_YYYYMMDD_HHMMSS.sql

# 3. Restart with previous version
git checkout <PREVIOUS_STABLE_TAG>
sudo docker-compose up -d
```

#### **If Total System Failure:**

```bash
# 1. Emergency contact list
echo "Contact: IT Manager - xxx-xxxx"
echo "Contact: Technical Lead - xxx-xxxx"
echo "Contact: Business Owner - xxx-xxxx"

# 2. Document incident
echo "Incident started: $(date)" >> incident_log.txt
echo "Actions taken:" >> incident_log.txt

# 3. Execute disaster recovery
# (Follow RUNBOOK_INCIDENT.md)
```

---

## 📊 **POST-DEPLOYMENT VALIDATION**

### **Performance Validation**

```bash
# 1. Response time check
curl -w "Response time: %{time_total}s\n" -s -o /dev/null http://localhost:8000/health

# 2. Database performance
time curl -s http://localhost:8000/health/database > /dev/null

# 3. Load test (optional for major changes)
# ab -n 100 -c 10 http://localhost:8000/api/v1/inventory/items
```

### **Business Function Validation**

- [ ] **User Login:** Admin can authenticate
- [ ] **Inventory Access:** Items can be viewed/created
- [ ] **Reports:** Sync reports work
- [ ] **Exports:** Async exports can be submitted
- [ ] **Audit:** Actions are being logged

---

## 📋 **DEPLOYMENT RECORD TEMPLATE**

**Deployment ID:** DEP-YYYY-MM-DD-XXX  
**Deployed By:** <DEPLOYING_ENGINEER>  
**Deployment Date/Time:** <DEPLOYMENT_TIMESTAMP>  
**Git Commit/Tag:** <GIT_COMMIT_HASH>

**Changes Deployed:**

- Feature/Fix 1: <CHANGE_DESCRIPTION_1>
- Feature/Fix 2: <CHANGE_DESCRIPTION_2>

**Validation Results:**

- [ ] Health checks: PASS/FAIL
- [ ] Performance: PASS/FAIL
- [ ] Business functions: PASS/FAIL

**Issues Encountered:**

---

**Rollback Executed:** YES/NO  
**Sign-off:** <TECHNICAL_LEAD_SIGNATURE> (Technical Lead)

---

## 🚨 **EMERGENCY PROCEDURES**

### **Critical System Down**

1. **STOP** - Don't make it worse
2. **ASSESS** - Check logs, monitoring, user reports
3. **CONTAIN** - Isolate the problem
4. **COMMUNICATE** - Update stakeholders
5. **RECOVER** - Execute appropriate runbook
6. **DOCUMENT** - Record everything for post-mortem

### **Escalation Matrix**

**Level 1:** Technical Lead (Response: 15 min)  
**Level 2:** IT Manager (Response: 30 min)  
**Level 3:** Business Owner (Response: 1 hour)  
**Level 4:** External Support (If contracted)

---

**Last Updated:** January 2026  
**Next Review:** April 2026  
**Owner:** Technical Lead
