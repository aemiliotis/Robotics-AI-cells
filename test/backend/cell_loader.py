import os
import importlib.util
from pathlib import Path

def load_cells(cells_dir):
    """Dynamically load all Python files in the cells directory as modules"""
    cells = {}
    
    for filepath in Path(cells_dir).glob('*.py'):
        if filepath.name.startswith('_'):
            continue
            
        module_name = filepath.stem
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # The module should have a 'process' function
        if hasattr(module, 'process'):
            cells[module_name] = module.process
    
    return cells
