"""
Automatic uploader for Mave.digital podcast hosting.
Supports multiple upload methods: WebDAV, FTP, SFTP, rsync.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict
import requests
from urllib.parse import urljoin

logger = logging.getLogger("mave_uploader")


class MaveUploader:
    """Upload files to Mave.digital hosting."""
    
    def __init__(
        self,
        site_url: str,
        upload_method: str = "webdav",
        credentials: Optional[Dict] = None
    ):
        """
        Initialize Mave uploader.
        
        Args:
            site_url: Mave.digital site URL (e.g., https://cloud.mave.digital/67282)
            upload_method: Upload method - 'webdav', 'ftp', 'sftp', 'rsync', or 'manual'
            credentials: Dict with authentication credentials
                         For WebDAV: {'username': str, 'password': str}
                         For FTP/SFTP: {'host': str, 'username': str, 'password': str, 'port': int}
        """
        self.site_url = site_url.rstrip('/')
        self.upload_method = upload_method.lower()
        self.credentials = credentials or {}
        
    def upload_file(self, local_path: Path, remote_filename: str, progress_callback=None) -> bool:
        """
        Upload a file to Mave.digital.
        
        Args:
            local_path: Local file path
            remote_filename: Remote filename (will be placed in media/ folder)
            progress_callback: Optional callback for upload progress
            
        Returns:
            True if upload successful, False otherwise
        """
        if not local_path.exists():
            logger.error(f"Local file not found: {local_path}")
            return False
            
        logger.info(f"Uploading {local_path.name} using method: {self.upload_method}")
        
        try:
            if self.upload_method == "webdav":
                return self._upload_webdav(local_path, remote_filename, progress_callback)
            elif self.upload_method == "ftp":
                return self._upload_ftp(local_path, remote_filename, progress_callback)
            elif self.upload_method == "sftp":
                return self._upload_sftp(local_path, remote_filename, progress_callback)
            elif self.upload_method == "rsync":
                return self._upload_rsync(local_path, remote_filename)
            elif self.upload_method == "manual":
                logger.info("Manual upload mode - skipping automatic upload")
                logger.info(f"Please manually upload: {local_path} to {self.site_url}/media/{remote_filename}")
                return True
            else:
                logger.error(f"Unknown upload method: {self.upload_method}")
                return False
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def _upload_webdav(self, local_path: Path, remote_filename: str, progress_callback=None) -> bool:
        """Upload via WebDAV protocol."""
        try:
            import webdav3.client as wc
        except ImportError:
            logger.error("webdavclient3 not installed. Run: pip install webdavclient3")
            return False
        
        try:
            webdav_url = self.credentials.get('webdav_url', f"{self.site_url}/webdav")
            
            options = {
                'webdav_hostname': webdav_url,
                'webdav_login': self.credentials.get('username'),
                'webdav_password': self.credentials.get('password'),
            }
            
            client = wc.Client(options)
            
            # Create media directory if not exists
            try:
                client.mkdir("media")
            except:
                pass  # Directory might already exist
            
            # Upload file
            remote_path = f"media/{remote_filename}"
            client.upload_sync(remote_path=remote_path, local_path=str(local_path))
            
            logger.info(f"Successfully uploaded via WebDAV: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"WebDAV upload failed: {e}")
            return False
    
    def _upload_ftp(self, local_path: Path, remote_filename: str, progress_callback=None) -> bool:
        """Upload via FTP protocol."""
        try:
            from ftplib import FTP
        except ImportError:
            logger.error("ftplib not available")
            return False
        
        try:
            host = self.credentials.get('host')
            username = self.credentials.get('username')
            password = self.credentials.get('password')
            port = self.credentials.get('port', 21)
            
            ftp = FTP()
            ftp.connect(host, port)
            ftp.login(username, password)
            
            # Change to or create media directory
            try:
                ftp.cwd('media')
            except:
                ftp.mkd('media')
                ftp.cwd('media')
            
            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
            
            ftp.quit()
            
            logger.info(f"Successfully uploaded via FTP: media/{remote_filename}")
            return True
            
        except Exception as e:
            logger.error(f"FTP upload failed: {e}")
            return False
    
    def _upload_sftp(self, local_path: Path, remote_filename: str, progress_callback=None) -> bool:
        """Upload via SFTP protocol."""
        try:
            import paramiko
        except ImportError:
            logger.error("paramiko not installed. Run: pip install paramiko")
            return False
        
        try:
            host = self.credentials.get('host')
            username = self.credentials.get('username')
            password = self.credentials.get('password')
            port = self.credentials.get('port', 22)
            
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            # Create media directory if not exists
            try:
                sftp.mkdir('media')
            except:
                pass
            
            # Upload file
            remote_path = f"media/{remote_filename}"
            sftp.put(str(local_path), remote_path)
            
            sftp.close()
            transport.close()
            
            logger.info(f"Successfully uploaded via SFTP: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"SFTP upload failed: {e}")
            return False
    
    def _upload_rsync(self, local_path: Path, remote_filename: str) -> bool:
        """Upload via rsync command."""
        import subprocess
        
        try:
            remote_host = self.credentials.get('host')
            remote_user = self.credentials.get('username')
            remote_path = self.credentials.get('remote_path', '/var/www/podcast')
            
            rsync_cmd = [
                'rsync',
                '-avz',
                '--progress',
                str(local_path),
                f"{remote_user}@{remote_host}:{remote_path}/media/{remote_filename}"
            ]
            
            result = subprocess.run(rsync_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully uploaded via rsync: {remote_filename}")
                return True
            else:
                logger.error(f"rsync failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"rsync upload failed: {e}")
            return False
    
    def upload_rss(self, rss_file: Path) -> bool:
        """
        Upload RSS feed file.
        
        Args:
            rss_file: Local RSS file path
            
        Returns:
            True if upload successful
        """
        return self.upload_file(rss_file, "rss.xml")
    
    def test_connection(self) -> bool:
        """
        Test connection to Mave.digital.
        
        Returns:
            True if connection successful
        """
        try:
            if self.upload_method == "webdav":
                try:
                    import webdav3.client as wc
                    webdav_url = self.credentials.get('webdav_url', f"{self.site_url}/webdav")
                    options = {
                        'webdav_hostname': webdav_url,
                        'webdav_login': self.credentials.get('username'),
                        'webdav_password': self.credentials.get('password'),
                    }
                    client = wc.Client(options)
                    client.list()
                    logger.info("WebDAV connection successful")
                    return True
                except Exception as e:
                    logger.error(f"WebDAV connection failed: {e}")
                    return False
                    
            elif self.upload_method in ["ftp", "sftp"]:
                # Test basic connectivity
                host = self.credentials.get('host')
                port = self.credentials.get('port', 21 if self.upload_method == 'ftp' else 22)
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    logger.info(f"{self.upload_method.upper()} connection test successful")
                    return True
                else:
                    logger.error(f"Cannot connect to {host}:{port}")
                    return False
                    
            elif self.upload_method == "manual":
                logger.info("Manual upload mode - no connection test needed")
                return True
                
            else:
                logger.warning(f"Connection test not implemented for {self.upload_method}")
                return True
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Convenience function for quick uploads
def upload_to_mave(
    audio_file: Path,
    rss_file: Path,
    site_url: str,
    method: str = "manual",
    credentials: Optional[Dict] = None
) -> bool:
    """
    Quick upload function.
    
    Args:
        audio_file: Audio file to upload
        rss_file: RSS file to upload
        site_url: Mave.digital site URL
        method: Upload method
        credentials: Authentication credentials
        
    Returns:
        True if both uploads successful
    """
    uploader = MaveUploader(site_url, method, credentials)
    
    # Test connection first
    if not uploader.test_connection():
        logger.error("Connection test failed, aborting upload")
        return False
    
    # Upload audio
    audio_success = uploader.upload_file(audio_file, audio_file.name)
    
    # Upload RSS
    rss_success = uploader.upload_rss(rss_file)
    
    return audio_success and rss_success
