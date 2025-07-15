// Configuration
const API_URL = "https://robotics-ai-cells.onrender.com";
const PING_URL = `${API_URL}/ping`;

// All 25 cells configuration
const CELLS = [
    // 1. Core Mathematical Cells
    {
        id: "fast_math",
        name: "Fast Trigonometry",
        category: "utils",
        description: "High-speed sin/cos calculations",
        inputs: [
            { id: "angle", label: "Angle (degrees)", type: "number", value: 45 }
        ]
    },
    {
        id: "pid_controller",
        name: "PID Controller",
        category: "motion",
        description: "Motor control loop",
        inputs: [
            { id: "error", label: "Error", type: "number", value: 0.5 },
            { id: "integral", label: "Integral", type: "number", value: 0 },
            { id: "last_error", label: "Last Error", type: "number", value: 0 }
        ]
    },
    
    // 2. Motion Control Cells
    {
        id: "arm_ik",
        name: "Arm IK Solver",
        category: "motion",
        description: "3DOF inverse kinematics",
        inputs: [
            { id: "target_x", label: "Target X", type: "number", value: 0.5 },
            { id: "target_y", label: "Target Y", type: "number", value: 0.2 },
            { id: "target_z", label: "Target Z", type: "number", value: 0.8 }
        ]
    },
    {
        id: "hexapod_gait",
        name: "Hexapod Gait",
        category: "motion",
        description: "Leg coordination patterns",
        inputs: [
            { id: "gait", label: "Gait Pattern", type: "select", options: ["tripod", "wave", "ripple"], value: "tripod" },
            { id: "step_count", label: "Step Count", type: "number", value: 0 }
        ]
    },
    
    // 3. Perception Cells
    {
        id: "lidar_compress",
        name: "LIDAR Compression",
        category: "perception",
        description: "Scan data optimization",
        inputs: [
            { id: "scan", label: "LIDAR Scan", type: "json", value: "[1.2, 1.21, 1.19, 5.3, 5.31, 5.29]" }
        ]
    },
    {
        id: "visual_odometry",
        name: "Visual Odometry",
        category: "perception",
        description: "Camera-based movement tracking",
        inputs: [
            { id: "prev_gray", label: "Previous Frame", type: "json", value: "[[120, 125], [130, 135]]" },
            { id: "curr_gray", label: "Current Frame", type: "json", value: "[[125, 130], [135, 140]]" },
            { id: "prev_keypoints", label: "Keypoints", type: "json", value: "[[10,20], [30,40]]" }
        ]
    },
    
    // 4. Power Management Cells
    {
        id: "motor_model",
        name: "Motor Model",
        category: "power",
        description: "Current/power estimation",
        inputs: [
            { id: "motor_type", label: "Motor Type", type: "select", options: ["maxon_ec45", "tmotor_5010"], value: "maxon_ec45" },
            { id: "voltage", label: "Voltage (V)", type: "number", value: 12.6 },
            { id: "rpm", label: "RPM", type: "number", value: 3500 }
        ]
    },
    {
        id: "solar_planner",
        name: "Solar Planner",
        category: "power",
        description: "Energy harvesting optimization",
        inputs: [
            { id: "month", label: "Month (1-12)", type: "number", min: 1, max: 12, value: 7 },
            { id: "lat", label: "Latitude", type: "number", min: -90, max: 90, value: 37.7 },
            { id: "panel_w", label: "Panel Watts", type: "number", value: 100 }
        ]
    },
    
    // 5. AI/ML Cells
    {
        id: "tinyml_classify",
        name: "TinyML Classifier",
        category: "perception",
        description: "On-device object detection",
        inputs: [
            { id: "image_data", label: "Image", type: "json", value: "[[[120, 110, 100], [121, 111, 101]], [[122, 112, 102], [123, 113, 103]]]" }
        ]
    },
    {
        id: "gesture_ml",
        name: "Gesture Recognition",
        category: "perception",
        description: "IMU-based gesture detection",
        inputs: [
            { id: "accel_x", label: "Accel X", type: "number", value: 0.12 },
            { id: "accel_y", label: "Accel Y", type: "number", value: 9.81 },
            { id: "accel_z", label: "Accel Z", type: "number", value: 0.33 },
            { id: "gyro_z", label: "Gyro Z", type: "number", value: 0.01 }
        ]
    },
    
    // 6. Communication Cells
    {
        id: "lora_packer",
        name: "LoRa Packer",
        category: "utils",
        description: "IoT message compression",
        inputs: [
            { id: "temp", label: "Temperature", type: "number", value: 25.3 },
            { id: "humidity", label: "Humidity", type: "number", value: 45 },
            { id: "accel_x", label: "Accel X", type: "number", value: 0.12 },
            { id: "battery", label: "Battery %", type: "number", value: 78.5 }
        ]
    },
    {
        id: "ros2_adapter",
        name: "ROS2 Adapter",
        category: "utils",
        description: "ROS message conversion",
        inputs: [
            { id: "vel_x", label: "Velocity X", type: "number", value: 0.5 },
            { id: "ang_vel", label: "Angular Vel", type: "number", value: 0.2 },
            { id: "frame", label: "Frame ID", type: "text", value: "base_link" }
        ]
    },
    
    // 7. Utility Cells
    {
        id: "error_handler",
        name: "Error Handler",
        category: "utils",
        description: "Fault recovery system",
        inputs: [
            { id: "error_code", label: "Error Code", type: "text", value: "0x21" }
        ]
    },
    {
        id: "micro_logger",
        name: "Micro Logger",
        category: "utils",
        description: "Data recording",
        inputs: [
            { id: "event", label: "Event Name", type: "text", value: "obstacle_detected" },
            { id: "value", label: "Value", type: "number", value: 1.75 }
        ]
    },
    
    // 8. Sensor Fusion
    {
        id: "sensor_fusion",
        name: "Sensor Fusion",
        category: "perception",
        description: "IMU + GPS + LIDAR",
        inputs: [
            { id: "accel_x", label: "Accel X", type: "number", value: 0.1 },
            { id: "accel_y", label: "Accel Y", type: "number", value: 0.02 },
            { id: "accel_z", label: "Accel Z", type: "number", value: 9.8 },
            { id: "gps_lat", label: "GPS Lat", type: "number", value: 37.7749 },
            { id: "gps_lon", label: "GPS Lon", type: "number", value: -122.4194 }
        ]
    },
    
    // 9. Path Planning
    {
        id: "path_optimization",
        name: "Path Optimization",
        category: "motion",
        description: "Energy-efficient navigation",
        inputs: [
            { id: "waypoints", label: "Waypoints", type: "json", value: "[[0,0], [1,1], [2,0], [3,1]]" },
            { id: "terrain", label: "Terrain Factor", type: "number", value: 1.2 }
        ]
    },
    
    // 10. Battery Optimization
    {
        id: "battery_optimization",
        name: "Battery Optimization",
        category: "power",
        description: "Power management",
        inputs: [
            { id: "charge_cycles", label: "Charge Cycles", type: "number", value: 150 },
            { id: "avg_dod", label: "Avg DoD %", type: "number", value: 80 },
            { id: "avg_temp", label: "Avg Temp °C", type: "number", value: 35 }
        ]
    },
    
    // 11. Computer Vision
    {
        id: "vision_optimized",
        name: "Vision Optimized",
        category: "perception",
        description: "Lightweight image processing",
        inputs: [
            { id: "image_data", label: "Image", type: "json", value: "[[[120, 120, 120], [125, 125, 125]], [[130, 130, 130], [135, 135, 135]]]" }
        ]
    },
    
    // 12. Shared Memory
    {
        id: "shared_memory",
        name: "Shared Memory",
        category: "utils",
        description: "Inter-process communication",
        inputs: [
            { id: "key", label: "Key", type: "text", value: "last_position" },
            { id: "value", label: "Value", type: "json", value: "[1.2, 3.4, 0.8]" }
        ]
    },
    
    // 13. Math Utilities
    {
        id: "math_utils",
        name: "Math Utilities",
        category: "utils",
        description: "Optimized calculations",
        inputs: [
            { id: "x", label: "Input Value", type: "number", value: 42 }
        ]
    },
    
    // 14. Precision Scaling
    {
        id: "precision_scaling",
        name: "Precision Scaling",
        category: "utils",
        description: "Data compression",
        inputs: [
            { id: "arr", label: "Array", type: "json", value: "[1.23, 4.56, 7.89]" },
            { id: "factor", label: "Scale Factor", type: "number", value: 100 }
        ]
    },
    
    // 15. Timed Process
    {
        id: "timed_process",
        name: "Timed Process",
        category: "utils",
        description: "Execution monitoring",
        inputs: [
            { id: "data", label: "Input Data", type: "json", value: "{\"sensor\": \"temp\", \"value\": 27.3}" }
        ]
    },
    
    // 16. Data Logger
    {
        id: "data_logger",
        name: "Data Logger",
        category: "utils",
        description: "System telemetry",
        inputs: [
            { id: "timestamp", label: "Timestamp", type: "number", value: 1625097600 },
            { id: "readings", label: "Readings", type: "json", value: "{\"current\": 1.2, \"voltage\": 12.3}" }
        ]
    },
    
    // 17. Network Optimizer
    {
        id: "network_optimizer",
        name: "Network Optimizer",
        category: "utils",
        description: "Communication tuning",
        inputs: [
            { id: "packet_size", label: "Packet Size", type: "number", value: 128 },
            { id: "signal_strength", label: "Signal dBm", type: "number", value: -67 }
        ]
    },
    
    // 18. Safety Monitor
    {
        id: "safety_monitor",
        name: "Safety Monitor",
        category: "utils",
        description: "Joint limit checking",
        inputs: [
            { id: "joint_angles", label: "Joint Angles", type: "json", value: "[0.1, 0.5, 1.2]" },
            { id: "limits", label: "Limits", type: "json", value: "[1.0, 1.0, 1.5]" }
        ]
    }
];

