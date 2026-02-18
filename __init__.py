"""
ComfyUI Blender Render Node — Production-safe init.

- Uses system-installed Blender (found via PATH).
- Auto-pulls Git LFS files (.blend) if they are stubs.
- Does NOT block ComfyUI startup if Blender is missing.
- Logs setup results clearly.
"""
import os
import glob
import shutil
import subprocess


LFS_POINTER_SIGNATURE = "version https://git-lfs.github.com/spec/"

# Import the node
try:
    from .blender_node import BlenderRenderNode
except ImportError as e:
    print(f"[BlenderRender] Import error — node disabled: {e}")
    BlenderRenderNode = None


def _is_lfs_pointer(filepath):
    """Check if a file is a Git LFS pointer (small text file with LFS header)."""
    try:
        # Real .blend files are binary and large; LFS pointers are < 200 bytes of text
        if os.path.getsize(filepath) > 1024:
            return False
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        return first_line.startswith(LFS_POINTER_SIGNATURE)
    except Exception:
        return False


def ensure_lfs_files():
    """
    Check if .blend files in the node directory are Git LFS pointers.
    If so, run `git lfs pull` to fetch the real files.
    Never raises — logs warnings on failure.
    """
    node_dir = os.path.dirname(os.path.abspath(__file__))
    blend_files = glob.glob(os.path.join(node_dir, "*.blend"))

    if not blend_files:
        return  # No .blend files to worry about

    # Check if any are LFS pointers
    stubs = [f for f in blend_files if _is_lfs_pointer(f)]
    if not stubs:
        return  # All files are already real

    stub_names = [os.path.basename(f) for f in stubs]
    print(f"[BlenderRender] LFS pointer files detected: {stub_names}")
    print("[BlenderRender] Running 'git lfs pull' to fetch real files...")

    # Check if git-lfs is available
    if not shutil.which("git-lfs") and not shutil.which("git"):
        print("[BlenderRender] WARNING: 'git' not found on PATH. "
              "Cannot pull LFS files. .blend files will be unusable.")
        return

    try:
        result = subprocess.run(
            ["git", "lfs", "pull"],
            cwd=node_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout for large files
        )
        if result.returncode == 0:
            print(f"[BlenderRender] LFS pull complete.")
            # Verify the stubs are now real files
            still_stubs = [f for f in stubs if _is_lfs_pointer(f)]
            if still_stubs:
                names = [os.path.basename(f) for f in still_stubs]
                print(f"[BlenderRender] WARNING: These files are still LFS pointers "
                      f"after pull: {names}")
            else:
                print(f"[BlenderRender] All .blend files are now ready.")
        else:
            print(f"[BlenderRender] WARNING: 'git lfs pull' failed "
                  f"(exit code {result.returncode})")
            if result.stderr:
                print(f"[BlenderRender]   stderr: {result.stderr.strip()[:500]}")
    except subprocess.TimeoutExpired:
        print("[BlenderRender] WARNING: 'git lfs pull' timed out after 300s")
    except Exception as e:
        print(f"[BlenderRender] WARNING: LFS pull failed: {e}")


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
ensure_lfs_files()
setup_blender()

# Node registration
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

if BlenderRenderNode is not None:
    NODE_CLASS_MAPPINGS["BlenderRenderNode"] = BlenderRenderNode
    NODE_DISPLAY_NAME_MAPPINGS["BlenderRenderNode"] = "🎨 Blender Render"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']