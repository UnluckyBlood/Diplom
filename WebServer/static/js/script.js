// script.js - ПОЛНЫЙ КОД С JWT АУТЕНТИФИКАЦИЕЙ И ВСЕМИ ФУНКЦИЯМИ
let ws, tempChart, humChart, vibChart, selectedFile = null;
let lastDataTime = null;
let authToken = null;
let currentUser = null;

// Буферы для агрегации данных по минутам
let minuteBuffers = {
    temperature: [],
    humidity: [],
    vibrations: []
};
let currentMinute = null;
let minuteInterval;
let chartHistory = [];

// Новая переменная для документа
let selectedDocFile = null;

// ============ АУТЕНТИФИКАЦИЯ ============

function checkAuth() {
    const token = localStorage.getItem('auth_token');
    const user = localStorage.getItem('current_user');

    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);

        fetch('/api/auth/verify', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                hideLoginModal();
                updateUserInterface();
                initApp();
            } else {
                logout();
            }
        })
        .catch(() => logout());
    } else {
        showLoginModal();
    }
}

function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');

    if (!username || !password) {
        errorDiv.textContent = '❌ Заполните все поля';
        return;
    }

    errorDiv.textContent = '⏳ Вход...';

    fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            hideLoginModal();
            updateUserInterface();
            initApp();
        } else {
            errorDiv.textContent = '❌ ' + (data.message || 'Ошибка входа');
        }
    })
    .catch(err => {
        errorDiv.textContent = '❌ Ошибка подключения к серверу';
        console.error(err);
    });
}

function register() {
    const username = document.getElementById('regUsername').value;
    const fullName = document.getElementById('regFullName').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;
    const errorDiv = document.getElementById('registerError');

    if (!username || !fullName || !email || !password) {
        errorDiv.textContent = '❌ Заполните все поля';
        return;
    }

    if (password !== confirmPassword) {
        errorDiv.textContent = '❌ Пароли не совпадают';
        return;
    }

    if (password.length < 6) {
        errorDiv.textContent = '❌ Пароль должен быть не менее 6 символов';
        return;
    }

    errorDiv.textContent = '⏳ Регистрация...';

    fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, email, full_name: fullName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('current_user', JSON.stringify(currentUser));
            hideLoginModal();
            updateUserInterface();
            initApp();
        } else {
            errorDiv.textContent = '❌ ' + (data.message || 'Ошибка регистрации');
        }
    })
    .catch(err => {
        errorDiv.textContent = '❌ Ошибка подключения к серверу';
        console.error(err);
    });
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('current_user');
    authToken = null;
    currentUser = null;

    if (ws) {
        ws.close();
    }

    showLoginModal();
}

function updateUserInterface() {
    if (currentUser) {
        const userNameSpan = document.getElementById('userName');
        if (userNameSpan) {
            userNameSpan.textContent = currentUser.full_name || currentUser.username;
        }

        const userMenu = document.querySelector('.user-menu');
        if (userMenu && !document.getElementById('logoutBtn')) {
            const logoutBtn = document.createElement('button');
            logoutBtn.id = 'logoutBtn';
            logoutBtn.className = 'btn logout-btn';
            logoutBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Выход';
            logoutBtn.onclick = logout;
            userMenu.appendChild(logoutBtn);
        }
    }
}

function showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'flex';
    }
    document.body.style.overflow = 'hidden';
}

function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'none';
    }
    document.body.style.overflow = 'auto';
}

function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabs = document.querySelectorAll('.tab-btn');

    tabs.forEach(btn => btn.classList.remove('active'));

    if (tab === 'login') {
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
        tabs[0].classList.add('active');
    } else {
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
        tabs[1].classList.add('active');
    }
}

// ============ API ВЫЗОВЫ С ТОКЕНОМ ============

