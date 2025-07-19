// Main application controller
class RoboticsAIHub {
    constructor() {
        this.cells = {};
        this.currentCell = null;
        
        // DOM Elements
        this.cellSelector = document.getElementById('cell-selector');
        this.inputFields = document.getElementById('input-fields');
        this.executeBtn = document.getElementById('execute-btn');
        this.resultsContainer = document.getElementById('results-container');
        this.resultsOutput = document.getElementById('results-output');
        this.backBtn = document.getElementById('back-btn');
        this.appContainer = document.getElementById('app-container');
        this.apiContainer = document.getElementById('api-container');
        
        // Event listeners
        this.cellSelector.addEventListener('change', (e) => this.loadCell(e.target.value));
        this.executeBtn.addEventListener('click', () => this.executeCell());
        this.backBtn.addEventListener('click', () => this.showForm());
        
        // Initialize
        this.checkApiMode();
    }
    
    async checkApiMode() {
    const params = new URLSearchParams(window.location.search);
    const apiMode = params.has('api');
    const cellParam = params.get('cell');
    
    if (apiMode && cellParam) {
        try {
            await this.loadAllCells();
            const result = await this.executeCellFromParams(params);
            
            // Return text response
            this.returnTextResponse(result);
        } catch (error) {
            this.returnTextResponse({
                error: error.message,
                stack: error.stack
            }, 400);
        }
    } else {
        // Normal UI mode
        this.loadAllCells();
    }
    }
    
    returnJsonResponse(data, statusCode = 200) {
    const params = new URLSearchParams(window.location.search);
    const format = params.get('format') || 'text';
    
    // Remove all DOM elements
    document.body.innerHTML = '';
    
    let output;
    if (format === 'json') {
        output = JSON.stringify(data, null, 2);
        // Add JSON content type meta
        const meta = document.createElement('meta');
        meta.httpEquiv = "Content-Type";
        meta.content = "application/json";
        document.head.appendChild(meta);
    } else {
        output = typeof data === 'string' ? data : JSON.stringify(data);
    }
    
    document.body.textContent = output;
}
    
    async executeCellFromParams(params) {
        const cellId = params.get('cell');
        if (!cellId || !this.cells[cellId]) {
            throw new Error(`Cell '${cellId}' not found`);
        }
        
        const cell = this.cells[cellId];
        const inputData = {};
        
        // Collect input values from URL parameters
        cell.config.inputs.forEach(input => {
            const paramValue = params.get(input.id);
            
            if (paramValue === null && input.required) {
                throw new Error(`Missing required parameter: ${input.id}`);
            }
            
            switch(input.type) {
                case 'number':
                    inputData[input.id] = parseFloat(paramValue);
                    if (isNaN(inputData[input.id])) throw new Error(`Invalid number for parameter: ${input.id}`);
                    break;
                case 'text':
                case 'select':
                    inputData[input.id] = paramValue || input.value;
                    break;
                case 'json':
                    try {
                        inputData[input.id] = paramValue ? JSON.parse(paramValue) : input.value;
                    } catch (e) {
                        throw new Error(`Invalid JSON for parameter: ${input.id}`);
                    }
                    break;
            }
        });
        
        // Execute the cell's process function
        return cell.process(inputData);
    }
    
    async loadAllCells() {
        try {
            // Try both possible paths for GitHub Pages
            const pathsToTry = [
                '/Robotics-AI-cells/cells/',  // GitHub Pages path
                'cells/'                      // Local development path
            ];
            
            let cellFiles = [];
            
            for (const path of pathsToTry) {
                try {
                    const response = await fetch(path);
                    if (!response.ok) continue;
                    
                    const html = await response.text();
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const links = Array.from(doc.querySelectorAll('a'));
                    
                    cellFiles = links
                        .map(a => a.href)
                        .filter(href => href.endsWith('.js'))
                        .map(href => {
                            // Extract filename from either GitHub Pages or local path
                            const segments = href.split('/');
                            return segments[segments.length - 1];
                        });
                    
                    if (cellFiles.length > 0) break;
                } catch (error) {
                    console.warn(`Failed to load from ${path}:`, error);
                }
            }
            
            // Fallback if no cells found
            if (cellFiles.length === 0) {
                console.warn('No cells found dynamically, using fallback list');
                cellFiles = [
                    'fast_math.js',
                    'pid_controller.js',
                    'arm_ik.js',
                    // ... other default cells
                ];
            }
            
            // Load each cell module
            for (const file of cellFiles) {
                const cellName = file.replace('.js', '');
                try {
                    const module = await import(`./cells/${file}`);
                    this.cells[cellName] = module;
                    this.cellSelector.add(new Option(
                        module.config.name, 
                        cellName
                    ));
                } catch (error) {
                    console.error(`Error loading cell ${cellName}:`, error);
                }
            }
        } catch (error) {
            console.error('Error loading cells:', error);
            this.loadFallbackCells();
        }
    }
    
