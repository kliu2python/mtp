"""
OpenStack API endpoints for VM deployment and management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.openstack import OpenStackCredential, OpenStackImage
from app.models.vm import VirtualMachine, VMStatus, VMProvider, VMPlatform
from app.services.openstack_service import openstack_service

router = APIRouter()


# Pydantic models for request/response
class OpenStackCredentialCreate(BaseModel):
    name: str
    auth_url: str
    username: str
    password: str
    project_name: str
    project_domain_name: str = "Default"
    user_domain_name: str = "Default"
    region_name: Optional[str] = None
    verify_ssl: bool = True
    description: Optional[str] = None


class OpenStackCredentialUpdate(BaseModel):
    name: Optional[str] = None
    auth_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    project_name: Optional[str] = None
    project_domain_name: Optional[str] = None
    user_domain_name: Optional[str] = None
    region_name: Optional[str] = None
    verify_ssl: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class VMDeployRequest(BaseModel):
    name: str
    platform: str  # "FortiGate" or "FortiAuthenticator"
    version: str
    credential_id: str
    image_id: str
    flavor: str
    network_id: Optional[str] = None
    assign_floating_ip: bool = True
    key_name: Optional[str] = None
    security_groups: Optional[List[str]] = None
    ssh_username: Optional[str] = "admin"
    ssh_password: Optional[str] = None


# Credential management endpoints
@router.post("/credentials", status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential_data: OpenStackCredentialCreate,
    db: Session = Depends(get_db)
):
    """Create a new OpenStack credential"""
    # Check if credential with same name already exists
    existing = db.query(OpenStackCredential).filter(
        OpenStackCredential.name == credential_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Credential with name '{credential_data.name}' already exists"
        )

    # Create new credential
    credential = OpenStackCredential(
        name=credential_data.name,
        auth_url=credential_data.auth_url,
        username=credential_data.username,
        password=credential_data.password,
        project_name=credential_data.project_name,
        project_domain_name=credential_data.project_domain_name,
        user_domain_name=credential_data.user_domain_name,
        region_name=credential_data.region_name,
        verify_ssl=credential_data.verify_ssl,
        description=credential_data.description
    )

    db.add(credential)
    db.commit()
    db.refresh(credential)

    return credential.to_dict()


@router.get("/credentials")
async def list_credentials(db: Session = Depends(get_db)):
    """List all OpenStack credentials"""
    credentials = db.query(OpenStackCredential).all()
    return [cred.to_dict() for cred in credentials]


@router.get("/credentials/{credential_id}")
async def get_credential(credential_id: str, db: Session = Depends(get_db)):
    """Get a specific OpenStack credential"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    return credential.to_dict()


@router.put("/credentials/{credential_id}")
async def update_credential(
    credential_id: str,
    credential_data: OpenStackCredentialUpdate,
    db: Session = Depends(get_db)
):
    """Update an OpenStack credential"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    # Update fields
    update_data = credential_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(credential, field, value)

    db.commit()
    db.refresh(credential)

    return credential.to_dict()


@router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str, db: Session = Depends(get_db)):
    """Delete an OpenStack credential"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    # Check if any VMs are using this credential
    vms_using_cred = db.query(VirtualMachine).filter(
        VirtualMachine.openstack_credential_id == cred_uuid
    ).count()

    if vms_using_cred > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete credential: {vms_using_cred} VMs are using it"
        )

    db.delete(credential)
    db.commit()

    return {"message": "Credential deleted successfully"}


@router.post("/credentials/{credential_id}/test")
async def test_credential(credential_id: str, db: Session = Depends(get_db)):
    """Test OpenStack credential connection"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    # Test the connection
    result = openstack_service.test_connection(credential)

    if result["success"]:
        # Update last_verified timestamp
        from datetime import datetime
        credential.last_verified = datetime.utcnow()
        db.commit()

    return result


# Resource discovery endpoints
@router.get("/credentials/{credential_id}/flavors")
async def list_flavors(credential_id: str, db: Session = Depends(get_db)):
    """List available VM flavors"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    try:
        flavors = await openstack_service.list_flavors(credential)
        return {"flavors": flavors}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/credentials/{credential_id}/images")