// State management
let apiStatus = false;
let lastResponse = null;
let currentUser = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Set API URL display
    document.getElementById('api-url').textContent = API_URL;
    
    // Create all cell cards
    renderAllCells();
    
    // Set up tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    
    // Check API status
    checkApiStatus();
    
    // API Management setup
    setupAPIManagement();
    
    // Check if user is logged in
    checkAuthStatus();
});

function renderAllCells() {
    const allCellsContainer = document.getElementById('all-cells');
    const motionContainer = document.getElementById('motion-cells');
    const perceptionContainer = document.getElementById('perception-cells');
    const powerContainer = document.getElementById('power-cells');
    const utilsContainer = document.getElementById('utils-cells');
    
    // Clear existing content
    allCellsContainer.innerHTML = '';
    motionContainer.innerHTML = '';
    perceptionContainer.innerHTML = '';
    powerContainer.innerHTML = '';
    utilsContainer.innerHTML = '';
    
    CELLS.forEach(cell => {
        const card = createCellCard(cell);
        allCellsContainer.appendChild(card.cloneNode(true));
        
        // Add to category-specific containers
        switch(cell.category) {
            case 'motion':
                motionContainer.appendChild(card);
                break;
            case 'perception':
                perceptionContainer.appendChild(card);
                break;
            case 'power':
                powerContainer.appendChild(card);
                break;
            case 'utils':
                utilsContainer.appendChild(card);
                break;
        }
    });
}