    loadFallbackCells() {
        const fallbackCells = [
            'fast_math.js', 'pid_controller.js', 'arm_ik.js', 
            'hexapod_gait.js', 'lidar_compress.js'
            // Add other essential cells
        ];
        
        fallbackCells.forEach(file => {
            const cellName = file.replace('.js', '');
            import(`./cells/${file}`)
                .then(module => {
                    this.cells[cellName] = module;
                    this.cellSelector.add(new Option(
                        module.config.name, 
                        cellName
                    ));
                })
                .catch(console.error);
        });
    }
    
    loadCell(cellId) {
        if (!cellId || !this.cells[cellId]) {
            this.inputFields.innerHTML = '';
            this.executeBtn.disabled = true;
            return;
        }
        
        this.currentCell = cellId;
        const cell = this.cells[cellId];
        this.inputFields.innerHTML = '';
        
        // Create input fields based on cell configuration
        cell.config.inputs.forEach(input => {
            const div = document.createElement('div');
            const label = document.createElement('label');
            label.textContent = input.label;
            label.style.display = 'block';
            label.style.marginTop = '10px';
            label.style.fontWeight = '500';
            
            let inputElement;
            
            switch(input.type) {
                case 'number':
                    inputElement = document.createElement('input');
                    inputElement.type = 'number';
                    inputElement.value = input.value;
                    if (input.min !== undefined) inputElement.min = input.min;
                    if (input.max !== undefined) inputElement.max = input.max;
                    break;
                    
                case 'text':
                    inputElement = document.createElement('input');
                    inputElement.type = 'text';
                    inputElement.value = input.value;
                    break;
                    
                case 'select':
                    inputElement = document.createElement('select');
                    input.options.forEach(option => {
                        const optElement = document.createElement('option');
                        optElement.value = option;
                        optElement.textContent = option;
                        if (option === input.value) optElement.selected = true;
                        inputElement.appendChild(optElement);
                    });
                    break;
                    
                case 'json':
                    inputElement = document.createElement('textarea');
                    inputElement.value = typeof input.value === 'string' ? input.value : JSON.stringify(input.value, null, 2);
                    inputElement.rows = 3;
                    break;
            }
            
            inputElement.id = `${cellId}_${input.id}`;
            inputElement.style.width = '100%';
            
            div.appendChild(label);
            div.appendChild(inputElement);
            this.inputFields.appendChild(div);
        });
        
        this.executeBtn.disabled = false;
    }
    
    executeCell() {
        if (!this.currentCell) return;
        
        const cell = this.cells[this.currentCell];
        const inputData = {};
        
        // Collect input values
        cell.config.inputs.forEach(input => {
            const inputElement = document.getElementById(`${this.currentCell}_${input.id}`);
            const value = inputElement.value.trim();
            
            switch(input.type) {
                case 'number':
                    inputData[input.id] = parseFloat(value);
                    if (isNaN(inputData[input.id])) throw new Error('Invalid number');
                    break;
                case 'text':
                case 'select':
                    inputData[input.id] = value;
                    break;
                case 'json':
                    inputData[input.id] = value ? JSON.parse(value) : null;
                    break;
            }
        });
        
        // Execute the cell's process function
        try {
            const result = cell.process(inputData);
            this.showResults(result);
        } catch (error) {
            this.showResults({
                error: error.message,
                stack: error.stack
            }, true);
        }
    }
    
    showResults(data, isError = false) {
        this.resultsOutput.textContent = JSON.stringify(data, null, 2);
        this.resultsOutput.style.borderLeftColor = isError ? 'var(--error)' : 'var(--success)';
        document.querySelector('.cell-form').classList.add('hidden');
        this.resultsContainer.classList.remove('hidden');
    }
    
    showForm() {
        this.resultsContainer.classList.add('hidden');
        document.querySelector('.cell-form').classList.remove('hidden');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RoboticsAIHub();
});
