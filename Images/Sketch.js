const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const rc = rough.canvas(canvas);
const angleInfo = document.getElementById('angleInfo');
let isDrawing = false;
let lastX = 0;
let lastY = 0;
let elements = [];
let selectedTool = 'pencil';
let selectedColor = '#ffffff';
let currentElement = null;
let undoStack = [];
let redoStack = [];
let isPanning = false;
let panStartX = 0;
let panStartY = 0;

function resizeCanvas() {
    canvas.width = window.innerWidth * 2;
    canvas.height = window.innerHeight * 2;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.scale(2, 2);
    redrawCanvas();
}

window.addEventListener('resize', resizeCanvas);

document.querySelectorAll('.tool').forEach(tool => {
    tool.addEventListener('click', () => {
        if (tool.id === 'clear') {
            elements = [];
            redrawCanvas();
        } else if (tool.id === 'undo') {
            undo();
        } else if (tool.id === 'redo') {
            redo();
        } else if (tool.id === 'select') {
            selectedTool = 'select';
            tool.classList.add('active'); // Keep the select tool active
        } else {
            document.querySelector('.tool.active').classList.remove('active');
            tool.classList.add('active');
            selectedTool = tool.id;
        }
    });
});

document.getElementById('colorPicker').addEventListener('input', (e) => {
    selectedColor = e.target.value;
});

canvas.addEventListener('mousedown', (e) => {
    if (selectedTool === 'select') {
        isPanning = true;
        panStartX = e.offsetX;
        panStartY = e.offsetY;
        document.getElementById('select').classList.add('active'); // Keep the select tool active while panning
    } else {
        startDrawing(e);
    }
});

canvas.addEventListener('mousemove', (e) => {
    if (isPanning) {
        const panEndX = e.offsetX;
        const panEndY = e.offsetY;
        const deltaX = panEndX - panStartX;
        const deltaY = panEndY - panStartY;
        elements.forEach(element => {
            switch (element.type) {
                case 'pencil':
                    element.x1 += deltaX;
                    element.y1 += deltaY;
                    element.x2 += deltaX;
                    element.y2 += deltaY;
                    break;
                case 'arrow':
                case 'line':
                case 'rectangle':
                case 'circle':
                case 'triangle':
                    element.x1 += deltaX;
                    element.y1 += deltaY;
                    element.x2 += deltaX;
                    element.y2 += deltaY;
                    break;
            }
        });
        redrawCanvas();
        panStartX = panEndX;
        panStartY = panEndY;
    } else {
        draw(e);
    }
});

canvas.addEventListener('mouseup', () => {
    isPanning = false;
    stopDrawing();
    document.getElementById('select').classList.remove('active'); // Remove the active class when panning ends
});

function startDrawing(e) {
    isDrawing = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
    currentElement = { type: selectedTool, x1: lastX, y1: lastY, color: selectedColor };
}

function draw(e) {
    if (!isDrawing) return;

    const currentX = e.offsetX;
    const currentY = e.offsetY;

    if (selectedTool === 'pencil') {
        elements.push({ type: 'pencil', x1: lastX, y1: lastY, x2: currentX, y2: currentY, color: selectedColor });
        [lastX, lastY] = [currentX, currentY];
    } else if (selectedTool === 'arrow') {
        currentElement.x2 = currentX;
        currentElement.y2 = currentY;
    } else if (selectedTool === 'eraser') {
        eraseAt(currentX, currentY);
    } else {
        currentElement.x2 = currentX;
        currentElement.y2 = currentY;
    }

    if (selectedTool === 'line' || selectedTool === 'arrow') {
        showAngle(lastX, lastY, currentX, currentY);
    }

    redrawCanvas();
}

function stopDrawing() {
    if (!isDrawing) return;
    isDrawing = false;
    angleInfo.style.display = 'none';

    if (selectedTool !== 'pencil' && selectedTool !== 'eraser') {
        elements.push(currentElement);
    }
    currentElement = null;
    saveState();
    redrawCanvas();
}

function redrawCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    elements.forEach(element => drawElement(element));
    if (currentElement) drawElement(currentElement);
}

function drawElement(element) {
    switch (element.type) {
        case 'pencil':
            rc.line(element.x1, element.y1, element.x2, element.y2, { stroke: element.color, roughness: 0, strokeWidth: 2 });
            break;
        case 'arrow':
            drawArrow(element.x1, element.y1, element.x2, element.y2, element.color);
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
    }
}

function drawArrow(x1, y1, x2, y2, color) {
    const headLength = 15;
    const angle = Math.atan2(y2 - y1, x2 - x1);

    rc.line(x1, y1, x2, y2, { stroke: color });

    const arrowX1 = x2 - headLength * Math.cos(angle - Math.PI / 6);
    const arrowY1 = y2 - headLength * Math.sin(angle - Math.PI / 6);

    const arrowX2 = x2 - headLength * Math.cos(angle + Math.PI / 6);
    const arrowY2 = y2 - headLength * Math.sin(angle + Math.PI / 6);

    rc.line(x2, y2, arrowX1, arrowY1, { stroke: color });
    rc.line(x2, y2, arrowX2, arrowY2, { stroke: color });
}

function showAngle(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;
    angle = (angle + 360) % 360;
    angleInfo.textContent = `Angle: ${angle.toFixed(1)}°`;
    angleInfo.style.display = 'block';
}

function eraseAt(x, y) {
    const eraserRadius = 10;
    elements = elements.filter(element => {
        if (element.type === 'pencil') {
            const distance = Math.sqrt(Math.pow((element.x1 + element.x2) / 2 - x, 2) + Math.pow((element.y1 + element.y2) / 2 - y, 2));
            return distance > eraserRadius;
        } else {
            const centerX = (element.x1 + element.x2) / 2;
            const centerY = (element.y1 + element.y2) / 2;
            const distance = Math.sqrt(Math.pow(centerX - x, 2) + Math.pow(centerY - y, 2));
            return distance > eraserRadius;
        }
    });
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

resizeCanvas();