function apiFetch(url, options = {}) {
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${authToken}`
    };
    return fetch(url, { ...options, headers });
}

// ============ НАВИГАЦИЯ ============

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    document.getElementById(pageId).classList.add('active');

    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    if (event && event.target) {
        event.target.classList.add('active');
    }

    if (pageId === 'dashboard') {
        setTimeout(() => {
            loadInitialData();
            loadCharts();
            loadAIRecommendations();
        }, 100);
    }

    if (pageId === 'settings') {
        setTimeout(loadSettings, 100);
    }

    if (pageId === 'documents') {
        setTimeout(loadDocuments, 100);
    }

    if (pageId === 'export') {
        const today = new Date().toISOString().split('T')[0];
        if (document.getElementById('startDate')) document.getElementById('startDate').value = today;
        if (document.getElementById('endDate')) document.getElementById('endDate').value = today;
    }

    if (pageId === 'profile') {
        setTimeout(loadProfile, 100);
    }
}

// ============ ГРАФИКИ ============

function generateTimeLabels(count = 60) {
    const now = new Date();
    const labels = [];

    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60000);
        const hours = time.getHours().toString().padStart(2, '0');
        const minutes = time.getMinutes().toString().padStart(2, '0');
        labels.push(`${hours}:${minutes}`);
    }
    return labels;
}

function aggregateMinuteData(data) {
    const now = new Date();
    const currentMinuteKey = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    if (currentMinute !== currentMinuteKey && currentMinute !== null) {
        processMinuteBuffer();
        currentMinute = currentMinuteKey;
    }

    if (currentMinute === null) {
        currentMinute = currentMinuteKey;
    }

    if (data.temperature !== undefined) {
        minuteBuffers.temperature.push(data.temperature);
    }
    if (data.humidity !== undefined) {
        minuteBuffers.humidity.push(data.humidity);
    }
    if (data.hits_per_minute !== undefined) {
        minuteBuffers.vibrations.push(data.hits_per_minute);
    }
}

function processMinuteBuffer() {
    if (minuteBuffers.temperature.length === 0 &&
        minuteBuffers.humidity.length === 0 &&
        minuteBuffers.vibrations.length === 0) {
        return;
    }

    const now = new Date();
    const aggregatedData = {
        timestamp: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
        fullTimestamp: now.toISOString(),
        temperature: 0,
        humidity: 0,
        hits_per_minute: 0
    };

    if (minuteBuffers.temperature.length > 0) {
        aggregatedData.temperature = Math.max(...minuteBuffers.temperature);
    }
    if (minuteBuffers.humidity.length > 0) {
        aggregatedData.humidity = Math.max(...minuteBuffers.humidity);
    }
    if (minuteBuffers.vibrations.length > 0) {
        aggregatedData.hits_per_minute = Math.max(...minuteBuffers.vibrations);
    }

    chartHistory.push(aggregatedData);

    if (chartHistory.length > 60) {
        chartHistory = chartHistory.slice(-60);
    }

    updateChartsWithHistory();

    minuteBuffers = {
        temperature: [],
        humidity: [],
        vibrations: []
    };
}

function updateChartsWithHistory() {
    if (chartHistory.length === 0) return;

    const labels = generateTimeLabels(chartHistory.length);
    const temps = chartHistory.map(d => d.temperature);
    const hums = chartHistory.map(d => d.humidity);
    const vibes = chartHistory.map(d => d.hits_per_minute);

    if (tempChart) {
        tempChart.data.labels = labels;
        tempChart.data.datasets[0].data = temps;
        tempChart.update('none');
    }

    if (humChart) {
        humChart.data.labels = labels;
        humChart.data.datasets[0].data = hums;
        humChart.update('none');
    }

    if (vibChart) {
        vibChart.data.labels = labels;
        vibChart.data.datasets[0].data = vibes;
        vibChart.update('none');
    }
}

function aggregateHistoryDataByMinute(data) {
    const aggregated = {};

    data.forEach(item => {
        const timestamp = new Date(item.timestamp);
        const minuteKey = `${timestamp.getHours().toString().padStart(2, '0')}:${timestamp.getMinutes().toString().padStart(2, '0')}`;

        if (!aggregated[minuteKey]) {
            aggregated[minuteKey] = {
                timestamp: minuteKey,
                fullTimestamp: item.timestamp,
                temperature: item.temperature || 0,
                humidity: item.humidity || 0,
                hits_per_minute: item.hits_per_minute || 0,
                count: 1
            };
        } else {
            aggregated[minuteKey].temperature = Math.max(aggregated[minuteKey].temperature, item.temperature || 0);
            aggregated[minuteKey].humidity = Math.max(aggregated[minuteKey].humidity, item.humidity || 0);
            aggregated[minuteKey].hits_per_minute = Math.max(aggregated[minuteKey].hits_per_minute, item.hits_per_minute || 0);
            aggregated[minuteKey].count++;
        }
    });

    return Object.values(aggregated).sort((a, b) => new Date(a.fullTimestamp) - new Date(b.fullTimestamp));
}

function createCharts(historyData) {
    if (!Array.isArray(historyData) || historyData.length === 0) {
        createEmptyCharts();
        return;
    }

    const labels = generateTimeLabels(historyData.length);
    const temps = historyData.map(d => d.temperature);
    const hums = historyData.map(d => d.humidity);
    const vibes = historyData.map(d => d.hits_per_minute);

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    label: function(context) {
                        return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}`;
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: false,
                grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false },
                ticks: { font: { size: 10 }, padding: 5 }
            },
            x: {
                grid: { display: true, drawBorder: false, color: 'rgba(0,0,0,0.03)' },
                ticks: {
                    maxTicksLimit: 12,
                    font: { size: 9 },
                    autoSkip: true,
                    maxRotation: 45,
                    minRotation: 45,
                    padding: 8,
                    callback: function(value, index, values) {
                        if (values && values.length >= 40) {
                            return index % 5 === 0 ? this.getLabelForValue(value) : '';
                        } else if (values && values.length >= 20) {
                            return index % 3 === 0 ? this.getLabelForValue(value) : '';
                        }
                        return this.getLabelForValue(value);
                    }
                }
            }
        },
        elements: {
            point: { radius: 1.5, hoverRadius: 3, hitRadius: 4 },
            line: { tension: 0.2, borderWidth: 1.5 }
        },
        interaction: { intersect: false, mode: 'index' },
        layout: { padding: { left: 0, right: 0, top: 0, bottom: 20 } }
    };

    const tempCtx = document.getElementById('tempChart');
    if (tempCtx) {
        if (tempChart) tempChart.destroy();
        tempChart = new Chart(tempCtx.getContext('2d'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Температура', data: temps, borderColor: '#e17055', backgroundColor: 'rgba(225, 112, 85, 0.1)', fill: true, borderWidth: 1.5, pointBackgroundColor: '#e17055', pointBorderColor: '#ffffff', pointBorderWidth: 1 }] },
            options: commonOptions
        });
    }

    const humCtx = document.getElementById('humChart');
    if (humCtx) {
        if (humChart) humChart.destroy();
        humChart = new Chart(humCtx.getContext('2d'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Влажность', data: hums, borderColor: '#0984e3', backgroundColor: 'rgba(9, 132, 227, 0.1)', fill: true, borderWidth: 1.5, pointBackgroundColor: '#0984e3', pointBorderColor: '#ffffff', pointBorderWidth: 1 }] },
            options: commonOptions
        });
    }

    const vibCtx = document.getElementById('vibChart');
    if (vibCtx) {
        if (vibChart) vibChart.destroy();
        vibChart = new Chart(vibCtx.getContext('2d'), {
            type: 'line',
            data: { labels: labels, datasets: [{ label: 'Вибрации', data: vibes, borderColor: '#00b894', backgroundColor: 'rgba(0, 184, 148, 0.1)', fill: true, borderWidth: 1.5, pointBackgroundColor: '#00b894', pointBorderColor: '#ffffff', pointBorderWidth: 1 }] },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, beginAtZero: true, suggestedMin: 0 } } }
        });
    }
}

