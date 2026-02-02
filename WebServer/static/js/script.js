// script.js - ПОЛНЫЙ ИСПРАВЛЕННЫЙ КОД ДЛЯ 60 ТОЧЕК
let ws, tempChart, humChart, vibChart, selectedFile = null;
let lastDataTime = null;

// Буферы для агрегации данных по минутам
let minuteBuffers = {
    temperature: [],
    humidity: [],
    vibrations: []
};
let currentMinute = null;
let minuteInterval;
let chartHistory = []; // Храним историю данных для графиков

// Навигация по страницам
function showPage(pageId) {
    // Скрыть все страницы
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // Показать выбранную страницу
    document.getElementById(pageId).classList.add('active');
    
    // Обновить активную ссылку в навигации
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // При показе главной страницы обновляем графики
    if (pageId === 'dashboard') {
        setTimeout(() => {
            loadInitialData();
            loadCharts();
            loadAIRecommendations();
        }, 100);
    }
    
    // При показе настроек загружаем сохраненные значения
    if (pageId === 'settings') {
        setTimeout(loadSettings, 100);
    }
    
    // При показе профиля загружаем данные профиля
    if (pageId === 'profile') {
        setTimeout(loadProfile, 100);
    }
}

// Функция для генерации меток времени для 60 минут
function generateTimeLabels(count = 60) {
    const now = new Date();
    const labels = [];
    
    // Создаем массив временных меток для последних count минут
    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 60000); // Каждую минуту
        const hours = time.getHours().toString().padStart(2, '0');
        const minutes = time.getMinutes().toString().padStart(2, '0');
        labels.push(`${hours}:${minutes}`);
    }
    
    return labels;
}

// Функция для агрегации данных по минутам
function aggregateMinuteData(data) {
    const now = new Date();
    const currentMinuteKey = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    // Если это новая минута, обрабатываем предыдущую
    if (currentMinute !== currentMinuteKey && currentMinute !== null) {
        processMinuteBuffer();
        currentMinute = currentMinuteKey;
    }
    
    // Для первого запуска
    if (currentMinute === null) {
        currentMinute = currentMinuteKey;
    }
    
    // Добавляем данные в буфер
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

// Обработка буфера за минуту (нахождение пиковых значений)
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
    
    // Находим максимальные значения за минуту
    if (minuteBuffers.temperature.length > 0) {
        aggregatedData.temperature = Math.max(...minuteBuffers.temperature);
    }
    if (minuteBuffers.humidity.length > 0) {
        aggregatedData.humidity = Math.max(...minuteBuffers.humidity);
    }
    if (minuteBuffers.vibrations.length > 0) {
        aggregatedData.hits_per_minute = Math.max(...minuteBuffers.vibrations);
    }
    
    // Добавляем в историю
    chartHistory.push(aggregatedData);
    
    // Ограничиваем историю 60 точками (60 минут)
    if (chartHistory.length > 60) {
        chartHistory = chartHistory.slice(-60);
    }
    
    // Обновляем графики
    updateChartsWithHistory();
    
    // Очищаем буферы
    minuteBuffers = {
        temperature: [],
        humidity: [],
        vibrations: []
    };
}

