# Session Context - SME ERP Authentication & RBAC

## Current Status: RBAC Production Ready ✅

**Authentication System:**

- ✅ JWT + SQLAlchemy user authentication integrated
- ✅ Role-based access control (VIEWER/STAFF/ADMIN/SUPER_ADMIN)
- ✅ OAuth2 scheme registered for Swagger UI

**Files Status:**

- ✅ `app/main.py` - Production app with real auth
- ✅ `app/core/auth/deps.py` - RBAC functions integrated
- ✅ `app/api/v1/inventory/router.py` - Protected with RBAC
- 🔄 `examples/demo_main_rbac.py` - Demo moved out of main path
- 🔄 `tests/test_rbac_inventory.py` - Production pytest matrix

## Current Goal: Validate Production RBAC

**Immediate Tasks:**

1. Run pytest RBAC matrix tests
2. Fix any authentication/role permission issues
3. Verify 401 vs 403 error handling is correct

## Next Phase:

- Security audit of JWT implementation
- Performance testing with database load
- CI/CD integration for automated testing

## Constraints & Don'ts:

- ❌ No mock authentication in production tests
- ❌ No hardcoded passwords in production code
- ❌ No confusion between demo and production files
- ❌ No bypass of role permission checks

## Production Commands:

```bash
# Run production app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run RBAC tests
pytest tests/test_rbac_inventory.py -v

# Demo only (if needed)
python -m uvicorn examples.demo_main_rbac:app --port 8002
```
