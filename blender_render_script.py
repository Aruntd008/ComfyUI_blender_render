import bpy
import os
import sys

# Parse command line arguments
argv = sys.argv
argv = argv[argv.index("--") + 1:]

if len(argv) < 9:
    print("Error: Not enough arguments provided")
    print("Expected: diffuse_path normal_path roughness_path specular_path output_path use_gpu samples use_denoising adaptive_sampling")
    sys.exit(1)

diffuse_path = argv[0]
normal_path = argv[1]
roughness_path = argv[2]
specular_path = argv[3]
output_path = argv[4]
use_gpu = argv[5].lower() == 'true'
samples = int(argv[6])
use_denoising = argv[7].lower() == 'true'
adaptive_sampling = argv[8].lower() == 'true'

print(f"=== Blender Render Configuration ===")
print(f"Diffuse texture: {diffuse_path}")
print(f"Normal texture: {normal_path}")
print(f"Roughness texture: {roughness_path}")
print(f"Specular texture: {specular_path}")
print(f"Output: {output_path}")
print(f"GPU: {use_gpu}")
print(f"Samples: {samples}")
print(f"Denoising: {use_denoising}")
print(f"Adaptive sampling: {adaptive_sampling}")

curtain_objects = ["cur_1", "cur_2"]
texture_paths = {
    "diffuse": diffuse_path,
    "normal": normal_path,
    "roughness": roughness_path,
    "specular": specular_path
}

def replace_texture_in_nodes(material, tex_key, texture_file_path):
    """Replace texture in material nodes more reliably."""
    if not material.use_nodes:
        return False
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    # Find Principled BSDF node first
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if not principled_node:
        print(f"No Principled BSDF found in {material.name}")
        return False
    
    # Debug: Print available inputs for first material only
    if tex_key == "diffuse":  # Only print once per material
        print(f"Available inputs in {material.name} Principled BSDF:")
        for inp in principled_node.inputs:
            print(f"  - {inp.name}")
    
    # Create or find the appropriate texture node for this texture type
    texture_node = None
    
    # Look for existing texture nodes connected to the right input
    input_mapping = {
        "diffuse": "Base Color",
        "normal": "Normal", 
        "roughness": "Roughness",
        "specular": "Specular IOR Level"  # Changed back to proper specular input for Blender 4.x
    }
    
    target_input = input_mapping.get(tex_key)
    if not target_input:
        print(f"Unknown texture type: {tex_key}")
        return
    
    # Check if the target input exists in this Principled BSDF version
    if target_input not in principled_node.inputs:
        print(f"Input '{target_input}' not found in Principled BSDF. Available inputs:")
        for inp in principled_node.inputs:
            print(f"  - {inp.name}")
        
        # Fallback mapping for different Blender versions
        fallback_mapping = {
            "specular": ["Metallic", "Specular", "Specular IOR Level"],
            "diffuse": ["Base Color", "Albedo"],
            "roughness": ["Roughness"],
            "normal": ["Normal"]
        }
        
        # Try fallback options
        for fallback in fallback_mapping.get(tex_key, []):
            if fallback in principled_node.inputs:
                target_input = fallback
                print(f"Using fallback input: {target_input}")
                break
        else:
            print(f"No suitable input found for {tex_key}")
            return
        
    # Try to find existing connected image texture node
    if target_input in principled_node.inputs:
        input_socket = principled_node.inputs[target_input]
        if input_socket.is_linked:
            for link in input_socket.links:
                if link.from_node.type == 'TEX_IMAGE':
                    texture_node = link.from_node
                    break
    
    # If no existing texture node, create a new one
    if not texture_node:
        texture_node = nodes.new(type='ShaderNodeTexImage')
        texture_node.location = (-400, 0 - len(nodes) * 50)  # Position it nicely
        texture_node.name = f"{tex_key}_texture"  # Give it a descriptive name
        
    # Always ensure proper connection (reconnect if needed)
    if target_input in principled_node.inputs:
        if tex_key == "normal":
            # For normal maps, we need a Normal Map node
            normal_map_node = None
            # Check if Normal Map node already exists
            for node in nodes:
                if node.type == 'NORMAL_MAP' and node.name.startswith(f"{tex_key}_"):
                    normal_map_node = node
                    break
            
            if not normal_map_node:
                normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                normal_map_node.location = (-200, texture_node.location.y)
                normal_map_node.name = f"{tex_key}_normal_map"
            
            # Clear existing connections and reconnect
            links.new(texture_node.outputs['Color'], normal_map_node.inputs['Color'])
            links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            print(f"Connected {tex_key} texture through Normal Map node")
        else:
            # Direct connection for other texture types
            links.new(texture_node.outputs['Color'], principled_node.inputs[target_input])
            print(f"Connected {tex_key} texture to {target_input}")
    else:
        print(f"Warning: Target input '{target_input}' not found for {tex_key}")
        return
    
    # Load and assign the new texture
    if os.path.exists(texture_file_path):
        try:
            # Remove any existing image with the same path to force reload
            existing_img = None
            for img in bpy.data.images:
                if img.filepath == texture_file_path:
                    existing_img = img
                    break
            
            if existing_img:
                new_img = existing_img
                print(f"Reusing existing image: {os.path.basename(texture_file_path)}")
            else:
                new_img = bpy.data.images.load(texture_file_path, check_existing=False)
                print(f"Loaded new image: {os.path.basename(texture_file_path)}")
            
            # Assign image to texture node
            texture_node.image = new_img
            
            # Set appropriate colorspace AFTER loading the image
            if tex_key in ["normal", "roughness", "specular"]:
                new_img.colorspace_settings.name = 'Non-Color'
                print(f"Set {tex_key} texture colorspace to Non-Color")
            else:
                new_img.colorspace_settings.name = 'sRGB'
                print(f"Set {tex_key} texture colorspace to sRGB")
                
            print(f"Successfully applied {tex_key} texture to {material.name}: {os.path.basename(texture_file_path)}")
            
        except Exception as e:
            print(f"Error loading texture {texture_file_path}: {e}")
            return False
    else:
        print(f"Texture file not found: {texture_file_path}")
        return False
    
    return True

