"""
ComfyUI Blender Render Node — Production-safe init.

- Does NOT block ComfyUI startup if Blender download fails.
- Logs setup results clearly.
- Only supports Windows and Linux.
"""
import os
import platform
import subprocess

# Import the node
try:
    from .blender_node import BlenderRenderNode
    from .blender_downloader import get_blender_path
except ImportError as e:
    print(f"[BlenderRender] Import error — node disabled: {e}")
    BlenderRenderNode = None


def setup_blender():
    """
    Attempt to locate or download Blender.
    Never raises — just logs warnings if setup fails.
    ComfyUI will still load; render will fail at runtime with a clear message.
    """
    if BlenderRenderNode is None:
        return

    system = platform.system()
    if system not in ("Windows", "Linux"):
        print(f"[BlenderRender] Unsupported platform: {system}. Node disabled.")
        return

    print(f"[BlenderRender] Setting up for {system}")
    node_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        blender_path = get_blender_path(node_dir)

        # Windows: unblock executable
        if system == "Windows" and os.path.exists(blender_path):
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     f"Unblock-File -Path '{blender_path}'"],
                    check=False, capture_output=True
                )
            except Exception:
                pass  # Non-critical

        # Verify Blender works
        if os.path.exists(blender_path):
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
                print(f"[BlenderRender] WARNING: Blender --version timed out")
            except Exception as e:
                print(f"[BlenderRender] WARNING: Could not verify Blender: {e}")

    except Exception as e:
        print(f"[BlenderRender] Setup failed (render will fail at runtime): {e}")


# Run setup (non-blocking)
setup_blender()

# Node registration
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if BlenderRenderNode is not None:
    NODE_CLASS_MAPPINGS["BlenderRenderNode"] = BlenderRenderNode
    NODE_DISPLAY_NAME_MAPPINGS["BlenderRenderNode"] = "🎨 Blender Render (Auto-Setup)"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']