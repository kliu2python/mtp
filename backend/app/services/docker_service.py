"""Docker service for container management"""
import docker
from typing import Dict, Any

class DockerService:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except:
            self.client = None
    
    async def start_vm(self, vm) -> str:
        """Start a VM container"""
        if not self.client:
            return "mock-container-id"
        
        try:
            container = self.client.containers.run(
                "alpine:latest",
                name=f"vm-{vm.name}",
                detach=True,
                labels={"vm_id": str(vm.id), "platform": str(vm.platform.value)}
            )
            return container.id
        except Exception as e:
            raise Exception(f"Failed to start container: {str(e)}")
    
    async def stop_container(self, container_id: str):
        """Stop a container"""
        if not self.client:
            return
        
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
        except:
            pass
    
    async def get_container_logs(self, container_id: str, tail: int = 100) -> list:
        """Get container logs"""
        if not self.client:
            return ["Mock log line 1", "Mock log line 2"]
        
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail).decode('utf-8').split('\n')
            return logs
        except:
            return []
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource stats"""
        if not self.client:
            return {"cpu_percent": 25.5, "memory_percent": 45.2, "disk_percent": 30.1}
        
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            cpu_percent = 0
            memory_percent = 0
            
            if 'cpu_stats' in stats:
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100
            
            if 'memory_stats' in stats:
                memory_percent = (stats['memory_stats']['usage'] / 
                                stats['memory_stats']['limit']) * 100
            
            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "disk_percent": 0
            }
        except:
            return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}

docker_service = DockerService()
