let ws;
let tempChart, humChart, vibChart;
let selectedFile = null;
let chartZoomLevel = 1.0;

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
            if (tempChart) refreshCharts();
            loadInitialData();
        }, 100);
    }
    
    // При показе настроек загружаем сохраненные значения
    if (pageId === 'settings') {
        loadSettings();
    }
    
    // При показе профиля загружаем данные профиля
    if (pageId === 'profile') {
        loadProfile();
    }
}

// WebSocket подключение
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        updateStatus(true);
        loadInitialData();
        loadCharts();
    };
    
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Ошибка парсинга WebSocket:', e);
        }
    };
    
    ws.onclose = function() {
        updateStatus(false);
        setTimeout(initWebSocket, 3000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket ошибка:', error);
    };
}

function updateStatus(connected) {
    const icon = document.getElementById('statusIcon');
    const text = document.getElementById('statusText');
    
    if (connected) {
        if (icon) {
            icon.style.color = '#00b894';
            text.textContent = 'Подключено';
        }
    } else {
        if (icon) {
            icon.style.color = '#e17055';
            text.textContent = 'Отключено';
        }
    }
}

function handleWebSocketMessage(data) {
    if (data.type === 'realtime') {
        updateDashboard(data.data);
        addDataToCharts(data.data);
    } else if (data.type === 'ai_recommendation') {
        addChatMessage(data.data);
    } else if (data.type === 'connection') {
        console.log('WebSocket:', data.message);
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
        if (tempStatusElement) tempStatusElement.textContent = `Статус: ${tempStatus}`;
        if (tempStatusElement) tempStatusElement.style.color = tempColor;
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
        if (humStatusElement) humStatusElement.textContent = `Статус: ${humStatus}`;
        if (humStatusElement) humStatusElement.style.color = humColor;
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
        console.error('Ошибка загрузки данных:', e);
    }
}

async function loadCharts() {
    try {
        const response = await fetch('/api/history?hours=1');
        const historyData = await response.json();
        
        if (Array.isArray(historyData) && historyData.length > 0) {
            createCharts(historyData);
        } else {
            createEmptyCharts();
        }
    } catch (e) {
        console.error('Ошибка загрузки графиков:', e);
        createEmptyCharts();
    }
}

function createCharts(historyData) {
    if (!Array.isArray(historyData) || historyData.length === 0) {
        createEmptyCharts();
        return;
    }
    
    // Сортируем по времени
    historyData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    // Для часового графика показываем только последние 60 точек
    // или агрегируем данные если их больше
    let displayData;
    const maxPoints = 60;
    
    if (historyData.length > maxPoints) {
        // Берем каждую N-ную точку
        const step = Math.ceil(historyData.length / maxPoints);
        displayData = [];
        for (let i = 0; i < historyData.length; i += step) {
            displayData.push(historyData[i]);
        }
        // Всегда добавляем последнюю точку
        if (displayData.length === 0 || displayData[displayData.length - 1] !== historyData[historyData.length - 1]) {
            displayData.push(historyData[historyData.length - 1]);
        }
    } else {
        displayData = historyData;
    }
    
    // Форматируем время
    const labels = displayData.map(d => {
        const date = new Date(d.timestamp);
        return date.getHours().toString().padStart(2, '0') + ':' + 
               date.getMinutes().toString().padStart(2, '0');
    });
    
    const temps = displayData.map(d => d.temperature || 0);
    const hums = displayData.map(d => d.humidity || 0);
    const vibes = displayData.map(d => d.hits_per_minute || 0);
    
    // Общие настройки графиков
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
            legend: { 
                display: true,
                position: 'top',
                labels: {
                    font: {
                        size: 12
                    }
                }
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
                    color: 'rgba(0,0,0,0.05)' 
                },
                ticks: {
                    font: {
                        size: 10
                    },
                    callback: function(value) {
                        return value.toFixed(1);
                    }
                }
            },
            x: { 
                grid: { 
                    display: false 
                },
                ticks: {
                    maxTicksLimit: 10,
                    font: {
                        size: 10
                    },
                    callback: function(value, index) {
                        // Показываем каждую 6-ю метку
                        return index % Math.ceil(labels.length / 10) === 0 ? labels[index] : '';
                    }
                }
            }
        },
        elements: {
            point: {
                radius: 2,
                hoverRadius: 5
            },
            line: {
                tension: 0.3,
                borderWidth: 2
            }
        },
        animation: {
            duration: 0
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
                    borderWidth: 2
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        title: {
                            display: true,
                            text: '°C',
                            color: '#e17055'
                        }
                    }
                }
            }
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
                    borderWidth: 2
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        title: {
                            display: true,
                            text: '%',
                            color: '#0984e3'
                        }
                    }
                }
            }
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
                    borderWidth: 2
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'уд/мин',
                            color: '#00b894'
                        }
                    }
                }
            }
        });
    }
}

