# Portable Blender Setup Guide (Windows & Linux)

This guide follows the Linux portable setup approach for consistent cross-platform behavior.

## Overview

This ComfyUI custom node uses a **portable Blender installation** inside the node folder to ensure consistent rendering across platforms. The setup automatically downloads and configures Blender 4.5.3 LTS.

## Platform-Specific Behavior

### Windows

- Downloads: `blender-4.5.3-windows-x64.zip` (165MB)
- Extracts to: `blender-4.5.3-windows-x64/`
- Executable: `blender-4.5.3-windows-x64/blender.exe`
- Auto-unblocks executable with PowerShell

### Linux (Following Linux Guide)

- Downloads: `blender-4.5.3-linux-x64.tar.xz` (190MB)
- Extracts to: `blender/` (renamed for convenience)
- Executable: `blender/blender`
- Sets executable permissions with `chmod +x`

## Automatic Setup Process

1. **Download**: Fetches appropriate Blender archive for your platform
2. **Extract**: Unpacks the archive to the node folder
3. **Rename** (Linux only): Renames folder to shorter "blender" name
4. **Permissions**: Sets executable permissions on Linux
5. **Verify**: Tests that Blender executable works correctly

## File Structure After Setup

```
ComfyUI_blender_render/
├── __init__.py                    # Node registration & setup
├── blender_node.py               # Main node implementation
├── blender_downloader.py         # Auto-download logic
├── blender_render_script.py      # Blender Python script
├── untitled.blend               # Scene with curtain models
├── test_setup.py                # Setup verification script
│
├── blender-4.5.3-windows-x64/   # Windows Blender (if on Windows)
│   ├── blender.exe
│   └── [Blender files...]
│
└── blender/                      # Linux Blender (if on Linux)
    ├── blender                   # Executable
    └── [Blender files...]
```

## Relative Path Usage (Following Linux Guide)

The node uses **relative paths** to access the Blender executable:

```python
# Path relative to node folder (as per Linux guide)
node_dir = os.path.dirname(__file__)

# Windows
blender_path = os.path.join(node_dir, "blender-4.5.3-windows-x64", "blender.exe")

# Linux (shorter name for convenience)
blender_path = os.path.join(node_dir, "blender", "blender")
```

## Command Execution (Following Linux Guide)

Blender is executed using subprocess with relative paths:

```python
# Following Linux guide approach: subprocess.run([blender_path, "-b", "-P", script_path])
cmd = [
    blender_path,           # Relative path to Blender
    "-b",                   # Background mode (no GUI)
    blend_file,             # Scene file
    "-P", script_path,      # Python script to run
    "--",                   # Script arguments separator
    # ... texture paths and render settings
]

subprocess.run(cmd, cwd=node_dir)  # Set working directory to node folder
```

## Testing Your Setup

Run the verification script:

```bash
# Test the setup
python test_setup.py
```

Expected output:

```
=== Testing Portable Blender Setup ===
Platform: Linux
Blender path: /path/to/node/blender/blender
✅ Blender executable found
✅ Blender executable has correct permissions
✅ Blender version: Blender 4.5.3 (sub 1)
✅ Scene file (untitled.blend) found
✅ All tests passed! Setup is working correctly.
```

## Manual Setup (Alternative)

If auto-download fails, you can manually set up Blender:

### Linux Manual Setup

```bash
# Download Blender
wget https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz

# Extract to node folder
cd /path/to/ComfyUI/custom_nodes/ComfyUI_blender_render
tar -xvf ~/Downloads/blender-4.5.3-linux-x64.tar.xz

# Rename for convenience (following Linux guide)
mv blender-4.5.3-linux-x64 blender

# Set executable permissions
chmod +x blender/blender

# Verify
./blender/blender --version
```

### Windows Manual Setup

1. Download `blender-4.5.3-windows-x64.zip`
2. Extract to the node folder (keep original folder name)
3. Run `Unblock-File` in PowerShell if needed

## Troubleshooting

### Permission Denied (Linux)

```bash
chmod +x blender/blender
```

### Executable Blocked (Windows)

```powershell
Unblock-File -Path "blender-4.5.3-windows-x64\blender.exe"
```

### Download Fails

- Check internet connection
- Ensure sufficient disk space (~200MB)
- Try manual setup instead

## Advantages of This Approach

1. **Portable**: Self-contained, no system dependencies
2. **Consistent**: Same Blender version across platforms
3. **Relative Paths**: Easy to move/distribute
4. **Automatic**: Downloads and configures automatically
5. **Verified**: Tests executable before use

This approach ensures your ComfyUI node works identically on both Windows and Linux systems!
