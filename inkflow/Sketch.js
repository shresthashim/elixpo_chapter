const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const rc = rough.canvas(canvas);
const angleInfo = document.getElementById('angleInfo');
const sidebar = document.getElementById('sidebar');
const savedList = document.getElementById('saved-list');
const textInput = document.getElementById('textInput');

let isDrawing = false;
let isWriting = false;
let hoveredElement = "";
let selectedStrokeWidth = 3;
let lastX = 0;
let lastY = 0;
let elements = [];
let selectedTool = 'pencil';
let selectedColor = '#1AFF7D';
let currentElement = "";
let selectedElement = "";
let offsetX = 0;
let offsetY = 0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;
let scale = 1;  
const scaleFactor = 0.1;  

let undoStack = [];
let redoStack = [];
const maxHistorySize = 10; 


function resizeCanvas() {
    canvas.width = window.innerWidth * 2;
    canvas.height = window.innerHeight * 2;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.scale(2, 2);
    redrawCanvas();
}

window.addEventListener('resize', handleResize);


document.getElementById('zoom-in').addEventListener('click', (e) => {
    const zoom = 1 + scaleFactor;
    scale *= zoom;
    const mouseX = canvas.width / 2 / scale;
    const mouseY = canvas.height / 2 / scale;
    elements.forEach(element => {
        element.x1 = mouseX + (element.x1 - mouseX) * zoom;
        element.y1 = mouseY + (element.y1 - mouseY) * zoom;
        if (element.x2 !== undefined) element.x2 = mouseX + (element.x2 - mouseX) * zoom;
        if (element.y2 !== undefined) element.y2 = mouseY + (element.y2 - mouseY) * zoom;
    });
    redrawCanvas();
});

document.getElementById('zoom-out').addEventListener('click', (e) => {
    const zoom = 1 - scaleFactor;
    scale *= zoom;
    const mouseX = canvas.width / 2 / scale;
    const mouseY = canvas.height / 2 / scale;
    elements.forEach(element => {
        element.x1 = mouseX + (element.x1 - mouseX) * zoom;
        element.y1 = mouseY + (element.y1 - mouseY) * zoom;
        if (element.x2 !== undefined) element.x2 = mouseX + (element.x2 - mouseX) * zoom;
        if (element.y2 !== undefined) element.y2 = mouseY + (element.y2 - mouseY) * zoom;
    });
    redrawCanvas();
});


canvas.addEventListener('wheel', (e) => {
    if (e.ctrlKey) {
        e.preventDefault();
        const mouseX = e.offsetX;
        const mouseY = e.offsetY;
        const zoom = e.deltaY < 0 ? 1 + scaleFactor : 1 - scaleFactor;

        // Adjust the scale
        scale *= zoom;

        // Adjust the elements' positions
        elements.forEach(element => {
            element.x1 = mouseX + (element.x1 - mouseX) * zoom;
            element.y1 = mouseY + (element.y1 - mouseY) * zoom;
            if (element.x2 !== undefined) element.x2 = mouseX + (element.x2 - mouseX) * zoom;
            if (element.y2 !== undefined) element.y2 = mouseY + (element.y2 - mouseY) * zoom;
        });

        redrawCanvas();
    }
});

canvas.addEventListener('contextmenu', (e) => {
    e.preventDefault(); 
});

canvas.addEventListener('mousedown', (e) => {
    if (e.button === 2) { 
        isPanning = true;
        startPanX = e.clientX;
        startPanY = e.clientY;
        canvas.style.cursor = 'grabbing';
    } else {
        handleMouseDown(e);
    }
});

canvas.addEventListener('mousemove', (e) => {
    if (isPanning) {
        pan(e);
    } else {
        handleMouseMove(e);
    }
});

canvas.addEventListener('mouseup', (e) => {
    if (e.button === 2) { 
        isPanning = false;
        canvas.style.cursor = 'crosshair';
    } else {
        handleMouseUp(e);
    }
});

document.getElementById('strokeWidth').addEventListener('change', (e) => {
    selectedStrokeWidth = parseInt(e.target.value);
});

