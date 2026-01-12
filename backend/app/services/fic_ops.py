"""
FortiToken Cloud Ops Service
Handles FortiToken Cloud operations with multi-user session management
"""

import os
import re
import base64
import subprocess
import time
import requests
from datetime import datetime, timedelta
import threading
import logging
import paramiko
import secrets
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

MS_TEAMS_WEHOOK = ("https://fortinet.webhook.office.com/webhookb2/"
                   "b8387ec8-f954-4f05-af67-05562fe4d6f4@2c36c478-3d00-452f"
                   "-8535-48396f5f01f0/IncomingWebhook/"
                   "895c041c1d00400a8a5f5765febb2bff/4a04faf1-b362-4326-96a4-"
                   "3f1d40639dc3/V2gImqWGU-sQmXUnKFDsnJAODS2L6ymxrSqf6rfkaU_zM1"
                   )

FAS_SERVICE = {
    '/etc/fas/fas.conf': 'fas-server',
    '/etc/fas/fas2.conf': 'fas2-server',
    '/etc/fas/fas3.conf': 'fas3-server',
    '/etc/fas/fas_3rd_api.conf': 'fas-3rd-api',
}


class FICTokenOps:
    @classmethod
    def decode_token(cls, token):
        decoded = base64.b32decode(token)

        # --- Byte 1 ---
        byte1 = decoded[0]
        version_bits = (byte1 >> 3) & 0x1F
        alg_bits = byte1 & 0x07

        version_map = {
            0b00110: 'v6',
            0b00101: 'v5',
            0b00100: 'v4',
            0b00011: 'v3',
            0b00010: 'v2',
        }
        algorithm_map = {
            0b000: 'HOTP',
            0b001: 'TOTP',
        }
        version = version_map.get(version_bits, f'unknown({version_bits})')
        algorithm = algorithm_map.get(alg_bits, f'unknown({alg_bits})')

        # --- Byte 2 ---
        byte2 = decoded[1]
        otplen_bits = (byte2 >> 5) & 0x07
        otplen_map = {
            0b000: 6,
            0b001: 8,
        }
        otplen = otplen_map.get(otplen_bits, f'unknown({otplen_bits})')
        tstep_bit = (byte2 >> 4) & 0x01
        timesteps = 30 if tstep_bit == 0 else 60
        type_bits = (byte2 >> 2) & 0x03
        type_map = {
            0b00: 'activation',
            0b01: 'transfer',
            0b10: 'reserve',
            0b11: 'reserve',
        }
        token_type = type_map.get(type_bits, f'unknown({type_bits})')
        protocol_bits = byte2 & 0x03
        protocol_map = {
            0b00: 'https',
            0b01: 'http',
        }
        protocol = protocol_map.get(protocol_bits, f'unknown({protocol_bits})')

        # --- Bytes 3-29: Hostname ---
        hostname_bits = "".join(format(b, '08b') for b in decoded[2:29])
        charmap = {
            '000000': '0', '000001': '1', '000010': '2', '000011': '3',
            '000100': '4', '000101': '5', '000110': '6', '000111': '7',
            '001000': '8', '001001': '9', '001010': 'a', '001011': 'b',
            '001100': 'c', '001101': 'd', '001110': 'e', '001111': 'f',
            '010000': 'g', '010001': 'h', '010010': 'i', '010011': 'j',
            '010100': 'k', '010101': 'l', '010110': 'm', '010111': 'n',
            '011000': 'o', '011001': 'p', '011010': 'q', '011011': 'r',
            '011100': 's', '011101': 't', '011110': 'u', '011111': 'v',
            '100000': 'w', '100001': 'x', '100010': 'y', '100011': 'z',
            '100100': '.', '100101': '-', '111111': 'delimiter',
        }
        chars = []
        for i in range(0, len(hostname_bits), 6):
            chunk = hostname_bits[i:i + 6]
            if chunk == '111111':
                break
            chars.append(charmap.get(chunk, '?'))
        hostname = "".join(chars)

        # --- Bytes 30-31: Port ---
        port = int.from_bytes(decoded[29:31], byteorder='big')
        if port == 0:
            port = 443

        # --- Byte 32: Extension ---
        byte32 = decoded[31]
        allow_rooted = bool((byte32 >> 7) & 0x01)
        apispec_bit = (byte32 >> 6) & 0x01
        apispec = 'FTC' if apispec_bit == 1 else 'FGD'

        # --- Bytes 33-40: Authentication Bytes ---
        authbytes = decoded[32:40].hex().upper()

        return {
            'version': version,
            'algorithm': algorithm,
            'otplength': otplen,
            'timesteps': timesteps,
            'type': token_type,
            'protocol': protocol,
            'hostname': hostname,
            'port': port,
            'allowrooteddevice': allow_rooted,
            'apispec': apispec,
            'authbytes': authbytes,
        }


