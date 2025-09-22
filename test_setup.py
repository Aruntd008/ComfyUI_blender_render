#!/usr/bin/env python3
"""
Test script to verify Blender portable setup on Linux/Windows
Following the Linux guide approach
"""
import os
import platform
import subprocess
from blender_downloader import get_blender_path

def test_setup():
    """Test the portable Blender setup"""
    print("=== Testing Portable Blender Setup ===")
    
    # Get node directory
    node_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Node directory: {node_dir}")
    
    # Test platform detection
    system = platform.system()
    print(f"Platform: {system}")
    
    if system not in ["Windows", "Linux"]:
        print("❌ Unsupported platform")
        return False
    
    try:
        # Test Blender path detection
        blender_path = get_blender_path(node_dir)
        print(f"Blender path: {blender_path}")
        
        # Test if executable exists
        if not os.path.exists(blender_path):
            print("❌ Blender executable not found")
            return False
        
        print("✅ Blender executable found")
        
        # Test executable permissions (Linux)
        if system == "Linux":
            if not os.access(blender_path, os.X_OK):
                print("❌ Blender executable not executable")
                return False
            print("✅ Blender executable has correct permissions")
        
        # Test Blender version (following Linux guide verification)
        try:
            result = subprocess.run([blender_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
                print(f"✅ Blender version: {version_line}")
            else:
                print("❌ Blender version test failed")
                return False
        except Exception as e:
            print(f"❌ Blender execution test failed: {e}")
            return False
        
        # Test scene file
        blend_file = os.path.join(node_dir, "untitled.blend")
        if os.path.exists(blend_file):
            print("✅ Scene file (untitled.blend) found")
        else:
            print("❌ Scene file (untitled.blend) not found")
            return False
        
        print("✅ All tests passed! Setup is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_setup()
    exit(0 if success else 1)