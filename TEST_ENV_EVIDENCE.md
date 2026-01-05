# Test Environment Evidence v1.0.5

## Dependency Versions

```
FastAPI: 0.115.6
Starlette: 0.41.3
HTTPX: 0.28.1
Pytest: 9.0.2
SQLAlchemy: 2.0.36
Pydantic: 2.10.3
```

## Pytest Test Run Results

**Date:** 2026-01-05  
**Command:** `JWT_SECRET_KEY="test-key" DATABASE_URL="sqlite:///./test.db" ENVIRONMENT="test" pytest tests/ -q`

### Test Status

- Total Tests: 68
- Passed: 36 tests (52.9%)
- Failed: 32 tests (47.1%)
- Warnings: 19

### Key Failures Detected

#### 1. Authentication Token Issues

Multiple tests failing with `KeyError` for auth tokens (admin, staff, viewer):

- `test_rbac_inventory.py`: 14 failures with empty `auth_tokens = {}` fixture
- `test_user_management_api.py`: 7 failures with authentication dependency issues

#### 2. Dependency Injection Error

Critical issue in `/app/api/v1/users/router.py:80`:

```
AttributeError: 'function' object has no attribute 'role'
```

The `current_user` parameter is receiving a function instead of a User object.

#### 3. Async Test Configuration

5 async tests failing with "async def functions are not natively supported":

- `test_ci_audit_compliance.py`: 5 async tests
- `test_ci_rbac_matrix.py`: 3 async tests

#### 4. Database Table Missing

`sqlite3.OperationalError: no such table: users` in some auth gate tests.

### Version Compatibility Assessment

- **HTTPX 0.28.1**: No specific "unexpected keyword argument 'app'" errors detected
- **Pytest 9.0.2**: Async test configuration issues identified
- **TestClient Pattern**: Working correctly (resolved in v1.0.4)

### Recommendations

1. Fix dependency injection in user router
2. Resolve auth_tokens fixture to properly authenticate test users
3. Configure pytest-asyncio for async test support
4. Ensure database tables are created in test setup

### Evidence Timestamp

Generated at `2026-01-05 05:26:40 UTC` during version compatibility testing.
