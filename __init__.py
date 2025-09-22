"""
ComfyUI Blender Render Node - Simple Setup (Windows & Linux only)
"""
import os
import platform
import subprocess

# Import the node
try:
    from .blender_node import BlenderRenderNode
    from .blender_downloader import get_blender_path
except ImportError as e:
    print(f"ComfyUI Blender Render: Import error - {e}")
    BlenderRenderNode = None

def setup_blender():
    """Simple setup for Windows and Linux only"""
    if BlenderRenderNode is None:
        return
    
    system = platform.system()
    if system not in ["Windows", "Linux"]:
        print(f"ComfyUI Blender Render: Unsupported platform {system}. Only Windows and Linux are supported.")
        return
    
    print(f"ComfyUI Blender Render: Setting up for {system}")
    
    node_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Auto-download Blender if needed
        blender_path = get_blender_path(node_dir)
        
        # Windows: Unblock the executable
        if system == "Windows" and os.path.exists(blender_path):
            try:
                subprocess.run([
                    "powershell", "-Command", f"Unblock-File -Path '{blender_path}'"
                ], check=False, capture_output=True)
                print(f"ComfyUI Blender Render: Unblocked Blender executable")
            except Exception as e:
                print(f"ComfyUI Blender Render: Warning - Could not unblock file: {e}")
        
        # Verify Blender executable works (following Linux guide)
        if os.path.exists(blender_path):
            try:
                # Test Blender version (similar to the Linux guide verification)
                result = subprocess.run([blender_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                    print(f"ComfyUI Blender Render: Verified - {version_line}")
                else:
                    print(f"ComfyUI Blender Render: Warning - Blender test failed")
            except Exception as e:
                print(f"ComfyUI Blender Render: Warning - Could not verify Blender: {e}")
        
        print(f"ComfyUI Blender Render: Ready! Blender at {blender_path}")
        
    except Exception as e:
        print(f"ComfyUI Blender Render: Setup error - {e}")

# Run setup
setup_blender()

# Node registration
NODE_CLASS_MAPPINGS = {
    "BlenderRenderNode": BlenderRenderNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BlenderRenderNode": "🎨 Blender Render (Auto-Setup)"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']