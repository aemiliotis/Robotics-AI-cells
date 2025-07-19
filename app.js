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
        
        // Event listeners
        this.cellSelector.addEventListener('change', (e) => this.loadCell(e.target.value));
        this.executeBtn.addEventListener('click', () => this.executeCell());
        this.backBtn.addEventListener('click', () => this.showForm());
        
        // Initialize
        this.loadAllCells();
    }
    
    async loadAllCells() {
        try {
            // Dynamically load all cells from the cells directory
            const response = await fetch('cells/');
            const parser = new DOMParser();
            const html = await response.text();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Extract all JavaScript files
            const cellFiles = Array.from(doc.querySelectorAll('a'))
                .map(a => a.href)
                .filter(href => href.endsWith('.js'))
                .map(href => href.split('/').pop());
            
            // Load each cell module
            for (const file of cellFiles) {
                const cellName = file.replace('.js', '');
                try {
                    const module = await import(`../cells/${file}`);
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
        }
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