// WebSocket подключение
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log(`🔌 Подключение к WebSocket: ${wsUrl}`);
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('✅ WebSocket подключен');
            updateWebSocketStatus(true);
            loadInitialData();
            loadCharts();
            loadAIRecommendations();
            
            // Запускаем таймер для обработки минутных данных
            if (minuteInterval) {
                clearInterval(minuteInterval);
            }
            minuteInterval = setInterval(() => {
                if (currentMinute !== null) {
                    processMinuteBuffer();
                }
            }, 60000); // Каждую минуту
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'realtime') {
                    updateDashboard(data.data);
                    // Агрегируем данные по минутам
                    aggregateMinuteData(data.data);
                } else if (data.type === 'ai_recommendation') {
                    // Добавляем AI сообщение в чат
                    if (data.data && data.data.message) {
                        const message = data.data.message;
                        // Извлекаем AI сообщение из формата
                        if (message.includes('AI:')) {
                            const aiMessage = message.split('AI:')[1]?.trim() || message;
                            addChatMessage(aiMessage, 'ai');
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
            if (minuteInterval) {
                clearInterval(minuteInterval);
            }
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

function updateDashboard(data) {
    // Температура
    if (data.temperature !== undefined) {
        const temp = data.temperature.toFixed(1);
        const tempElement = document.getElementById('temperature');
        if (tempElement) tempElement.textContent = temp;
        
        let tempStatus = 'Норма';
        let tempColor = '#00b894';
        if (data.temperature > 35) {
            tempStatus = 'Критично';
            tempColor = '#e17055';
        } else if (data.temperature > 30) {
            tempStatus = 'Повышена';
            tempColor = '#fdcb6e';
        } else if (data.temperature < 15) {
            tempStatus = 'Низкая';
            tempColor = '#0984e3';
        }
        
        const tempStatusElement = document.getElementById('tempStatus');
        const tempStatusIcon = document.getElementById('tempStatusIcon');
        if (tempStatusElement) {
            tempStatusElement.textContent = `Статус: ${tempStatus}`;
            tempStatusElement.style.color = tempColor;
        }
        if (tempStatusIcon) tempStatusIcon.style.color = tempColor;
    }
    
    // Влажность
    if (data.humidity !== undefined) {
        const hum = data.humidity.toFixed(1);
        const humElement = document.getElementById('humidity');
        if (humElement) humElement.textContent = hum;
        
        let humStatus = 'Норма';
        let humColor = '#00b894';
        if (data.humidity > 80) {
            humStatus = 'Высокая';
            humColor = '#e17055';
        } else if (data.humidity > 60) {
            humStatus = 'Повышена';
            humColor = '#fdcb6e';
        } else if (data.humidity < 20) {
            humStatus = 'Низкая';
            humColor = '#0984e3';
        }
        
        const humStatusElement = document.getElementById('humStatus');
        const humStatusIcon = document.getElementById('humStatusIcon');
        if (humStatusElement) {
            humStatusElement.textContent = `Статус: ${humStatus}`;
            humStatusElement.style.color = humColor;
        }
        if (humStatusIcon) humStatusIcon.style.color = humColor;
    }
    
    // Вибрации
    if (data.hits_per_minute !== undefined) {
        const hits = parseFloat(data.hits_per_minute);
        const vibElement = document.getElementById('vibrations');
        if (vibElement) {
            vibElement.textContent = hits.toFixed(1);
            
            let vibColor = '#00b894';
            if (hits > 30) {
                vibColor = '#e17055';
            } else if (hits > 20) {
                vibColor = '#fdcb6e';
            } else if (hits > 10) {
                vibColor = '#00b894';
            } else {
                vibColor = '#667eea';
            }
            vibElement.style.color = vibColor;
            
            const vibStatusIcon = document.getElementById('vibStatusIcon');
            if (vibStatusIcon) vibStatusIcon.style.color = vibColor;
        }
        
        updateRiskFromHits(hits);
    }
    
    // Общее количество ударов
    if (data.hit_count !== undefined) {
        const totalHitsElement = document.getElementById('totalHits');
        if (totalHitsElement) totalHitsElement.textContent = data.hit_count;
    }
}

function updateRiskFromHits(hitsPerMinute) {
    let riskPercent, riskLevel, riskColor;
    
    if (hitsPerMinute > 30) {
        riskPercent = 90;
        riskLevel = 'Критический';
        riskColor = '#e17055';
    } else if (hitsPerMinute > 20) {
        riskPercent = 70;
        riskLevel = 'Высокий';
        riskColor = '#fdcb6e';
    } else if (hitsPerMinute > 10) {
        riskPercent = 50;
        riskLevel = 'Средний';
        riskColor = '#00b894';
    } else if (hitsPerMinute > 5) {
        riskPercent = 30;
        riskLevel = 'Низкий';
        riskColor = '#667eea';
    } else {
        riskPercent = 10;
        riskLevel = 'Минимальный';
        riskColor = '#667eea';
    }
    
    const riskScoreElement = document.getElementById('riskScore');
    const riskLevelElement = document.getElementById('riskLevel');
    const riskStatusIcon = document.getElementById('riskStatusIcon');
    
    if (riskScoreElement) {
        riskScoreElement.textContent = `${riskPercent}%`;
        riskScoreElement.style.color = riskColor;
    }
    if (riskLevelElement) {
        riskLevelElement.textContent = `Уровень: ${riskLevel}`;
        riskLevelElement.style.color = riskColor;
    }
    if (riskStatusIcon) riskStatusIcon.style.color = riskColor;
}

async function loadInitialData() {
    try {
        const response = await fetch('/api/current');
        const data = await response.json();
        
        if (data.temperature !== undefined) {
            updateDashboard(data);
        }
    } catch (e) {
        console.error('❌ Ошибка загрузки данных:', e);
    }
}

// AI рекомендации
async function loadAIRecommendations() {
    try {
        const response = await fetch('/api/ai/recommendations?limit=5');
        const recommendations = await response.json();
        
        if (Array.isArray(recommendations) && recommendations.length > 0) {
            // Очищаем чат, оставляя только приветственное сообщение
            const chatDiv = document.getElementById('aiChatFull');
            if (chatDiv) {
                // Находим приветственное сообщение AI
                const welcomeMessage = chatDiv.querySelector('.message.ai');
                chatDiv.innerHTML = '';
                
                // Восстанавливаем приветственное сообщение
                if (welcomeMessage) {
                    chatDiv.appendChild(welcomeMessage);
                }
                
                // Добавляем последние рекомендации (в обратном порядке - от старых к новым)
                recommendations.slice().reverse().forEach(rec => {
                    if (rec.message) {
                        const message = rec.message;
                        // Извлекаем AI сообщение если оно в формате "Пользователь: ...\nAI: ..."
                        if (message.includes('\n')) {
                            const lines = message.split('\n');
                            const aiLine = lines.find(line => line.includes('AI:'));
                            if (aiLine) {
                                const aiMessage = aiLine.replace('AI:', '').trim();
                                addChatMessage(aiMessage, 'ai', rec.timestamp);
                            }
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

// Графики
async function loadCharts() {
    try {
        // Добавляем временную метку чтобы избежать кэширования
        const timestamp = Date.now();
        const response = await fetch(`/api/history?hours=1&_=${timestamp}`);
        const historyData = await response.json();
        
        if (Array.isArray(historyData) && historyData.length > 0) {
            // Агрегируем исторические данные по минутам
            const aggregatedData = aggregateHistoryDataByMinute(historyData);
            
            // Ограничиваем 60 точками
            if (aggregatedData.length > 60) {
                chartHistory = aggregatedData.slice(-60);
            } else {
                chartHistory = aggregatedData;
            }
            
            createCharts(chartHistory);
        } else {
            createEmptyCharts();
        }
    } catch (e) {
        console.error('❌ Ошибка загрузки графиков:', e);
        createEmptyCharts();
    }
}

// Функция агрегации исторических данных по минутам
function aggregateHistoryDataByMinute(data) {
    const aggregated = {};
    
    data.forEach(item => {
        const timestamp = new Date(item.timestamp);
        // Округляем до минуты
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
            // Находим максимальные значения
            aggregated[minuteKey].temperature = Math.max(
                aggregated[minuteKey].temperature, 
                item.temperature || 0
            );
            aggregated[minuteKey].humidity = Math.max(
                aggregated[minuteKey].humidity, 
                item.humidity || 0
            );
            aggregated[minuteKey].hits_per_minute = Math.max(
                aggregated[minuteKey].hits_per_minute, 
                item.hits_per_minute || 0
            );
            aggregated[minuteKey].count++;
        }
    });
    
    // Преобразуем в массив и сортируем по времени
    const result = Object.values(aggregated).sort((a, b) => {
        return new Date(a.fullTimestamp) - new Date(b.fullTimestamp);
    });
    
    return result;
}

function createCharts(historyData) {
    if (!Array.isArray(historyData) || historyData.length === 0) {
        createEmptyCharts();
        return;
    }
    
    // Генерируем метки времени для последних 60 минут
    const labels = generateTimeLabels(historyData.length);
    const temps = historyData.map(d => d.temperature);
    const hums = historyData.map(d => d.humidity);
    const vibes = historyData.map(d => d.hits_per_minute);
    
    // Общие настройки графиков - ОПТИМИЗИРОВАННЫЕ ДЛЯ 60 ТОЧЕК
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
            legend: { 
                display: false
            },
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
                grid: { 
                    color: 'rgba(0,0,0,0.05)',
                    drawBorder: false
                },
                ticks: {
                    font: {
                        size: 10
                    },
                    padding: 5,
                    callback: function(value) {
                        return value.toFixed(1);
                    }
                }
            },
            x: {
                grid: { 
                    display: true,
                    drawBorder: false,
                    color: 'rgba(0,0,0,0.03)'
                },
                ticks: {
                    maxTicksLimit: 12, // Показываем только 12 меток для 60 минут
                    font: {
                        size: 9
                    },
                    autoSkip: true,
                    maxRotation: 45, // Наклон меток для лучшего отображения
                    minRotation: 45,
                    padding: 8,
                    callback: function(value, index) {
                        const labels = this.chart.data.labels;
                        if (!labels || labels.length === 0) return '';
                        
                        // Для 60 точек показываем только каждую 5-ю метку
                        if (labels.length >= 40) {
                            return index % 5 === 0 ? labels[index] : '';
                        } else if (labels.length >= 20) {
                            return index % 3 === 0 ? labels[index] : '';
                        } else {
                            return labels[index];
                        }
                    }
                }
            }
        },
        elements: {
            point: {
                radius: 1.5, // Уменьшаем точки для 60 значений
                hoverRadius: 3,
                hitRadius: 4
            },
            line: {
                tension: 0.2,
                borderWidth: 1.5 // Более тонкая линия
            }
        },
        interaction: {
            intersect: false,
            mode: 'index'
        },
        layout: {
            padding: {
                left: 0,
                right: 0,
                top: 0,
                bottom: 20 // Увеличиваем отступ снизу для меток
            }
        }
    };
    
    // График температуры
    const tempCtx = document.getElementById('tempChart');
    if (tempCtx) {
        if (tempChart) tempChart.destroy();
        
        tempChart = new Chart(tempCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Температура',
                    data: temps,
                    borderColor: '#e17055',
                    backgroundColor: 'rgba(225, 112, 85, 0.1)',
                    fill: true,
                    borderWidth: 1.5,
                    pointBackgroundColor: '#e17055',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1
                }]
            },
            options: commonOptions
        });
    }
    
    // График влажности
    const humCtx = document.getElementById('humChart');
    if (humCtx) {
        if (humChart) humChart.destroy();
        
        humChart = new Chart(humCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Влажность',
                    data: hums,
                    borderColor: '#0984e3',
                    backgroundColor: 'rgba(9, 132, 227, 0.1)',
                    fill: true,
                    borderWidth: 1.5,
                    pointBackgroundColor: '#0984e3',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1
                }]
            },
            options: commonOptions
        });
    }
    
    // График вибраций
    const vibCtx = document.getElementById('vibChart');
    if (vibCtx) {
        if (vibChart) vibChart.destroy();
        
        vibChart = new Chart(vibCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Вибрации',
                    data: vibes,
                    borderColor: '#00b894',
                    backgroundColor: 'rgba(0, 184, 148, 0.1)',
                    fill: true,
                    borderWidth: 1.5,
                    pointBackgroundColor: '#00b894',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 1
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        beginAtZero: true,
                        suggestedMin: 0
                    }
                }
            }
        });
    }
}

