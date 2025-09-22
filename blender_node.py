import os
import subprocess
import torch
import numpy as np
from PIL import Image
import tempfile
import platform

def get_default_blender_path():
    """Get Blender executable path using relative paths (following Linux guide approach)"""
    # Path to Blender executable relative to the node folder (as per Linux guide)
    node_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try using the simple downloader first
    try:
        from .blender_downloader import get_blender_path
        return get_blender_path(node_dir)
    except Exception as e:
        print(f"Auto-downloader failed: {e}")
    
    # Manual detection using relative paths (following Linux guide)
    system = platform.system()
    if system == "Windows":
        # Windows: Full folder name
        blender_path = os.path.join(node_dir, "blender-4.5.3-windows-x64", "blender.exe")
    elif system == "Linux":
        # Linux: Shorter "blender" folder name (as per Linux guide)
        blender_path = os.path.join(node_dir, "blender", "blender")
    else:
        raise Exception(f"Unsupported platform: {system}. Only Windows and Linux are supported.")
    
    # Verify the executable exists and is accessible
    if os.path.exists(blender_path):
        # On Linux, verify it's executable (following Linux guide)
        if system == "Linux":
            if not os.access(blender_path, os.X_OK):
                try:
                    os.chmod(blender_path, 0o755)
                    print(f"Fixed executable permissions: {blender_path}")
                except:
                    pass
        return blender_path
    else:
        if system == "Windows":
            raise FileNotFoundError(f"Blender not found at: {blender_path}. Auto-download may have failed.")
        else:  # Linux
            raise FileNotFoundError(f"Blender not found at: {blender_path}. Please check auto-download or manually extract to 'blender' folder.")

class BlenderRenderNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "diffuse_texture": ("IMAGE",),
                "normal_texture": ("IMAGE",),
                "roughness_texture": ("IMAGE",),
                "specular_texture": ("IMAGE",),
                "use_gpu": ("BOOLEAN", {"default": True}),
                "samples": ("INT", {"default": 128, "min": 1, "max": 4096, "step": 1}),
                "use_denoising": ("BOOLEAN", {"default": True}),
                "adaptive_sampling": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "render"
    CATEGORY = "External/Blender"
    OUTPUT_NODE = False
    
    # Force ComfyUI to reload the node by using a unique hash
    @classmethod  
    def IS_CHANGED(cls, **kwargs):
        import time
        return str(time.time())  # Always return a unique value

    def render(self, diffuse_texture, normal_texture, roughness_texture, specular_texture, use_gpu=True, samples=128, use_denoising=True, adaptive_sampling=True):
        # Get paths relative to the node directory
        node_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(node_dir, "blender_render_script.py")
        
        # Use the auto-detected Blender path
        blender_path = get_default_blender_path()
        if not blender_path or not os.path.exists(blender_path):
            raise FileNotFoundError(f"Blender executable not found. Expected at: {blender_path}")
        
        # Use the bundled blend file
        blend_file = os.path.join(node_dir, "untitled.blend")
        if not os.path.exists(blend_file):
            raise FileNotFoundError(f"Blender scene file not found at: {blend_file}")
        
        # Generate unique output filename with timestamp
        import time
        timestamp = int(time.time())
        output_path = os.path.join(node_dir, f"render_output_{timestamp}.png")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create temporary directory for textures
        temp_dir = tempfile.mkdtemp(prefix="comfyui_blender_textures_")
        
        try:
            # Save texture inputs to temporary files
            texture_paths = {}
            texture_inputs = {
                "diffuse": diffuse_texture,
                "normal": normal_texture,
                "roughness": roughness_texture,
                "specular": specular_texture
            }
            
            for tex_name, tex_tensor in texture_inputs.items():
                # Convert tensor to PIL Image
                if tex_tensor.dim() == 4:  # Remove batch dimension if present
                    tex_tensor = tex_tensor.squeeze(0)
                
                # Convert from [0,1] float to [0,255] uint8
                tex_array = (tex_tensor.cpu().numpy() * 255).astype(np.uint8)
                tex_image = Image.fromarray(tex_array)
                
                # Save to temporary file with maximum quality
                tex_path = os.path.join(temp_dir, f"input_{tex_name}.png")
                tex_image.save(tex_path, optimize=False, compress_level=0)  # No compression for max quality
                texture_paths[tex_name] = tex_path
                print(f"Saved {tex_name} texture to: {tex_path}")

            # Prepare command following Linux guide approach: 
            # subprocess.run([blender_path, "-b", "-P", script_path])
            cmd = [
                blender_path,
                "-b",  # Background mode (no GUI)
                blend_file,  # .blend file to open
                "-P", script_path,  # Python script to execute
                "--",  # Separator for script arguments
                texture_paths["diffuse"],
                texture_paths["normal"], 
                texture_paths["roughness"],
                texture_paths["specular"],
                output_path,
                str(use_gpu).lower(),
                str(samples),
                str(use_denoising).lower(),
                str(adaptive_sampling).lower()
            ]
            
            print(f"Running Blender render with GPU: {use_gpu}, Samples: {samples}")
            print("Command:", " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]))
            
            try:
                # Use relative path approach as recommended in Linux guide
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, 
                                      cwd=node_dir)  # Set working directory to node folder
                print("Blender render completed successfully!")
                if result.stdout:
                    print("Blender output:", result.stdout[-500:])  # Show last 500 chars
                if result.stderr:
                    print("Blender warnings:", result.stderr[-500:])
            except PermissionError as e:
                if platform.system() == "Windows":
                    error_msg = f"Permission denied when trying to execute Blender. Try running: Unblock-File '{blender_path}' in PowerShell as administrator."
                else:  # Linux
                    error_msg = f"Permission denied when trying to execute Blender. Try running: chmod +x '{blender_path}'"
                print(error_msg)
                raise PermissionError(error_msg) from e
            except subprocess.CalledProcessError as e:
                print(f"Blender render failed with code {e.returncode}")
                print("Error output:", e.stderr)
                raise

            # Load the rendered image
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Render output not found: {output_path}")
            
            img = Image.open(output_path).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None,]  # add batch dimension
            
            # Clean up the output file after loading
            try:
                os.remove(output_path)
                print(f"Cleaned up render output: {output_path}")
            except Exception as e:
                print(f"Warning: Could not clean up output file: {e}")
            
            return (tensor,)
            
        finally:
            # Clean up temporary files
            import shutil
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up temp dir {temp_dir}: {e}")

NODE_CLASS_MAPPINGS = {
    "Blender Render Node": BlenderRenderNode
}