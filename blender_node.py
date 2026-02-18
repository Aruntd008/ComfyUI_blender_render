"""
ComfyUI Blender Render Node — production-safe for Docker / RunPod.

- Never crashes ComfyUI on Blender failure (returns structured error).
- Logs full stdout/stderr from Blender.
- Uses check=False subprocess to control error handling.
"""
import os
import subprocess
import time
import tempfile
import shutil

import torch
import numpy as np
from PIL import Image


def get_default_blender_path():
    """Get Blender executable path from system PATH."""
    blender_path = shutil.which("blender")
    if not blender_path:
        raise FileNotFoundError(
            "Blender executable not found on system PATH. "
            "Please install Blender and ensure it is available in your PATH "
            "(e.g. `apt install blender` or add it to your Dockerfile)."
        )
    print(f"[BlenderRender] Using system Blender: {blender_path}")
    return blender_path


class BlenderRenderNode:
    """ComfyUI node that renders a .blend scene with a diffuse texture input."""

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
        return str(time.time())

    def render(self, blend_file, diffuse_texture, width_ratio=1.0,
               height_ratio=1.0, use_gpu=True, samples=128,
               use_denoising=True, adaptive_sampling=True):
        node_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(node_dir, "blender_render_script.py")

        # ── Resolve Blender executable ──────────────────────────
        blender_path = get_default_blender_path()

        # ── Resolve .blend scene ────────────────────────────────
        blend_file_path = os.path.join(node_dir, blend_file)
        if not os.path.exists(blend_file_path):
            raise FileNotFoundError(
                f"Blender scene file not found at: {blend_file_path}"
            )

        # Unique output path to avoid collisions
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(node_dir, f"render_output_{timestamp}.png")
        temp_dir = tempfile.mkdtemp(prefix="comfyui_blender_textures_")

        try:
            # ── Save input texture to temp file ─────────────────
            if diffuse_texture.dim() == 4:
                diffuse_tensor = diffuse_texture.squeeze(0)
            else:
                diffuse_tensor = diffuse_texture

            tex_array = (diffuse_tensor.cpu().numpy() * 255).astype(np.uint8)
            tex_image = Image.fromarray(tex_array)
            diffuse_path = os.path.join(temp_dir, "input_diffuse.png")
            tex_image.save(diffuse_path, optimize=False, compress_level=0)
            print(f"[BlenderRender] Saved diffuse texture: {diffuse_path}")

            # ── Build Blender CLI command ───────────────────────
            cmd = [
                blender_path,
                "-b",                    # background mode
                blend_file_path,
                "-P", script_path,       # run Python script
                "--",                     # separator for script args
                diffuse_path,
                output_path,
                str(width_ratio),
                str(height_ratio),
                str(use_gpu).lower(),
                str(samples),
                str(use_denoising).lower(),
                str(adaptive_sampling).lower(),
            ]

            print(f"[BlenderRender] GPU={use_gpu}, Samples={samples}, "
                  f"Denoise={use_denoising}, Adaptive={adaptive_sampling}")
            print(f"[BlenderRender] Command: "
                  + " ".join(f'"{a}"' if ' ' in a else a for a in cmd))

            # ── Run Blender (check=False — we handle errors) ────
            result = subprocess.run(
                cmd,
                check=False,           # Do NOT raise on non-zero exit
                capture_output=True,
                text=True,
                cwd=node_dir,
                timeout=600,           # 10 min safety timeout
            )

            # ── Always log output ───────────────────────────────
            if result.stdout:
                print("[BlenderRender] ── Blender STDOUT ──")
                print(result.stdout[-3000:])  # Last 3k chars
            if result.stderr:
                print("[BlenderRender] ── Blender STDERR ──")
                print(result.stderr[-3000:])

            # ── Check for failure ───────────────────────────────
            if result.returncode != 0:
                error_msg = (
                    f"Blender exited with code {result.returncode}.\n"
                    f"STDERR (last 1000 chars):\n"
                    f"{(result.stderr or 'no stderr')[-1000:]}\n"
                    f"STDOUT (last 1000 chars):\n"
                    f"{(result.stdout or 'no stdout')[-1000:]}"
                )
                print(f"[BlenderRender] RENDER FAILED:\n{error_msg}")
                raise RuntimeError(
                    f"Blender render failed (exit code {result.returncode}). "
                    f"Check ComfyUI console for full logs."
                )

            print("[BlenderRender] Blender process exited successfully (code 0)")

            # ── Verify output file exists ───────────────────────
            if not os.path.exists(output_path):
                raise FileNotFoundError(
                    f"Blender exited OK but render output not found: {output_path}. "
                    f"Check Blender logs above for clues."
                )

            # ── Load rendered image → tensor ────────────────────
            img = Image.open(output_path).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None,]

            # Clean up output file
            try:
                os.remove(output_path)
            except OSError as e:
                print(f"[BlenderRender] Warning: Could not clean up {output_path}: {e}")

            print("[BlenderRender] Render complete, returning image tensor")
            return (tensor,)

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Blender render timed out after 600 seconds. "
                "Consider reducing samples or scene complexity."
            )
        except (FileNotFoundError, RuntimeError, PermissionError):
            # Re-raise structured errors as-is
            raise
        except Exception as e:
            # Catch-all: log and wrap in RuntimeError
            print(f"[BlenderRender] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Blender render failed unexpectedly: {e}") from e
        finally:
            # Always clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                print(f"[BlenderRender] Warning: temp cleanup failed: {e}")


NODE_CLASS_MAPPINGS = {
    "Blender Render Node": BlenderRenderNode
}
