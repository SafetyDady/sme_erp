# SME ERP - GOVERNANCE & CONTROL FRAMEWORK

## 🎯 **OVERVIEW**

This document establishes enterprise governance controls for SME ERP production operations, balancing comprehensive oversight with SME-appropriate lean processes.

**Governance Principles:**

- **Safety First:** All production changes must be controlled and traceable
- **Lean Process:** Minimal overhead while maintaining accountability
- **Evidence-Based:** Documentation that proves compliance and enables improvement
- **SME-Scaled:** Procedures appropriate for small-medium teams

---

## 🔐 **ACCESS GOVERNANCE**

### **Quarterly Access Review Cadence**

**Frequency:** Every quarter (Jan, Apr, Jul, Oct)  
**Owner:** IT Manager or designated Security Officer  
**Scope:** All elevated privileges (ADMIN, SUPER_ADMIN)

**Process:**

1. Generate current privilege report from system
2. Review each elevated account with business owner
3. Document justification for continued access
4. Remove/adjust permissions as needed
5. File signed review in governance folder

**Documentation:** See [ACCESS_REVIEW_TEMPLATE.md](ACCESS_REVIEW_TEMPLATE.md)

---

## 📋 **CHANGE MANAGEMENT**

### **Production Change Requirements**

All production changes (deployments, config updates, database migrations) **MUST** include:

**1. Ticket/Issue ID**

- Jira ticket, GitHub issue, or equivalent tracking number
- Business justification documented

**2. Code Review**

- At least 1 reviewer approval
- All CI checks passing (green build)

**3. Migration Safety**

- Database changes: dry-run checklist completed
- Rollback plan documented
- Deployment window scheduled

**4. Documentation Update**

- README, API docs, runbooks updated if applicable

**Documentation:** See [RUNBOOK_DEPLOYMENT.md](RUNBOOK_DEPLOYMENT.md)

---

## 🚨 **INCIDENT RESPONSE**

### **Incident Response Framework**

**1. Detection**

- Monitoring alerts
- User reports
- System health checks

**2. Containment**

- Stop the impact spread
- Preserve evidence
- Communicate status

**3. Recovery**

- Execute recovery runbook
- Verify system stability
- Monitor for recurrence

**4. Post-Mortem**

- Document root cause
- Identify improvement actions
- Update runbooks

**Critical Scenarios:**

- Database replica down
- Export worker stuck/overwhelmed
- Elevated error rates
- Authentication system failure

**Documentation:** See [RUNBOOK_INCIDENT.md](RUNBOOK_INCIDENT.md)

---

## 📊 **DATA GOVERNANCE**

### **Data Retention Policy**

**Audit Logs:**

- Retention: 3 years for compliance
- Archival: Annual compression to long-term storage
- Access: Read-only after 1 year

**Export Jobs & Files:**

- Active files: 7 days (auto-cleanup)
- Job metadata: 90 days for analysis
- Large export retention: Business owner approval required

**Inventory/Financial Data:**

- Transaction ledger: 7 years (legal requirement)
- Inventory snapshots: 2 years
- User activity: 1 year

**Documentation:** See [DATA_RETENTION_POLICY.md](DATA_RETENTION_POLICY.md)

---

## 🔍 **AUDIT & COMPLIANCE**

### **Evidence Management**

**Required Documentation:**

- [ ] Quarterly access reviews with signatures
- [ ] Production change logs with approvals
- [ ] Incident response drill evidence
- [ ] Data retention compliance reports

**Audit Trail Requirements:**

- All privileged actions logged
- Change approvals preserved
- Access review results filed
- Incident drill outcomes documented

---

## 🏃 **IMPLEMENTATION ROADMAP**

### **Phase 1: Foundation (Week 1)**

- [ ] Deploy runbooks and policies
- [ ] Conduct first incident drill
- [ ] Complete template access review

### **Phase 2: Integration (Week 2)**

- [ ] Integrate change controls with CI/CD
- [ ] Train team on new procedures
- [ ] Establish monitoring for policy compliance

### **Phase 3: Maturity (Ongoing)**

- [ ] Quarterly access reviews
- [ ] Annual policy review and updates
- [ ] Continuous drill and improvement cycles

---

## 📞 **CONTACTS & RESPONSIBILITIES**

**Governance Owner:** IT Manager  
**Security Officer:** [Designated Person]  
**Change Approver:** Technical Lead  
**Incident Commander:** On-call Engineer

**Escalation Path:**

1. Technical Lead
2. IT Manager
3. Business Owner
4. External Support (if contracted)

---

## 🌐 **PUBLIC ENDPOINT EXPOSURE POLICY**

### **Health Check Endpoints (Public Access)**

The following endpoints are intentionally exposed without authentication for operational monitoring:

#### **🟢 Public (Load Balancer / Monitoring)**

- `GET /health` - Basic application health
- `GET /health/live` - Liveness probe for container orchestration
- `GET /health/ready` - Readiness probe for traffic routing

#### **🟡 Internal (Network-Restricted Recommended)**

- `GET /health/database` - Database connectivity status
- `GET /health/metrics` - Performance metrics
- `GET /health/startup` - Startup validation checks
- `GET /health/stateless` - Architecture validation
- `GET /health/scaling` - Scaling readiness status
- `GET /health/lb` - Load balancer health

**Rationale**: Health endpoints enable external monitoring systems to assess application status without authentication overhead. Internal endpoints may expose configuration details and should be restricted at network level.

**Security Consideration**: Health endpoints do not expose sensitive business data but may reveal system architecture details.

---

## 📋 **QUICK REFERENCE**

**Emergency Contacts:** See RUNBOOK_INCIDENT.md  
**Change Checklist:** See RUNBOOK_DEPLOYMENT.md  
**Access Review:** See ACCESS_REVIEW_TEMPLATE.md  
**Data Policies:** See DATA_RETENTION_POLICY.md

**Last Updated:** January 2026  
**Next Review:** April 2026  
**Version:** 1.0
