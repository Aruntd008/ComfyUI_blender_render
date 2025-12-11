import os
import subprocess
import torch
import numpy as np
from PIL import Image
import tempfile
import platform

def get_default_blender_path():
    """Get Blender executable path using relative paths (following Linux guide approach)"""
    node_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        from .blender_downloader import get_blender_path
        return get_blender_path(node_dir)
    except Exception as e:
        print(f"Auto-downloader failed: {e}")
    
    system = platform.system()
    if system == "Windows":
        blender_path = os.path.join(node_dir, "blender-4.5.3-windows-x64", "blender.exe")
    elif system == "Linux":
        blender_path = os.path.join(node_dir, "blender", "blender")
    else:
        raise Exception(f"Unsupported platform: {system}. Only Windows and Linux are supported.")
    
    if os.path.exists(blender_path):
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
        else:
            raise FileNotFoundError(f"Blender not found at: {blender_path}. Please check auto-download or manually extract to 'blender' folder.")

class BlenderRenderNode:
    @classmethod
    def INPUT_TYPES(cls):
        node_dir = os.path.dirname(os.path.abspath(__file__))
        blend_files = [f for f in os.listdir(node_dir) if f.endswith('.blend')]

        if not blend_files:
            blend_files = ["untitled.blend"]

        return {
            "required": {
                "blend_file": (blend_files, {"default": blend_files[0]}),
                "diffuse_texture": ("IMAGE",),
                "width_ratio": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0}),
                "height_ratio": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 100.0}),
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
    
    @classmethod  
    def IS_CHANGED(cls, **kwargs):
        import time
        return str(time.time())

    def render(self, blend_file, diffuse_texture, width_ratio=1.0, height_ratio=1.0, use_gpu=True, samples=128, use_denoising=True, adaptive_sampling=True):
        node_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(node_dir, "blender_render_script.py")

        blender_path = get_default_blender_path()
        if not blender_path or not os.path.exists(blender_path):
            raise FileNotFoundError(f"Blender executable not found. Expected at: {blender_path}")

        blend_file_path = os.path.join(node_dir, blend_file)
        if not os.path.exists(blend_file_path):
            raise FileNotFoundError(f"Blender scene file not found at: {blend_file_path}")
        
        import time
        timestamp = int(time.time())
        output_path = os.path.join(node_dir, f"render_output_{timestamp}.png")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        temp_dir = tempfile.mkdtemp(prefix="comfyui_blender_textures_")
        
        try:
            # Save texture input
            if diffuse_texture.dim() == 4:
                diffuse_tensor = diffuse_texture.squeeze(0)
            else:
                diffuse_tensor = diffuse_texture
            
            tex_array = (diffuse_tensor.cpu().numpy() * 255).astype(np.uint8)
            tex_image = Image.fromarray(tex_array)
            
            diffuse_path = os.path.join(temp_dir, "input_diffuse.png")
            tex_image.save(diffuse_path, optimize=False, compress_level=0)
            print(f"Saved diffuse texture to: {diffuse_path}")

            cmd = [
                blender_path,
                "-b",
                blend_file_path,
                "-P", script_path,
                "--",
                diffuse_path,
                output_path,
                str(width_ratio),
                str(height_ratio),
                str(use_gpu).lower(),
                str(samples),
                str(use_denoising).lower(),
                str(adaptive_sampling).lower()
            ]
            
            print(f"Running Blender render with GPU: {use_gpu}, Samples: {samples}")
            print("Command:", " ".join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]))
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=node_dir)
                print("Blender render completed successfully!")
                if result.stdout:
                    print("Blender output:", result.stdout[-500:])
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
                # Dump internal blender error if possible
                pass
                raise

            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Render output not found: {output_path}")
            
            img = Image.open(output_path).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None,]
            
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"Warning: Could not clean up output file: {e}")
            
            return (tensor,)
            
        finally:
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp dir {temp_dir}: {e}")

NODE_CLASS_MAPPINGS = {
    "Blender Render Node": BlenderRenderNode
}