class SSHJumpboxManager:
    def __init__(
            self, jumpbox_host, jumpbox_user, jumpbox_password,
            target_host, target_user, target_key_file,
    ):
        self.jumpbox_host = jumpbox_host
        self.jumpbox_user = jumpbox_user
        self.jumpbox_password = jumpbox_password
        self.target_host = target_host
        self.target_user = target_user
        self.target_key_file = target_key_file
        self.connection_id = f"{jumpbox_host}_{target_host}_{int(time.time())}"
        self.jumpbox_client = None

    def connect(self, timeout=30):
        if (self.jumpbox_client and self.jumpbox_client.get_transport() and
                self.jumpbox_client.get_transport().is_active()):
            return  # Already connected
        self.jumpbox_client = paramiko.SSHClient()
        self.jumpbox_client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy(),
        )
        self.jumpbox_client.connect(
            hostname=self.jumpbox_host,
            username=self.jumpbox_user,
            password=self.jumpbox_password,
            timeout=timeout,
        )

    def close(self):
        if self.jumpbox_client:
            self.jumpbox_client.close()
            self.jumpbox_client = None

    def execute_remote_command(self, command, timeout=30):
        try:
            self.connect(timeout)
            ssh_command = (f'ssh -i {self.target_key_file}'
                           f' -o StrictHostKeyChecking=no {self.target_user}'
                           f'@{self.target_host} "{command}"')
            logger.info(f"[{self.connection_id}] Executing command: {command}")
            stdin, stdout, stderr = self.jumpbox_client.exec_command(
                ssh_command, timeout=timeout,
            )
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'stdout': stdout_text,
                'stderr': stderr_text,
            }
        except Exception as e:
            logger.error(
                f"[{self.connection_id}] SSH command execution failed: {e}",
            )
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': '',
            }

    def read_remote_file(self, file_path):
        """Read file content from target server through jumpbox"""
        # Try with regular permissions first
        command = f'cat {file_path}'
        result = self.execute_remote_command(command)

        if result['success']:
            return result['stdout']
        else:
            # If regular read fails, try with sudo
            logger.info(
                f"[{self.connection_id}] Regular read failed,"
                f" trying with sudo for {file_path}",
            )
            sudo_command = f'sudo cat {file_path}'
            sudo_result = self.execute_remote_command(sudo_command)

            if sudo_result['success']:
                return sudo_result['stdout']
            else:
                logger.error(
                    f"[{self.connection_id}] Failed to"
                    f" read file {file_path} even with sudo",
                )
                return None

    def write_remote_file(self, file_path, content):
        """Write content to file on target server through jumpbox"""
        # Create a temporary file and then move it with sudo
        temp_file = f'/tmp/fas_conf_temp_{int(time.time())}'

        try:
            # First, write to temporary file
            escaped_content = content.replace("'", "'\"'\"'")
            temp_command = f"echo '{escaped_content}' > {temp_file}"

            temp_result = self.execute_remote_command(temp_command)
            if not temp_result['success']:
                logger.error(
                    f"[{self.connection_id}] Failed to create temporary file",
                )
                return False

            # Then move temp file to target location with sudo
            move_command = f'sudo mv {temp_file} {file_path}'
            move_result = self.execute_remote_command(move_command)

            if move_result['success']:
                # Set proper permissions
                chmod_command = f'sudo chmod 644 {file_path}'
                self.execute_remote_command(chmod_command)
                return True
            else:
                # Clean up temp file if move failed
                cleanup_command = f'rm -f {temp_file}'
                self.execute_remote_command(cleanup_command)
                return False

        except Exception as e:
            logger.error(
                f"[{self.connection_id}] Failed to write file {file_path}: {e}",
            )
            # Attempt cleanup
            cleanup_command = f'rm -f {temp_file}'
            self.execute_remote_command(cleanup_command)
            return False


