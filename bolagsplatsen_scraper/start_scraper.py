#!/usr/bin/env python3
"""
Cloud-optimized startup script for Bolagsplatsen Scraper
This script ensures proper environment setup for Render/Heroku deployment
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_cloud_environment():
    """Setup environment for cloud deployment"""
    
    # Ensure we're in the right directory
    current_dir = Path.cwd()
    print(f"Current working directory: {current_dir}")
    
    # Check if we're in a cloud environment
    is_cloud = any([
        os.environ.get('RENDER', False),
        os.environ.get('HEROKU', False),
        os.environ.get('PORT', False),
        os.environ.get('DYNO', False)
    ])
    
    if is_cloud:
        print("🌐 Cloud environment detected")
        print("📁 Setting up cloud-optimized configuration...")
        
        # Ensure output directory exists and is writable
        output_dir = current_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Test write permissions
        test_file = output_dir / "test_write.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✅ Write permissions confirmed")
        except Exception as e:
            print(f"⚠️  Write permission issue: {e}")
            return False
    else:
        print("💻 Local environment detected")
    
    return True

def run_scraper():
    """Run the Scrapy spider with cloud-optimized settings"""
    
    if not setup_cloud_environment():
        print("❌ Environment setup failed")
        return False
    
    print("🚀 Starting Bolagsplatsen scraper...")
    
    try:
        # Run the scraper with cloud-optimized settings
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", "bolagsplatsen",
            "-s", "LOG_LEVEL=INFO",
            "-s", "TELNETCONSOLE_ENABLED=False",
            "-s", "MEMUSAGE_ENABLED=True",
            "-s", "MEMUSAGE_LIMIT_MB=512"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print("✅ Scraper completed successfully")
            print(f"📊 Output: {result.stdout}")
            
            # Check if output file was created
            output_file = Path("bolagsplatsen_listings.json")
            if output_file.exists():
                file_size = output_file.stat().st_size
                print(f"📁 Output file created: {output_file} ({file_size} bytes)")
                return True
            else:
                print("⚠️  Output file not found")
                return False
        else:
            print(f"❌ Scraper failed with exit code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running scraper: {e}")
        return False

if __name__ == "__main__":
    success = run_scraper()
    sys.exit(0 if success else 1)