// Toolbar functionality
document.querySelectorAll('.tool').forEach(tool => {
    tool.addEventListener('click', () => {
        if (tool.id === 'clear') {
            elements = [];
            redrawCanvas();
        } else if (tool.id === 'save') {
            saveWork();
        } else if (tool.id === 'open-sidebar') {
            sidebar.classList.toggle('open');
           // updateSavedList(); // Update sidebar height after toggling
        } 
        else if (tool.id === 'undo') {
            undo();
        } else if (tool.id === 'redo') {
            redo();
        } else if (tool.id === 'select') {
            selectedTool = 'select';
            tool.classList.add('active'); // Keep the select tool active
        }
        else {
            document.querySelector('.tool.active').classList.remove('active');
            tool.classList.add('active');
            selectedTool = tool.id;
            updateCursorStyle();
        }
    });
});

document.getElementById('colorPicker').addEventListener('input', (e) => {
    selectedColor = e.target.value;
});

// Consolidated event listeners
canvas.addEventListener('mousedown', handleMouseDown);
canvas.addEventListener('mousemove', handleMouseMove);
canvas.addEventListener('mouseup', handleMouseUp);

canvas.addEventListener('mousemove', (e) => {
    if (selectedTool === 'eraser') {
        hoveredElement = getElementAtPosition(e.offsetX, e.offsetY); // Check for hover
        redrawCanvas(); // Redraw with opacity changes
    } else {
        hoveredElement = null; // Reset hover
        redrawCanvas();
    }
})

canvas.addEventListener('mouseup', (e) => {
    if (selectedTool === 'eraser' && hoveredElement) {
        // If the mouse is released while hovering over an element, erase it
        elements = elements.filter(element => element !== hoveredElement);
        hoveredElement = null;
        redrawCanvas();
    }
})

function handleMouseDown(e) {
    if (selectedTool === 'select') {
        const clickedX = e.offsetX;
        const clickedY = e.offsetY;
        selectedElement = getElementAtPosition(clickedX, clickedY);

        if (selectedElement) {
            // Calculate offset from where the mouse was clicked
            offsetX = clickedX - selectedElement.x1;
            offsetY = clickedY - selectedElement.y1;
        } else {
            isPanning = true;
            startPanX = e.clientX;
            startPanY = e.clientY;
        }
    } else if (selectedTool === 'arrow') {
        isDrawing = true;
        startX = e.offsetX;
        startY = e.offsetY;
    } else {
        startDrawing(e);
    }
}

function handleMouseMove(e) {
    if (selectedElement) {
        const newX = e.offsetX;
        const newY = e.offsetY;

        // Move both x1, y1 and x2, y2 coordinates equally without altering the element size
        const moveX = newX - offsetX;
        const moveY = newY - offsetY;

        const dx = moveX - selectedElement.x1;
        const dy = moveY - selectedElement.y1;

        selectedElement.x1 = moveX;
        selectedElement.y1 = moveY;

        // If the element has x2, y2 (for lines, rectangles, triangles), move them equally
        if (selectedElement.x2 !== undefined && selectedElement.y2 !== undefined) {
            selectedElement.x2 += dx;
            selectedElement.y2 += dy;
        }

        // Special handling for the pencil tool (move all segments)
        if (selectedElement.type === 'pencil') {
            elements = elements.map(element => {
                if (element === selectedElement) {
                    return {
                        ...element,
                        x1: element.x1 + dx,
                        y1: element.y1 + dy,
                        x2: element.x2 + dx,
                        y2: element.y2 + dy
                    };
                }
                return element;
            });
        }

        // Special handling for the triangle tool (update its vertices)
        if (selectedElement.type === 'triangle') {
            // Move the vertices of the triangle
            selectedElement.x1 += dx;
            selectedElement.y1 += dy; // Move the top vertex
            selectedElement.x2 += dx; // Move the left vertex
            selectedElement.y2 += dy; // Move the right vertex
        }

        redrawCanvas();  // Redraw after moving the selected element
    } else if (isPanning) {
        pan(e);
    } else if (isDrawing && selectedTool === 'arrow') {
        redrawCanvas();
        const context = canvas.getContext('2d');
        drawArrow(context, startX, startY, e.offsetX, e.offsetY);
    } else {
        draw(e);
    }
}