function createEmptyCharts() {
    const emptyLabels = ['Нет данных'];
    const emptyValues = [0];

    const configs = [
        { id: 'tempChart', color: '#e17055', label: 'Температура' },
        { id: 'humChart', color: '#0984e3', label: 'Влажность' },
        { id: 'vibChart', color: '#00b894', label: 'Вибрации' }
    ];

    configs.forEach(config => {
        const canvas = document.getElementById(config.id);
        if (!canvas) return;

        if (config.id === 'tempChart' && tempChart) tempChart.destroy();
        if (config.id === 'humChart' && humChart) humChart.destroy();
        if (config.id === 'vibChart' && vibChart) vibChart.destroy();

        new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { labels: emptyLabels, datasets: [{ label: config.label, data: emptyValues, borderColor: config.color, backgroundColor: config.color + '20', borderWidth: 2, fill: true }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    });
}

function zoomChart(direction) {
    const charts = [tempChart, humChart, vibChart].filter(c => c && c.zoom);
    charts.forEach(chart => chart.zoom(direction === 'in' ? 1.1 : 0.9));
}

function resetChartZoom() {
    const charts = [tempChart, humChart, vibChart].filter(c => c && c.resetZoom);
    charts.forEach(chart => chart.resetZoom());
}

function refreshCharts() {
    chartHistory = [];
    loadCharts();
}

function resizeCharts() {
    if (tempChart) tempChart.resize();
    if (humChart) humChart.resize();
    if (vibChart) vibChart.resize();
}

// ============ ДАННЫЕ ДАШБОРДА ============

function updateDashboard(data) {
    if (data.temperature !== undefined) {
        const temp = data.temperature.toFixed(1);
        const tempElement = document.getElementById('temperature');
        if (tempElement) tempElement.textContent = temp;

        let tempStatus = 'Норма';
        let tempColor = '#00b894';
        if (data.temperature > 35) { tempStatus = 'Критично'; tempColor = '#e17055'; }
        else if (data.temperature > 30) { tempStatus = 'Повышена'; tempColor = '#fdcb6e'; }
        else if (data.temperature < 15) { tempStatus = 'Низкая'; tempColor = '#0984e3'; }

        const tempStatusElement = document.getElementById('tempStatus');
        const tempStatusIcon = document.getElementById('tempStatusIcon');
        if (tempStatusElement) { tempStatusElement.textContent = `Статус: ${tempStatus}`; tempStatusElement.style.color = tempColor; }
        if (tempStatusIcon) tempStatusIcon.style.color = tempColor;
    }

    if (data.humidity !== undefined) {
        const hum = data.humidity.toFixed(1);
        const humElement = document.getElementById('humidity');
        if (humElement) humElement.textContent = hum;

        let humStatus = 'Норма';
        let humColor = '#00b894';
        if (data.humidity > 80) { humStatus = 'Высокая'; humColor = '#e17055'; }
        else if (data.humidity > 60) { humStatus = 'Повышена'; humColor = '#fdcb6e'; }
        else if (data.humidity < 20) { humStatus = 'Низкая'; humColor = '#0984e3'; }

        const humStatusElement = document.getElementById('humStatus');
        const humStatusIcon = document.getElementById('humStatusIcon');
        if (humStatusElement) { humStatusElement.textContent = `Статус: ${humStatus}`; humStatusElement.style.color = humColor; }
        if (humStatusIcon) humStatusIcon.style.color = humColor;
    }

    if (data.hits_per_minute !== undefined) {
        const hits = parseFloat(data.hits_per_minute);
        const vibElement = document.getElementById('vibrations');
        if (vibElement) {
            vibElement.textContent = hits.toFixed(1);
            let vibColor = '#00b894';
            if (hits > 30) vibColor = '#e17055';
            else if (hits > 20) vibColor = '#fdcb6e';
            else if (hits > 10) vibColor = '#00b894';
            else vibColor = '#667eea';
            vibElement.style.color = vibColor;

            const vibStatusIcon = document.getElementById('vibStatusIcon');
            if (vibStatusIcon) vibStatusIcon.style.color = vibColor;
        }
        updateRiskFromHits(hits);
    }

    if (data.hit_count !== undefined) {
        const totalHitsElement = document.getElementById('totalHits');
        if (totalHitsElement) totalHitsElement.textContent = data.hit_count;
    }
}

function updateRiskFromHits(hitsPerMinute) {
    let riskPercent, riskLevel, riskColor;

    if (hitsPerMinute > 30) { riskPercent = 90; riskLevel = 'Критический'; riskColor = '#e17055'; }
    else if (hitsPerMinute > 20) { riskPercent = 70; riskLevel = 'Высокий'; riskColor = '#fdcb6e'; }
    else if (hitsPerMinute > 10) { riskPercent = 50; riskLevel = 'Средний'; riskColor = '#00b894'; }
    else if (hitsPerMinute > 5) { riskPercent = 30; riskLevel = 'Низкий'; riskColor = '#667eea'; }
    else { riskPercent = 10; riskLevel = 'Минимальный'; riskColor = '#667eea'; }

    const riskScoreElement = document.getElementById('riskScore');
    const riskLevelElement = document.getElementById('riskLevel');
    const riskStatusIcon = document.getElementById('riskStatusIcon');

    if (riskScoreElement) { riskScoreElement.textContent = `${riskPercent}%`; riskScoreElement.style.color = riskColor; }
    if (riskLevelElement) { riskLevelElement.textContent = `Уровень: ${riskLevel}`; riskLevelElement.style.color = riskColor; }
    if (riskStatusIcon) riskStatusIcon.style.color = riskColor;
}

async function loadInitialData() {
    try {
        const response = await apiFetch('/api/current');
        const data = await response.json();
        if (data.temperature !== undefined) updateDashboard(data);
    } catch (e) {
        console.error('❌ Ошибка загрузки данных:', e);
    }
}

async function loadCharts() {
    try {
        const response = await apiFetch(`/api/history?hours=1&_=${Date.now()}`);
        const historyData = await response.json();

        if (Array.isArray(historyData) && historyData.length > 0) {
            const aggregatedData = aggregateHistoryDataByMinute(historyData);
            chartHistory = aggregatedData.length > 60 ? aggregatedData.slice(-60) : aggregatedData;
            createCharts(chartHistory);
        } else {
            createEmptyCharts();
        }
    } catch (e) {
        console.error('❌ Ошибка загрузки графиков:', e);
        createEmptyCharts();
    }
}

// ============ AI ЧАТ ============

async function loadAIRecommendations() {
    try {
        const response = await apiFetch('/api/ai/recommendations?limit=5');
        const recommendations = await response.json();

        if (Array.isArray(recommendations) && recommendations.length > 0) {
            const chatDiv = document.getElementById('aiChatFull');
            if (chatDiv) {
                const welcomeMessage = chatDiv.querySelector('.message.ai');
                chatDiv.innerHTML = '';
                if (welcomeMessage) chatDiv.appendChild(welcomeMessage);

                recommendations.slice().reverse().forEach(rec => {
                    if (rec.message) {
                        const message = rec.message;
                        if (message.includes('\n')) {
                            const lines = message.split('\n');
                            const aiLine = lines.find(line => line.includes('AI:'));
                            if (aiLine) addChatMessage(aiLine.replace('AI:', '').trim(), 'ai', rec.timestamp);
                        } else {
                            addChatMessage(message, 'ai', rec.timestamp);
                        }
                    }
                });
                chatDiv.scrollTop = chatDiv.scrollHeight;
            }
        }
    } catch (e) {
        console.error('❌ Ошибка загрузки AI рекомендаций:', e);
    }
}

async function sendUserMessage() {
    if (!authToken) {
        alert('Пожалуйста, войдите в систему');
        return;
    }

    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    if (!message) return;

    addChatMessage(message, 'user');
    userInput.value = '';

    try {
        const response = await apiFetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        if (data.status === 'success') {
            addChatMessage(data.response, 'ai');
        } else {
            addChatMessage('❌ Ошибка получения ответа от AI', 'ai');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        addChatMessage('❌ Ошибка подключения к серверу', 'ai');
    }
}

function addChatMessage(text, sender, timestamp = null) {
    const chatDiv = document.getElementById('aiChatFull');
    if (!chatDiv) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    const senderName = sender === 'user' ? 'Вы:' : 'AI:';
    const senderIcon = sender === 'user' ? '👤' : '🤖';

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-sender">${senderIcon} ${senderName}</div>
            <div class="message-text">${text}</div>
        </div>
        <div class="message-time">${timeStr}</div>
    `;

    chatDiv.appendChild(messageDiv);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

// ============ НАСТРОЙКИ ============

async function loadSettings() {
    try {
        const response = await apiFetch('/api/get_settings');
        const data = await response.json();

        if (data.status === 'success') {
            const settings = data.settings;
            const inputs = document.querySelectorAll('.parameter-input');

            inputs.forEach(input => {
                const val = input.defaultValue;
                if (val === '20') input.value = settings.temperature_min || '20';
                else if (val === '75') input.value = settings.temperature_max || '75';
                else if (val === '80') input.value = settings.temperature_critical || '80';
                else if (val === '5') input.value = settings.pressure_min || '5';
                else if (val === '10') input.value = settings.pressure_max || '10';
                else if (val === '12') input.value = settings.pressure_critical || '12';
                else if (val === '0') input.value = settings.vibration_min || '0';
                else if (val === '6') input.value = settings.vibration_max || '6';
                else if (val === '8') input.value = settings.vibration_critical || '8';
            });

            updateSettingsDisplay();
        }
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

function updateSettingsDisplay() {
    const tempMin = document.querySelector('.parameter-input[value="20"]')?.value || '20';
    const tempMax = document.querySelector('.parameter-input[value="75"]')?.value || '75';
    const tempCritical = document.querySelector('.parameter-input[value="80"]')?.value || '80';
    const pressureMin = document.querySelector('.parameter-input[value="5"]')?.value || '5';
    const pressureMax = document.querySelector('.parameter-input[value="10"]')?.value || '10';
    const pressureCritical = document.querySelector('.parameter-input[value="12"]')?.value || '12';
    const vibMin = document.querySelector('.parameter-input[value="0"]')?.value || '0';
    const vibMax = document.querySelector('.parameter-input[value="6"]')?.value || '6';
    const vibCritical = document.querySelector('.parameter-input[value="8"]')?.value || '8';

    const tempNormal = document.getElementById('tempNormal');
    const tempHigh = document.getElementById('tempHigh');
    const tempCriticalSpan = document.getElementById('tempCritical');
    if (tempNormal) tempNormal.textContent = `${tempMin} - ${tempMax} °C`;
    if (tempHigh) tempHigh.textContent = `${tempMax} + °C`;
    if (tempCriticalSpan) tempCriticalSpan.textContent = `${tempCritical} + °C`;

    const pressureNormal = document.getElementById('pressureNormal');
    const pressureHigh = document.getElementById('pressureHigh');
    const pressureCriticalSpan = document.getElementById('pressureCritical');
    if (pressureNormal) pressureNormal.textContent = `${pressureMin} - ${pressureMax} бар`;
    if (pressureHigh) pressureHigh.textContent = `${pressureMax} + бар`;
    if (pressureCriticalSpan) pressureCriticalSpan.textContent = `${pressureCritical} + бар`;

    const vibNormal = document.getElementById('vibNormal');
    const vibHigh = document.getElementById('vibHigh');
    const vibCriticalSpan = document.getElementById('vibCritical');
    if (vibNormal) vibNormal.textContent = `${vibMin} - ${vibMax} мм/с`;
    if (vibHigh) vibHigh.textContent = `${vibMax} + мм/с`;
    if (vibCriticalSpan) vibCriticalSpan.textContent = `${vibCritical} + мм/с`;
}

async function saveSettings() {
    const settings = {
        temperature: {
            min: document.querySelector('.parameter-input[value="20"]')?.value || '20',
            max: document.querySelector('.parameter-input[value="75"]')?.value || '75',
            critical: document.querySelector('.parameter-input[value="80"]')?.value || '80'
        },
        pressure: {
            min: document.querySelector('.parameter-input[value="5"]')?.value || '5',
            max: document.querySelector('.parameter-input[value="10"]')?.value || '10',
            critical: document.querySelector('.parameter-input[value="12"]')?.value || '12'
        },
        vibration: {
            min: document.querySelector('.parameter-input[value="0"]')?.value || '0',
            max: document.querySelector('.parameter-input[value="6"]')?.value || '6',
            critical: document.querySelector('.parameter-input[value="8"]')?.value || '8'
        }
    };

    try {
        const response = await apiFetch('/api/save_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        const data = await response.json();
        if (data.status === 'success') {
            updateSettingsDisplay();
            alert('✅ Настройки успешно сохранены!');
        } else {
            alert(`❌ Ошибка: ${data.message}`);
        }
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        alert('❌ Ошибка сохранения настроек');
    }
}

function resetSettings() {
    document.querySelectorAll('.parameter-input').forEach(input => {
        input.value = input.defaultValue;
    });
    updateSettingsDisplay();
}

// ============ ПРОФИЛЬ ============

async function loadProfile() {
    try {
        const response = await apiFetch('/api/get_profile');
        const data = await response.json();
        if (data.status === 'success') {
            const profile = data.profile;

            const fullNameInput = document.getElementById('fullName');
            const emailInput = document.getElementById('email');
            const phoneInput = document.getElementById('phone');
            const departmentSelect = document.getElementById('department');
            const positionInput = document.getElementById('position');

            if (fullNameInput) fullNameInput.value = profile.fullName;
            if (emailInput) emailInput.value = profile.email;
            if (phoneInput) phoneInput.value = profile.phone;
            if (departmentSelect) departmentSelect.value = profile.department;
            if (positionInput) positionInput.value = profile.position;

            const profileName = document.getElementById('profileName');
            const profileRole = document.getElementById('profileRole');
            if (profileName) profileName.textContent = profile.fullName;
            if (profileRole) profileRole.textContent = profile.position;

            const userNameSpan = document.getElementById('userName');
            if (userNameSpan && currentUser) userNameSpan.textContent = profile.fullName;
        }
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
    }
}

async function saveProfile() {
    const profile = {
        fullName: document.getElementById('fullName')?.value || '',
        email: document.getElementById('email')?.value || '',
        phone: document.getElementById('phone')?.value || '',
        department: document.getElementById('department')?.value || '',
        position: document.getElementById('position')?.value || ''
    };

    if (!profile.fullName || !profile.email) {
        alert('❌ Заполните обязательные поля: Имя и Email');
        return;
    }

    try {
        const response = await apiFetch('/api/save_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });

        const data = await response.json();
        if (data.status === 'success') {
            const profileName = document.getElementById('profileName');
            const profileRole = document.getElementById('profileRole');
            if (profileName) profileName.textContent = profile.fullName;
            if (profileRole) profileRole.textContent = profile.position;

            const userNameSpan = document.getElementById('userName');
            if (userNameSpan) userNameSpan.textContent = profile.fullName;

            if (currentUser) {
                currentUser.full_name = profile.fullName;
                localStorage.setItem('current_user', JSON.stringify(currentUser));
            }

            alert('✅ Профиль успешно сохранен!');
        } else {
            alert(`❌ Ошибка: ${data.message}`);
        }
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        alert('❌ Ошибка сохранения профиля');
    }
}

function resetProfile() {
    loadProfile();
}

// ============ ОБОРУДОВАНИЕ ============

function configureEquipment(id) {
    alert(`⚙️ Настройка оборудования №${id}\nФункционал в разработке`);
}

// ============ ЭКСПОРТ (НОВЫЕ РЕАЛИЗОВАННЫЕ ФУНКЦИИ) ============

async function exportData() {
    const format = document.querySelector('input[name="format"]:checked')?.value || 'csv';
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    let url = `/api/export/${format === 'pdf' ? 'pdf' : 'data'}?`;
    if (startDate) url += `start_date=${startDate}&`;
    if (endDate) url += `end_date=${endDate}&`;
    if (format !== 'pdf') url += `format=${format}`;

    try {
        if (format === 'pdf' || format === 'csv') {
            const response = await apiFetch(url);
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = format === 'pdf' ? 'report.pdf' : 'data.csv';
            link.click();
        } else if (format === 'json') {
            const response = await apiFetch(url);
            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'data.json';
            link.click();
        }
    } catch (e) {
        alert('Ошибка экспорта: ' + e.message);
    }
}

async function previewExport() {
    try {
        const resp = await apiFetch('/api/history?hours=24');
        const data = await resp.json();
        const container = document.getElementById('previewTableContainer');
        let html = '<table class="data-table"><thead><tr><th>Время</th><th>Темп.</th><th>Влажн.</th><th>Вибр.</th><th>Удары</th></tr></thead><tbody>';
        data.slice(0, 50).forEach(row => {
            html += `<tr>
                <td>${row.timestamp}</td>
                <td>${row.temperature?.toFixed(1) || ''}</td>
                <td>${row.humidity?.toFixed(1) || ''}</td>
                <td>${row.hits_per_minute?.toFixed(1) || ''}</td>
                <td>${row.hit_count || ''}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
        document.getElementById('previewModal').style.display = 'flex';
    } catch (e) {
        alert('Ошибка предпросмотра');
    }
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
}

// ============ ЗАГРУЗКА ФАЙЛОВ (CSV) ============

function handleDragOver(event) {
    event.preventDefault();
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.classList.add('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.classList.remove('dragover');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        selectedFile = file;
        const fileInfo = document.getElementById('fileInfo');
        const uploadBtn = document.getElementById('uploadBtn');
        if (fileInfo) {
            fileInfo.innerHTML = `<i class="fas fa-check-circle" style="color: #00b894;"></i> Выбран файл: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
        }
        if (uploadBtn) uploadBtn.disabled = false;
    } else {
        alert('❌ Пожалуйста, выберите CSV файл');
    }
}

async function uploadFile() {
    if (!selectedFile) {
        alert('❌ Сначала выберите файл');
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await apiFetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.status === 'success') {
            alert(`✅ ${data.message}`);
            clearUpload();
            loadCharts();
        } else {
            alert(`❌ Ошибка: ${data.message}`);
        }
    } catch (error) {
        console.error('Ошибка загрузки:', error);
        alert('❌ Ошибка загрузки файла');
    }
}

function clearUpload() {
    selectedFile = null;
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const uploadBtn = document.getElementById('uploadBtn');

    if (fileInput) fileInput.value = '';
    if (fileInfo) fileInfo.innerHTML = '';
    if (uploadBtn) uploadBtn.disabled = true;
}

// ============ ДОКУМЕНТЫ AI (НОВЫЕ ФУНКЦИИ) ============

function handleDocFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        selectedDocFile = files[0];
        document.getElementById('docFileInfo').innerHTML = `<i class="fas fa-check-circle" style="color:#00b894;"></i> ${selectedDocFile.name} (${(selectedDocFile.size/1024).toFixed(2)} KB)`;
        document.getElementById('uploadDocBtn').disabled = false;
    }
}

async function uploadDocument() {
    if (!selectedDocFile) return;
    const formData = new FormData();
    formData.append('file', selectedDocFile);
    try {
        const resp = await apiFetch('/api/documents/upload', { method: 'POST', body: formData });
        if (!resp.ok) {
            const errData = await resp.json();
            alert('Ошибка: ' + (errData.detail || 'Неизвестная ошибка'));
            return;
        }
        const data = await resp.json();
        if (data.status === 'success') {
            alert(data.message);
            selectedDocFile = null;
            document.getElementById('docFileInput').value = '';
            document.getElementById('docFileInfo').innerHTML = '';
            document.getElementById('uploadDocBtn').disabled = true;
            loadDocuments();
        } else {
            alert('Ошибка: ' + (data.message || data.detail || 'Неизвестная ошибка'));
        }
    } catch (e) {
        alert('Ошибка загрузки документа: ' + e.message);
    }
}

async function loadDocuments() {
    try {
        const resp = await apiFetch('/api/documents');
        const data = await resp.json();
        const container = document.getElementById('documentsTable');
        if (!container) return;
        if (data.documents.length === 0) {
            container.innerHTML = '<p>Нет загруженных документов.</p>';
            return;
        }
        let html = '<table class="data-table"><thead><tr><th>Файл</th><th>Дата загрузки</th><th>Действия</th></tr></thead><tbody>';
        data.documents.forEach(doc => {
            html += `<tr>
                <td>${doc.filename}</td>
                <td>${new Date(doc.created_at).toLocaleString()}</td>
                <td><button class="btn btn-sm" onclick="deleteDocument(${doc.id})"><i class="fas fa-trash"></i> Удалить</button></td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (e) {
        console.error(e);
    }
}

async function deleteDocument(id) {
    if (!confirm('Удалить документ?')) return;
    await apiFetch(`/api/documents/${id}`, { method: 'DELETE' });
    loadDocuments();
}

// ============ WEBSOCKET ============

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('✅ WebSocket подключен');
            updateWebSocketStatus(true);
            loadInitialData();
            loadCharts();
            loadAIRecommendations();

            if (minuteInterval) clearInterval(minuteInterval);
            minuteInterval = setInterval(() => {
                if (currentMinute !== null) processMinuteBuffer();
            }, 60000);
        };

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'realtime') {
                    updateDashboard(data.data);
                    aggregateMinuteData(data.data);
                } else if (data.type === 'ai_recommendation') {
                    if (data.data && data.data.message) {
                        const message = data.data.message;
                        if (message.includes('AI:')) {
                            addChatMessage(message.split('AI:')[1]?.trim() || message, 'ai');
                        } else {
                            addChatMessage(message, 'ai');
                        }
                    }
                }
            } catch (e) {
                console.error('❌ Ошибка парсинга WebSocket:', e);
            }
        };

        ws.onclose = function() {
            console.log('🔌 WebSocket отключен, переподключение через 3 секунды...');
            updateWebSocketStatus(false);
            if (minuteInterval) clearInterval(minuteInterval);
            setTimeout(initWebSocket, 3000);
        };

        ws.onerror = function(error) {
            console.error('❌ WebSocket ошибка:', error);
            updateWebSocketStatus(false);
        };

    } catch (e) {
        console.error('❌ Ошибка создания WebSocket:', e);
        updateWebSocketStatus(false);
    }
}

function updateWebSocketStatus(connected) {
    const statusIndicator = document.getElementById('webSocketStatus');
    if (statusIndicator) {
        if (connected) {
            statusIndicator.innerHTML = '<i class="fas fa-circle" style="color: #00b894;"></i> <span>Подключено</span>';
        } else {
            statusIndicator.innerHTML = '<i class="fas fa-circle" style="color: #e17055;"></i> <span>Отключено</span>';
        }
    }
}

// ============ ИНИЦИАЛИЗАЦИЯ ============

function initApp() {
    initWebSocket();
    showPage('dashboard');

    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendUserMessage();
        });
    }

    window.addEventListener('resize', function() {
        setTimeout(resizeCharts, 100);
    });

    setInterval(loadInitialData, 5000);
    setInterval(loadAIRecommendations, 60000);
}

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();

    const loginPassword = document.getElementById('loginPassword');
    const regConfirmPassword = document.getElementById('regConfirmPassword');

    if (loginPassword) {
        loginPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') login();
        });
    }

    if (regConfirmPassword) {
        regConfirmPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') register();
        });
    }
});