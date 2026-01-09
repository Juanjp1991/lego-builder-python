"""CAD tools for generating and rendering 3D models.

This module provides functions to execute build123d scripts in a sandboxed process
and render the resulting STL files to images.
"""

import os
import uuid
import logging
import contextvars
import multiprocessing
import traceback
import pyvista as pv
import trimesh
from build123d import *
from config import settings
from tools.security import validate_code

# Configure logging
logger = logging.getLogger(__name__)

# Context variable to track the current task ID
task_id_var = contextvars.ContextVar("task_id", default=None)

# Context variable to track the current generation prompt (for colored OBJ)
prompt_var = contextvars.ContextVar("generation_prompt", default="")

OUTPUT_DIR = settings.OUTPUT_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Color mapping for prompt keywords (RGBA, 0-255)
PROMPT_COLOR_MAP = {
    "tree": [34, 139, 34, 255],      # Forest Green
    "plant": [34, 139, 34, 255],
    "leaf": [50, 205, 50, 255],       # Lime Green
    "forest": [34, 139, 34, 255],
    "bear": [139, 90, 43, 255],       # Saddle Brown
    "teddy": [139, 90, 43, 255],
    "animal": [139, 90, 43, 255],
    "car": [220, 20, 60, 255],        # Crimson Red
    "truck": [220, 20, 60, 255],
    "vehicle": [220, 20, 60, 255],
    "plane": [245, 245, 245, 255],    # White Smoke
    "airplane": [245, 245, 245, 255],
    "aircraft": [245, 245, 245, 255],
    "house": [178, 34, 34, 255],      # Fire Brick Red
    "building": [178, 34, 34, 255],
    "home": [178, 34, 34, 255],
    "robot": [105, 105, 105, 255],    # Dim Gray
    "machine": [105, 105, 105, 255],
    "boat": [65, 105, 225, 255],      # Royal Blue
    "ship": [65, 105, 225, 255],
}
DEFAULT_COLOR = [30, 144, 255, 255]  # Dodger Blue


def _get_color_from_prompt(prompt: str) -> list:
    """Determine the model color based on prompt keywords.
    
    Args:
        prompt: The user's generation prompt.
        
    Returns:
        RGBA color as list of 4 integers (0-255).
    """
    prompt_lower = prompt.lower() if prompt else ""
    for keyword, color in PROMPT_COLOR_MAP.items():
        if keyword in prompt_lower:
            return color
    return DEFAULT_COLOR


def _stl_to_colored_obj(stl_path: str, prompt: str, output_dir: str, base_name: str) -> str | None:
    """Convert STL to colored OBJ file.
    
    Args:
        stl_path: Path to the source STL file.
        prompt: The generation prompt (for color determination).
        output_dir: Directory to save the OBJ file.
        base_name: Base name for the output file.
        
    Returns:
        Path to the generated OBJ file, or None if conversion failed.
    """
    try:
        # Get color based on prompt keywords
        color = _get_color_from_prompt(prompt)
        
        # Load STL mesh
        mesh = trimesh.load(stl_path)
        
        # Apply color to all faces
        # trimesh uses RGBA with 0-255 values
        mesh.visual.face_colors = color
        
        # Export to OBJ
        obj_path = os.path.join(output_dir, f"{base_name}.obj")
        mesh.export(obj_path, file_type='obj')
        
        logger.info(f"Converted STL to colored OBJ: {obj_path} with color {color}")
        return obj_path
    except Exception as e:
        logger.error(f"Failed to convert STL to OBJ: {e}")
        return None


def _execute_and_export(script_code: str, output_dir: str, base_name: str, prompt: str = "") -> dict:
    """Execute code and export files in a separate process.

    Args:
        script_code (str): The Python script to execute.
        output_dir (str): Directory to save output files.
        base_name (str): Base name for output files.
        prompt (str): The user's generation prompt (for color determination).

    Returns:
        dict: Result dictionary with success status and file paths.
    """
    try:
        # Validate code before execution
        validate_code(script_code)

        # Dynamically populate the execution scope with build123d symbols
        # This avoids verbose explicit imports while ensuring a clean state
        import build123d
        local_scope = {name: getattr(build123d, name) for name in dir(build123d) if not name.startswith("_")}
        
        # Execute the script
        exec(script_code, {}, local_scope)
        
        # Look for 'result' or 'part'
        result_obj = local_scope.get("result") or local_scope.get("part")
        
        if not result_obj:
            return {
                "success": False, 
                "error": "No 'result' or 'part' variable defined."
            }

        step_path = os.path.join(output_dir, f"{base_name}.step")
        stl_path = os.path.join(output_dir, f"{base_name}.stl")
        glb_path = os.path.join(output_dir, f"{base_name}.glb")

        export_step(result_obj, step_path)
        export_stl(result_obj, stl_path)
        
        # New: Export GLTF for web viewer
        export_gltf(result_obj, glb_path)
        
        # Convert STL to colored OBJ (legacy support)
        obj_path = _stl_to_colored_obj(stl_path, prompt, output_dir, base_name)
        
        return {
            "success": True,
            "files": {
                "step": step_path,
                "stl": stl_path,
                "glb": glb_path,
                "obj": obj_path  # May be None if conversion failed
            }
        }
    except Exception as e:
        return {
            "success": False, 
            "error": f"Execution failed: {str(e)}\n{traceback.format_exc()}"
        }

