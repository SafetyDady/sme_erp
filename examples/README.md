# Demo Files (Mock/Testing Only)

⚠️ **WARNING: These files are for DEMONSTRATION ONLY**

## Files in this directory:

### `demo_main_rbac.py`

- **Purpose**: RBAC concept demonstration with mock users
- **Users**: Mock credentials (admin@sme-erp.com/admin123, etc.)
- **Tokens**: Fake JWT tokens for testing
- **Usage**: `python -m uvicorn examples.demo_main_rbac:app --port 8002`

### `test_rbac_demo.py`

- **Purpose**: Manual testing script for demo app
- **Target**: Points to localhost:8002 (demo app)
- **Usage**: `python examples/test_rbac_demo.py`

## ❌ DO NOT USE IN PRODUCTION

These files use:

- Mock authentication
- Hardcoded passwords
- Fake tokens
- No database validation

## ✅ Production Files

Use these instead:

- **Main App**: `app/main.py` (real JWT + DB)
- **Tests**: `tests/test_rbac_*.py` (pytest with real auth)
- **Run**: `python -m uvicorn app.main:app --port 8000`
