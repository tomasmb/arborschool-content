/**
 * Skill Tree Visualization - D3.js Component
 * 
 * Visualizes atoms as a skill tree with collapsible nodes.
 * Shows mastery state: dominated (green), not dominated (red), not evaluated (gray).
 */

// ============================================================================
// CONFIGURACIÓN
// ============================================================================

const SKILL_TREE_CONFIG = {
    nodeRadius: 8,
    levelHeight: 60,
    siblingSpacing: 25,
    colors: {
        dominated: '#10b981',      // green
        notDominated: '#ef4444',   // red  
        notEvaluated: '#6b7280',   // gray
        misconception: '#f59e0b',  // amber
    },
    ejeColors: {
        algebra_y_funciones: '#8b5cf6',      // purple
        numeros: '#3b82f6',                   // blue
        geometria: '#10b981',                 // green
        probabilidad_y_estadistica: '#f59e0b', // amber
    },
};

// ============================================================================
// ESTADO
// ============================================================================

let skillTreeData = null;
let skillTreeSvg = null;
let currentMasteryState = {}; // { atomId: 'dominated' | 'notDominated' | 'notEvaluated' | 'misconception' }

// ============================================================================
// CARGA DE DATOS
// ============================================================================

async function loadSkillTreeData() {
    try {
        const response = await fetch('/data/skill_tree.json');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        skillTreeData = await response.json();
        console.log('Skill tree loaded:', skillTreeData.metadata);
        return skillTreeData;
    } catch (error) {
        console.error('Error loading skill tree:', error);
        return null;
    }
}

// ============================================================================
// RENDERIZADO DEL ÁRBOL
// ============================================================================

function renderSkillTree(containerId, masteryState = {}) {
    if (!skillTreeData) {
        console.error('Skill tree data not loaded');
        return;
    }

    currentMasteryState = masteryState;
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('Container not found:', containerId);
        return;
    }

    // Clear previous content
    container.innerHTML = '';

    // Create container for controls
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'skill-tree-controls';
    controlsDiv.innerHTML = `
        <div class="tree-legend">
            <span class="legend-item"><span class="legend-dot dominated"></span> Dominado</span>
            <span class="legend-item"><span class="legend-dot not-dominated"></span> Por aprender</span>
            <span class="legend-item"><span class="legend-dot not-evaluated"></span> No evaluado</span>
        </div>
        <div class="tree-filters">
            <button class="filter-btn active" data-filter="all">Todos</button>
            <button class="filter-btn" data-filter="evaluated">Solo evaluados</button>
        </div>
    `;
    container.appendChild(controlsDiv);

    // Create SVG container
    const svgContainer = document.createElement('div');
    svgContainer.className = 'skill-tree-svg-container';
    container.appendChild(svgContainer);

    // Render each eje as a separate tree
    const hierarchicalData = skillTreeData.hierarchical;

    hierarchicalData.forEach((ejeData, index) => {
        const ejeContainer = document.createElement('div');
        ejeContainer.className = 'eje-tree-container';
        ejeContainer.innerHTML = `<h3 class="eje-title">${ejeData.name}</h3>`;

        const ejeSvgContainer = document.createElement('div');
        ejeSvgContainer.id = `eje-tree-${index}`;
        ejeSvgContainer.className = 'eje-svg';
        ejeContainer.appendChild(ejeSvgContainer);

        svgContainer.appendChild(ejeContainer);

        renderEjeTree(ejeSvgContainer.id, ejeData);
    });

    // Add event listeners for filters
    container.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            applyFilter(e.target.dataset.filter);
        });
    });
}

function renderEjeTree(containerId, ejeData) {
    const container = document.getElementById(containerId);
    const width = container.clientWidth || 400;
    const height = Math.max(200, ejeData.children.length * 25);

    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'skill-tree-svg');

    const g = svg.append('g')
        .attr('transform', 'translate(40, 20)');

    // Create a simple layout for the nodes
    const nodes = ejeData.children.map((child, index) => ({
        ...child,
        x: 0,
        y: index * 22,
        depth: child.attributes?.depth || 0,
    }));

    // Render nodes
    const nodeGroup = g.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'tree-node')
        .attr('transform', d => `translate(${d.depth * 20}, ${d.y})`);

    // Node circles
    nodeGroup.append('circle')
        .attr('r', SKILL_TREE_CONFIG.nodeRadius)
        .attr('class', d => `node-circle ${getMasteryClass(d.name)}`)
        .style('fill', d => getMasteryColor(d.name))
        .style('stroke', d => getEjeColor(ejeData.name))
        .style('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('mouseover', showNodeTooltip)
        .on('mouseout', hideNodeTooltip)
        .on('click', toggleNodeExpand);

    // Node labels
    nodeGroup.append('text')
        .attr('x', SKILL_TREE_CONFIG.nodeRadius + 8)
        .attr('y', 4)
        .attr('class', 'node-label')
        .text(d => truncateText(d.attributes?.title || d.name, 40))
        .style('font-size', '12px')
        .style('fill', '#374151');
}

