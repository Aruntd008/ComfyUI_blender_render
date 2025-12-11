import bpy
import os
import sys

# Parse command line arguments
argv = sys.argv
argv = argv[argv.index("--") + 1:]

if len(argv) < 8:
    print("Error: Not enough arguments provided")
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

print(f"=== Blender Render Configuration ===")
print(f"Diffuse texture: {diffuse_path}")
print(f"Ratios: W={width_ratio:.2f}, H={height_ratio:.2f}")
print(f"Output: {output_path}")

curtain_objects = ["cur_1", "cur_2"]

def apply_diffuse_and_scale(material, diffuse_path, w_ratio, h_ratio):
    if not material.use_nodes:
        return False
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    # 1. Apply Diffuse Texture
    principled = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled = node
            break
            
    if not principled:
        print(f"No Principled BSDF in {material.name}")
        return False
        
    # Find Image Texture node connected to Base Color
    tex_node = None
    if "Base Color" in principled.inputs:
        socket = principled.inputs["Base Color"]
        if socket.is_linked:
            tex_node = socket.links[0].from_node
            
    if not tex_node or tex_node.type != 'TEX_IMAGE':
        # Create new if not found
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.location = (-300, 300)
        links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
        
    try:
        # Load image
        img = bpy.data.images.load(diffuse_path, check_existing=False)
        tex_node.image = img
        print(f"Applied diffuse to {material.name}")
    except Exception as e:
        print(f"Failed to load diffuse for {material.name}: {e}")
        
    # 2. Update Mapping Scale
    # Find Mapping node connected to the texture
    mapping_node = None
    if "Vector" in tex_node.inputs and tex_node.inputs["Vector"].is_linked:
        mapping_node = tex_node.inputs["Vector"].links[0].from_node
    
    # If not found directly, look for ANY Mapping node in the tree?
    if not mapping_node or mapping_node.type != 'MAPPING':
        for node in nodes:
            if node.type == 'MAPPING':
                mapping_node = node
                break
    
    if mapping_node:
        # Update Scale
        # Scale is [x, y, z]
        old_scale = mapping_node.inputs['Scale'].default_value[:]
        new_x = old_scale[0] * w_ratio
        new_y = old_scale[1] * h_ratio
        new_z = old_scale[2] * w_ratio # Uniform Z scaling based on Width?
        
        mapping_node.inputs['Scale'].default_value[0] = new_x
        mapping_node.inputs['Scale'].default_value[1] = new_y
        mapping_node.inputs['Scale'].default_value[2] = new_z
        
        print(f"Updated Mapping Scale in {material.name}: {old_scale} -> ({new_x:.2f}, {new_y:.2f}, {new_z:.2f})")
    else:
        print(f"No Mapping node found in {material.name}, skipping scale update.")
        
    return True

# --- Main Logic ---
for obj_name in curtain_objects:
    obj = bpy.data.objects.get(obj_name)
    if obj:
        for slot in obj.material_slots:
            if slot.material:
                apply_diffuse_and_scale(slot.material, diffuse_path, width_ratio, height_ratio)

# --- Render Setup ---
camera_obj = bpy.data.objects.get("Camera.006")
if camera_obj:
    bpy.context.scene.camera = camera_obj

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.render.filepath = output_path

# GPU
if use_gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'CUDA' # Default try
    # (Simple logic: enable all devices)
    for device in prefs.devices:
        device.use = True
    scene.cycles.device = "GPU"
else:
    scene.cycles.device = "CPU"

scene.cycles.samples = samples
scene.cycles.use_denoising = use_denoising

try:
    bpy.ops.render.render(write_still=True)
except Exception as e:
    print(f"Render failed: {e}")
    sys.exit(1)
