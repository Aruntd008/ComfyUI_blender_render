"""
ComfyUI Blender Render Node — Production-safe init.

- Uses system-installed Blender (found via PATH).
- Does NOT block ComfyUI startup if Blender is missing.
- Logs setup results clearly.
"""
import shutil
import subprocess

# Import the node
try:
    from .blender_node import BlenderRenderNode
except ImportError as e:
    print(f"[BlenderRender] Import error — node disabled: {e}")
    BlenderRenderNode = None


def setup_blender():
    """
    Verify system Blender is available on PATH.
    Never raises — just logs warnings if not found.
    ComfyUI will still load; render will fail at runtime with a clear message.
    """
    if BlenderRenderNode is None:
        return

    blender_path = shutil.which("blender")
    if not blender_path:
        print("[BlenderRender] WARNING: 'blender' not found on system PATH. "
              "Render will fail at runtime. Install Blender and add it to PATH.")
        return

    try:
        result = subprocess.run(
            [blender_path, "--version"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
            print(f"[BlenderRender] Ready: {version_line} at {blender_path}")
        else:
            print(f"[BlenderRender] WARNING: Blender --version returned code {result.returncode}")
    except subprocess.TimeoutExpired:
        print("[BlenderRender] WARNING: Blender --version timed out")
    except Exception as e:
        print(f"[BlenderRender] WARNING: Could not verify Blender: {e}")


# Run setup (non-blocking)
setup_blender()

# Node registration
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if BlenderRenderNode is not None:
    NODE_CLASS_MAPPINGS["BlenderRenderNode"] = BlenderRenderNode
    NODE_DISPLAY_NAME_MAPPINGS["BlenderRenderNode"] = "🎨 Blender Render"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']