class UserSession:
    def __init__(self, session_id, ssh_config, expires_in_hours=24):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(hours=expires_in_hours)
        self.last_accessed = self.created_at
        self.ssh_manager = None
        self.ops_manager = None
        self.user_info = {
            'jumpbox_host': ssh_config.get('jumpbox_host'),
            'target_host': ssh_config.get('target_host'),
            'target_user': ssh_config.get('target_user'),
        }

        # Initialize SSH connection
        self._initialize_ssh_connection(ssh_config)

    def _initialize_ssh_connection(self, config):
        """Initialize SSH connection for this session"""
        try:
            self.ssh_manager = SSHJumpboxManager(
                jumpbox_host=config['jumpbox_host'],
                jumpbox_user=config['jumpbox_user'],
                jumpbox_password=config['jumpbox_password'],
                target_host=config['target_host'],
                target_user=config['target_user'],
                target_key_file=config['target_key_file'],
            )

            # Test connection
            test_result = self.ssh_manager.execute_remote_command(
                'echo "Connection test"',
            )
            if not test_result['success']:
                logger.error(
                    f"SSH connection test failed for session {self.session_id}",
                )
                self.ssh_manager = None
                return False

            self.ops_manager = FortiTokenOpsManager(
                fas_conf_paths=config.get(
                    'fas_conf_paths',
                    [
                        '/etc/fas/fas.conf',
                        '/etc/fas/fas2.conf',
                        '/etc/fas/fas3.conf',
                        '/etc/fas/fas_3rd_api.conf',
                    ],
                ),
                ssh_manager=self.ssh_manager,
                session_id=self.session_id,
            )

            logger.info(
                f"SSH connection initialized for session {self.session_id}",
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to initialize SSH"
                f" connection for session {self.session_id}: {e}",
            )
            self.ssh_manager = None
            self.ops_manager = None
            return False

    def is_expired(self):
        """Check if session is expired"""
        return datetime.now() > self.expires_at

    def update_last_accessed(self):
        """Update last accessed timestamp"""
        self.last_accessed = datetime.now()

    def get_session_info(self):
        """Get session information"""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'is_expired': self.is_expired(),
            'user_info': self.user_info,
            'has_ssh_connection': self.ssh_manager is not None,
        }


