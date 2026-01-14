/**
 * Prueba Diagnóstica PAES M1 - Aplicación Principal
 * 
 * Maneja el flujo de la prueba MST:
 * 1. Pantalla de bienvenida
 * 2. Etapa 1: Routing (8 preguntas)
 * 3. Pantalla de transición
 * 4. Etapa 2: Ruta adaptada (8 preguntas)
 * 5. Pantalla de resultados
 */

// ============================================================================
// CONFIGURACIÓN - Las 32 preguntas seleccionadas (v2.0 - Optimizado 2026-01-09)
// Cobertura: 83% de átomos (190/229)
// ============================================================================
const MST_CONFIG = {
    R1: [
        { exam: "Prueba-invierno-2025", id: "Q28", axis: "ALG", skill: "RES", score: 0.45 },
        { exam: "prueba-invierno-2026", id: "Q31", axis: "ALG", skill: "MOD", score: 0.55 },
        { exam: "prueba-invierno-2026", id: "Q23", axis: "NUM", skill: "ARG", score: 0.45 },
        { exam: "seleccion-regular-2025", id: "Q15", axis: "NUM", skill: "ARG", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q46", axis: "GEO", skill: "ARG", score: 0.45 },
        { exam: "prueba-invierno-2026", id: "Q45", axis: "GEO", skill: "ARG", score: 0.55 },
        { exam: "prueba-invierno-2026", id: "Q58", axis: "PROB", skill: "REP", score: 0.45 },
        { exam: "seleccion-regular-2026", id: "Q60", axis: "PROB", skill: "RES", score: 0.45 },
    ],
    A2: [
        { exam: "Prueba-invierno-2025", id: "Q40", axis: "ALG", skill: "RES", score: 0.25 },
        { exam: "seleccion-regular-2026", id: "Q35", axis: "ALG", skill: "MOD", score: 0.25 },
        { exam: "prueba-invierno-2026", id: "Q40", axis: "ALG", skill: "RES", score: 0.25 },
        { exam: "seleccion-regular-2025", id: "Q10", axis: "NUM", skill: "RES", score: 0.30 },
        { exam: "Prueba-invierno-2025", id: "Q6", axis: "NUM", skill: "RES", score: 0.30 },
        { exam: "seleccion-regular-2025", id: "Q63", axis: "GEO", skill: "REP", score: 0.30 },
        { exam: "prueba-invierno-2026", id: "Q64", axis: "PROB", skill: "ARG", score: 0.35 },
        { exam: "seleccion-regular-2025", id: "Q54", axis: "PROB", skill: "RES", score: 0.25 },
    ],
    B2: [
        { exam: "prueba-invierno-2026", id: "Q42", axis: "ALG", skill: "MOD", score: 0.45 },
        { exam: "seleccion-regular-2025", id: "Q38", axis: "ALG", skill: "RES", score: 0.55 },
        { exam: "seleccion-regular-2025", id: "Q36", axis: "ALG", skill: "MOD", score: 0.55 },
        { exam: "seleccion-regular-2025", id: "Q3", axis: "NUM", skill: "ARG", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q22", axis: "NUM", skill: "MOD", score: 0.45 },
        { exam: "seleccion-regular-2025", id: "Q60", axis: "GEO", skill: "RES", score: 0.45 },
        { exam: "seleccion-regular-2025", id: "Q55", axis: "PROB", skill: "RES", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q65", axis: "PROB", skill: "REP", score: 0.45 },
    ],
    C2: [
        { exam: "seleccion-regular-2026", id: "Q59", axis: "ALG", skill: "RES", score: 0.60 },
        { exam: "seleccion-regular-2026", id: "Q11", axis: "ALG", skill: "MOD", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q33", axis: "ALG", skill: "MOD", score: 0.60 },
        { exam: "Prueba-invierno-2025", id: "Q56", axis: "NUM", skill: "ARG", score: 0.65 },
        { exam: "seleccion-regular-2026", id: "Q23", axis: "NUM", skill: "RES", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q50", axis: "GEO", skill: "REP", score: 0.55 },
        { exam: "Prueba-invierno-2025", id: "Q61", axis: "PROB", skill: "ARG", score: 0.65 },
        { exam: "prueba-invierno-2026", id: "Q60", axis: "PROB", skill: "ARG", score: 0.55 },
    ],
};

// Mapping de puntajes PAES (v2.1 - Ajustado por cobertura real)
// 10% de átomos no inferibles → techo real ~900
const PAES_MAPPING = {
    A: {
        // Ruta A: Solo preguntas fáciles → techo ~700
        ranges: [[0, 2, 150, 100, 200], [3, 4, 250, 200, 300], [5, 6, 350, 300, 400], [7, 8, 450, 400, 500], [9, 10, 525, 475, 575], [11, 12, 575, 525, 625], [13, 14, 625, 575, 675], [15, 16, 675, 625, 700]],
    },
    B: {
        // Ruta B: Preguntas medias → techo ~850
        ranges: [[0, 5, 400, 350, 450], [6, 7, 475, 425, 525], [8, 9, 550, 500, 600], [10, 11, 625, 575, 675], [12, 13, 700, 650, 750], [14, 15, 775, 725, 825], [16, 16, 825, 775, 850]],
    },
    C: {
        // Ruta C: Preguntas medio-altas → techo ~900 (10% no inferible)
        ranges: [[0, 8, 525, 475, 575], [9, 10, 600, 550, 650], [11, 12, 675, 625, 725], [13, 14, 775, 725, 825], [15, 15, 850, 800, 900], [16, 16, 900, 850, 950]],
    },
};

// ============================================================================
// ESTADO DE LA APLICACIÓN
// ============================================================================
const state = {
    currentScreen: 'welcome',
    currentStage: 1, // 1 = R1, 2 = Stage 2
    currentQuestionIndex: 0,
    route: null, // A, B, or C
    responses: [], // {question, responseType, selectedOption}
    r1Responses: [],
    stage2Responses: [],
    timerInterval: null,
    timeRemaining: 30 * 60, // 30 minutes in seconds
};

// ============================================================================
// FUNCIONES DE NAVEGACIÓN
// ============================================================================

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
    state.currentScreen = screenId;
}

function startTest() {
    showScreen('question-screen');
    state.currentStage = 1;
    state.currentQuestionIndex = 0;
    loadQuestion();
    startTimer();
}

function continueToStage2() {
    showScreen('question-screen');
    state.currentStage = 2;
    state.currentQuestionIndex = 0;
    updateStageBadge();
    loadQuestion();
}

// ============================================================================
// FUNCIONES DE PREGUNTAS
// ============================================================================

function getCurrentQuestions() {
    if (state.currentStage === 1) {
        return MST_CONFIG.R1;
    } else {
        const routeModule = `${state.route}2`;
        return MST_CONFIG[routeModule];
    }
}

async function loadQuestion() {
    const questions = getCurrentQuestions();
    const question = questions[state.currentQuestionIndex];

    // Update progress
    const totalInStage = 8;
    const questionNum = state.currentQuestionIndex + 1;
    const overallNum = state.currentStage === 1 ? questionNum : 8 + questionNum;

    document.getElementById('progress-text').textContent =
        `Pregunta ${questionNum} de ${totalInStage}`;

    const progressPercent = (overallNum / 16) * 100;
    document.getElementById('progress-bar').style.width = `${progressPercent}%`;

    // Load question XML - use relative path for Vercel deployment
    const questionPath = `/data/pruebas/finalizadas/${question.exam}/qti/${question.id}/question.xml`;

    try {
        const response = await fetch(questionPath);
        if (response.ok) {
            const xmlText = await response.text();
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, "text/xml");

            // Extract question content
            const itemBody = xmlDoc.querySelector('qti-item-body');
            const prompt = xmlDoc.querySelector('qti-prompt');
            const choices = xmlDoc.querySelectorAll('qti-simple-choice');
            const correctResponse = xmlDoc.querySelector('qti-correct-response qti-value');

            // Store correct answer for this question
            question.correctAnswerIdentifier = correctResponse ? correctResponse.textContent : null;

            // Build question HTML
            let questionHtml = '';
            if (itemBody) {
                // Get paragraphs and images (excluding the choice interaction)
                const paragraphs = itemBody.querySelectorAll(':scope > p');
                paragraphs.forEach(p => {
                    const img = p.querySelector('img');
                    if (img) {
                        questionHtml += `<p><img src="${img.getAttribute('src')}" alt="${img.getAttribute('alt') || 'Imagen'}"></p>`;
                    } else {
                        questionHtml += `<p>${p.innerHTML}</p>`;
                    }
                });
            }

            // Add the prompt
            if (prompt) {
                questionHtml += `<p class="question-prompt"><strong>${prompt.innerHTML}</strong></p>`;
            }

            document.getElementById('question-content').innerHTML = questionHtml;

            // Trigger MathJax to render any mathematical notation
            if (window.MathJax && window.MathJax.typeset) {
                MathJax.typeset();
            }

            // Generate options from XML
            generateOptionsFromXML(choices, question);

        } else {
            // Fallback: show placeholder with question info
            showQuestionPlaceholder(question, `Error ${response.status}`);
            generateOptions();
        }
    } catch (error) {
        console.error('Error loading question:', error);
        showQuestionPlaceholder(question, error.message);
        generateOptions();
    }

    // Reset state
    document.getElementById('btn-next').disabled = true;
    document.getElementById('btn-dont-know').classList.remove('selected');
    document.querySelectorAll('.option-card').forEach(o => o.classList.remove('selected'));
}

function showQuestionPlaceholder(question, errorMsg) {
    const axisNames = { ALG: 'Álgebra', NUM: 'Números', GEO: 'Geometría', PROB: 'Probabilidad' };
    const skillNames = { RES: 'Resolver', MOD: 'Modelar', REP: 'Representar', ARG: 'Argumentar' };

    document.getElementById('question-content').innerHTML = `
        <div class="question-placeholder">
            <p><strong>Pregunta ${question.id}</strong> de ${question.exam}</p>
            <p>Eje: ${axisNames[question.axis] || question.axis} | Habilidad: ${skillNames[question.skill] || question.skill}</p>
            <p><em>${errorMsg || 'Contenido no disponible'}</em></p>
        </div>
    `;
}

function generateOptionsFromXML(choices, question) {
    const container = document.getElementById('options-container');
    const letters = ['A', 'B', 'C', 'D'];

    if (!choices || choices.length === 0) {
        generateOptions();
        return;
    }

    // Store choice identifiers for answer checking
    question.choiceMap = {};

    container.innerHTML = Array.from(choices).map((choice, index) => {
        const letter = letters[index];
        const identifier = choice.getAttribute('identifier');
        question.choiceMap[letter] = identifier;

        // Get the text content, handling MathML
        let optionText = '';
        const mathElement = choice.querySelector('math, m\\:math');
        if (mathElement) {
            // Keep the full MathML for MathJax to render
            optionText = choice.innerHTML;
        } else {
            optionText = choice.innerHTML;
        }

        return `
            <div class="option-card" onclick="selectOption('${letter}')">
                <div class="option-letter">${letter}</div>
                <div class="option-text">${optionText}</div>
            </div>
        `;
    }).join('');
}

function parseMathML(mathElement) {
    let result = '';
    const children = mathElement.children;

    for (const child of children) {
        const tagName = child.localName || child.tagName.replace('m:', '');

        switch (tagName) {
            case 'mi': // identifier
            case 'mn': // number
            case 'mo': // operator
                result += child.textContent;
                break;
            case 'mfrac':
                const num = child.children[0]?.textContent || '';
                const den = child.children[1]?.textContent || '';
                result += `(${num}/${den})`;
                break;
            case 'msup':
                const base = child.children[0]?.textContent || '';
                const exp = child.children[1]?.textContent || '';
                result += `${base}^${exp}`;
                break;
            default:
                result += child.textContent;
        }
    }

    return result || mathElement.textContent;
}

function generateOptions() {
    const container = document.getElementById('options-container');
    const letters = ['A', 'B', 'C', 'D'];

    container.innerHTML = letters.map(letter => `
        <div class="option-card" onclick="selectOption('${letter}')">
            <div class="option-letter">${letter}</div>
            <div class="option-text">Opción ${letter}</div>
        </div>
    `).join('');
}

let selectedOption = null;

function selectOption(letter) {
    // Clear previous selection
    document.querySelectorAll('.option-card').forEach(o => o.classList.remove('selected'));
    document.getElementById('btn-dont-know').classList.remove('selected');

    // Select this option
    const cards = document.querySelectorAll('.option-card');
    const index = ['A', 'B', 'C', 'D'].indexOf(letter);
    cards[index].classList.add('selected');

    selectedOption = letter;
    document.getElementById('btn-next').disabled = false;
}

function selectDontKnow() {
    // Clear option selection
    document.querySelectorAll('.option-card').forEach(o => o.classList.remove('selected'));

    // Select don't know
    document.getElementById('btn-dont-know').classList.add('selected');
    selectedOption = 'DONT_KNOW';
    document.getElementById('btn-next').disabled = false;
}

function nextQuestion() {
    if (!selectedOption) return;

    // Record response
    const questions = getCurrentQuestions();
    const question = questions[state.currentQuestionIndex];

    const response = {
        question: question,
        responseType: selectedOption === 'DONT_KNOW' ? 'dont_know' : 'selected',
        selectedOption: selectedOption === 'DONT_KNOW' ? null : selectedOption,
        // For demo purposes, we'll randomly determine if correct
        isCorrect: selectedOption !== 'DONT_KNOW' && Math.random() > 0.5,
    };

    if (state.currentStage === 1) {
        state.r1Responses.push(response);
    } else {
        state.stage2Responses.push(response);
    }

    state.responses.push(response);
    selectedOption = null;

    // Move to next question or stage
    state.currentQuestionIndex++;

    if (state.currentQuestionIndex >= 8) {
        if (state.currentStage === 1) {
            // End of R1 - determine route and show transition
            determineRoute();
            showTransitionScreen();
        } else {
            // End of test - show results
            showResults();
        }
    } else {
        loadQuestion();
    }
}

// ============================================================================
// ROUTING
// ============================================================================

function determineRoute() {
    const correctCount = state.r1Responses.filter(r => r.isCorrect).length;

    if (correctCount <= 3) {
        state.route = 'A';
    } else if (correctCount <= 6) {
        state.route = 'B';
    } else {
        state.route = 'C';
    }

    console.log(`Route determined: ${state.route} (${correctCount}/8 correct)`);
}

function showTransitionScreen() {
    const correctCount = state.r1Responses.filter(r => r.isCorrect).length;

    document.getElementById('transition-stats').innerHTML = `
        <div class="stat-item">
            <div class="stat-value">${correctCount}/8</div>
            <div class="stat-label">Correctas</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">Ruta ${state.route}</div>
            <div class="stat-label">Asignada</div>
        </div>
    `;

    showScreen('transition-screen');
}

function updateStageBadge() {
    const routeNames = { A: 'Nivel Básico', B: 'Nivel Intermedio', C: 'Nivel Avanzado' };
    document.getElementById('stage-badge').textContent = routeNames[state.route];
}

// ============================================================================
// RESULTADOS
// ============================================================================

function showResults() {
    stopTimer();

    // Calculate scores
    const totalCorrect = state.responses.filter(r => r.isCorrect).length;
    const { score, min, max, level } = calculatePAESScore(state.route, totalCorrect);

    // Update score display
    document.getElementById('score-value').textContent = `${min} - ${max}`;
    document.getElementById('level-text').textContent = level;

    // Calculate axis performance
    const axisPerformance = calculateAxisPerformance();
    renderAxisBars(axisPerformance);

    // Calculate skill performance
    const skillPerformance = calculateSkillPerformance();
    renderSkillBars(skillPerformance);

    // Generate recommendations
    generateRecommendations(axisPerformance, skillPerformance);

    showScreen('results-screen');
}

function calculatePAESScore(route, totalCorrect) {
    // Nueva fórmula ponderada (v3.0)
    // PAES = 100 + 900 × score_ponderado × factor_ruta × factor_cobertura

    // 1. Calcular score ponderado basado en dificultad de cada pregunta
    const PESO_LOW = 1.0;
    const PESO_MEDIUM = 1.8;

    let scorePonderado = 0;
    let maxScorePonderado = 0;

    // R1 responses (8 preguntas)
    MST_CONFIG.R1.forEach((q, i) => {
        const peso = q.score <= 0.35 ? PESO_LOW : PESO_MEDIUM;
        maxScorePonderado += peso;
        if (state.r1Responses[i] && state.r1Responses[i].isCorrect) {
            scorePonderado += peso;
        }
    });

    // Stage 2 responses (8 preguntas de la ruta asignada)
    const routeModule = `${route}2`;
    const stage2Questions = MST_CONFIG[routeModule];
    stage2Questions.forEach((q, i) => {
        const peso = q.score <= 0.35 ? PESO_LOW : PESO_MEDIUM;
        maxScorePonderado += peso;
        if (state.stage2Responses[i] && state.stage2Responses[i].isCorrect) {
            scorePonderado += peso;
        }
    });

    // Score normalizado (0-1)
    const scoreNormalizado = maxScorePonderado > 0 ? scorePonderado / maxScorePonderado : 0;

    // 2. Factor por ruta (nivel de dificultad evaluado)
    const FACTOR_RUTA = { A: 0.70, B: 0.85, C: 1.00 };
    const factorRuta = FACTOR_RUTA[route];

    // 3. Factor de cobertura (10% de átomos no inferibles)
    const FACTOR_COBERTURA = 0.90;

    // 4. Calcular PAES
    const paesRaw = 100 + 900 * scoreNormalizado * factorRuta * FACTOR_COBERTURA;
    const score = Math.round(paesRaw);

    // Margen de error típico: ±50 puntos
    const margin = 50;
    const min = Math.max(100, score - margin);
    const max = Math.min(1000, score + margin);

    return { score, min, max, level: getLevel(score) };
}

function getLevel(score) {
    if (score < 450) return 'Muy Inicial';
    if (score < 500) return 'Inicial';
    if (score < 550) return 'Intermedio Bajo';
    if (score < 600) return 'Intermedio';
    if (score < 650) return 'Intermedio Alto';
    if (score < 700) return 'Alto';
    return 'Muy Alto';
}

function calculateAxisPerformance() {
    const axes = {
        ALG: { correct: 0, total: 0 }, NUM: { correct: 0, total: 0 },
        GEO: { correct: 0, total: 0 }, PROB: { correct: 0, total: 0 }
    };

    for (const response of state.responses) {
        const axis = response.question.axis;
        axes[axis].total++;
        if (response.isCorrect) axes[axis].correct++;
    }

    const result = {};
    for (const [axis, data] of Object.entries(axes)) {
        const pct = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;
        result[axis] = { pct, correct: data.correct, total: data.total };
    }

    return result;
}

function calculateSkillPerformance() {
    const skills = {
        RES: { correct: 0, total: 0 }, MOD: { correct: 0, total: 0 },
        REP: { correct: 0, total: 0 }, ARG: { correct: 0, total: 0 }
    };

    for (const response of state.responses) {
        const skill = response.question.skill;
        skills[skill].total++;
        if (response.isCorrect) skills[skill].correct++;
    }

    const result = {};
    for (const [skill, data] of Object.entries(skills)) {
        const pct = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;
        result[skill] = { pct, correct: data.correct, total: data.total };
    }

    return result;
}

function renderAxisBars(performance) {
    const axisNames = { ALG: 'Álgebra', NUM: 'Números', GEO: 'Geometría', PROB: 'Probabilidad' };
    const container = document.getElementById('axis-bars');

    container.innerHTML = Object.entries(performance).map(([axis, data]) => {
        const colorClass = data.pct >= 75 ? 'success' : data.pct >= 50 ? 'warning' : 'danger';
        const icon = data.pct >= 75 ? '✓' : data.pct < 50 ? '⚠️' : '';

        return `
            <div class="bar-item">
                <div class="bar-label">${axisNames[axis]}</div>
                <div class="bar-container">
                    <div class="bar-fill ${colorClass}" style="width: ${data.pct}%"></div>
                </div>
                <div class="bar-value">${data.pct}%</div>
                <div class="bar-icon">${icon}</div>
            </div>
        `;
    }).join('');
}

function renderSkillBars(performance) {
    const skillNames = { RES: 'Resolver', MOD: 'Modelar', REP: 'Representar', ARG: 'Argumentar' };
    const container = document.getElementById('skill-bars');

    container.innerHTML = Object.entries(performance).map(([skill, data]) => {
        const colorClass = data.pct >= 75 ? 'success' : data.pct >= 50 ? 'warning' : 'danger';

        return `
            <div class="bar-item">
                <div class="bar-label">${skillNames[skill]}</div>
                <div class="bar-container">
                    <div class="bar-fill ${colorClass}" style="width: ${data.pct}%"></div>
                </div>
                <div class="bar-value">${data.pct}%</div>
                <div class="bar-icon"></div>
            </div>
        `;
    }).join('');
}

function generateRecommendations(axisPerf, skillPerf) {
    const recommendations = [];

    // Find weakest axis
    const sortedAxes = Object.entries(axisPerf).sort((a, b) => a[1].pct - b[1].pct);
    const weakestAxis = sortedAxes[0];
    const axisNames = { ALG: 'Álgebra', NUM: 'Números', GEO: 'Geometría', PROB: 'Probabilidad' };

    if (weakestAxis[1].pct < 75) {
        recommendations.push({
            icon: '🎯',
            text: `Enfócate en <strong>${axisNames[weakestAxis[0]]}</strong> para mejorar tu puntaje.`
        });
    }

    // Find weakest skill
    const sortedSkills = Object.entries(skillPerf).sort((a, b) => a[1].pct - b[1].pct);
    const weakestSkill = sortedSkills[0];
    const skillNames = { RES: 'Resolver', MOD: 'Modelar', REP: 'Representar', ARG: 'Argumentar' };

    if (weakestSkill[1].pct < 75) {
        recommendations.push({
            icon: '💡',
            text: `Practica ejercicios de <strong>${skillNames[weakestSkill[0]]}</strong>.`
        });
    }

    // General tip
    recommendations.push({
        icon: '📚',
        text: 'Revisa los conceptos fundamentales de los ejes con menor rendimiento.'
    });

    const container = document.getElementById('recommendations-content');
    container.innerHTML = recommendations.map(r => `
        <div class="recommendation-item">
            <span class="recommendation-icon">${r.icon}</span>
            <span>${r.text}</span>
        </div>
    `).join('');
}

function showStudyPlan() {
    alert('Plan de estudio próximamente...');
}

let skillTreeVisible = false;
let skillTreeLoaded = false;
let questionAtomsData = null;

async function loadQuestionAtoms() {
    if (questionAtomsData) return questionAtomsData;
    try {
        const response = await fetch('/data/question_atoms.json');
        questionAtomsData = await response.json();
        return questionAtomsData;
    } catch (error) {
        console.error('Error loading question atoms:', error);
        return null;
    }
}

async function toggleSkillTree() {
    const container = document.getElementById('skill-tree-container');
    const button = container.previousElementSibling;

    if (!skillTreeVisible) {
        // Show loading state
        button.textContent = 'Cargando...';
        button.disabled = true;

        // Load data in parallel
        await Promise.all([
            skillTreeLoaded ? Promise.resolve() : SkillTree.load(),
            loadQuestionAtoms()
        ]);
        skillTreeLoaded = true;

        // Build mastery state from responses
        const masteryState = buildMasteryStateFromDiagnostic();

        // Show container and render tree
        container.style.display = 'block';
        SkillTree.render('skill-tree-container', masteryState);

        button.textContent = 'Ocultar Árbol ↑';
        button.disabled = false;
        skillTreeVisible = true;
    } else {
        // Hide container
        container.style.display = 'none';
        button.textContent = 'Ver Árbol de Conocimientos →';
        skillTreeVisible = false;
    }
}

function buildMasteryStateFromDiagnostic() {
    const masteryState = {};

    if (!questionAtomsData || state.responses.length === 0) {
        return masteryState;
    }

    // Process each response
    for (const response of state.responses) {
        const question = response.question;
        const key = `${question.exam}/${question.id}`;
        const questionData = questionAtomsData.question_atoms[key];

        if (!questionData) {
            console.warn('No atom data for question:', key);
            continue;
        }

        // Map response to atom states
        for (const atom of questionData.atoms) {
            const atomId = atom.atom_id;

            if (response.responseType === 'dont_know') {
                // "No lo sé" = gap
                masteryState[atomId] = 'notEvaluated'; // Could be 'gap'
            } else if (response.isCorrect) {
                // Correct = dominated (only if primary or first time seeing this atom)
                if (!masteryState[atomId] || atom.relevance === 'primary') {
                    masteryState[atomId] = 'dominated';
                }
            } else {
                // Incorrect = not dominated (misconception if primary)
                if (atom.relevance === 'primary') {
                    masteryState[atomId] = 'misconception';
                } else if (!masteryState[atomId]) {
                    masteryState[atomId] = 'notDominated';
                }
            }
        }
    }

    console.log('Mastery state:', masteryState);
    return masteryState;
}

// ============================================================================
// TIMER
// ============================================================================

function startTimer() {
    updateTimerDisplay();
    state.timerInterval = setInterval(() => {
        state.timeRemaining--;
        updateTimerDisplay();

        if (state.timeRemaining <= 0) {
            stopTimer();
            alert('¡Se acabó el tiempo!');
            showResults();
        }
    }, 1000);
}

function stopTimer() {
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

function updateTimerDisplay() {
    const minutes = Math.floor(state.timeRemaining / 60);
    const seconds = state.timeRemaining % 60;
    document.getElementById('timer-display').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Prueba Diagnóstica PAES M1 - Inicializada');
});
