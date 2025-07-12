import importlib.util
import os
from typing import Dict, Callable

def load_cells(cells_dir: str) -> Dict[str, Callable]:
    """
    Dynamically loads all Python files in cells/ as AI modules
    Returns: { "cell_name": cell_function }
    """
    cells = {}
    for filename in os.listdir(cells_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            cell_name = filename[:-3]  # Remove .py
            try:
                spec = importlib.util.spec_from_file_location(
                    cell_name, 
                    os.path.join(cells_dir, filename)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                cells[cell_name] = module.process  # Each cell must have process()
            except Exception as e:
                print(f"Failed to load {filename}: {str(e)}")
    return cells
