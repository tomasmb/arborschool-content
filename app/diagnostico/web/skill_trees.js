/**
 * Skill Trees Visualization - Gaming Style
 * D3.js component for rendering skill trees per axis
 */

// ============================================================================
// DATA STRUCTURE
// ============================================================================

let atomData = null;
let masteryState = {};
let activeTooltip = null;

const EJE_CONFIG = {
    'algebra_y_funciones': {
        id: 'algebra',
        title: 'Álgebra',
        color: '#ff6b9d',
        icon: 'x²'
    },
    'numeros': {
        id: 'numeros',
        title: 'Números',
        color: '#ffd93d',
        icon: '#'
    },
    'geometria': {
        id: 'geometria',
        title: 'Geometría',
        color: '#6bcb77',
        icon: '△'
    },
    'probabilidad_y_estadistica': {
        id: 'probabilidad',
        title: 'Probabilidad',
        color: '#4d96ff',
        icon: '%'
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================

async function initSkillTrees() {
    try {
        // Load atom data
        const response = await fetch('/data/skill_tree.json');
        const rawData = await response.json();

        // The JSON has nodes in flat.nodes, not at root level
        atomData = { nodes: rawData.flat?.nodes || rawData.nodes || [] };

        // Group atoms by eje
        const atomsByEje = groupAtomsByEje(atomData.nodes);

        // Render each tree
        renderAllTrees(atomsByEje);

        // Load mastery state if available
        loadMasteryState();

        // Update header stats
        updateHeaderStats();

    } catch (error) {
        console.error('Error initializing skill trees:', error);
        document.getElementById('trees-container').innerHTML = `
            <div class="error-state">
                <p>Error cargando árboles: ${error.message}</p>
            </div>
        `;
    }
}

function groupAtomsByEje(nodes) {
    const grouped = {};

    for (const node of nodes) {
        const eje = node.eje || 'unknown';
        if (!grouped[eje]) {
            grouped[eje] = [];
        }
        grouped[eje].push(node);
    }

    return grouped;
}

// ============================================================================
// TREE RENDERING
// ============================================================================

function renderAllTrees(atomsByEje) {
    const container = document.getElementById('trees-container');
    container.innerHTML = '';

    const ejeOrder = ['algebra_y_funciones', 'numeros', 'geometria', 'probabilidad_y_estadistica'];

    for (const eje of ejeOrder) {
        const atoms = atomsByEje[eje] || [];
        const config = EJE_CONFIG[eje];

        if (config) {
            const panel = createTreePanel(config, atoms);
            container.appendChild(panel);
        }
    }
}

function createTreePanel(config, atoms) {
    const panel = document.createElement('div');
    panel.className = 'skill-tree-panel';
    panel.id = `panel-${config.id}`;

    // Calculate progress
    const dominated = atoms.filter(a => getMasteryState(a.id) === 'dominated' || getMasteryState(a.id) === 'inferred').length;
    const progress = atoms.length > 0 ? Math.round((dominated / atoms.length) * 100) : 0;

    panel.innerHTML = `
        <div class="panel-header">
            <h3 class="panel-title ${config.id}">${config.icon} ${config.title}</h3>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill ${config.id}" style="width: ${progress}%"></div>
                </div>
                <span class="progress-text">${progress}%</span>
            </div>
        </div>
        <div class="tree-canvas" id="canvas-${config.id}">
            <svg class="tree-connections" id="connections-${config.id}"></svg>
            <div class="nodes-container" id="nodes-${config.id}"></div>
        </div>
    `;

    // Render nodes after DOM is ready
    setTimeout(() => renderNodes(config.id, atoms), 0);

    return panel;
}

function renderNodes(ejeId, atoms) {
    const container = document.getElementById(`nodes-${ejeId}`);
    const svg = document.getElementById(`connections-${ejeId}`);

    if (!container) return;

    // Calculate levels (depth from roots)
    const atomById = new Map(atoms.map(a => [a.id, a]));
    const levels = calculateLevels(atoms, atomById);

    // Group by level
    const byLevel = {};
    for (const [atomId, level] of Object.entries(levels)) {
        if (!byLevel[level]) byLevel[level] = [];
        byLevel[level].push(atomById.get(atomId));
    }

    // Render level by level
    const nodePositions = {};
    const nodeSize = 48;
    const gapX = 60;
    const gapY = 70;
    const paddingTop = 20;
    const paddingLeft = 20;

    let maxLevel = Math.max(...Object.keys(byLevel).map(Number));

    for (let level = 0; level <= maxLevel; level++) {
        const levelAtoms = byLevel[level] || [];
        const y = paddingTop + level * gapY;

        levelAtoms.forEach((atom, i) => {
            const x = paddingLeft + i * gapX;
            const state = getMasteryState(atom.id);

            const node = document.createElement('div');
            node.className = `skill-node ${state}`;
            node.style.position = 'absolute';
            node.style.left = `${x}px`;
            node.style.top = `${y}px`;
            node.dataset.atomId = atom.id;

            // Icon based on state
            const icons = {
                dominated: '✓',
                inferred: '↻',
                error: '✗',
                locked: '●'
            };
            node.innerHTML = icons[state] || '●';

            // Events
            node.addEventListener('mouseenter', (e) => showTooltip(e, atom, state));
            node.addEventListener('mouseleave', hideTooltip);
            node.addEventListener('click', () => showAtomDetails(atom));

            container.appendChild(node);

            nodePositions[atom.id] = {
                x: x + nodeSize / 2,
                y: y + nodeSize / 2
            };
        });
    }

    // Draw connections
    drawConnections(svg, atoms, nodePositions);

    // Set container size
    const maxY = paddingTop + (maxLevel + 1) * gapY;
    const maxItems = Math.max(...Object.values(byLevel).map(arr => arr.length));
    const maxX = paddingLeft + maxItems * gapX;
    container.style.height = `${maxY}px`;
    container.style.minWidth = `${maxX}px`;
    svg.style.height = `${maxY}px`;
    svg.style.minWidth = `${maxX}px`;
}

function calculateLevels(atoms, atomById) {
    const levels = {};
    const visited = new Set();

    function getLevel(atomId, path = []) {
        if (levels[atomId] !== undefined) return levels[atomId];
        if (path.includes(atomId)) return 0; // Cycle detected

        const atom = atomById.get(atomId);
        if (!atom) return 0;

        const prereqs = atom.prerequisites || [];
        if (prereqs.length === 0) {
            levels[atomId] = 0;
            return 0;
        }

        let maxPrereqLevel = -1;
        for (const prereqId of prereqs) {
            if (atomById.has(prereqId)) {
                maxPrereqLevel = Math.max(maxPrereqLevel, getLevel(prereqId, [...path, atomId]));
            }
        }

        levels[atomId] = maxPrereqLevel + 1;
        return levels[atomId];
    }

    for (const atom of atoms) {
        getLevel(atom.id);
    }

    return levels;
}

function drawConnections(svg, atoms, positions) {
    svg.innerHTML = '';

    for (const atom of atoms) {
        const prereqs = atom.prerequisites || [];
        const toPos = positions[atom.id];

        if (!toPos) continue;

        for (const prereqId of prereqs) {
            const fromPos = positions[prereqId];
            if (!fromPos) continue;

            const fromState = getMasteryState(prereqId);
            const toState = getMasteryState(atom.id);

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', fromPos.x);
            line.setAttribute('y1', fromPos.y);
            line.setAttribute('x2', toPos.x);
            line.setAttribute('y2', toPos.y);

            // Style based on state
            if (fromState === 'dominated' || fromState === 'inferred') {
                if (toState === 'dominated') {
                    line.classList.add('active');
                } else if (toState === 'inferred') {
                    line.classList.add('inferred');
                }
            }

            svg.appendChild(line);
        }
    }
}

// ============================================================================
// MASTERY STATE
// ============================================================================

function getMasteryState(atomId) {
    return masteryState[atomId] || 'locked';
}

function loadMasteryState() {
    // Try to load from localStorage (from diagnostic test)
    const saved = localStorage.getItem('skillTreeMasteryState');
    if (saved) {
        masteryState = JSON.parse(saved);
    } else {
        // Demo: set some random states
        setDemoMasteryState();
    }
}

function setDemoMasteryState() {
    if (!atomData || !atomData.nodes) return;

    // For demo, randomly set some atoms as dominated
    for (const node of atomData.nodes) {
        const rand = Math.random();
        if (rand < 0.2) {
            masteryState[node.id] = 'dominated';
        } else if (rand < 0.35) {
            masteryState[node.id] = 'inferred';
        } else if (rand < 0.4) {
            masteryState[node.id] = 'error';
        }
    }
}

// ============================================================================
// TOOLTIP
// ============================================================================

function showTooltip(event, atom, state) {
    hideTooltip();

    const tooltip = document.createElement('div');
    tooltip.className = 'skill-tooltip';
    tooltip.id = 'active-tooltip';

    const stateLabels = {
        dominated: 'Dominado',
        inferred: 'Inferido',
        error: 'Error conceptual',
        locked: 'No evaluado'
    };

    tooltip.innerHTML = `
        <h4>${atom.titulo || atom.id}</h4>
        <p>${atom.descripcion || 'Sin descripción'}</p>
        <span class="status-badge ${state}">${stateLabels[state]}</span>
    `;

    document.body.appendChild(tooltip);

    // Position near mouse
    const x = event.clientX + 15;
    const y = event.clientY + 15;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;

    // Adjust if off screen
    const rect = tooltip.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
        tooltip.style.left = `${event.clientX - rect.width - 15}px`;
    }
    if (rect.bottom > window.innerHeight) {
        tooltip.style.top = `${event.clientY - rect.height - 15}px`;
    }

    requestAnimationFrame(() => tooltip.classList.add('visible'));
}

function hideTooltip() {
    const existing = document.getElementById('active-tooltip');
    if (existing) {
        existing.remove();
    }
}

function showAtomDetails(atom) {
    // Could open a modal with full details
    console.log('Atom details:', atom);
}

// ============================================================================
// HEADER STATS
// ============================================================================

function updateHeaderStats() {
    if (!atomData || !atomData.nodes) return;

    const total = atomData.nodes.length;
    const dominated = atomData.nodes.filter(n => getMasteryState(n.id) === 'dominated').length;
    const inferred = atomData.nodes.filter(n => getMasteryState(n.id) === 'inferred').length;
    const errors = atomData.nodes.filter(n => getMasteryState(n.id) === 'error').length;

    document.getElementById('stat-dominated').textContent = dominated;
    document.getElementById('stat-inferred').textContent = inferred;
    document.getElementById('stat-errors').textContent = errors;
    document.getElementById('stat-total').textContent = total;
}

// ============================================================================
// INIT
// ============================================================================

document.addEventListener('DOMContentLoaded', initSkillTrees);