function createCellCard(cell) {
    const card = document.createElement('div');
    card.className = 'cell-card';
    card.dataset.cellId = cell.id;
    
    // Header
    const header = document.createElement('div');
    header.className = 'cell-header';
    
    const title = document.createElement('div');
    title.className = 'cell-title';
    title.textContent = cell.name;
    
    header.appendChild(title);
    card.appendChild(header);
    
    // Description
    const desc = document.createElement('p');
    desc.textContent = cell.description;
    desc.style.fontSize = '0.9em';
    desc.style.color = '#666';
    card.appendChild(desc);
    
    // Controls
    const controls = document.createElement('div');
    controls.className = 'cell-controls';
    
    cell.inputs.forEach(input => {
        const label = document.createElement('label');
        label.textContent = input.label;
        label.style.display = 'block';
        label.style.marginTop = '10px';
        label.style.fontWeight = '500';
        controls.appendChild(label);
        
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
        
        inputElement.id = `${cell.id}_${input.id}`;
        inputElement.style.width = '100%';
        controls.appendChild(inputElement);
    });
    
    const button = document.createElement('button');
    button.textContent = 'Execute';
    button.addEventListener('click', () => executeCell(cell.id));
    controls.appendChild(button);
    
    card.appendChild(controls);
    
    // Response area
    const response = document.createElement('div');
    response.className = 'response';
    response.id = `${cell.id}_response`;
    response.textContent = 'Response will appear here...';
    card.appendChild(response);
    
    return card;
}