// Обновление графиков с текущей историей
function updateChartsWithHistory() {
    if (chartHistory.length === 0) return;
    
    const labels = generateTimeLabels(chartHistory.length);
    const temps = chartHistory.map(d => d.temperature);
    const hums = chartHistory.map(d => d.humidity);
    const vibes = chartHistory.map(d => d.hits_per_minute);
    
    // Обновляем данные графиков
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

function createEmptyCharts() {
    const emptyLabels = ['Нет данных'];
    const emptyValues = [0];
    
    const chartConfigs = [
        { id: 'tempChart', color: '#e17055', label: 'Температура' },
        { id: 'humChart', color: '#0984e3', label: 'Влажность' },
        { id: 'vibChart', color: '#00b894', label: 'Вибрации' }
    ];
    
    chartConfigs.forEach(config => {
        const canvas = document.getElementById(config.id);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (config.id === 'tempChart' && tempChart) tempChart.destroy();
        if (config.id === 'humChart' && humChart) humChart.destroy();
        if (config.id === 'vibChart' && vibChart) vibChart.destroy();
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: emptyLabels,
                datasets: [{
                    label: config.label,
                    data: emptyValues,
                    borderColor: config.color,
                    backgroundColor: config.color + '20',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    });
}

// AI Чат
async function sendUserMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    addChatMessage(message, 'user');
    userInput.value = '';
    
    try {
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
    
    let timeStr;
    if (timestamp) {
        const date = new Date(timestamp);
        timeStr = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } else {
        timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    
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

// Управление оборудованием
function configureEquipment(id) {
    alert(`⚙️ Настройка оборудования №${id}\nФункционал в разработке`);
}

// Настройки параметров
async function loadSettings() {
    try {
        const response = await fetch('/api/get_settings');
        const data = await response.json();
        
        if (data.status === 'success') {
            const settings = data.settings;
            
            // Устанавливаем значения в поля
            document.querySelectorAll('.parameter-input').forEach(input => {
                const value = input.defaultValue;
                if (value === '20') input.value = settings.temperature_min || '20';
                if (value === '75') input.value = settings.temperature_max || '75';
                if (value === '80') input.value = settings.temperature_critical || '80';
                if (value === '5') input.value = settings.pressure_min || '5';
                if (value === '10') input.value = settings.pressure_max || '10';
                if (value === '12') input.value = settings.pressure_critical || '12';
                if (value === '0') input.value = settings.vibration_min || '0';
                if (value === '6') input.value = settings.vibration_max || '6';
                if (value === '8') input.value = settings.vibration_critical || '8';
            });
            
            // Обновляем отображение
            updateSettingsDisplay();
        }
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

function updateSettingsDisplay() {
    const tempMin = document.querySelector('.parameter-input[value="20"]').value;
    const tempMax = document.querySelector('.parameter-input[value="75"]').value;
    const tempCritical = document.querySelector('.parameter-input[value="80"]').value;
    
    const pressureMin = document.querySelector('.parameter-input[value="5"]').value;
    const pressureMax = document.querySelector('.parameter-input[value="10"]').value;
    const pressureCritical = document.querySelector('.parameter-input[value="12"]').value;
    
    const vibMin = document.querySelector('.parameter-input[value="0"]').value;
    const vibMax = document.querySelector('.parameter-input[value="6"]').value;
    const vibCritical = document.querySelector('.parameter-input[value="8"]').value;
    
    document.getElementById('tempNormal').textContent = `${tempMin} - ${tempMax} °C`;
    document.getElementById('tempHigh').textContent = `${tempMax} + °C`;
    document.getElementById('tempCritical').textContent = `${tempCritical} + °C`;
    
    document.getElementById('pressureNormal').textContent = `${pressureMin} - ${pressureMax} бар`;
    document.getElementById('pressureHigh').textContent = `${pressureMax} + бар`;
    document.getElementById('pressureCritical').textContent = `${pressureCritical} + бар`;
    
    document.getElementById('vibNormal').textContent = `${vibMin} - ${vibMax} мм/с`;
    document.getElementById('vibHigh').textContent = `${vibMax} + мм/с`;
    document.getElementById('vibCritical').textContent = `${vibCritical} + мм/с`;
}

async function saveSettings() {
    const settings = {
        temperature: {
            min: document.querySelector('.parameter-input[value="20"]').value,
            max: document.querySelector('.parameter-input[value="75"]').value,
            critical: document.querySelector('.parameter-input[value="80"]').value
        },
        pressure: {
            min: document.querySelector('.parameter-input[value="5"]').value,
            max: document.querySelector('.parameter-input[value="10"]').value,
            critical: document.querySelector('.parameter-input[value="12"]').value
        },
        vibration: {
            min: document.querySelector('.parameter-input[value="0"]').value,
            max: document.querySelector('.parameter-input[value="6"]').value,
            critical: document.querySelector('.parameter-input[value="8"]').value
        }
    };
    
    try {
        const response = await fetch('/api/save_settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
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

// Профиль
async function loadProfile() {
    try {
        const response = await fetch('/api/get_profile');
        const data = await response.json();
        if (data.status === 'success') {
            const profile = data.profile;
            
            document.getElementById('fullName').value = profile.fullName;
            document.getElementById('email').value = profile.email;
            document.getElementById('phone').value = profile.phone;
            document.getElementById('department').value = profile.department;
            document.getElementById('position').value = profile.position;
            
            document.getElementById('profileName').textContent = profile.fullName;
            document.getElementById('profileRole').textContent = profile.position;
            document.getElementById('userName').textContent = profile.fullName;
        }
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
    }
}

async function saveProfile() {
    const profile = {
        fullName: document.getElementById('fullName').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        department: document.getElementById('department').value,
        position: document.getElementById('position').value
    };
    
    if (!profile.fullName || !profile.email) {
        alert('❌ Заполните обязательные поля: Имя и Email');
        return;
    }
    
    try {
        const response = await fetch('/api/save_profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(profile)
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('profileName').textContent = profile.fullName;
            document.getElementById('profileRole').textContent = profile.position;
            document.getElementById('userName').textContent = profile.fullName;
            
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
    loadProfile(); // Просто перезагружаем сохраненные данные
}

// Управление графиками
function zoomChart(direction) {
    if (!tempChart || !humChart || !vibChart) return;
    
    const charts = [tempChart, humChart, vibChart];
    charts.forEach(chart => {
        if (chart.options.scales.x.zoom) {
            if (direction === 'in') {
                chart.zoom(1.1);
            } else {
                chart.zoom(0.9);
            }
        }
    });
}

function resetChartZoom() {
    if (!tempChart || !humChart || !vibChart) return;
    
    const charts = [tempChart, humChart, vibChart];
    charts.forEach(chart => {
        if (chart.resetZoom) {
            chart.resetZoom();
        }
    });
}

function refreshCharts() {
    // Сбрасываем историю и загружаем свежие данные
    chartHistory = [];
    loadCharts();
}

// Перерисовка графиков при изменении размера окна
function resizeCharts() {
    if (tempChart) tempChart.resize();
    if (humChart) humChart.resize();
    if (vibChart) vibChart.resize();
}

// Инициализация
window.onload = function() {
    initWebSocket();
    showPage('dashboard');
    
    // Обработчик Enter в чате
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendUserMessage();
            }
        });
    }
    
    // Обработчик изменения размера окна
    window.addEventListener('resize', function() {
        setTimeout(resizeCharts, 100);
    });
    
    // Обновление данных каждые 5 секунд
    setInterval(loadInitialData, 5000);
    
    // Загрузка AI рекомендаций каждую минуту
    setInterval(loadAIRecommendations, 60000);
};