function addDataToCharts(newData) {
    if (!newData.timestamp || !tempChart || !humChart || !vibChart) return;
    
    const time = new Date(newData.timestamp);
    const timeLabel = time.getHours().toString().padStart(2, '0') + ':' + 
                      time.getMinutes().toString().padStart(2, '0');
    
    // Ограничиваем количество точек до 60
    [tempChart, humChart, vibChart].forEach(chart => {
        if (chart.data.labels.length >= 60) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => dataset.data.shift());
        }
        
        chart.data.labels.push(timeLabel);
    });
    
    tempChart.data.datasets[0].data.push(newData.temperature || 0);
    humChart.data.datasets[0].data.push(newData.humidity || 0);
    vibChart.data.datasets[0].data.push(newData.hits_per_minute || 0);
    
    tempChart.update('none');
    humChart.update('none');
    vibChart.update('none');
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
    
    addFullChatMessage(message, 'user');
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
            addFullChatMessage(data.response, 'ai');
        } else {
            addFullChatMessage('❌ Ошибка получения ответа от AI', 'ai');
        }
        
    } catch (error) {
        console.error('Ошибка:', error);
        addFullChatMessage('❌ Ошибка подключения к серверу', 'ai');
    }
}

function addFullChatMessage(text, sender) {
    const chatDiv = document.getElementById('aiChatFull');
    if (!chatDiv) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const time = new Date();
    const timeStr = time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
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

function addChatMessage(data) {
    addFullChatMessage(data.message, 'ai');
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
            document.querySelector('.parameter-input[value="20"]').value = settings.temperature_min || '20';
            document.querySelector('.parameter-input[value="75"]').value = settings.temperature_max || '75';
            document.querySelector('.parameter-input[value="80"]').value = settings.temperature_critical || '80';
            
            document.querySelector('.parameter-input[value="5"]').value = settings.pressure_min || '5';
            document.querySelector('.parameter-input[value="10"]').value = settings.pressure_max || '10';
            document.querySelector('.parameter-input[value="12"]').value = settings.pressure_critical || '12';
            
            document.querySelector('.parameter-input[value="0"]').value = settings.vibration_min || '0';
            document.querySelector('.parameter-input[value="6"]').value = settings.vibration_max || '6';
            document.querySelector('.parameter-input[value="8"]').value = settings.vibration_critical || '8';
            
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

// Экспорт данных
async function exportData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const equipment = document.getElementById('exportEquipment').value;
    const format = document.querySelector('input[name="format"]:checked').value;
    
    if (!startDate || !endDate) {
        alert('❌ Укажите период данных');
        return;
    }
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                equipment: equipment,
                format: format
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            // Создаем и скачиваем файл
            let content, filename, mimeType;
            
            if (format === 'json') {
                content = JSON.stringify(data.data, null, 2);
                filename = `monitoring-${startDate}-to-${endDate}.json`;
                mimeType = 'application/json';
            } else if (format === 'csv') {
                content = convertToCSV(data.data);
                filename = `monitoring-${startDate}-to-${endDate}.csv`;
                mimeType = 'text/csv';
            } else {
                // Для Excel используем CSV
                content = convertToCSV(data.data);
                filename = `monitoring-${startDate}-to-${endDate}.csv`;
                mimeType = 'text/csv';
            }
            
            const blob = new Blob([content], {type: mimeType});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            alert(`✅ Данные успешно экспортированы!\nФайл: ${filename}\nЗаписей: ${data.metadata.data_count}`);
        } else {
            alert(`❌ Ошибка: ${data.message}`);
        }
    } catch (error) {
        console.error('Ошибка экспорта:', error);
        alert('❌ Ошибка экспорта данных');
    }
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = ['timestamp', 'temperature', 'humidity', 'hits_per_minute', 'hit_count'];
    const csvRows = [headers.join(',')];
    
    for (const row of data) {
        const values = headers.map(header => {
            const escaped = ('' + (row[header] || '')).replace(/"/g, '""');
            return `"${escaped}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

function previewExport() {
    alert('👁️ Предварительный просмотр\nФункционал в разработке');
}

// Загрузка файлов
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropZone = document.getElementById('dropZone');
    dropZone.classList.add('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const dropZone = document.getElementById('dropZone');
    dropZone.classList.remove('dragover');
    
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
    if (!file.name.toLowerCase().endsWith('.csv')) {
        alert('❌ Пожалуйста, выберите CSV файл');
        return;
    }
    
    selectedFile = file;
    
    const fileInfo = document.getElementById('fileInfo');
    fileInfo.innerHTML = `
        <strong>📄 Выбран файл:</strong> ${file.name}<br>
        <strong>📦 Размер:</strong> ${(file.size / 1024).toFixed(2)} KB<br>
        <strong>📝 Тип:</strong> ${file.type || 'text/csv'}
    `;
    
    document.getElementById('uploadBtn').disabled = false;
}

async function uploadFile() {
    if (!selectedFile) {
        alert('❌ Пожалуйста, выберите файл');
        return;
    }
    
    const equipment = document.getElementById('uploadEquipment').value;
    if (equipment === 'Выберите оборудование') {
        alert('❌ Пожалуйста, выберите оборудование');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('equipment', equipment);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            alert(`✅ Файл "${selectedFile.name}" успешно загружен!\nИмпортировано строк: ${data.rows}`);
            clearUpload();
        } else {
            alert(`❌ Ошибка: ${data.message}`);
        }
    } catch (error) {
        console.error('Ошибка загрузки:', error);
        alert('❌ Ошибка загрузки файла');
    }
}

function clearUpload() {
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').innerHTML = '';
    document.getElementById('uploadBtn').disabled = true;
    selectedFile = null;
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
    if (direction === 'in') {
        chartZoomLevel *= 1.2;
    } else {
        chartZoomLevel /= 1.2;
    }
    
    // Применяем масштаб ко всем графикам
    [tempChart, humChart, vibChart].forEach(chart => {
        if (chart) {
            chart.options.scales.x.ticks.font.size = Math.max(8, 10 * chartZoomLevel);
            chart.options.scales.y.ticks.font.size = Math.max(8, 10 * chartZoomLevel);
            chart.options.elements.point.radius = Math.max(1, 2 * chartZoomLevel);
            chart.options.elements.point.hoverRadius = Math.max(3, 5 * chartZoomLevel);
            chart.update();
        }
    });
}

function resetChartZoom() {
    chartZoomLevel = 1.0;
    [tempChart, humChart, vibChart].forEach(chart => {
        if (chart) {
            chart.resetZoom();
            chart.options.scales.x.ticks.font.size = 10;
            chart.options.scales.y.ticks.font.size = 10;
            chart.options.elements.point.radius = 2;
            chart.options.elements.point.hoverRadius = 5;
            chart.update();
        }
    });
}

function refreshCharts() {
    loadCharts();
}

function setupChartsResponsive() {
    const width = window.innerWidth;
    
    [tempChart, humChart, vibChart].forEach(chart => {
        if (chart) {
            if (width < 768) {
                // На мобильных устройствах
                chart.options.scales.x.ticks.maxTicksLimit = 5;
                chart.options.plugins.legend.position = 'bottom';
            } else if (width < 1200) {
                // На планшетах
                chart.options.scales.x.ticks.maxTicksLimit = 8;
                chart.options.plugins.legend.position = 'top';
            } else {
                // На десктопах
                chart.options.scales.x.ticks.maxTicksLimit = 12;
                chart.options.plugins.legend.position = 'top';
            }
            chart.update();
        }
    });
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
    window.addEventListener('resize', setupChartsResponsive);
    
    // Обновление данных каждые 5 секунд
    setInterval(loadInitialData, 5000);
    
    // Обновление графиков каждые 30 секунд
    setInterval(loadCharts, 30000);
};