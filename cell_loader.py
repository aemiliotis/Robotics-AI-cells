import importlib.util
import os
from typing import Dict, Callable
import sys

def load_cells(cells_dir: str) -> Dict[str, Callable]:
    """
    Dynamically loads all Python files in cells/ as AI modules
    Returns: { "cell_name": cell_function }
    """
    cells = {}
    
    # Ensure cells directory exists
    if not os.path.exists(cells_dir):
        return cells
        
    for filename in os.listdir(cells_dir):
        # Skip non-Python files and hidden files
        if not filename.endswith('.py') or filename.startswith('_'):
            continue
            
        cell_name = filename[:-3]  # Remove .py extension
        module_path = os.path.join(cells_dir, filename)
        
        try:
            # Modern Python 3.5+ module loading
            spec = importlib.util.spec_from_file_location(
                f"cells.{cell_name}",
                module_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"cells.{cell_name}"] = module
            spec.loader.exec_module(module)
            
            # Verify the module has required process() function
            if hasattr(module, 'process'):
                cells[cell_name] = module.process
            else:
                print(f"Warning: {filename} missing process() function")
                
        except Exception as e:
            print(f"Failed to load {filename}: {str(e)}")
            continue
            
    return cells