function handleMouseUp(e) {
    if (selectedElement) {
        selectedElement = null;
    } else if (isPanning) {
        isPanning = false;
    } else if (isDrawing && selectedTool === 'arrow') {
        isDrawing = false;
        elements.push({
            type: 'arrow',
            x1: startX,
            y1: startY,
            x2: e.offsetX,
            y2: e.offsetY,
            color: selectedColor
        });
        saveState(); // Save state after adding a new arrow
        redrawCanvas(); // Redraw all the elements, including the new arrow
    } else {
        stopDrawing();
        saveState(); // Save state after drawing is stopped
    }
}

function startDrawing(e) {
    isDrawing = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
    if ((selectedTool === 'text') && !isWriting) {
        showTextInput(e.offsetX, e.offsetY);
    } else {
        currentElement = { type: selectedTool, x1: lastX, y1: lastY, color: selectedColor };
    }
}

function draw(e) {
    if (!isDrawing) return;

    const currentX = e.offsetX;
    const currentY = e.offsetY;

    if (selectedTool === 'pencil') {
        elements.push({
            type: 'pencil',
            x1: lastX,
            y1: lastY,
            x2: currentX,
            y2: currentY,
            color: selectedColor,
            strokeWidth: selectedStrokeWidth // Save the stroke width for this segment
        });
        // Update last position
        [lastX, lastY] = [currentX, currentY];
    } else if (selectedTool === 'eraser') {
        eraseAt(currentX, currentY);
    } else if (currentElement) {
        currentElement.x2 = currentX;
        currentElement.y2 = currentY;
    }

    if (selectedTool === 'line') {
        showAngle(lastX, lastY, currentX, currentY);
    }

    redrawCanvas();
}


function eraseAt(x, y) {
    const eraserRadius = 20;
    elements = elements.filter(element => {
        // Check if the element is of type text; if so, don't erase it
        if (element.type === 'text') {
            return true; // Keep the text element
        }

        if (element.type === 'pencil') {
            const distance = Math.sqrt(
                Math.pow((element.x1 + element.x2) / 2 - x, 2) +
                Math.pow((element.y1 + element.y2) / 2 - y, 2)
            );
            return distance > eraserRadius; // Erase if within radius
        } else {
            const centerX = (element.x1 + element.x2) / 2;
            const centerY = (element.y1 + element.y2) / 2;
            const distance = Math.sqrt(
                Math.pow(centerX - x, 2) +
                Math.pow(centerY - y, 2)
            );
            return distance > eraserRadius; // Erase if within radius
        }
    });
}


function stopDrawing() {
    if (!isDrawing) return;
    isDrawing = false;
    angleInfo.style.display = 'none';

    if (selectedTool !== 'pencil' && selectedTool !== 'eraser' && selectedTool !== 'text') {
        elements.push(currentElement);
    }
    currentElement = null;
    saveState(); // Save state after stopping drawing
    redrawCanvas();
}

function redrawCanvas() {
    // Clear the entire canvas before redrawing
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw existing elements
    elements.forEach(element => {
        if (element === hoveredElement) {
            ctx.globalAlpha = 0.3; // Reduce opacity for hovered element
            drawElement(element);
            ctx.globalAlpha = 1;   // Reset opacity
        } else {
            drawElement(element);
        }
    });

    // Draw the current element (in progress)
    if (currentElement) {
        drawElement(currentElement);
    }

    // Handle tool-specific behavior
    if (selectedTool === 'eraser') {
        canvas.addEventListener('mousemove', showEraserRadius);
        canvas.removeEventListener('mousemove', showPencilRadius);
    } else if (selectedTool === 'pencil') {
        canvas.addEventListener('mousemove', showPencilRadius);
        canvas.removeEventListener('mousemove', showEraserRadius);
    } else {
        // Remove radius display for other tools
        canvas.removeEventListener('mousemove', showEraserRadius);
        canvas.removeEventListener('mousemove', showPencilRadius);
    }
}