def create_cad_model(script_code: str, prompt: str = "") -> dict:
    """Executes build123d code and exports STEP/STL/OBJ.

    Runs in a separate process with a timeout.

    Args:
        script_code (str): The build123d script to execute.
        prompt (str): The user's generation prompt (for color determination in OBJ).
                     If not provided, uses prompt_var context variable.

    Returns:
        dict: A dictionary containing 'success', 'error', and 'files' (dict of paths).
    """
    # Use task ID if available, otherwise UUID
    task_id = task_id_var.get()
    if task_id:
        base_name = f"{task_id}_{uuid.uuid4().hex[:8]}"
    else:
        base_name = str(uuid.uuid4())
    
    # Get prompt from context variable if not passed directly
    effective_prompt = prompt if prompt else prompt_var.get()

    # Run in a separate process to allow timeout and isolation
    with multiprocessing.Pool(processes=1) as pool:
        async_result = pool.apply_async(_execute_and_export, (script_code, OUTPUT_DIR, base_name, effective_prompt))
        try:
            # 10 minute timeout (600 seconds)
            result = async_result.get(timeout=600)
            return result
        except multiprocessing.TimeoutError:
            return {
                "success": False, 
                "error": "Execution timed out (10 min limit). The model might be too complex."
            }
        except Exception as e:
            return {
                "success": False, 
                "error": f"Process error: {str(e)}"
            }

def _render_worker(stl_path: str, output_dir: str, base_name: str) -> dict:
    """Render the STL in a separate process.

    Args:
        stl_path (str): Path to the STL file.
        output_dir (str): Directory to save images.
        base_name (str): Base name for output images.

    Returns:
        dict: Result dictionary with success status and image paths.
    """
    try:
        # Configure PyVista for headless rendering with EGL/OSMesa
        pv.OFF_SCREEN = True
        
        # Force EGL or OSMesa if available (avoids X server requirement)
        # Note: This requires libosmesa6-dev in Dockerfile
        try:
            pv.start_xvfb() # No-op if not needed, but safe to remove if using pure EGL
        except:
            pass
            
        plotter = pv.Plotter(off_screen=True)
        mesh = pv.read(stl_path)
        plotter.add_mesh(mesh, color="lightblue", show_edges=True)
        plotter.set_background("white")

        # Views to generate
        views = {
            "iso": lambda p: p.view_isometric(),
            "top": lambda p: p.view_xy(),
            "front": lambda p: p.view_xz(), # Assuming Y-up or Z-up, adjust as needed
            "right": lambda p: p.view_yz()
        }

        image_paths = []
        for name, view_func in views.items():
            view_func(plotter)
            plotter.camera.zoom(1.2)
            out_path = os.path.join(output_dir, f"{base_name}_{name}.png")
            plotter.screenshot(out_path)
            image_paths.append(out_path)
        
        plotter.close()
        return {"success": True, "images": image_paths}

    except Exception as e:
        return {"success": False, "error": f"Rendering failed: {str(e)}\n{traceback.format_exc()}"}

def render_cad_model(stl_path: str) -> dict:
    """Renders an STL file to PNG screenshots (Iso, Top, Front, Right).

    Runs in a separate process to ensure VTK/OpenGL isolation.

    Args:
        stl_path (str): Path to the STL file.

    Returns:
        dict: A dictionary containing 'success', 'error', and 'images' (list of paths).
    """
    if not os.path.exists(stl_path):
        return {"success": False, "error": "STL file not found."}

    base_name = os.path.splitext(os.path.basename(stl_path))[0]

    # Run in a separate process
    with multiprocessing.Pool(processes=1) as pool:
        async_result = pool.apply_async(_render_worker, (stl_path, OUTPUT_DIR, base_name))
        try:
            # 30 second timeout for rendering
            result = async_result.get(timeout=30)
            return result
        except multiprocessing.TimeoutError:
            return {
                "success": False, 
                "error": "Rendering timed out (30s limit)."
            }
        except Exception as e:
            return {
                "success": False, 
                "error": f"Render process error: {str(e)}"
            }