def apply_textures_to_all_materials():
    """Apply textures to all materials in all curtain objects."""
    print("=== Applying Textures to All Curtain Materials ===")
    
    success_count = 0
    total_count = 0
    
    for obj_name in curtain_objects:
        obj = bpy.data.objects.get(obj_name)
        if obj and obj.type == 'MESH':
            print(f"Processing object: {obj_name}")
            for i, slot in enumerate(obj.material_slots):
                mat = slot.material
                if mat:
                    print(f"  Processing material: {mat.name}")
                    # Make sure the material uses nodes
                    if not mat.use_nodes:
                        mat.use_nodes = True
                        print(f"  Enabled nodes for material: {mat.name}")
                    
                    for tex_key, tex_path in texture_paths.items():
                        total_count += 1
                        try:
                            result = replace_texture_in_nodes(mat, tex_key, tex_path)
                            if result:
                                success_count += 1
                            else:
                                print(f"  Failed to apply {tex_key} to {mat.name}")
                        except Exception as e:
                            print(f"  Error applying {tex_key} to {mat.name}: {e}")
                else:
                    print(f"  Material slot {i} is empty")
        else:
            print(f"Object '{obj_name}' not found or not a mesh")
    
    print(f"=== Texture Application Summary: {success_count}/{total_count} successful ===")
    return success_count, total_count

# --- Apply textures to all curtain objects ---
success_count, total_count = apply_textures_to_all_materials()

# --- Validate texture application ---
if success_count == 0:
    print("WARNING: No textures were successfully applied!")
elif success_count < total_count:
    print(f"WARNING: Only {success_count} out of {total_count} textures were applied successfully!")
else:
    print("SUCCESS: All textures applied successfully!")

