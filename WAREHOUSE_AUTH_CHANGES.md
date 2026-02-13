# Warehouse API Authentication Changes

## Overview
This document describes the changes made to add authentication to the warehouse API endpoints.

## Changes Made

### 1. Authentication Dependency
Added a new authentication dependency function `verify_warehouse_access` that:
- Verifies OTP authentication for warehouse operations
- Checks the Authorization header for a valid email with verified OTP
- Returns the authenticated user's email
- Raises HTTP 401 error if authentication fails

### 2. Protected Endpoints
The following warehouse API endpoints now require authentication:

#### GET /api/warehouse/count
- Returns counts of available codes for all types
- Public endpoint (no authentication required)

#### POST /api/warehouse/random
- **Before**: Returned a random code without authentication
- **After**: Requires valid OTP authentication via Authorization header
- **Header Format**: `Authorization: Bearer user@fortinet.com`
- Logs warehouse activity when a code is fetched

#### POST /api/warehouse/upload
- **Before**: Accepted file uploads without authentication
- **After**: Requires valid OTP authentication via Authorization header
- **Header Format**: `Authorization: Bearer user@fortinet.com`
- Logs warehouse activity when codes are uploaded

#### POST /api/warehouse/recycle
- **Before**: Accepted code recycling without authentication
- **After**: Requires valid OTP authentication via Authorization header
- **Header Format**: `Authorization: Bearer user@fortinet.com`
- Logs warehouse activity when codes are recycled

### 3. Warehouse Activity Logging
All warehouse operations now log activities:
- **fetch**: When getting a random code
- **upload**: When uploading new codes
- **recycle**: When recycling used codes

Activities are logged with:
- User email and username
- Action type
- Code type (FortiGate, FortiAuthenticator, FortiToken, etc.)
- Partial code value (masked for security)
- Count of uploaded files

## Implementation Details

### Authentication Flow
1. User generates OTP via `/api/warehouse/auth/generate-otp`
2. User verifies OTP via `/api/warehouse/auth/verify-otp`
3. User includes Authorization header in warehouse API requests
4. System validates OTP status before processing requests

### Error Responses
- **401 Unauthorized**: Missing or invalid Authorization header
- **401 Unauthorized**: OTP not verified for the provided email
- **400 Bad Request**: Invalid email format in Authorization header

## Files Modified
- `backend/app/api/warehouse/__init__.py`: Added authentication dependencies and updated endpoints

## Testing
The implementation has been tested for syntax correctness. Further integration testing should be performed to verify:
1. OTP generation and verification flow
2. Authenticated access to warehouse endpoints
3. Warehouse activity logging
4. Proper error handling for unauthenticated requests