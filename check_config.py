#!/usr/bin/env python3
"""
Configuration checker for YouTube to Podcast converter.
Validates environment, directories, and deployment readiness.
"""

import sys
from pathlib import Path
from typing import List, Tuple
import os
from urllib.parse import urlparse

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_env_var(var_name: str, required: bool = True, expected_prefix: str = None) -> Tuple[bool, str]:
    """
    Check if environment variable is set and valid.
    
    Returns:
        (is_valid, value)
    """
    value = os.getenv(var_name)
    
    if value is None or value == '':
        if required:
            return False, ''
        return True, ''
    
    # Validate URL format if expected
    if expected_prefix and not (value.startswith('http://') or value.startswith('https://')):
        return False, value
    
    return True, value

def check_directory(path: Path, should_exist: bool = True) -> bool:
    """Check if directory exists and is writable."""
    if not path.exists():
        if should_exist:
            return False
        return True
    
    if not path.is_dir():
        return False
    
    # Check if writable
    test_file = path / '.write_test'
    try:
        test_file.touch()
        test_file.unlink()
        return True
    except Exception:
        return False

def main():
    """Run all configuration checks."""
    
    print_header("🔍 YouTube to Podcast - Configuration Checker")
    
    errors = []
    warnings = []
    
    # =========================================================================
    # 1. Environment Variables Check
    # =========================================================================
    print_header("1️⃣  Environment Variables")
    
    # Required variables
    required_vars = {
        'SITE_URL': 'https://',
        'MEDIA_BASE_URL': 'https://',
    }
    
    for var_name, prefix in required_vars.items():
        is_valid, value = check_env_var(var_name, required=True, expected_prefix=prefix)
        
        if not is_valid:
            if not value:
                print_error(f"{var_name} is not set")
                errors.append(f"{var_name} must be set in environment variables")
            else:
                print_error(f"{var_name} has invalid format: {value}")
                errors.append(f"{var_name} must start with http:// or https://")
        else:
            print_success(f"{var_name} = {value}")
    
    # Optional but recommended variables
    optional_vars = {
        'PODCAST_TITLE': None,
        'PODCAST_AUTHOR': None,
        'PODCAST_DESCRIPTION': None,
        'AUDIO_FORMAT': None,
        'FEED_MAX_ITEMS': None,
        'AUTO_PUBLISH': None,
    }
    
    print("\n" + Colors.BOLD + "Optional Variables:" + Colors.END)
    for var_name, _ in optional_vars.items():
        is_valid, value = check_env_var(var_name, required=False)
        if value:
            print_success(f"{var_name} = {value}")
        else:
            print_info(f"{var_name} not set (using default)")
    
    # Auto-publish specific checks
    auto_publish = os.getenv('AUTO_PUBLISH', 'manual')
    if auto_publish == 'github':
        print("\n" + Colors.BOLD + "GitHub Auto-Publish Configuration:" + Colors.END)
        is_valid, github_repo = check_env_var('GITHUB_REPO', required=False)
        is_valid2, github_branch = check_env_var('GITHUB_BRANCH', required=False)
        
        if github_repo:
            print_success(f"GITHUB_REPO = {github_repo}")
        else:
            print_warning("GITHUB_REPO not set (auto-publish may fail)")
            warnings.append("Set GITHUB_REPO for GitHub auto-publish")
        
        if github_branch:
            print_success(f"GITHUB_BRANCH = {github_branch}")
        else:
            print_info("GITHUB_BRANCH not set (using default: main)")
    
    elif auto_publish == 'mave':
        print("\n" + Colors.BOLD + "Mave.io Auto-Publish Configuration:" + Colors.END)
        mave_vars = ['MAVE_WEBDAV_URL', 'MAVE_USERNAME', 'MAVE_PASSWORD']
        mave_ok = True
        for var in mave_vars:
            is_valid, value = check_env_var(var, required=False)
            if value:
                # Mask password
                display_value = '***' if 'PASSWORD' in var else value
                print_success(f"{var} = {display_value}")
            else:
                print_warning(f"{var} not set")
                mave_ok = False
        
        if not mave_ok:
            warnings.append("Incomplete Mave.io configuration")
    
    # =========================================================================
    # 2. Directory Structure Check
    # =========================================================================
    print_header("2️⃣  Directory Structure")
    
    base_dir = Path(__file__).parent
    podcast_dir = base_dir / "podcast"
    media_dir = podcast_dir / "media"
    
    directories = {
        'Base Directory': base_dir,
        'Podcast Directory': podcast_dir,
        'Media Directory': media_dir,
    }
    
    for name, path in directories.items():
        if check_directory(path, should_exist=False):
            if path.exists():
                print_success(f"{name}: {path} (exists, writable)")
            else:
                print_warning(f"{name}: {path} (will be created)")
        else:
            print_error(f"{name}: {path} (not writable)")
            errors.append(f"{name} is not writable")
    
    # =========================================================================
    # 3. File Permissions Check
    # =========================================================================
    print_header("3️⃣  File Permissions")
    
    rss_file = podcast_dir / "rss.xml"
    
    if rss_file.exists():
        if os.access(rss_file, os.R_OK):
            print_success(f"RSS file readable: {rss_file}")
        else:
            print_error(f"RSS file not readable: {rss_file}")
            errors.append("RSS file exists but not readable")
        
        if os.access(rss_file, os.W_OK):
            print_success(f"RSS file writable: {rss_file}")
        else:
            print_error(f"RSS file not writable: {rss_file}")
            errors.append("RSS file exists but not writable")
    else:
        print_info(f"RSS file does not exist yet: {rss_file}")
    
    # =========================================================================
    # 4. URL Configuration Validation
    # =========================================================================
    print_header("4️⃣  URL Configuration")
    
    site_url = os.getenv('SITE_URL', '')
    media_base_url = os.getenv('MEDIA_BASE_URL', '')
    
    if site_url and media_base_url:
        # Parse URLs
        try:
            site_parsed = urlparse(site_url)
            media_parsed = urlparse(media_base_url)
            
            print_success(f"Site URL scheme: {site_parsed.scheme}")
            print_success(f"Site URL domain: {site_parsed.netloc}")
            print_success(f"Media URL scheme: {media_parsed.scheme}")
            print_success(f"Media URL domain: {media_parsed.netloc}")
            
            # Check if media URL is under site URL
            if not media_base_url.startswith(site_url):
                print_warning("MEDIA_BASE_URL should typically start with SITE_URL")
                warnings.append("MEDIA_BASE_URL doesn't start with SITE_URL (may be intentional)")
            else:
                print_success("MEDIA_BASE_URL is under SITE_URL ✓")
            
            # Suggest Railway URLs if using Railway
            if 'railway.app' in site_parsed.netloc:
                print_info("Railway deployment detected")
                expected_media = f"{site_url}/media"
                if media_base_url != expected_media:
                    print_warning(f"For Railway, MEDIA_BASE_URL should be: {expected_media}")
                
        except Exception as e:
            print_error(f"Failed to parse URLs: {e}")
            errors.append("Invalid URL format")
    
    # =========================================================================
    # 5. Python Dependencies Check
    # =========================================================================
    print_header("5️⃣  Python Dependencies")
    
    required_packages = [
        'flask',
        'feedgen',
        'yt_dlp',
        'python-decouple',
        'flask_cors',
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} not installed")
            errors.append(f"Missing Python package: {package}")
    
    # =========================================================================
    # 6. Configuration Loading Test
    # =========================================================================
    print_header("6️⃣  Configuration Loading Test")
    
    try:
        from config import get_settings
        settings = get_settings()
        print_success("Configuration loaded successfully")
        print_info(f"Podcast Title: {settings.podcast_title}")
        print_info(f"Audio Format: {settings.audio_format}")
        print_info(f"Feed Max Items: {settings.feed_max_items}")
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        errors.append(f"Configuration error: {e}")
    
    # =========================================================================
    # 7. Summary
    # =========================================================================
    print_header("📊 Summary")
    
    if not errors and not warnings:
        print_success("All checks passed! ✅")
        print_info("\nYour configuration is ready for deployment.")
        print_info("You can start the web server with: python web.py")
        return 0
    
    if warnings and not errors:
        print_warning(f"Configuration has {len(warnings)} warning(s):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print_info("\nConfiguration should work, but consider addressing warnings.")
        return 0
    
    if errors:
        print_error(f"Configuration has {len(errors)} error(s):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        
        print("\n" + Colors.BOLD + "🔧 How to fix:" + Colors.END)
        print("\n1. Create/update .env file in the project root:")
        print(f"\n{Colors.YELLOW}   SITE_URL=https://your-app.up.railway.app")
        print(f"   MEDIA_BASE_URL=https://your-app.up.railway.app/media{Colors.END}")
        print("\n2. Or set environment variables on Railway:")
        print(f"   {Colors.BLUE}Railway Dashboard → Settings → Variables{Colors.END}")
        print("\n3. After fixing, run this script again to verify")
        
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
