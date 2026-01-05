# SME ERP Authentication System

Enterprise Resource Planning system for Small and Medium Enterprises with complete OAuth2 authentication.

## Features

- 🔐 **OAuth2 Password Flow** - Swagger UI Authorize button support
- 🔑 **JWT Authentication** - Access & Refresh tokens
- 👥 **Role-based Access Control** - Super Admin, Admin, Staff, Viewer
- 🔒 **Password Hashing** - Secure bcrypt password storage
- 🛡️ **Protected Endpoints** - All inventory routes require authentication
- ⚙️ **User Management** - Admin-only user registration and management
- 📱 **Profile Management** - Get and update user profiles

## Quick Start

### 1. Install Dependencies

```bash
cd /workspaces/sme_erp/backend
pip install -r requirements.txt
```

### 2. Create Admin User

```bash
python /workspace/backend/create_admin.py
```

### 3. Run the Application

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Access API Documentation

Visit: `http://localhost:8001/docs`

**🚀 Look for the "Authorize" button in the top-right corner!**

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - OAuth2 compatible login (Swagger UI support)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user profile
- `POST /api/v1/auth/register` - Register new user (admin only)

### Protected Inventory

- `GET /api/v1/inventory/items` - Get inventory items (requires login)
- `POST /api/v1/inventory/items` - Create inventory item (requires staff+ role)

## Default Admin Credentials

```
Email: admin@sme-erp.com
Password: admin123
Role: SUPER_ADMIN
```

⚠️ **Please change the admin password after first login!**

## Environment Variables

Create a `.env` file in the backend directory:

```env
JWT_SECRET_KEY=your_super_secret_jwt_key_change_this_in_production_make_it_very_long_and_random
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14
DATABASE_URL=sqlite:///./sme_erp.db
```

## Using the API

### 1. Login via Swagger UI

1. Visit `http://localhost:8001/docs`
2. Click **"Authorize"** button (🔓) in top-right corner
3. Enter credentials:
   - **Username**: `admin@sme-erp.com`
   - **Password**: `admin123`
4. Click **"Authorize"**
5. Try protected endpoints - they'll now work with authentication!

### 2. Login via curl

```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@sme-erp.com&password=admin123"
```

Response:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 3. Access protected endpoints

```bash
curl -X GET "http://localhost:8001/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

```bash
curl -X GET "http://localhost:8001/api/v1/inventory/items" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application with OAuth2
│   ├── core/
│   │   ├── config.py           # App configuration with JWT settings
│   │   └── auth/
│   │       ├── security.py     # Password hashing utilities
│   │       ├── jwt.py          # JWT token creation/validation
│   │       └── deps.py         # OAuth2 dependencies & role checking
│   ├── db/
│   │   ├── session.py          # Database session management
│   │   └── base.py             # Base for Alembic migrations
│   ├── api/
│   │   └── v1/
│   │       ├── router.py       # Main API v1 router
│   │       ├── auth/
│   │       │   └── router.py   # Authentication endpoints
│   │       └── inventory/
│   │           └── router.py   # Protected inventory endpoints
│   └── modules/
│       └── users/
│           ├── models.py       # User SQLAlchemy model with roles
│           └── schemas.py      # Pydantic schemas with tokens
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (JWT secrets)
└── create_admin.py            # Admin user creation script
```

## User Roles

- **🔴 SUPER_ADMIN** - Full system access, can manage all users
- **🟠 ADMIN** - Can manage users and access all features
- **🟡 STAFF** - Can create/modify inventory items
- **🟢 VIEWER** - Read-only access to inventory

## Security Features

- **🔐 OAuth2 Password Flow** - Standard OAuth2 implementation for Swagger UI
- **🔑 JWT Access & Refresh Tokens** - Secure token-based authentication
- **🔒 Password Hashing** - Using bcrypt for secure password storage
- **👥 Role-based Access Control** - Fine-grained permissions by user role
- **⏰ Token Expiration** - Configurable access (60min) and refresh (14 days) token expiry
- **🛡️ Input Validation** - Pydantic schemas for request validation
- **🔍 Protected Endpoints** - All sensitive operations require authentication

## Development

### Running with Auto-reload

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Testing Authentication

1. **Open Swagger UI**: http://localhost:8001/docs
2. **See Authorize button**: 🔓 (top-right corner)
3. **Login with admin**: admin@sme-erp.com / admin123
4. **Test protected endpoints**: Try `/inventory/items`
5. **Check lock icons**: 🔒 on protected endpoints

### Database Management

- **SQLite Default**: Database auto-created at `sme_erp.db`
- **Production**: Set `DATABASE_URL` environment variable
- **Migrations**: Use Alembic for schema changes

## Troubleshooting

### No Authorize Button?

- Ensure `OAuth2PasswordBearer` is properly imported
- Check that `tokenUrl` points to correct login endpoint
- Verify at least one endpoint uses the oauth2_scheme dependency

### 401 Unauthorized?

- Check token expiration (60 minutes default)
- Verify Bearer token format in Authorization header
- Use `/auth/refresh` endpoint to get new access token

### Role Permission Denied?

- Check user role in database
- Verify role requirements for specific endpoints
- Super Admin has access to all endpoints