async def list_images(
    credential_id: str,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List available images, optionally filtered by platform"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    try:
        images = await openstack_service.list_images(credential, platform)
        return {"images": images}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/credentials/{credential_id}/networks")
async def list_networks(credential_id: str, db: Session = Depends(get_db)):
    """List available networks"""
    try:
        cred_uuid = uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    try:
        networks = await openstack_service.list_networks(credential)
        return {"networks": networks}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# VM deployment endpoint
@router.post("/deploy", status_code=status.HTTP_201_CREATED)
async def deploy_vm(deploy_request: VMDeployRequest, db: Session = Depends(get_db)):
    """Deploy a new VM in OpenStack"""
    # Validate credential
    try:
        cred_uuid = uuid.UUID(deploy_request.credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID format"
        )

    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == cred_uuid
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    # Validate platform
    try:
        platform_enum = VMPlatform(deploy_request.platform)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform: {deploy_request.platform}"
        )

    # Check if VM with same name already exists
    existing_vm = db.query(VirtualMachine).filter(
        VirtualMachine.name == deploy_request.name
    ).first()

    if existing_vm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"VM with name '{deploy_request.name}' already exists"
        )

    # Create VM record with PROVISIONING status
    vm = VirtualMachine(
        name=deploy_request.name,
        platform=platform_enum,
        version=deploy_request.version,
        provider=VMProvider.OPENSTACK,
        status=VMStatus.PROVISIONING,
        openstack_credential_id=cred_uuid,
        openstack_image_id=deploy_request.image_id,
        openstack_flavor=deploy_request.flavor,
        openstack_network_id=deploy_request.network_id,
        ssh_username=deploy_request.ssh_username,
        ssh_password=deploy_request.ssh_password
    )

    db.add(vm)
    db.commit()
    db.refresh(vm)

    # Deploy VM in OpenStack
    try:
        server_details = await openstack_service.deploy_vm(
            credential=credential,
            name=deploy_request.name,
            image_id=deploy_request.image_id,
            flavor=deploy_request.flavor,
            network_id=deploy_request.network_id,
            assign_floating_ip=deploy_request.assign_floating_ip,
            key_name=deploy_request.key_name,
            security_groups=deploy_request.security_groups
        )

        # Update VM with server details
        vm.openstack_server_id = server_details["id"]
        vm.openstack_floating_ip = server_details.get("floating_ip")
        vm.ip_address = server_details.get("floating_ip") or server_details.get("private_ip")
        vm.status = VMStatus.RUNNING
        vm.config = server_details

        db.commit()
        db.refresh(vm)

        return vm.to_dict()

    except Exception as e:
        # Mark VM as failed
        vm.status = VMStatus.FAILED
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy VM: {str(e)}"
        )


# VM management endpoints
@router.post("/vms/{vm_id}/start")
async def start_vm(vm_id: str, db: Session = Depends(get_db)):
    """Start a stopped OpenStack VM"""
    try:
        vm_uuid = uuid.UUID(vm_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VM ID format"
        )

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_uuid).first()

    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VM not found"
        )

    if vm.provider != VMProvider.OPENSTACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VM is not an OpenStack VM"
        )

    # Get credential
    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == vm.openstack_credential_id
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenStack credential not found"
        )

    try:
        await openstack_service.start_server(credential, vm.openstack_server_id)
        vm.status = VMStatus.RUNNING
        db.commit()

        return {"message": "VM started successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/vms/{vm_id}/stop")
async def stop_vm(vm_id: str, db: Session = Depends(get_db)):
    """Stop a running OpenStack VM"""
    try:
        vm_uuid = uuid.UUID(vm_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VM ID format"
        )

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_uuid).first()

    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VM not found"
        )

    if vm.provider != VMProvider.OPENSTACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VM is not an OpenStack VM"
        )

    # Get credential
    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == vm.openstack_credential_id
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenStack credential not found"
        )

    try:
        await openstack_service.stop_server(credential, vm.openstack_server_id)
        vm.status = VMStatus.STOPPED
        db.commit()

        return {"message": "VM stopped successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/vms/{vm_id}")
async def delete_vm(vm_id: str, db: Session = Depends(get_db)):
    """Delete an OpenStack VM"""
    try:
        vm_uuid = uuid.UUID(vm_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VM ID format"
        )

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_uuid).first()

    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VM not found"
        )

    if vm.provider != VMProvider.OPENSTACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VM is not an OpenStack VM"
        )

    # Get credential
    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == vm.openstack_credential_id
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenStack credential not found"
        )

    try:
        # Delete from OpenStack
        if vm.openstack_server_id:
            await openstack_service.delete_server(credential, vm.openstack_server_id)

        # Delete from database
        db.delete(vm)
        db.commit()

        return {"message": "VM deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/vms/{vm_id}/status")
async def get_vm_status(vm_id: str, db: Session = Depends(get_db)):
    """Get OpenStack VM status"""
    try:
        vm_uuid = uuid.UUID(vm_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VM ID format"
        )

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_uuid).first()

    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VM not found"
        )

    if vm.provider != VMProvider.OPENSTACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VM is not an OpenStack VM"
        )

    # Get credential
    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == vm.openstack_credential_id
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenStack credential not found"
        )

    try:
        status_info = await openstack_service.get_server_status(
            credential, vm.openstack_server_id
        )
        return status_info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/vms/{vm_id}/console")
async def get_vm_console(vm_id: str, db: Session = Depends(get_db)):
    """Get OpenStack VM console URL"""
    try:
        vm_uuid = uuid.UUID(vm_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid VM ID format"
        )

    vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_uuid).first()

    if not vm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VM not found"
        )

    if vm.provider != VMProvider.OPENSTACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VM is not an OpenStack VM"
        )

    # Get credential
    credential = db.query(OpenStackCredential).filter(
        OpenStackCredential.id == vm.openstack_credential_id
    ).first()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenStack credential not found"
        )

    try:
        console_url = await openstack_service.get_server_console(
            credential, vm.openstack_server_id
        )

        if console_url:
            return {"console_url": console_url}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Console URL not available"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