async function executeCell(cellId) {
    const cell = CELLS.find(c => c.id === cellId);
    if (!cell) return;

    const responseElement = document.getElementById(`${cellId}_response`);
    const button = document.querySelector(`.cell-card[data-cell-id="${cellId}"] button`);
    
    // Reset UI
    responseElement.className = 'response loading';
    responseElement.textContent = 'Processing...';
    button.disabled = true;

    try {
        // Prepare input data
        const cellInputData = {};
        for (const input of cell.inputs) {
            const inputElement = document.getElementById(`${cellId}_${input.id}`);
            const value = inputElement.value.trim();
            
            switch(input.type) {
                case 'number':
                    cellInputData[input.id] = parseFloat(value);
                    if (isNaN(cellInputData[input.id])) throw new Error('Invalid number');
                    break;
                case 'text':
                case 'select':
                    cellInputData[input.id] = value;
                    break;
                case 'json':
                    cellInputData[input.id] = value ? JSON.parse(value) : null;
                    break;
            }
        }

        // Structure data to match backend expectations
        const requestData = {
            cells: [cellId],
            data: {
                [cellId]: cellInputData
            }
        };

        const response = await fetch(`${API_URL}/ai-api`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        
        if (!response.ok || !result.success) {
            throw new Error(result.error || `API request failed with status ${response.status}`);
        }

        // Handle backend response format
        if (result.results && result.results[cellId]) {
            responseElement.textContent = JSON.stringify(result.results[cellId], null, 2);
            responseElement.className = 'response success';
        } else {
            throw new Error('API did not return results for this cell');
        }
        
        updateLastUpdate();

    } catch (error) {
        console.error('Execution error:', error);
        responseElement.textContent = `Error: ${error.message}`;
        responseElement.className = 'response error';
    } finally {
        button.disabled = false;
    }
}

function switchTab(tabId) {
    // Update active tab
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    // Show corresponding content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabId}-tab`);
    });
    
    // Special handling for API tab
    if (tabId === 'api') {
        populateCellSelection();
        if (currentUser) {
            loadAPIKeys();
        }
    }
}

async function checkApiStatus() {
    const statusElement = document.getElementById('api-status');
    statusElement.className = 'api-status checking';
    
    try {
        const response = await fetch(PING_URL, {
            method: 'GET',
            mode: 'cors',
            credentials: 'omit'
        });
        
        apiStatus = response.ok;
        statusElement.className = `api-status ${apiStatus ? 'online' : 'offline'}`;
        
        if (apiStatus) {
            const data = await response.json();
            console.log("API Status:", data.status);
        }
    } catch (e) {
        apiStatus = false;
        statusElement.className = 'api-status offline';
        console.error("API Status Check Failed:", e);
    }
    
    setTimeout(checkApiStatus, 30000);
}

function updateLastUpdate() {
    const now = new Date();
    document.getElementById('last-update').textContent = 
        `Last updated: ${now.toLocaleTimeString()}`;
}

// API Management Functions
function setupAPIManagement() {
    document.getElementById('generate-api-key').addEventListener('click', generateAPIKey);
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    document.getElementById('register-btn').addEventListener('click', handleRegister);
    populateCellSelection();
}

function checkAuthStatus() {
    const apiKey = localStorage.getItem('api_key');
    const secretKey = localStorage.getItem('secret_key');
    
    if (apiKey && secretKey) {
        // We have credentials, verify them
        verifyAPIKeys(apiKey, secretKey);
    } else {
        // Show login form
        showLoginUI();
    }
}

async function verifyAPIKeys(apiKey, secretKey) {
    try {
        const response = await fetch(`${API_URL}/api/list-keys`, {
            method: 'GET',
            headers: {
                'X-API-KEY': apiKey,
                'X-SECRET-KEY': secretKey
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser = {
                apiKey,
                secretKey
            };
            showAPIKeyUI();
            loadAPIKeys();
        } else {
            // Invalid keys, clear them
            localStorage.removeItem('api_key');
            localStorage.removeItem('secret_key');
            showLoginUI();
        }
    } catch (error) {
        console.error('Error verifying API keys:', error);
        showLoginUI();
    }
}

function showLoginUI() {
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('api-key-form').style.display = 'none';
    document.getElementById('api-key-result').style.display = 'none';
    document.getElementById('api-keys-list').style.display = 'none';
}

function showAPIKeyUI() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('api-key-form').style.display = 'block';
    document.getElementById('api-keys-list').style.display = 'block';
    document.getElementById('api-key-result').style.display = 'none';
}

async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    if (!email || !password) {
        alert('Please enter email and password');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                password
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Login failed');
        }
        
        const data = await response.json();
        
        // Store the API keys
        localStorage.setItem('api_key', data.api_key);
        localStorage.setItem('secret_key', data.secret_key);
        
        // Update UI
        currentUser = {
            apiKey: data.api_key,
            secretKey: data.secret_key,
            email: data.user.email
        };
        
        showAPIKeyUI();
        loadAPIKeys();
        
    } catch (error) {
        console.error('Login error:', error);
        alert('Login failed: ' + error.message);
    }
}