// ============================================================================
// HELPERS
// ============================================================================

function getMasteryClass(atomId) {
    const state = currentMasteryState[atomId];
    switch (state) {
        case 'dominated': return 'dominated';
        case 'notDominated': return 'not-dominated';
        case 'misconception': return 'misconception';
        default: return 'not-evaluated';
    }
}

function getMasteryColor(atomId) {
    const state = currentMasteryState[atomId];
    switch (state) {
        case 'dominated': return SKILL_TREE_CONFIG.colors.dominated;
        case 'notDominated': return SKILL_TREE_CONFIG.colors.notDominated;
        case 'misconception': return SKILL_TREE_CONFIG.colors.misconception;
        default: return SKILL_TREE_CONFIG.colors.notEvaluated;
    }
}

function getEjeColor(ejeName) {
    const ejeMap = {
        'Álgebra y Funciones': SKILL_TREE_CONFIG.ejeColors.algebra_y_funciones,
        'Números': SKILL_TREE_CONFIG.ejeColors.numeros,
        'Geometría': SKILL_TREE_CONFIG.ejeColors.geometria,
        'Probabilidad y Estadística': SKILL_TREE_CONFIG.ejeColors.probabilidad_y_estadistica,
    };
    return ejeMap[ejeName] || '#6b7280';
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function showNodeTooltip(event, d) {
    const tooltip = d3.select('body').append('div')
        .attr('class', 'skill-tree-tooltip')
        .style('position', 'absolute')
        .style('background', 'white')
        .style('border', '1px solid #e5e7eb')
        .style('border-radius', '8px')
        .style('padding', '12px')
        .style('box-shadow', '0 4px 6px rgba(0,0,0,0.1)')
        .style('z-index', '1000')
        .style('max-width', '300px');

    const state = currentMasteryState[d.name];
    const stateLabel = {
        dominated: '✅ Dominado',
        notDominated: '❌ Por aprender',
        misconception: '⚠️ Misconception',
    }[state] || '⚪ No evaluado';

    tooltip.html(`
        <div style="font-weight: 600; margin-bottom: 4px;">${d.attributes?.title || d.name}</div>
        <div style="font-size: 12px; color: #6b7280;">${d.name}</div>
        <div style="margin-top: 8px; font-size: 13px;">${stateLabel}</div>
        <div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">
            Profundidad: ${d.attributes?.depth || 0} | Habilidad: ${d.attributes?.habilidad || '-'}
        </div>
    `);

    tooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
}

function hideNodeTooltip() {
    d3.selectAll('.skill-tree-tooltip').remove();
}

function toggleNodeExpand(event, d) {
    console.log('Node clicked:', d.name);
    // Future: expand/collapse node children
}

function applyFilter(filter) {
    const nodes = d3.selectAll('.tree-node');

    if (filter === 'all') {
        nodes.style('opacity', 1);
    } else if (filter === 'evaluated') {
        nodes.style('opacity', d => {
            const state = currentMasteryState[d.name];
            return state && state !== 'notEvaluated' ? 1 : 0.2;
        });
    }
}

// ============================================================================
// INTEGRACIÓN CON RESULTADOS
// ============================================================================

function buildMasteryStateFromResponses(responses) {
    // This will be called from app.js results screen
    // For now, returns mock data based on responses
    const masteryState = {};

    // In real implementation, we'd map questions to atoms
    // For demo, we'll mark some atoms based on responses
    if (skillTreeData) {
        skillTreeData.flat.nodes.forEach(node => {
            // Random for demo - replace with actual logic
            const rand = Math.random();
            if (rand > 0.7) {
                masteryState[node.id] = 'dominated';
            } else if (rand > 0.4) {
                masteryState[node.id] = 'notDominated';
            }
            // else: notEvaluated (default)
        });
    }

    return masteryState;
}

// ============================================================================
// EXPORTACIÓN
// ============================================================================

window.SkillTree = {
    load: loadSkillTreeData,
    render: renderSkillTree,
    buildMasteryState: buildMasteryStateFromResponses,
};
