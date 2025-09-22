"""
Simple Blender Auto-Downloader for Windows and Linux only
"""
import os
import platform
import urllib.request
import zipfile
import tarfile

# Simple configuration - only Windows and Linux
BLENDER_VERSION = "4.5.3"
DOWNLOAD_URLS = {
    "Windows": f"https://download.blender.org/release/Blender4.5/blender-{BLENDER_VERSION}-windows-x64.zip",
    "Linux": f"https://download.blender.org/release/Blender4.5/blender-{BLENDER_VERSION}-linux-x64.tar.xz"
}

# Use shorter names for easier access (following Linux guide recommendation)
EXTRACT_FOLDERS = {
    "Windows": f"blender-{BLENDER_VERSION}-windows-x64",
    "Linux": "blender"  # Renamed to shorter "blender" folder for Linux convenience
}

BLENDER_EXECUTABLES = {
    "Windows": "blender.exe",
    "Linux": "blender"  # Linux executable inside the blender folder
}

def get_platform():
    """Get current platform (Windows or Linux only)"""
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Linux":
        return "Linux"
    else:
        raise Exception(f"Unsupported platform: {system}. Only Windows and Linux are supported.")

def download_blender(node_dir):
    """Download and extract Blender for current platform"""
    current_platform = get_platform()
    url = DOWNLOAD_URLS[current_platform]
    extract_folder = EXTRACT_FOLDERS[current_platform]
    
    # Check if already exists
    blender_dir = os.path.join(node_dir, extract_folder)
    executable_path = os.path.join(blender_dir, BLENDER_EXECUTABLES[current_platform])
    
    if os.path.exists(executable_path):
        print(f"Blender already exists at: {executable_path}")
        return executable_path
    
    print(f"Downloading Blender {BLENDER_VERSION} for {current_platform}...")
    
    # Download
    filename = url.split("/")[-1]
    download_path = os.path.join(node_dir, filename)
    
    try:
        urllib.request.urlretrieve(url, download_path)
        print(f"Downloaded: {filename}")
        
        # Extract
        print(f"Extracting {filename}...")
        if current_platform == "Windows":
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(node_dir)
        else:  # Linux
            # Extract tar.xz and rename to shorter "blender" folder (following Linux guide)
            temp_extract_name = f"blender-{BLENDER_VERSION}-linux-x64"
            with tarfile.open(download_path, 'r:xz') as tar_ref:
                tar_ref.extractall(node_dir)
            
            # Rename extracted folder to shorter "blender" name for convenience
            temp_path = os.path.join(node_dir, temp_extract_name)
            final_path = os.path.join(node_dir, "blender")
            if os.path.exists(temp_path):
                if os.path.exists(final_path):
                    import shutil
                    shutil.rmtree(final_path)  # Remove old version
                os.rename(temp_path, final_path)
                print(f"Renamed to shorter folder name: blender")
        
        # Clean up download file
        os.remove(download_path)
        print(f"Cleaned up: {filename}")
        
        # Set executable permissions on Linux (following Linux guide)
        if current_platform == "Linux":
            os.chmod(executable_path, 0o755)
            print(f"Made executable: {executable_path}")
            
            # Also set permissions on any other binaries in the blender folder
            blender_bin_dir = os.path.dirname(executable_path)
            for item in os.listdir(blender_bin_dir):
                item_path = os.path.join(blender_bin_dir, item)
                if os.path.isfile(item_path) and not item.endswith(('.py', '.txt', '.md')):
                    try:
                        os.chmod(item_path, 0o755)
                    except:
                        pass  # Ignore permission errors on non-executable files
        
        print(f"Blender {BLENDER_VERSION} ready at: {executable_path}")
        return executable_path
        
    except Exception as e:
        print(f"Error downloading Blender: {e}")
        if os.path.exists(download_path):
            os.remove(download_path)
        raise

def get_blender_path(node_dir):
    """Get Blender executable path, download if needed"""
    current_platform = get_platform()
    extract_folder = EXTRACT_FOLDERS[current_platform]
    executable = BLENDER_EXECUTABLES[current_platform]
    
    blender_path = os.path.join(node_dir, extract_folder, executable)
    
    if os.path.exists(blender_path):
        return blender_path
    else:
        return download_blender(node_dir)