async function handleRegister() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    if (!email || !password) {
        alert('Please enter email and password');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                password
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Registration failed');
        }
        
        alert('Registration successful! Please login.');
        document.getElementById('login-email').value = email;
        document.getElementById('login-password').value = '';
        
    } catch (error) {
        console.error('Registration error:', error);
        alert('Registration failed: ' + error.message);
    }
}

function populateCellSelection() {
    const container = document.getElementById('cell-selection');
    container.innerHTML = '';
    
    CELLS.forEach(cell => {
        const div = document.createElement('div');
        div.className = 'cell-checkbox';
        div.innerHTML = `
            <input type="checkbox" id="cell-${cell.id}" value="${cell.id}">
            <label for="cell-${cell.id}">${cell.name} (${cell.id})</label>
        `;
        container.appendChild(div);
    });
}

async function generateAPIKey() {
    const name = document.getElementById('api-key-name').value.trim();
    const description = document.getElementById('api-key-desc').value.trim();
    
    if (!name) {
        alert('Please enter a name for your API key');
        return;
    }
    
    // Get selected cells
    const selectedCells = [];
    document.querySelectorAll('#cell-selection input[type="checkbox"]:checked').forEach(cb => {
        selectedCells.push(cb.value);
    });
    
    try {
        const response = await fetch(`${API_URL}/api/create-api-key`, {
            method: 'POST',
            headers: {
                'X-API-KEY': currentUser.apiKey,
                'X-SECRET-KEY': currentUser.secretKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                description,
                allowed_cells: selectedCells
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to generate API key');
        }
        
        const data = await response.json();
        
        // Show the new keys
        document.getElementById('new-api-key').value = data.api_key;
        document.getElementById('new-secret-key').value = data.secret_key;
        
        // Generate example usage
        const exampleCell = selectedCells.length > 0 ? selectedCells[0] : 'pid_controller';
        document.getElementById('api-example').textContent = `fetch("${API_URL}/ai-api", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-KEY": "${data.api_key}",
    "X-SECRET-KEY": "${data.secret_key}"
  },
  body: JSON.stringify({
    cells: ["${exampleCell}"],
    data: {
      "${exampleCell}": {
        // Input parameters for ${exampleCell}
      }
    }
  })
});`;
        
        document.getElementById('api-key-form').style.display = 'none';
        document.getElementById('api-key-result').style.display = 'block';
        
        // Reload keys list
        await loadAPIKeys();
    } catch (error) {
        console.error('Error generating API key:', error);
        alert('Error generating API key: ' + error.message);
    }
}

async function loadAPIKeys() {
    try {
        const response = await fetch(`${API_URL}/api/list-keys`, {
            method: 'GET',
            headers: {
                'X-API-KEY': currentUser.apiKey,
                'X-SECRET-KEY': currentUser.secretKey
            }
        });
        
        if (!response.ok) throw new Error('Failed to load API keys');
        
        const data = await response.json();
        renderAPIKeys(data.keys);
    } catch (error) {
        console.error('Error loading API keys:', error);
        alert('Error loading API keys: ' + error.message);
    }
}

function renderAPIKeys(keys) {
    const tbody = document.getElementById('keys-table-body');
    tbody.innerHTML = '';
    
    if (!keys || keys.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No API keys found</td></tr>';
        return;
    }
    
    keys.forEach(key => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${key.name || 'Unnamed'}</td>
            <td>${new Date(key.created_at).toLocaleString()}</td>
            <td>${key.last_used ? new Date(key.last_used).toLocaleString() : 'Never'}</td>
            <td><span class="status-badge ${key.is_active ? 'active' : 'inactive'}">
                ${key.is_active ? 'Active' : 'Inactive'}
            </span></td>
            <td>
                <button class="btn-sm revoke-btn" data-key-id="${key.id}" ${!key.is_active ? 'disabled' : ''}>
                    Revoke
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    // Add event listeners to revoke buttons
    document.querySelectorAll('.revoke-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to revoke this API key?')) {
                try {
                    const response = await fetch(`${API_URL}/api/revoke-key/${btn.dataset.keyId}`, {
                        method: 'POST',
                        headers: {
                            'X-API-KEY': currentUser.apiKey,
                            'X-SECRET-KEY': currentUser.secretKey,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (!response.ok) throw new Error('Failed to revoke key');
                    
                    alert('API key revoked successfully');
                    await loadAPIKeys();
                } catch (error) {
                    console.error('Error revoking key:', error);
                    alert('Error revoking key: ' + error.message);
                }
            }
        });
    });
}
