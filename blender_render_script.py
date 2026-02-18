"""
Blender render script for ComfyUI Blender Render Node.
Runs inside Blender's Python environment (bpy).

Production-safe: GPU auto-detection (OPTIX → CUDA → CPU fallback),
full error logging, structured exit codes.
"""
import bpy
import os
import sys
import traceback

# ─── Parse CLI args ───────────────────────────────────────────────
argv = sys.argv
argv = argv[argv.index("--") + 1:]

if len(argv) < 8:
    print("ERROR: Not enough arguments provided")
    print("Expected: diffuse_path output_path width_ratio height_ratio use_gpu samples use_denoising adaptive_sampling")
    sys.exit(1)

diffuse_path = argv[0]
output_path = argv[1]
width_ratio = float(argv[2])
height_ratio = float(argv[3])
use_gpu = argv[4].lower() == 'true'
samples = int(argv[5])
use_denoising = argv[6].lower() == 'true'
adaptive_sampling = argv[7].lower() == 'true'

print("=" * 60)
print("  Blender Render Configuration")
print("=" * 60)
print(f"  Diffuse texture : {diffuse_path}")
print(f"  Output          : {output_path}")
print(f"  Ratios          : W={width_ratio:.2f}, H={height_ratio:.2f}")
print(f"  GPU requested   : {use_gpu}")
print(f"  Samples         : {samples}")
print(f"  Denoising       : {use_denoising}")
print(f"  Adaptive        : {adaptive_sampling}")
print("=" * 60)

curtain_objects = ["cur_1", "cur_2"]


# ─── Material helpers ─────────────────────────────────────────────
def apply_diffuse_and_scale(material, diffuse_path, w_ratio, h_ratio):
    if not material.use_nodes:
        return False

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # Find Principled BSDF
    principled = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled = node
            break

    if not principled:
        print(f"  WARN: No Principled BSDF in {material.name}")
        return False

    # Find or create Image Texture node connected to Base Color
    tex_node = None
    if "Base Color" in principled.inputs:
        socket = principled.inputs["Base Color"]
        if socket.is_linked:
            tex_node = socket.links[0].from_node

    if not tex_node or tex_node.type != 'TEX_IMAGE':
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.location = (-300, 300)
        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])

    try:
        img = bpy.data.images.load(diffuse_path, check_existing=False)
        tex_node.image = img
        print(f"  Applied diffuse to {material.name}")
    except Exception as e:
        print(f"  ERROR: Failed to load diffuse for {material.name}: {e}")

    # Find and update Mapping node
    mapping_node = None
    if "Vector" in tex_node.inputs and tex_node.inputs["Vector"].is_linked:
        mapping_node = tex_node.inputs["Vector"].links[0].from_node

    if not mapping_node or mapping_node.type != 'MAPPING':
        for node in nodes:
            if node.type == 'MAPPING':
                mapping_node = node
                break

    if mapping_node:
        old_scale = mapping_node.inputs['Scale'].default_value[:]
        new_x = old_scale[0] * w_ratio
        new_y = old_scale[1] * h_ratio
        new_z = old_scale[2] * w_ratio
        mapping_node.inputs['Scale'].default_value[0] = new_x
        mapping_node.inputs['Scale'].default_value[1] = new_y
        mapping_node.inputs['Scale'].default_value[2] = new_z
        print(f"  Updated Mapping Scale in {material.name}: "
              f"{tuple(old_scale)} -> ({new_x:.2f}, {new_y:.2f}, {new_z:.2f})")
    else:
        print(f"  WARN: No Mapping node in {material.name}, skipping scale update.")

    return True


# ─── GPU setup with auto-fallback ─────────────────────────────────
def setup_gpu(scene):
    """
    Try to enable GPU rendering with automatic backend detection.
    Order: OPTIX → CUDA → CPU fallback.
    Compatible with Blender 4.5+ and CUDA 13 / Blackwell GPUs.
    """
    prefs = bpy.context.preferences.addons["cycles"].preferences

    # Backends to try in priority order
    backends = ['OPTIX', 'CUDA']
    gpu_enabled = False

    for backend in backends:
        try:
            prefs.compute_device_type = backend
            # Force Blender to refresh its device list
            prefs.get_devices()

            # Check if any GPU devices were actually found
            gpu_devices = [d for d in prefs.devices if d.type != 'CPU']
            if not gpu_devices:
                print(f"  GPU/{backend}: No GPU devices found, trying next backend...")
                continue

            # Enable all available devices (GPU + CPU for hybrid)
            for device in prefs.devices:
                device.use = True
                print(f"  GPU/{backend}: Enabled device: {device.name} ({device.type})")

            scene.cycles.device = "GPU"
            gpu_enabled = True
            print(f"  GPU: Successfully configured with {backend} backend")
            break

        except Exception as e:
            print(f"  GPU/{backend}: Failed to initialize — {e}")
            continue

    if not gpu_enabled:
        print("  GPU: All backends failed. Falling back to CPU rendering.")
        scene.cycles.device = "CPU"

    return gpu_enabled


# ─── Main Logic ───────────────────────────────────────────────────
try:
    # Apply textures to curtain objects
    for obj_name in curtain_objects:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            for slot in obj.material_slots:
                if slot.material:
                    apply_diffuse_and_scale(slot.material, diffuse_path,
                                            width_ratio, height_ratio)

    # Set camera
    camera_obj = bpy.data.objects.get("Camera.006")
    if camera_obj:
        bpy.context.scene.camera = camera_obj
    else:
        print("  WARN: Camera.006 not found, using scene default camera")

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.filepath = output_path

    # GPU or CPU
    if use_gpu:
        gpu_ok = setup_gpu(scene)
        if not gpu_ok:
            print("  NOTE: Rendering will proceed on CPU (GPU fallback)")
    else:
        scene.cycles.device = "CPU"
        print("  Render device: CPU (user requested)")

    # Sampling
    scene.cycles.samples = samples
    scene.cycles.use_denoising = use_denoising
    if hasattr(scene.cycles, 'use_adaptive_sampling'):
        scene.cycles.use_adaptive_sampling = adaptive_sampling

    # ─── Render ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Starting render: {samples} samples, "
          f"device={scene.cycles.device}, denoising={use_denoising}")
    print("=" * 60)

    bpy.ops.render.render(write_still=True)

    # Verify output was written
    if os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"\n  Render complete! Output: {output_path} ({size_kb:.1f} KB)")
    else:
        print(f"\n  ERROR: Render appeared to succeed but output file not found: {output_path}")
        sys.exit(2)

except Exception as e:
    print("\n" + "=" * 60)
    print("  BLENDER RENDER FAILED")
    print("=" * 60)
    print(f"  Error: {e}")
    print("\n  Full traceback:")
    traceback.print_exc()
    print("=" * 60)
    sys.exit(1)