# --- Debug: Print scene information ---
print("=== Scene Debug Information ===")
print(f"Total objects in scene: {len(bpy.data.objects)}")
print("Curtain objects status:")
for obj_name in curtain_objects:
    obj = bpy.data.objects.get(obj_name)
    if obj:
        print(f"  {obj_name}: Found, {len(obj.material_slots)} material slots")
        for i, slot in enumerate(obj.material_slots):
            mat_name = slot.material.name if slot.material else "None"
            print(f"    Slot {i}: {mat_name}")
    else:
        print(f"  {obj_name}: NOT FOUND")

# --- Set render camera ---
camera_obj = bpy.data.objects.get("Camera.006")
if camera_obj:
    bpy.context.scene.camera = camera_obj
    print("Render camera set to Camera.006")
else:
    raise Exception("Camera.006 not found in scene")

# --- Configure rendering engine ---
scene = bpy.context.scene
scene.render.engine = "CYCLES"

# --- GPU Configuration ---
if use_gpu:
    cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
    
    # Debug: Print all available devices
    print("=== Available Compute Devices ===")
    for i, device in enumerate(cycles_prefs.devices):
        print(f"Device {i}: {device.name} ({device.type}) - Use: {device.use}")

    # Force refresh devices
    try:
        cycles_prefs.get_devices()
        print("Refreshed device list")
    except:
        print("Could not refresh device list")

    # Try different compute device types to find available GPUs
    available_types = ['OPTIX', 'CUDA', 'OPENCL', 'HIP']
    gpu_found = False

    for device_type in available_types:
        try:
            cycles_prefs.compute_device_type = device_type
            cycles_prefs.get_devices()
            
            print(f"--- Checking {device_type} devices ---")
            type_devices = []
            for device in cycles_prefs.devices:
                if device.type == device_type:
                    type_devices.append(device)
            
            if type_devices:
                print(f"Found {len(type_devices)} {device_type} device(s)")
                # Enable all GPU devices of this type
                for device in cycles_prefs.devices:
                    if device.type == device_type:
                        device.use = True
                        print(f"Enabled {device_type} device: {device.name}")
                    else:
                        device.use = False
                
                scene.cycles.device = "GPU"
                gpu_found = True
                print(f"Successfully configured {device_type} GPU rendering")
                
                # Set denoiser to match GPU type
                if device_type == 'OPTIX' and use_denoising:
                    scene.cycles.denoiser = 'OPTIX'
                    print("Set denoiser to OptiX")
                elif use_denoising:
                    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
                    print("Set denoiser to OpenImageDenoise")
                
                break
        except Exception as e:
            print(f"Error checking {device_type}: {e}")
            continue

    if not gpu_found:
        print("=== GPU Setup Failed - Using CPU ===")
        cycles_prefs.compute_device_type = "NONE"
        scene.cycles.device = "CPU"
        for device in cycles_prefs.devices:
            if device.type == "CPU":
                device.use = True
            else:
                device.use = False
        print("Configured CPU rendering")
else:
    print("=== Using CPU Rendering (GPU disabled by user) ===")
    scene.cycles.device = "CPU"

# --- Optimize Cycles settings ---
scene.cycles.samples = samples
scene.cycles.preview_samples = max(32, samples // 4)
scene.cycles.use_adaptive_sampling = adaptive_sampling
if adaptive_sampling:
    scene.cycles.adaptive_threshold = 0.01

# Advanced optimizations
scene.cycles.feature_set = 'SUPPORTED'  # GPU-supported features only
scene.cycles.use_denoising = use_denoising
scene.cycles.use_preview_denoising = use_denoising

# Memory optimizations
scene.render.use_persistent_data = True
scene.cycles.debug_use_spatial_splits = True
# scene.cycles.debug_bvh_type = 'STATIC_BVH'

print(f"Render settings: {samples} samples, GPU: {use_gpu}, Denoising: {use_denoising}")

# --- Render settings ---
scene.render.filepath = output_path
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = 'RGB'

# --- Render and save ---
try:
    print("Starting render...")
    bpy.ops.render.render(write_still=True)
    print(f"Render completed and saved to: {output_path}")
except Exception as e:
    print(f"Render failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)