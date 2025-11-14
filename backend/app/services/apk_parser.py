"""
APK/IPA metadata parser service
"""
import hashlib
import logging
import os
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_android_manifest(apk_path: str) -> Dict[str, any]:
    """
    Parse AndroidManifest.xml from APK using aapt2 or apkanalyzer
    Falls back to basic ZIP parsing if tools are not available
    """
    metadata = {}

    # Try using aapt2 (Android Asset Packaging Tool)
    try:
        result = subprocess.run(
            ["aapt2", "dump", "badging", apk_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            output = result.stdout

            # Parse package name
            package_match = re.search(r"package: name='([^']+)'", output)
            if package_match:
                metadata["package_name"] = package_match.group(1)

            # Parse version name
            version_name_match = re.search(r"versionName='([^']+)'", output)
            if version_name_match:
                metadata["version_name"] = version_name_match.group(1)

            # Parse version code
            version_code_match = re.search(r"versionCode='(\d+)'", output)
            if version_code_match:
                metadata["version_code"] = int(version_code_match.group(1))

            # Parse SDK versions
            min_sdk_match = re.search(r"sdkVersion:'(\d+)'", output)
            if min_sdk_match:
                metadata["min_sdk_version"] = min_sdk_match.group(1)

            target_sdk_match = re.search(r"targetSdkVersion:'(\d+)'", output)
            if target_sdk_match:
                metadata["target_sdk_version"] = target_sdk_match.group(1)

            # Parse app name
            app_label_match = re.search(r"application-label:'([^']+)'", output)
            if app_label_match:
                metadata["app_name"] = app_label_match.group(1)

            return metadata
    except FileNotFoundError:
        logger.warning("aapt2 not found, trying alternative methods")
    except Exception as e:
        logger.error(f"Error using aapt2: {e}")

    # Fallback: Try basic ZIP parsing
    try:
        with zipfile.ZipFile(apk_path, 'r') as apk_zip:
            # Try to read AndroidManifest.xml (it's binary, so limited info)
            if 'AndroidManifest.xml' in apk_zip.namelist():
                manifest_data = apk_zip.read('AndroidManifest.xml')

                # Try to extract package name from binary manifest
                # This is a simple heuristic and may not always work
                package_match = re.search(rb'([a-z]+\.[a-z]+\.[a-z]+[a-z0-9._]*)', manifest_data)
                if package_match:
                    try:
                        metadata["package_name"] = package_match.group(1).decode('utf-8')
                    except:
                        pass
    except Exception as e:
        logger.error(f"Error parsing APK as ZIP: {e}")

    return metadata


def parse_ios_info_plist(ipa_path: str) -> Dict[str, any]:
    """
    Parse Info.plist from IPA file
    """
    metadata = {}

    try:
        with zipfile.ZipFile(ipa_path, 'r') as ipa_zip:
            # Find Info.plist (usually in Payload/*.app/Info.plist)
            plist_files = [f for f in ipa_zip.namelist() if f.endswith('Info.plist')]

            if not plist_files:
                logger.warning("No Info.plist found in IPA")
                return metadata

            # Read the first Info.plist found
            plist_path = plist_files[0]
            plist_data = ipa_zip.read(plist_path)

            # Try to parse plist using plistlib
            try:
                import plistlib
                plist_dict = plistlib.loads(plist_data)

                # Extract common fields
                metadata["bundle_id"] = plist_dict.get("CFBundleIdentifier", "")
                metadata["version_name"] = plist_dict.get("CFBundleShortVersionString", "")
                metadata["version_code"] = plist_dict.get("CFBundleVersion", "")
                metadata["app_name"] = plist_dict.get("CFBundleDisplayName", plist_dict.get("CFBundleName", ""))
                metadata["min_os_version"] = plist_dict.get("MinimumOSVersion", "")

            except Exception as e:
                logger.error(f"Error parsing plist: {e}")

                # Fallback: regex parsing
                try:
                    plist_text = plist_data.decode('utf-8')

                    bundle_id_match = re.search(r'<key>CFBundleIdentifier</key>\s*<string>([^<]+)</string>', plist_text)
                    if bundle_id_match:
                        metadata["bundle_id"] = bundle_id_match.group(1)

                    version_match = re.search(r'<key>CFBundleShortVersionString</key>\s*<string>([^<]+)</string>', plist_text)
                    if version_match:
                        metadata["version_name"] = version_match.group(1)

                except Exception as e2:
                    logger.error(f"Error in fallback plist parsing: {e2}")

    except Exception as e:
        logger.error(f"Error reading IPA file: {e}")

    return metadata


def parse_app_metadata(file_path: str, platform: str) -> Dict[str, any]:
    """
    Parse app metadata from APK or IPA file

    Args:
        file_path: Path to the APK/IPA file
        platform: 'android' or 'ios'

    Returns:
        Dictionary with parsed metadata
    """
    metadata = {
        "file_size": os.path.getsize(file_path),
        "file_hash": calculate_file_hash(file_path),
        "platform": platform
    }

    if platform.lower() == "android":
        manifest_data = parse_android_manifest(file_path)
        metadata.update(manifest_data)
    elif platform.lower() == "ios":
        plist_data = parse_ios_info_plist(file_path)
        metadata.update(plist_data)

    return metadata


def get_platform_from_extension(filename: str) -> Optional[str]:
    """
    Determine platform from file extension

    Args:
        filename: Name of the file

    Returns:
        'android' or 'ios' or None
    """
    ext = Path(filename).suffix.lower()
    if ext == '.apk':
        return 'android'
    elif ext in ['.ipa', '.app']:
        return 'ios'
    return None