class FortiTokenOpsManager:
    def __init__(self, fas_conf_paths=None, ssh_manager=None, session_id=None):
        # Accept a list or a single string for backward compatibility
        if fas_conf_paths is None:
            fas_conf_paths = [
                '/etc/fas/fas.conf',
                '/etc/fas/fas2.conf',
                '/etc/fas/fas3.conf',
                '/etc/fas/fas_3rd_api.conf',
            ]
        elif isinstance(fas_conf_paths, str):
            fas_conf_paths = [fas_conf_paths]
        self.fas_conf_paths = fas_conf_paths
        self.ssh_manager = ssh_manager
        self.session_id = session_id
        self.frontend_url = None
        self.backend_url = None
        self.monitoring_interval = None
        self.server_status = {
            'frontend': {'status': 'unknown', 'last_check': None},
            'backend': {'status': 'unknown', 'last_check': None},
        }
        self.monitoring_active = False

    def read_fas_conf(self, conf_path):
        """Read fas.conf file content through SSH or locally."""
        if not self.ssh_manager:
            return self._read_local_file(conf_path)
        try:
            content = self.ssh_manager.read_remote_file(conf_path)
            if content is None:
                logger.error(
                    f"[{self.session_id}] Configuration file"
                    f" cannot be read: {conf_path}",
                )
                return None
            return content
        except Exception as e:
            logger.error(
                f"[{self.session_id}] Failed to read configuration file: {e}",
            )
            return None

    def _read_local_file(self, conf_path):
        """Fallback method for local file reading"""
        try:
            if not os.path.exists(conf_path):
                logger.error(f"Configuration file does not exist: {conf_path}")
                return None
            with open(conf_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read configuration file: {e}")
            return None

    def get_token_format_version(self):
        """Return token_format_version for all files."""
        results = []
        for conf_path in self.fas_conf_paths:
            content = self.read_fas_conf(conf_path)
            if content is None:
                results.append(
                    {
                        'file_path': conf_path,
                        'error': 'Unable to read configuration file',
                        'session_id': self.session_id,
                    },
                )
                continue
            pattern = r'^\s*token_format_version\s*=\s*([^\s#]+)'
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                token_format_version = match.group(1).strip()
                logger.info(
                    f"[{self.session_id}] Found token_format_version"
                    f" in {conf_path}: {token_format_version}",
                )
                results.append(
                    {
                        'token_format_version': token_format_version,
                        'exists': True,
                        'file_path': conf_path,
                        'session_id': self.session_id,
                    },
                )
            else:
                logger.info(
                    f"[{self.session_id}] token_format_version not found"
                    f" in {conf_path}, using default value v5",
                )
                results.append(
                    {
                        'token_format_version': 'v5',
                        'exists': False,
                        'file_path': conf_path,
                        'note': 'token_format_version does not'
                                ' exist, using default value v5',
                        'session_id': self.session_id,
                    },
                )
        return results if len(results) > 1 else results[0]

    def update_token_format_version(self, new_format):
        """
        Update token_format_version in
        all config files, restart all services.
        """
        if new_format not in ['v5', 'v6']:
            return {
                'error': 'Invalid token_format_version '
                         'value, only v5 or v6 supported',
            }

        restart_results = []
        update_results = []
        for conf_path in self.fas_conf_paths:
            svc = FAS_SERVICE.get(conf_path)
            content = self.read_fas_conf(conf_path)
            if content is None:
                update_results.append(
                    {
                        'file': conf_path,
                        'error': 'Unable to read configuration file',
                    },
                )
                continue

            # Get current version in file
            pattern = r'^\s*token_format_version\s*=\s*([^\s#]+)'
            match = re.search(pattern, content, re.MULTILINE)
            current_format = match.group(1).strip() if match else 'v5'
            exists = bool(match)

            if current_format == new_format:
                update_results.append(
                    {
                        'file': conf_path,
                        'success': True,
                        'message': f'token_format_version is already '
                                   f'{new_format}, no changes needed',
                        'current_format': current_format,
                    },
                )
                continue

            try:
                backup_path = f"{conf_path}.backup.{int(time.time())}"
                if self.ssh_manager:
                    backup_result = self.ssh_manager.execute_remote_command(
                        f'sudo cp {conf_path} {backup_path}',
                    )
                    if not backup_result['success']:
                        update_results.append(
                            {
                                'file': conf_path,
                                'error': 'Failed to create backup file',
                            },
                        )
                        continue
                    self.ssh_manager.execute_remote_command(
                        f'sudo chmod 644 {backup_path}',
                    )
                else:
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                logger.info(
                    f"[{self.session_id}] Backup file created: {backup_path}",
                )

                # Update or insert the config line
                replacement = f'token_format_version = {new_format}'
                if exists:
                    new_content = re.sub(
                        pattern, replacement, content, flags=re.MULTILINE,
                    )
                else:
                    new_content = content.rstrip() + f'\n{replacement}\n'

                if self.ssh_manager:
                    if not self.ssh_manager.write_remote_file(
                            conf_path, new_content,
                    ):
                        update_results.append(
                            {
                                'file': conf_path,
                                'error': 'Failed to write configuration file',
                            },
                        )
                        continue
                else:
                    with open(conf_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                update_results.append(
                    {
                        'file': conf_path,
                        'success': True,
                        'message': f'token_format_version updated '
                                   f'from {current_format} to {new_format}',
                        'previous_format': current_format,
                        'new_format': new_format,
                        'backup_file': backup_path,
                    },
                )
                result = self.restart_service(service_name=svc)
                restart_results.append({'service': svc, **result})

            except Exception as e:
                update_results.append(
                    {
                        'file': conf_path,
                        'error': f'Failed to update configuration: {str(e)}',
                    },
                )

        # Send MS Teams notification (optional, can customize)
        files = ",".join(
            r["file"] for r in update_results if r.get("success")
        )

        MessageClient().init_message(
            f"token_format_version updated to **{new_format}** on files: {files}"
        )

        return {
            'file_updates': update_results,
            'service_restarts': restart_results,
            'session_id': self.session_id,
        }

    def get_use_sandbox_status(self):
        """Check the current value of use_sandbox under [push] section."""
        results = []
        # captures content of [push] section
        section_pattern = r'^\s*\[push\](.*?)^\s*(\[.*?\]|$)'
        # finds use_sandbox assignment
        key_pattern = r'^\s*use_sandbox\s*=\s*(\w+)'

        for conf_path in self.fas_conf_paths:
            content = self.read_fas_conf(conf_path)
            if content is None:
                results.append(
                    {
                        'file': conf_path,
                        'error': 'Unable to read configuration file',
                    },
                )
                continue

            try:
                match = re.search(
                    section_pattern, content, re.DOTALL | re.MULTILINE,
                )
                if match:
                    section_body = match.group(1)
                    sandbox_match = re.search(
                        key_pattern, section_body, re.MULTILINE,
                    )
                    if sandbox_match:
                        value = sandbox_match.group(1).lower()
                        results.append(
                            {
                                'file': conf_path,
                                'use_sandbox': value,
                                'exists': True,
                                'session_id': self.session_id,
                            },
                        )
                    else:
                        results.append(
                            {
                                'file': conf_path,
                                'use_sandbox': 'true',  # Default value assumed
                                'exists': False,
                                'note': 'use_sandbox not set,'
                                        ' assuming default True',
                                'session_id': self.session_id,
                            },
                        )
                else:
                    results.append(
                        {
                            'file': conf_path,
                            'use_sandbox': 'unknown',
                            'exists': False,
                            'error': '[push] section not found',
                            'session_id': self.session_id,
                        },
                    )
            except Exception as e:
                results.append(
                    {
                        'file': conf_path,
                        'error': f'Failed to check use_sandbox: {str(e)}',
                        'session_id': self.session_id,
                    },
                )

        return results if len(results) > 1 else results[0]

    def update_use_sandbox(self, new_value: str):
        """Set use_sandbox = True/False under [push] in config files"""
        new_value = new_value.strip().lower()
        section_body_new = None
        restart = False
        if new_value not in ['true', 'false']:
            return {
                'error': 'Invalid value for use_sandbox.'
                         ' Must be "True" or "False".',
            }

        restart_results = []
        results = []
        # content in [push]
        section_pattern = r'^\s*\[push\](.*?)^\s*(\[.*?\]|$)'
        key_pattern = r'^\s*use_sandbox\s*=\s*(\w+)'  # use_sandbox line

        for conf_path in self.fas_conf_paths:
            svc = FAS_SERVICE.get(conf_path)
            content = self.read_fas_conf(conf_path)
            if content is None:
                results.append(
                    {
                        'file': conf_path,
                        'error': 'Unable to read configuration file',
                    },
                )
                continue

            updated = False
            try:
                match = re.search(
                    section_pattern, content, re.DOTALL | re.MULTILINE,
                )
                if match:
                    section_body = match.group(1)
                    section_start = match.start(1)
                    section_end = match.end(1)

                    # Check for use_sandbox inside [push]
                    sandbox_match = re.search(
                        key_pattern, section_body, re.MULTILINE,
                    )
                    if sandbox_match:
                        current_val = sandbox_match.group(1).lower()
                        if current_val != new_value:
                            section_body_new = re.sub(
                                key_pattern,
                                f'use_sandbox = {new_value}',
                                section_body,
                                flags=re.MULTILINE,
                            )
                            updated = True
                    else:
                        section_body_new = section_body.rstrip(
                        ) + f'\nuse_sandbox = {new_value}\n'
                        updated = True

                    if updated:
                        new_content = (
                                content[:section_start] + section_body_new
                                + content[section_end:]
                        )
                        backup_path = (f"{conf_path}.backup"
                                       f"_sandbox_{int(time.time(),)}")

                        if self.ssh_manager:
                            self.ssh_manager.execute_remote_command(
                                f'sudo cp {conf_path} {backup_path}',
                            )
                            self.ssh_manager.write_remote_file(
                                conf_path, new_content,
                            )
                        else:
                            with open(backup_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            with open(conf_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)

                        results.append(
                            {
                                'file': conf_path,
                                'updated': True,
                                'message': f"'use_sandbox = {new_value}"
                                           f"' updated under [push]",
                                'backup_file': backup_path,
                            },
                        )
                        result = self.restart_service(service_name=svc)
                        restart_results.append({'service': svc, **result})
                    else:
                        results.append(
                            {
                                'file': conf_path,
                                'updated': False,
                                'message': f"use_sandbox already set"
                                           f" to {new_value}",
                            },
                        )
                else:
                    results.append(
                        {
                            'file': conf_path,
                            'error': '[push] section not found',
                        },
                    )

            except Exception as e:
                results.append(
                    {
                        'file': conf_path,
                        'error': str(e),
                    },
                )

        return {
            'file_updates': results,
            'service_restarts': restart_results,
            'session_id': self.session_id,
        }

    def restart_service(self, service_name='fas-server'):
        """Restart a given service."""
        try:
            if self.ssh_manager:
                result = self.ssh_manager.execute_remote_command(
                    f'sudo systemctl restart {service_name}', timeout=60,
                )
                if result['success']:
                    logger.info(
                        f"[{self.session_id}] Service {service_name}"
                        f" restarted successfully",
                    )
                    return {
                        'success': True,
                        'message': f'Service {service_name}'
                                   f' restarted successfully',
                    }
                else:
                    logger.error(
                        f"[{self.session_id}] Service {service_name}"
                        f" restart failed",
                    )
                    return {
                        'success': False,
                        'error': result.get(
                            'stderr',
                            result.get('error'),
                        ),
                    }
            else:
                result = subprocess.run(
                    ['systemctl', 'restart', service_name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    logger.info(
                        f"Service {service_name} restarted successfully",
                    )
                    return {
                        'success': True,
                        'message': f'Service {service_name} '
                                   f'restarted successfully',
                    }
                else:
                    logger.error(
                        f"Service {service_name} restart fail: {result.stderr}"
                    )
                    return {'success': False, 'error': result.stderr}
        except Exception as e:
            logger.error(
                f"[{self.session_id}] Service {service_name} restart fail: {e}",
            )
            return {'success': False, 'error': str(e)}

    def check_server_status(self, server_type, url, timeout=10):
        """Check server status"""
        try:
            if self.ssh_manager:
                # Use curl through SSH to check server status
                curl_command = (f'curl -s -w "%{{http_code}}" -o /dev/null '
                                f'--connect-timeout {timeout} --max-time '
                                f'{timeout} "{url}"')
                result = self.ssh_manager.execute_remote_command(curl_command)

                if result['success']:
                    status_code = result['stdout'].strip()
                    if status_code == '200':
                        status = 'online'
                        details = {'status_code': 200, 'method': 'ssh_curl'}
                    else:
                        status = 'error'
                        details = {
                            'status_code': status_code,
                            'method': 'ssh_curl',
                        }
                else:
                    status = 'offline'
                    details = {
                        'error': result.get(
                            'stderr',
                            result.get('error'),
                        ),
                        'method': 'ssh_curl',
                    }
            else:
                # Direct HTTP request
                response = requests.get(url, timeout=timeout, verify=False)
                if response.status_code == 200:
                    status = 'online'
                    details = {
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds(),
                        'method': 'direct_http',
                    }
                else:
                    status = 'error'
                    details = {
                        'status_code': response.status_code,
                        'error': f'HTTP {response.status_code}',
                        'method': 'direct_http',
                    }
        except requests.exceptions.Timeout:
            status = 'timeout'
            details = {'error': 'Connection timeout', 'method': 'direct_http'}
        except requests.exceptions.ConnectionError:
            status = 'offline'
            details = {'error': 'Connection failed', 'method': 'direct_http'}
        except Exception as e:
            status = 'error'
            details = {'error': str(e)}

        return {
            'server_type': server_type,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'session_id': self.session_id,
        }

    def get_current_status(self):
        """Get current server status"""
        return {
            'frontend': self.server_status['frontend'],
            'backend': self.server_status['backend'],
            'monitoring_active': self.monitoring_active,
            'ssh_enabled': self.ssh_manager is not None,
            'session_id': self.session_id,
        }

    def start_monitoring(self, frontend_url, backend_url, interval=60):
        """Start server status monitoring"""
        if self.monitoring_active:
            return {
                'message': 'Monitoring is already running',
                'session_id': self.session_id,
            }

        self.monitoring_active = True
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.monitoring_interval = interval

        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True,
        )
        monitor_thread.start()

        logger.info(
            f"[{self.session_id}] Server monitoring started,"
            f" interval: {interval} seconds",
        )
        return {
            'success': True,
            'message': 'Monitoring started',
            'frontend_url': frontend_url,
            'backend_url': backend_url,
            'interval': interval,
            'session_id': self.session_id,
        }

    def stop_monitoring(self):
        """Stop server status monitoring"""
        self.monitoring_active = False
        logger.info(f"[{self.session_id}] Server monitoring stopped")
        return {
            'success': True,
            'message': 'Monitoring stopped',
            'session_id': self.session_id,
        }

    def _monitoring_loop(self):
        """Monitoring loop (runs in background thread)"""
        while self.monitoring_active:
            try:
                # Check frontend server
                frontend_status = self.check_server_status(
                    'frontend', self.frontend_url,
                )
                self.server_status['frontend'] = frontend_status

                # Check backend server
                backend_status = self.check_server_status(
                    'backend', self.backend_url,
                )
                self.server_status['backend'] = backend_status

                logger.info(
                    f"[{self.session_id}] Server status updated -"
                    f" Frontend: {frontend_status['status']},"
                    f" Backend: {backend_status['status']}",
                )

                # Wait for next check
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"[{self.session_id}] Monitoring loop error: {e}")
                time.sleep(5)  # Short wait when error occurs


class SessionManager:
    def __init__(self):
        self.sessions = {}  # session_id -> UserSession
        self.cleanup_thread = None
        self.start_cleanup_thread()

    def create_session(self, ssh_config, expires_in_hours=24):
        """Create a new user session"""
        # Generate secure session ID
        session_id = self._generate_session_id()

        # Create session
        session = UserSession(session_id, ssh_config, expires_in_hours)

        if session.ssh_manager is None:
            return None, "Failed to establish SSH connection"

        self.sessions[session_id] = session
        logger.info(
            f"Created new session {session_id}"
            f" for {ssh_config.get('jumpbox_host')}"
            f" -> {ssh_config.get('target_host')}",
        )

        return session_id, None

    def get_session(self, session_id):
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired():
            self.delete_session(session_id)
            return None

        session.update_last_accessed()
        return session

    def delete_session(self, session_id):
        """Delete a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.ops_manager and session.ops_manager.monitoring_active:
                session.ops_manager.stop_monitoring()
            if session.ssh_manager:
                session.ssh_manager.close()
                logger.info(f"Terminal SSH Client of session {session_id}")
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")

    def list_sessions(self):
        """List all active sessions"""
        return {
            session_id: session.get_session_info()
            for session_id, session in self.sessions.items()
        }

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]

        for session_id in expired_sessions:
            self.delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def _generate_session_id(self):
        """Generate a secure session ID"""
        # Generate random token
        random_bytes = secrets.token_bytes(32)
        timestamp = str(int(time.time()))

        # Create hash
        hash_input = random_bytes + timestamp.encode()
        session_hash = hashlib.sha256(hash_input).hexdigest()

        return f"fto_{session_hash[:32]}"  # fto = FortiToken Ops

    def start_cleanup_thread(self):
        """Start background thread to cleanup expired sessions"""

        def cleanup_loop():
            while True:
                try:
                    self.cleanup_expired_sessions()
                    time.sleep(3600)  # Cleanup every hour
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
                    time.sleep(60)  # Wait 1 minute on error

        self.cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("Session cleanup thread started")


class MessageClient:
    def init_message(self, status):
        message = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "Test Notification",
            "themeColor": "0076D7",
            "title": "FIC Server Config Update",
            "text": status,
            "sections": [
                {
                    "activityTitle": "User Info",
                    "facts": [
                        {"name": "Username", "value": "FIC-Ops"},
                        # You can add more fields here as needed
                    ],
                },
            ]
        }
        self._send_message_to_ms_teams_(message)

    @classmethod
    def _send_message_to_ms_teams_(cls, message):
        response = requests.post(
            MS_TEAMS_WEHOOK,
            json=message,
        )
        logger.info("Sent!" if response.ok else f"Error: {response.text}")


# Global session manager
session_manager = SessionManager()