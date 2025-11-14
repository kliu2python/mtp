# OpenStack VM Auto-Deployment Feature

This document describes the new OpenStack integration feature that allows automated deployment of FortiGate and FortiAuthenticator VMs in OpenStack cloud environments.

## Overview

The OpenStack deployment feature enables you to:
- Manage multiple OpenStack credentials
- Automatically deploy FortiGate and FortiAuthenticator VMs
- Select from available images, flavors, and networks
- Assign floating IPs to deployed VMs
- Manage VM lifecycle (start, stop, delete)

## Architecture

### Backend Components

1. **Models** (`backend/app/models/openstack.py`)
   - `OpenStackCredential`: Stores OpenStack authentication credentials
   - `OpenStackImage`: Caches information about available images

2. **Service Layer** (`backend/app/services/openstack_service.py`)
   - `OpenStackService`: Handles all OpenStack API interactions
   - Methods for VM deployment, resource discovery, and lifecycle management

3. **API Endpoints** (`backend/app/api/openstack.py`)
   - Credential management: CRUD operations for OpenStack credentials
   - Resource discovery: List flavors, images, and networks
   - VM deployment: Deploy VMs with custom configurations
   - VM management: Start, stop, delete, and get status

### Frontend Components

1. **OpenStack Deploy Component** (`frontend/src/components/OpenStackDeploy.jsx`)
   - Credential management interface
   - Deployment wizard with step-by-step configuration
   - Resource browsing and selection

## Setup Instructions

### 1. Install Dependencies

The OpenStack SDK dependencies are already included in `backend/requirements.txt`:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Application

```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or manually
cd backend
python main.py
```

### 3. Prepare OpenStack Environment

Before deploying VMs, ensure your OpenStack environment has:
- FortiGate and/or FortiAuthenticator images uploaded
- Appropriate flavors configured (recommended: at least 2 vCPUs, 4GB RAM)
- Network configured with external connectivity
- Floating IP pool available (if using floating IPs)

## Usage Guide

### Step 1: Add OpenStack Credentials

1. Navigate to **OpenStack Deploy** in the sidebar
2. Go to the **Credentials** tab
3. Click **Add Credential**
4. Fill in the form:
   - **Credential Name**: A friendly name (e.g., "Production OpenStack")
   - **Auth URL**: Your OpenStack Keystone endpoint (e.g., `https://openstack.example.com:5000/v3`)
   - **Username**: OpenStack username
   - **Password**: OpenStack password
   - **Project Name**: OpenStack project/tenant name
   - **Project Domain**: Usually "Default"
   - **User Domain**: Usually "Default"
   - **Region** (optional): OpenStack region name
   - **Verify SSL**: Enable/disable SSL verification

5. Click **OK** to save
6. Click **Test** to verify the connection

### Step 2: Deploy a VM

1. Go to the **Deploy VM** tab
2. Click **Start Deployment**
3. Follow the wizard:

   **Step 1: Select Credential**
   - Choose an OpenStack credential from the dropdown
   - Wait for resources to load

   **Step 2: Choose Platform**
   - Select platform: FortiGate or FortiAuthenticator
   - Enter version number

   **Step 3: Configure VM**
   - Enter VM name
   - Select image from available FortiGate/FortiAuthenticator images
   - Choose flavor (VM size)
   - Select network (optional)
   - Configure SSH credentials
   - Choose whether to assign a floating IP

   **Step 4: Review & Deploy**
   - Review configuration
   - Click **Deploy** to start deployment

4. Wait for deployment to complete (may take several minutes)
5. VM will appear in the Virtual Machines page

### Step 3: Manage Deployed VMs

Deployed VMs appear in the **Virtual Machines** page with:
- Provider tag: "openstack"
- IP address (floating IP if assigned)
- Status tracking
- Management actions (start, stop, delete)

## API Reference

### Credentials

- `POST /api/openstack/credentials` - Create credential
- `GET /api/openstack/credentials` - List credentials
- `GET /api/openstack/credentials/{id}` - Get credential details
- `PUT /api/openstack/credentials/{id}` - Update credential
- `DELETE /api/openstack/credentials/{id}` - Delete credential
- `POST /api/openstack/credentials/{id}/test` - Test connection

### Resources

- `GET /api/openstack/credentials/{id}/flavors` - List available flavors
- `GET /api/openstack/credentials/{id}/images?platform=FortiGate` - List images
- `GET /api/openstack/credentials/{id}/networks` - List networks

