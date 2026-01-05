# Acceptance Criteria - Production RBAC System

## Authentication Requirements

### ✅ Token Validation

- [ ] Invalid/expired token → **401 Unauthorized**
- [ ] Missing Authorization header → **401 Unauthorized**
- [ ] Malformed token → **401 Unauthorized**
- [ ] Valid token but insufficient role → **403 Forbidden**

### ✅ Role-Based Access Control Matrix

| Endpoint                     | VIEWER | STAFF  | ADMIN  | SUPER_ADMIN |
| ---------------------------- | ------ | ------ | ------ | ----------- |
| GET /inventory/items         | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200      |
| GET /inventory/stock         | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200      |
| POST /inventory/items        | ❌ 403 | ✅ 200 | ✅ 200 | ✅ 200      |
| POST /inventory/tx           | ❌ 403 | ✅ 200 | ✅ 200 | ✅ 200      |
| POST /inventory/locations    | ❌ 403 | ❌ 403 | ✅ 200 | ✅ 200      |
| PUT /inventory/items/{id}    | ❌ 403 | ❌ 403 | ✅ 200 | ✅ 200      |
| DELETE /inventory/items/{id} | ❌ 403 | ❌ 403 | ✅ 200 | ✅ 200      |

## Security Requirements

### ✅ JWT Implementation

- [ ] Tokens contain valid `sub` claim (user ID)
- [ ] Token expiration is enforced
- [ ] Access tokens cannot be used as refresh tokens
- [ ] User roles are fetched from database (not just token)
- [ ] Inactive users are rejected

### ✅ Error Handling

- [ ] No sensitive information leaked in error messages
- [ ] Consistent error format across all endpoints
- [ ] 401 vs 403 distinction is clear and correct
- [ ] Rate limiting prevents brute force attacks

## Database Integration

### ✅ User Management

- [ ] Users exist in database with proper roles
- [ ] Role changes take effect immediately
- [ ] Inactive users cannot authenticate
- [ ] Password hashing is secure (bcrypt/argon2)

## Testing Requirements

### ✅ Test Coverage

- [ ] pytest runs successfully with 100% RBAC coverage
- [ ] All role combinations tested for each endpoint
- [ ] Authentication failure scenarios covered
- [ ] Integration tests use real database (not mocked)

### ✅ CI/CD Ready

- [ ] Tests can run in automated environment
- [ ] No hardcoded credentials in test code
- [ ] Test database setup/teardown is automated
- [ ] Test results are deterministic and repeatable

## Production Readiness

### ✅ Code Quality

- [ ] No demo/mock code in production paths
- [ ] Clear separation between examples and production
- [ ] Consistent import paths and dependencies
- [ ] Error logging for security events

### ✅ Documentation

- [ ] API documentation shows required roles for each endpoint
- [ ] Swagger UI Authorize button works correctly
- [ ] README contains correct production commands
- [ ] Security guidelines documented for developers

## Performance Requirements

### ✅ Scalability

- [ ] Database queries are optimized (no N+1 problems)
- [ ] JWT verification doesn't hit database unnecessarily
- [ ] Role checking is efficient
- [ ] Response times < 200ms for simple endpoints

---

## Definition of Done

**All checkboxes must be ✅ before considering RBAC production-ready.**

**Critical Path:**

1. pytest test_rbac_inventory.py passes 100%
2. Manual testing via Swagger UI confirms matrix
3. Security review confirms no bypass vulnerabilities
4. Performance testing shows acceptable response times
