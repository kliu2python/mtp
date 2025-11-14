"""
OpenStack service for VM deployment and management
"""
import openstack
from openstack.connection import Connection
from typing import Dict, Any, List, Optional
import time
import logging

logger = logging.getLogger(__name__)


class OpenStackService:
    """Service to interact with OpenStack for VM deployment"""

    def __init__(self):
        self.connections: Dict[str, Connection] = {}

    def get_connection(self, credential) -> Connection:
        """Get or create OpenStack connection"""
        cred_id = str(credential.id)

        # Return cached connection if available
        if cred_id in self.connections:
            return self.connections[cred_id]

        # Create new connection
        try:
            conn = openstack.connect(
                auth_url=credential.auth_url,
                project_name=credential.project_name,
                username=credential.username,
                password=credential.password,
                project_domain_name=credential.project_domain_name,
                user_domain_name=credential.user_domain_name,
                region_name=credential.region_name,
                verify=credential.verify_ssl
            )

            # Test the connection
            conn.authorize()

            # Cache the connection
            self.connections[cred_id] = conn
            logger.info(f"Connected to OpenStack: {credential.name}")

            return conn

        except Exception as e:
            logger.error(f"Failed to connect to OpenStack: {str(e)}")
            raise Exception(f"OpenStack connection failed: {str(e)}")

    def test_connection(self, credential) -> Dict[str, Any]:
        """Test OpenStack credentials and return connection info"""
        try:
            conn = self.get_connection(credential)

            # Get project info
            project = conn.identity.find_project(credential.project_name)

            return {
                "success": True,
                "project_id": project.id if project else None,
                "project_name": credential.project_name,
                "region": credential.region_name,
                "auth_url": credential.auth_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def list_flavors(self, credential) -> List[Dict[str, Any]]:
        """List available VM flavors"""
        try:
            conn = self.get_connection(credential)
            flavors = []

            for flavor in conn.compute.flavors():
                flavors.append({
                    "id": flavor.id,
                    "name": flavor.name,
                    "vcpus": flavor.vcpus,
                    "ram": flavor.ram,
                    "disk": flavor.disk,
                    "is_public": flavor.is_public
                })

            return flavors

        except Exception as e:
            logger.error(f"Failed to list flavors: {str(e)}")
            raise Exception(f"Failed to list flavors: {str(e)}")

    async def list_images(self, credential, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available images, optionally filtered by platform"""
        try:
            conn = self.get_connection(credential)
            images = []

            for image in conn.compute.images():
                # Skip if image is not active
                if image.status != "ACTIVE":
                    continue

                image_name = image.name.lower()

                # Filter by platform if specified
                if platform:
                    platform_lower = platform.lower()
                    if platform_lower == "fortigate":
                        if "fortigate" not in image_name and "fgt" not in image_name:
                            continue
                    elif platform_lower == "fortiauthenticator":
                        if "fortiauthenticator" not in image_name and "fac" not in image_name:
                            continue

                images.append({
                    "id": image.id,
                    "name": image.name,
                    "status": image.status,
                    "size": getattr(image, 'size', None),
                    "min_disk": getattr(image, 'min_disk', 0),
                    "min_ram": getattr(image, 'min_ram', 0),
                    "created_at": str(getattr(image, 'created_at', '')),
                    "properties": getattr(image, 'properties', {})
                })

            return images

        except Exception as e:
            logger.error(f"Failed to list images: {str(e)}")
            raise Exception(f"Failed to list images: {str(e)}")

    async def list_networks(self, credential) -> List[Dict[str, Any]]:
        """List available networks"""
        try:
            conn = self.get_connection(credential)
            networks = []

            for network in conn.network.networks():
                networks.append({
                    "id": network.id,
                    "name": network.name,
                    "status": network.status,
                    "is_router_external": network.is_router_external,
                    "is_shared": network.is_shared,
                    "subnets": network.subnet_ids
                })

            return networks

        except Exception as e:
            logger.error(f"Failed to list networks: {str(e)}")
            raise Exception(f"Failed to list networks: {str(e)}")

    async def deploy_vm(
        self,
        credential,
        name: str,
        image_id: str,
        flavor: str,
        network_id: Optional[str] = None,
        assign_floating_ip: bool = True,
        key_name: Optional[str] = None,
        security_groups: Optional[List[str]] = None,
        user_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deploy a VM in OpenStack"""
        try:
            conn = self.get_connection(credential)

            # Prepare server creation parameters
            server_params = {
                "name": name,
                "image_id": image_id,
                "flavor_id": flavor,
                "wait": True,
                "timeout": 600  # 10 minutes timeout
            }

            # Add network if specified
            if network_id:
                server_params["network"] = network_id

            # Add key pair if specified
            if key_name:
                server_params["key_name"] = key_name

            # Add security groups if specified
            if security_groups:
                server_params["security_groups"] = security_groups

            # Add user data if specified
            if user_data:
                server_params["userdata"] = user_data

            logger.info(f"Creating OpenStack server: {name}")

            # Create the server
            server = conn.compute.create_server(**server_params)

            # Wait for server to be active
            server = conn.compute.wait_for_server(server, status='ACTIVE', wait=600)

            logger.info(f"Server {name} created successfully: {server.id}")

            # Get server details including IP addresses
            server_details = {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "addresses": server.addresses,
                "flavor": server.flavor,
                "image": server.image,
                "created_at": str(server.created_at)
            }

            # Try to assign floating IP if requested
            floating_ip = None
            if assign_floating_ip:
                try:
                    floating_ip = await self._assign_floating_ip(conn, server)
                    if floating_ip:
                        server_details["floating_ip"] = floating_ip
                        logger.info(f"Assigned floating IP {floating_ip} to {name}")
                except Exception as e:
                    logger.warning(f"Failed to assign floating IP: {str(e)}")

            # Get the private IP
            private_ip = self._get_server_ip(server)
            server_details["private_ip"] = private_ip

            return server_details

        except Exception as e:
            logger.error(f"Failed to deploy VM: {str(e)}")
            raise Exception(f"Failed to deploy VM: {str(e)}")

    async def _assign_floating_ip(self, conn: Connection, server) -> Optional[str]:
        """Assign a floating IP to a server"""
        try:
            # Try to find an available floating IP
            floating_ip = None
            for fip in conn.network.ips():
                if fip.fixed_ip_address is None:
                    floating_ip = fip
                    break

            # Create a new floating IP if none available
            if not floating_ip:
                # Find external network
                external_network = None
                for network in conn.network.networks():
                    if network.is_router_external:
                        external_network = network
                        break

                if external_network:
                    floating_ip = conn.network.create_ip(
                        floating_network_id=external_network.id
                    )

            if floating_ip:
                # Attach floating IP to server
                conn.compute.add_floating_ip_to_server(
                    server.id,
                    floating_ip.floating_ip_address
                )
                return floating_ip.floating_ip_address

            return None

        except Exception as e:
            logger.error(f"Failed to assign floating IP: {str(e)}")
            return None

    def _get_server_ip(self, server) -> Optional[str]:
        """Extract IP address from server"""
        try:
            if not server.addresses:
                return None

            # Get the first network's first IP
            for network_name, addresses in server.addresses.items():
                if addresses and len(addresses) > 0:
                    return addresses[0].get('addr')

            return None

        except Exception as e:
            logger.error(f"Failed to get server IP: {str(e)}")
            return None

    async def get_server_status(self, credential, server_id: str) -> Dict[str, Any]:
        """Get server status and details"""
        try:
            conn = self.get_connection(credential)
            server = conn.compute.get_server(server_id)

            if not server:
                return {"error": "Server not found"}

            return {
                "id": server.id,
                "name": server.name,
                "status": server.status,
                "power_state": server.power_state,
                "addresses": server.addresses,
                "flavor": server.flavor,
                "created_at": str(server.created_at),
                "updated_at": str(server.updated_at)
            }

        except Exception as e:
            logger.error(f"Failed to get server status: {str(e)}")
            return {"error": str(e)}

    async def start_server(self, credential, server_id: str) -> bool:
        """Start a stopped server"""
        try:
            conn = self.get_connection(credential)
            conn.compute.start_server(server_id)
            logger.info(f"Started server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            raise Exception(f"Failed to start server: {str(e)}")

    async def stop_server(self, credential, server_id: str) -> bool:
        """Stop a running server"""
        try:
            conn = self.get_connection(credential)
            conn.compute.stop_server(server_id)
            logger.info(f"Stopped server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop server: {str(e)}")
            raise Exception(f"Failed to stop server: {str(e)}")

    async def delete_server(self, credential, server_id: str) -> bool:
        """Delete a server"""
        try:
            conn = self.get_connection(credential)

            # Get server details to check for floating IPs
            server = conn.compute.get_server(server_id)

            # Delete the server
            conn.compute.delete_server(server_id, wait=True)

            logger.info(f"Deleted server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete server: {str(e)}")
            raise Exception(f"Failed to delete server: {str(e)}")

    async def get_server_console(self, credential, server_id: str) -> Optional[str]:
        """Get server console URL"""
        try:
            conn = self.get_connection(credential)
            console = conn.compute.create_server_remote_console(
                server_id,
                protocol='novnc',
                console_type='novnc'
            )

            return console.url if console else None

        except Exception as e:
            logger.error(f"Failed to get console URL: {str(e)}")
            return None


# Global instance
openstack_service = OpenStackService()