### VM Deployment

- `POST /api/openstack/deploy` - Deploy new VM
  ```json
  {
    "name": "my-fortigate",
    "platform": "FortiGate",
    "version": "7.0.0",
    "credential_id": "uuid",
    "image_id": "openstack-image-id",
    "flavor": "flavor-id",
    "network_id": "network-id",
    "assign_floating_ip": true,
    "ssh_username": "admin",
    "ssh_password": "password"
  }
  ```

### VM Management

- `POST /api/openstack/vms/{id}/start` - Start VM
- `POST /api/openstack/vms/{id}/stop` - Stop VM
- `DELETE /api/openstack/vms/{id}` - Delete VM
- `GET /api/openstack/vms/{id}/status` - Get VM status
- `GET /api/openstack/vms/{id}/console` - Get console URL

## Database Schema

### openstack_credentials Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String | Credential name |
| auth_url | String | Keystone endpoint |
| username | String | OpenStack username |
| password | String | OpenStack password (TODO: encrypt) |
| project_name | String | Project/tenant name |
| project_domain_name | String | Project domain |
| user_domain_name | String | User domain |
| region_name | String | Region (optional) |
| verify_ssl | Boolean | SSL verification flag |
| description | String | Description |
| is_active | Boolean | Active status |
| last_verified | DateTime | Last connection test |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Update timestamp |

### virtual_machines Table Extensions

New columns added:
- `provider` (ENUM): "docker" or "openstack"
- `openstack_credential_id` (UUID): Reference to credential
- `openstack_server_id` (String): OpenStack server UUID
- `openstack_flavor` (String): Flavor ID
- `openstack_image_id` (String): Image ID
- `openstack_network_id` (String): Network ID
- `openstack_floating_ip` (String): Assigned floating IP

## Security Considerations

### Current Implementation

- Passwords are stored in plain text in the database
- CORS is enabled for all origins
- No authentication required for API access

### Production Recommendations

1. **Encrypt Credentials**: Use encryption for storing OpenStack passwords
   - Implement using `cryptography` library
   - Store encryption key securely (e.g., environment variable)

2. **Enable Authentication**: Implement JWT-based authentication
   - Add user authentication to the platform
   - Restrict credential access by user/role

3. **Network Security**:
   - Configure firewall rules for OpenStack API access
   - Use VPN or private network for OpenStack communication
   - Enable SSL verification in production

4. **RBAC**: Implement role-based access control
   - Separate roles for credential management and VM deployment
   - Audit logging for all OpenStack operations

## Troubleshooting

### Connection Test Fails

- Verify auth_url is correct and accessible
- Check username/password credentials
- Verify project name and domain names
- Check SSL certificate if verify_ssl is enabled
- Review OpenStack firewall rules

### Deployment Fails

- Check if selected image is ACTIVE
- Verify flavor has sufficient resources
- Ensure network exists and is accessible
- Check quota limits in OpenStack project
- Review OpenStack Nova logs

### VM Not Accessible

- Check if floating IP was assigned
- Verify security groups allow SSH access
- Check VM console for boot issues
- Verify network connectivity

### Images Not Appearing

- Ensure images are uploaded to OpenStack Glance
- Image names should contain "fortigate", "fgt", "fortiauthenticator", or "fac"
- Images must have status "ACTIVE"
- Check image visibility (public/private)

## Example: Uploading FortiGate Image to OpenStack

```bash
# Download FortiGate image (qcow2 format)
wget https://support.fortinet.com/...

# Upload to OpenStack
openstack image create \
  --disk-format qcow2 \
  --container-format bare \
  --file fortios.qcow2 \
  --property hw_disk_bus=virtio \
  --property hw_vif_model=virtio \
  FortiGate-7.0.0

# Verify image
openstack image list | grep FortiGate
```

## Future Enhancements

- [ ] Credential encryption
- [ ] Support for multiple availability zones
- [ ] Volume attachment for persistent storage
- [ ] Security group management
- [ ] Snapshot and backup integration
- [ ] Automated scaling groups
- [ ] Cost tracking and billing integration
- [ ] Multi-region support
- [ ] Heat template support for complex deployments

## Support

For issues or questions:
- Check the troubleshooting section
- Review OpenStack logs
- Contact your OpenStack administrator
- Submit an issue on the project repository
