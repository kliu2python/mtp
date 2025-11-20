# Authentication & User Management Guide

This guide explains how to use the authentication system in Mobile Test Pilot, which supports both **Local User Authentication** and **SAML Single Sign-On (SSO)**.

## Table of Contents

1. [Overview](#overview)
2. [Local User Authentication](#local-user-authentication)
3. [SAML Authentication](#saml-authentication)
4. [API Endpoints](#api-endpoints)
5. [Configuration](#configuration)
6. [Frontend Integration](#frontend-integration)

---

## Overview

Mobile Test Pilot now includes a complete user management and authentication system that supports:

- **Local Authentication**: Username/password-based authentication with JWT tokens
- **SAML SSO**: Enterprise single sign-on integration with identity providers like Okta, Azure AD, Auth0, etc.
- **Role-Based Access Control**: Admin, User, and Viewer roles
- **Account Security**: Password hashing with bcrypt, account locking after failed attempts
- **Session Management**: JWT-based stateless authentication

### User Roles

- **Admin**: Full access to all features, can manage users and system settings
- **User**: Can create and run tests, view results
- **Viewer**: Read-only access to test results and dashboards

---

## Local User Authentication

### Registration

Register a new user account:

**Endpoint**: `POST /api/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "SecurePassword123!",
  "full_name": "Test User"
}
```

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "testuser",
  "full_name": "Test User",
  "auth_provider": "local",
  "role": "user",
  "is_active": true,
  "is_superuser": false,
  "permissions": [],
  "last_login": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### Login

Authenticate with username and password to receive a JWT token:

**Endpoint**: `POST /api/auth/login` (OAuth2 form)

**Form Data**:
```
username=testuser
password=SecurePassword123!
```

**Alternative Endpoint**: `POST /api/auth/login/json` (JSON payload)

**Request Body**:
```json
{
  "username": "testuser",
  "password": "SecurePassword123!"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "testuser",
    "role": "user",
    ...
  }
}
```

### Using the JWT Token

Include the JWT token in the `Authorization` header for all authenticated requests:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/auth/me
```

### Get Current User

**Endpoint**: `GET /api/auth/me`

**Headers**: `Authorization: Bearer {token}`

**Response**: Current user profile

### Update Profile

**Endpoint**: `PUT /api/auth/me`

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name"
}
```

### Change Password

**Endpoint**: `POST /api/auth/change-password`

**Headers**: `Authorization: Bearer {token}`

**Request Body**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

### Account Security

- Passwords are hashed using bcrypt
- After 5 failed login attempts, accounts are locked for 30 minutes
- Password requirements: minimum 8 characters
- Username requirements: 3-50 alphanumeric characters (underscores and hyphens allowed)

---

## SAML Authentication

SAML SSO allows users to authenticate using your organization's identity provider (IdP) like Okta, Azure AD, Auth0, etc.

### SAML Configuration

1. **Configure Environment Variables**:

   Edit `.env` file with your SAML IdP details:

   ```bash
   SAML_SP_BASE_URL=https://yourdomain.com
   SAML_SP_ENTITY_ID=https://yourdomain.com/api/saml/metadata
   SAML_IDP_ENTITY_ID=https://your-idp.com/entity-id
   SAML_IDP_SSO_URL=https://your-idp.com/sso
   SAML_IDP_SLO_URL=https://your-idp.com/slo
   SAML_IDP_CERT="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
   ```

2. **Get SP Metadata**:

   **Endpoint**: `GET /api/saml/metadata`

   Download the Service Provider metadata XML and upload it to your IdP.

3. **Test SAML Configuration**:

   **Endpoint**: `GET /api/saml/test`

   Check if SAML is configured correctly:

   ```json
   {
     "saml_enabled": true,
     "configured": true,
     "sp_entity_id": "https://yourdomain.com/api/saml/metadata",
     "idp_entity_id": "https://your-idp.com/entity-id",
     "missing_config": []
   }
   ```

### SAML Login Flow

1. **Initiate SAML Login**:

   **Endpoint**: `GET /api/saml/login?relay_state=https://yourdomain.com/dashboard`

   - Redirects user to IdP login page
   - `relay_state` is the URL to redirect after successful login

2. **SAML Assertion Consumer Service (ACS)**:

   **Endpoint**: `POST /api/saml/acs`

   - IdP posts SAML response here after authentication
   - System validates response and creates/updates user
   - Returns JWT token or redirects to `relay_state` with token

3. **SAML Logout**:

   **Endpoint**: `GET /api/saml/logout?relay_state=https://yourdomain.com`

   - Initiates Single Logout (SLO) with IdP
   - Only works for SAML-authenticated users

### SAML User Provisioning

When a user logs in via SAML for the first time:

1. System extracts user info from SAML attributes:
   - `email`: User's email address
   - `username`: Username (or extracted from email)
   - `displayName` or `cn`: Full name

2. Creates a new user with:
   - `auth_provider`: "saml"
   - `saml_name_id`: SAML NameID for future logins
   - `role`: "user" (default)
   - `is_active`: true

3. For subsequent logins, user is matched by `saml_name_id` and attributes are updated

### SAML Attribute Mapping

Configure your IdP to send these attributes:

| SAML Attribute | Description | Required |
|----------------|-------------|----------|
| `email` | User email | Yes |
| `username` | Username | No (extracted from email if missing) |
| `displayName` or `cn` | Full name | No |

---

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/register` | POST | Register new local user | No |
| `/api/auth/login` | POST | Login (OAuth2 form) | No |
| `/api/auth/login/json` | POST | Login (JSON) | No |
| `/api/auth/me` | GET | Get current user | Yes |
| `/api/auth/me` | PUT | Update profile | Yes |
| `/api/auth/change-password` | POST | Change password | Yes |
| `/api/auth/logout` | POST | Logout | Yes |
| `/api/auth/verify` | GET | Verify token | Yes |

### SAML Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/saml/metadata` | GET | Get SP metadata XML | No |
| `/api/saml/login` | GET | Initiate SAML SSO | No |
| `/api/saml/acs` | POST | Assertion Consumer Service | No |
| `/api/saml/logout` | GET | Initiate SAML SLO | Yes |
| `/api/saml/sls` | GET/POST | Single Logout Service | No |
| `/api/saml/test` | GET | Test SAML config | No |

---

## Configuration

### Environment Variables

See `.env.example` for a complete list of authentication-related environment variables.

**Required for Local Auth**:
- `SECRET_KEY`: Secret key for JWT signing (minimum 32 characters)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: 1440 = 24 hours)

**Required for SAML**:
- `SAML_SP_BASE_URL`: Your application base URL
- `SAML_IDP_ENTITY_ID`: IdP entity identifier
- `SAML_IDP_SSO_URL`: IdP SSO endpoint
- `SAML_IDP_CERT`: IdP X.509 certificate

**Optional for SAML**:
- `SAML_SP_CERT`: SP certificate for signing
- `SAML_SP_PRIVATE_KEY`: SP private key
- `SAML_IDP_SLO_URL`: IdP Single Logout URL
- `SAML_DEBUG`: Enable SAML debug mode
- `SAML_USE_HTTPS`: Force HTTPS for SAML URLs

### Database Migration

The User model is automatically created on startup. To manually create tables:

```bash
cd backend
python -c "from app.core.database import engine, Base; from app.models.user import User; Base.metadata.create_all(bind=engine)"
```

### Creating an Admin User

Via Python shell:

```python
from app.core.database import SessionLocal
from app.services.auth_service import auth_service
from app.models.user import UserRole, AuthProvider

db = SessionLocal()

admin = auth_service.create_user(
    db=db,
    email="admin@example.com",
    username="admin",
    password="AdminPassword123!",
    full_name="System Administrator",
    auth_provider=AuthProvider.LOCAL,
    role=UserRole.ADMIN
)

admin.is_superuser = True
db.commit()
print(f"Admin user created: {admin.username}")
```

---

## Frontend Integration

### React Example

```javascript
// Login
const login = async (username, password) => {
  const response = await fetch('http://localhost:8000/api/auth/login/json', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  const data = await response.json();

  if (response.ok) {
    // Store token
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  } else {
    throw new Error(data.detail || 'Login failed');
  }
};

// Make authenticated requests
const fetchProtectedData = async () => {
  const token = localStorage.getItem('access_token');

  const response = await fetch('http://localhost:8000/api/jenkins/jobs', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return await response.json();
};

// SAML Login
const loginWithSAML = () => {
  const relayState = encodeURIComponent(window.location.href);
  window.location.href = `http://localhost:8000/api/saml/login?relay_state=${relayState}`;
};

// Handle SAML callback (after IdP redirects back)
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');

  if (token) {
    localStorage.setItem('access_token', token);
    // Fetch user info
    fetchUserInfo();
  }
}, []);
```

### Axios Example

```javascript
import axios from 'axios';

// Configure axios with auth interceptor
const api = axios.create({
  baseURL: 'http://localhost:8000/api'
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## Security Best Practices

1. **Use HTTPS in Production**: Always use HTTPS when deploying to production
2. **Strong Secret Key**: Generate a strong SECRET_KEY (minimum 32 characters)
3. **Token Expiration**: Set appropriate ACCESS_TOKEN_EXPIRE_MINUTES
4. **Password Policy**: Enforce strong passwords (consider adding complexity requirements)
5. **Rate Limiting**: Add rate limiting to login endpoints
6. **Audit Logging**: Log authentication events for security monitoring
7. **CORS Configuration**: Restrict ALLOWED_ORIGINS to trusted domains

---

## Troubleshooting

### Common Issues

**Issue**: "Could not validate credentials"
- **Solution**: Check if token is included in Authorization header
- **Solution**: Verify token hasn't expired

**Issue**: "Username or email already exists"
- **Solution**: Try a different username/email or use login endpoint

**Issue**: "Account locked due to failed attempts"
- **Solution**: Wait 30 minutes or contact administrator

**Issue**: SAML login redirects to error page
- **Solution**: Check SAML configuration with `/api/saml/test`
- **Solution**: Verify IdP metadata is correctly configured
- **Solution**: Check SAML_IDP_CERT is in correct PEM format

**Issue**: "Failed to create/update user" after SAML login
- **Solution**: Check IdP is sending required attributes (email, username)
- **Solution**: Review backend logs for detailed error

---

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review backend logs for detailed error messages
3. Test SAML configuration with `/api/saml/test`
4. Ensure all required environment variables are set

---

## What's Next?

- Implement role-based access control on specific endpoints
- Add OAuth2 support (Google, GitHub, etc.)
- Implement email-based password reset
- Add two-factor authentication (2FA)
- User management UI for administrators