function showEraserRadius(e) {
    redrawCanvas(); // Clear the canvas and redraw all elements
    const eraserRadius = 20;
    ctx.beginPath();
    ctx.arc(e.offsetX, e.offsetY, eraserRadius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(69, 69, 69, 0.5)'; // Semi-transparent circle
    ctx.fillStyle = 'rgba(69, 69, 69, 0.5)'; // Semi-transparent fill
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fill();
}

function showPencilRadius(e) {
    redrawCanvas(); // Clear the canvas and redraw all elements
    const eraserRadius = selectedStrokeWidth;
    ctx.beginPath();
    ctx.arc(e.offsetX, e.offsetY, eraserRadius, 0, Math.PI * 2);
    ctx.strokeStyle = selectedColor; // Semi-transparent circle
    ctx.fillStyle = selectedColor; // Semi-transparent fill
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fill();
}

function clearRadius(e) {
    redrawCanvas(); // Clear the canvas and redraw all elements
    const eraserRadius = 0;
    ctx.beginPath();
    ctx.arc(e.offsetX, e.offsetY, eraserRadius, 0, Math.PI * 2);
    ctx.strokeStyle = selectedColor; // Semi-transparent circle
    ctx.fillStyle = selectedColor; // Semi-transparent fill
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fill();
}

function drawElement(element) {
    switch (element.type) {
        case 'pencil':
            rc.line(element.x1, element.y1, element.x2, element.y2, { stroke: element.color, roughness: 0, strokeWidth: element.strokeWidth });
            break;
        case 'line':
            rc.line(element.x1, element.y1, element.x2, element.y2, { stroke: element.color });
            break;
        case 'rectangle':
            rc.rectangle(element.x1, element.y1, element.x2 - element.x1, element.y2 - element.y1, { stroke: element.color });
            break;
        case 'circle':
            const width = element.x2 - element.x1;
            const height = element.y2 - element.y1;
            const diameter = Math.max(Math.abs(width), Math.abs(height));
            rc.circle(element.x1 + width / 2, element.y1 + height / 2, diameter, { stroke: element.color });
            break;
        case 'triangle':
            rc.path(`M ${element.x1} ${element.y2} L ${element.x2} ${element.y2} L ${(element.x1 + element.x2) / 2} ${element.y1} Z`, { stroke: element.color });
            break;
        case 'text':
            ctx.font = '25px monospace';
            ctx.fillStyle = element.color;
            if(element.text != 'undefined')
            {
                ctx.fillText(element.text, element.x1, element.y1);
            }
            break;
        case 'arrow':
            drawArrow(ctx, element.x1, element.y1, element.x2, element.y2);
            break;
    }
}
// Pan functionality
function pan(e) {
    const dx = (e.clientX - startPanX) / 2; // Adjust for the canvas scale
    const dy = (e.clientY - startPanY) / 2; // Adjust for the canvas scale
    elements.forEach(element => {
        element.x1 += dx;
        element.y1 += dy;
        if (element.x2 !== undefined) element.x2 += dx;
        if (element.y2 !== undefined) element.y2 += dy;
    });
    startPanX = e.clientX;
    startPanY = e.clientY;
    redrawCanvas();
}

// Show angle
function showAngle(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;
    angle = (angle + 360) % 360; // Normalize to 0-360
    angleInfo.textContent = `Angle: ${angle.toFixed(1)}°`;
    angleInfo.style.display = 'block';
}

// Eraser functionality


// Text functionality
function showTextInput(x, y) {
    isWriting = true;
    textInput.value = '';
    textInput.style.display = 'block';
    textInput.style.fontSize = '25px';
    textInput.style.color = selectedColor;
    textInput.style.backgroundColor = 'transparent';
    textInput.style.fontFamily = 'monospace';
    textInput.style.caretColor = selectedColor;
    textInput.style.left = `${x}px`;
    textInput.style.top = `${y - 20}px`;
    setTimeout(() => textInput.focus(), 500); // Delay to ensure focus
    textInput.focus(); 
}





canvas.addEventListener('click', (e) => {
    if (isWriting) {
        const text = textInput.value;
        if (text && text.trim() !== '') { // Check if text is not empty
            elements.push({
                type: 'text',
                x1: parseInt(textInput.style.left),
                y1: parseInt(textInput.style.top) + 20, // Adjust for text baseline
                text: text,
                color: selectedColor
            });
            redrawCanvas();
        } else {
            // Clear the text input if it's empty or undefined
            textInput.value = ''; 
        }
        textInput.style.display = 'none';
        isWriting = false;
    }
});
function adjustSize() {
    // Reset the width and height to 'auto' to calculate new dimensions
    textInput.style.width = 'auto';
    textInput.style.height = 'auto';
    
    // Set the width and height based on the scrollHeight and scrollWidth
    textInput.style.height = `${textInput.scrollHeight}px`;
    textInput.style.width = `${textInput.scrollWidth}px`;
}
textInput.addEventListener('input', adjustSize);

// Save and load functionality
function saveWork() {
    const name = prompt("Enter a name for this work:");
    if (name) {
        const savedWorks = JSON.parse(localStorage.getItem('savedWorks') || '[]');
        savedWorks.push({ name, elements: JSON.parse(JSON.stringify(elements)) });
        localStorage.setItem('savedWorks', JSON.stringify(savedWorks));
        // updateSavedList();
    }
}

function updateSavedList() {
    const savedWorks = JSON.parse(localStorage.getItem('savedWorks') || '[]');
    // savedList.innerHTML = '';
    savedWorks.forEach((work, index) => {
        const item = document.createElement('div');
        item.className = 'saved-item';
        item.innerHTML = `
            <span>${work.name}</span>
            <div>
                <button onclick="loadWork(${index})"><i class="fas fa-folder-open"></i></button>
                <button onclick="deleteWork(${index})"><i class="fas fa-trash"></i></button>
            </div>
        `;
        savedList.appendChild(item);
    });

    // Adjust the sidebar height based on content
    const sidebarHeight = Math.min(savedList.scrollHeight + 100, window.innerHeight * 0.8);
    sidebar.style.height = `${sidebarHeight}px`;
    sidebar.style.bottom = sidebar.classList.contains('open') ? '0' : `-${sidebarHeight}px`;
}

function loadWork(index) {
    const savedWorks = JSON.parse(localStorage.getItem('savedWorks') || '[]');
    if (savedWorks[index]) {
        elements = JSON.parse(JSON.stringify(savedWorks[index].elements));
        redrawCanvas();
        sidebar.classList.remove('open');
        // updateSavedList(); // Update sidebar height after loading
    }
}

function deleteWork(index) {
    const savedWorks = JSON.parse(localStorage.getItem('savedWorks') || '[]');
    savedWorks.splice(index, 1);
    localStorage.setItem('savedWorks', JSON.stringify(savedWorks));
    // updateSavedList();
}

function handleResize() {
    resizeCanvas();
    // updateSavedList();
}

function updateCursorStyle() {
    if (selectedTool === 'select') {
        canvas.style.cursor = 'grab';
    } 
    else if (selectedTool === 'text') {
        canvas.style.cursor = 'text';
    }
    else {
        canvas.style.cursor = 'crosshair';
    }
}

// Add this function to handle drawing an arrow
function drawArrow(context, fromX, fromY, toX, toY) {
    const headLength = 10; // length of the arrow head
    const dx = toX - fromX;
    const dy = toY - fromY;
    const angle = Math.atan2(dy, dx);

    context.beginPath();
    context.moveTo(fromX, fromY);
    context.lineTo(toX, toY);
    context.moveTo(toX, toY);
    context.lineTo(toX - headLength * Math.cos(angle - Math.PI / 6), toY - headLength * Math.sin(angle - Math.PI / 6));
    context.moveTo(toX, toY);
    context.lineTo(toX - headLength * Math.cos(angle + Math.PI / 6), toY - headLength * Math.sin(angle + Math.PI / 6));
    context.strokeStyle = selectedColor;  // Make sure to apply the selected color
    context.lineWidth = 2;  // Set line width if necessary
    context.stroke();
}

function getElementAtPosition(x, y) {
    // Iterate over elements in reverse to prioritize the most recently drawn ones
    for (let i = elements.length - 1; i >= 0; i--) {
        const element = elements[i];
        if (isWithinBounds(element, x, y)) {
            return element;
        }
    }
    return null;
}

function isWithinBounds(element, x, y) {
    switch (element.type) {
        case 'line':
        case 'arrow':
            // For lines/arrows, check the distance from the line
            const distance = pointToLineDistance(element.x1, element.y1, element.x2, element.y2, x, y);
            return distance < 5; // Allow a tolerance of 5px for clicking
        case 'rectangle':
            // For rectangles, check if the click is inside the rectangle's bounds
            return x >= element.x1 && x <= element.x2 && y >= element.y1 && y <= element.y2;
        case 'circle':
            const radius = Math.abs(element.x2 - element.x1) / 2;
            const centerX = element.x1 + radius;
            const centerY = element.y1 + radius;
            const distFromCenter = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
            return distFromCenter <= radius;
        case 'text':
            // Check for text bounds
            return x >= element.x1 && x <= element.x1 + 100 && y >= element.y1 - 20 && y <= element.y1;
        case 'triangle':
            return isPointInTriangle(x, y, element.x1, element.y1, element.x2, element.y2, element.midX, element.y2);
        default:
            return false;
    }
}

function isPointInTriangle(px, py, x1, y1, x2, y2, x3, y3) {
    const area = 0.5 * (-y2 * x1 + y1 * (-x2 + x3) + x2 * y1 + y2 * (x1 - x3) + x3 * y2);
    const s = 1 / (2 * area) * (y1 * x2 - x1 * y2 + (y2 - y1) * px + (x1 - x2) * py);
    const t = 1 / (2 * area) * (x1 * y3 - y1 * x3 + (y1 - y3) * px + (x2 - x1) * py);
    return s >= 0 && t >= 0 && (s + t <= 1);
}

// Helper function to calculate distance from a point to a line
function pointToLineDistance(x1, y1, x2, y2, px, py) {
    const A = px - x1;
    const B = py - y1;
    const C = x2 - x1;
    const D = y2 - y1;
    const dot = A * C + B * D;
    const len_sq = C * C + D * D;
    const param = len_sq !== 0 ? dot / len_sq : -1;
    let xx, yy;

    if (param < 0) {
        xx = x1;
        yy = y1;
    } else if (param > 1) {
        xx = x2;
        yy = y2;
    } else {
        xx = x1 + param * C;
        yy = y1 + param * D;
    }

    const dx = px - xx;
    const dy = py - yy;
    return Math.sqrt(dx * dx + dy * dy);
}

function saveState() {
    undoStack.push([...elements]);
    redoStack = [];
}

function undo() {
    if (undoStack.length > 0) {
        redoStack.push([...elements]);
        elements = undoStack.pop();
        redrawCanvas();
    }
}

function redo() {
    if (redoStack.length > 0) {
        undoStack.push([...elements]);
        elements = redoStack.pop();
        redrawCanvas();
    }
}

window.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'z') { // Ctrl + Z for undo
        e.preventDefault();
        undo();
        console.log("undo triggered");
    } else if (e.ctrlKey && e.key === 'y') { // Ctrl + Y for redo
        e.preventDefault();
        redo();
    } else if (e.ctrlKey && e.key === 's') { // Optional: Ctrl + S to save work
        e.preventDefault();
        saveWork();
    }
});


window.removeEventListener('resize', resizeCanvas);
window.addEventListener('resize', handleResize);

handleResize();
// updateSavedList();
updateCursorStyle();
