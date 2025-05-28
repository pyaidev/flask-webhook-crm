document.addEventListener('DOMContentLoaded', function() {
    // Инициализация переменных
    let currentDate = new Date();
    let selectedStage = null;
    let cachedStatsData = {}; // Кэш для хранения данных по датам
    
    // Получение элементов DOM
    const calendarEl = document.getElementById('calendar');
    const currentMonthEl = document.getElementById('currentMonth');
    const currentDateEl = document.getElementById('currentDate');
    const prevMonthBtn = document.getElementById('prevMonth');
    const nextMonthBtn = document.getElementById('nextMonth');
    const stagesListEl = document.getElementById('stagesList');
    const dealsListEl = document.getElementById('dealsList');
    const statsContainerEl = document.querySelector('.stats-container');
    const dealsContainerEl = document.getElementById('dealsContainer');
    const selectedStageEl = document.getElementById('selectedStage');
    const backToStatsBtn = document.getElementById('backToStats');
    const totalSumEl = document.getElementById('totalSum');
    const totalHooksEl = document.getElementById('totalHooks');
    const confirmedSumEl = document.getElementById('confirmedSum'); // Новый элемент для суммы подтвержденных заказов
    const statsHeaderEl = document.querySelector('.stats-header h2');
    
    // Добавляем элементы для вывода процентов
    const statsContainer = document.querySelector('.stats-summary');
    
    // Создаем и добавляем элементы для процентов отмен
    const cancelPercentItem = document.createElement('div');
    cancelPercentItem.className = 'summary-item';
    cancelPercentItem.innerHTML = `
        <div class="summary-title">% отмен</div>
        <div class="summary-value" id="cancelPercent">0%</div>
        <div class="summary-formula">=(п.14+п.19+п.23)/п.7×100%</div>
    `;
    statsContainer.appendChild(cancelPercentItem);
    
    // Создаем и добавляем элементы для процентов недозвонов
    const missedPercentItem = document.createElement('div');
    missedPercentItem.className = 'summary-item';
    missedPercentItem.innerHTML = `
        <div class="summary-title">% недозвонов</div>
        <div class="summary-value" id="missedPercent">0%</div>
        <div class="summary-formula">=(п.15+п.20+п.24)/п.7×100%</div>
    `;
    statsContainer.appendChild(missedPercentItem);
    
    // Создаем и добавляем элемент для отображения суммы подтвержденных заказов
    const confirmedSumItem = document.createElement('div');
    confirmedSumItem.className = 'summary-item';
    confirmedSumItem.innerHTML = `
        <div class="summary-title">Сумма подтв. заказов</div>
        <div class="summary-value" id="confirmedSum">0 ₽</div>
        <div class="summary-formula">=п.13+п.18+п.22</div>
    `;
    statsContainer.appendChild(confirmedSumItem);
    
    // Массив с названиями месяцев
    const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    
    // Массив с названиями дней недели
    const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    
    // Порядок стадий сделок для отображения
    const stagesOrder = [
        "Все сделки",
        "Без статуса",
        "Без даты",
        "Без региона",
        "Без суммы",
        "Без адреса",
        "Все готово",
        "МСК",
        "СПб",
        "Регион",
        "Звоним без предоплаты",
        "Звоним без предоплаты несколько товаров",
        "Подтвердил заказ без предоплаты",
        "Отменил заказ без предоплаты",
        "Не взял трубку без предоплаты",
        "Звоним с предоплатой",
        "Звоним с предоплатой несколько товаров",
        "Подтвердил заказ с предоплатой",
        "Отменил заказ с предоплатой",
        "Не взял трубку с предоплатой",
        "Звоним регион",
        "Подтвердил заказ регион",
        "Отменил заказ регион",
        "Не взял трубку регион",
        "Непонятно"
    ];
    
    // Функция для форматирования даты в виде 'YYYY-MM-DD'
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Функция для форматирования даты в виде 'DD.MM.YYYY'
    function formatDisplayDate(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    }
    
    // Функция для обновления заголовка статистики
    function updateStatisticsHeader(date) {
        // Форматируем дату для заголовка
        const displayDate = formatDisplayDate(date);
        
        // Обновляем заголовок в DOM
        if (statsHeaderEl && statsHeaderEl.querySelector('span')) {
            statsHeaderEl.querySelector('span').textContent = displayDate;
        } else {
            currentDateEl.textContent = displayDate;
        }
        
        // Также устанавливаем текст в span#currentDate
        if (currentDateEl) {
            currentDateEl.textContent = displayDate;
        }
    }
    
    // Функция для отрисовки календаря
    function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        
        // Обновляем заголовок месяца
        currentMonthEl.textContent = `${months[month]} ${year}`;
        
        // Очищаем календарь
        calendarEl.innerHTML = '';
        
        // Добавляем заголовки дней недели
        const calendarHeader = document.createElement('div');
        calendarHeader.className = 'calendar-header';
        
        weekDays.forEach(day => {
            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day-name';
            dayEl.textContent = day;
            calendarHeader.appendChild(dayEl);
        });
        
        calendarEl.appendChild(calendarHeader);
        
        // Получаем первый день месяца
        const firstDay = new Date(year, month, 1);
        
        // Получаем первый день для отображения в календаре
        // (может быть из предыдущего месяца)
        let startDay = new Date(firstDay);
        let firstDayOfWeek = startDay.getDay() || 7; // Преобразуем 0 (воскресенье) в 7
        startDay.setDate(startDay.getDate() - (firstDayOfWeek - 1));
        
        // Получаем последний день месяца
        const lastDay = new Date(year, month + 1, 0);
        
        // Получаем последний день для отображения в календаре
        // (может быть из следующего месяца)
        let endDay = new Date(lastDay);
        let lastDayOfWeek = endDay.getDay() || 7;
        endDay.setDate(endDay.getDate() + (7 - lastDayOfWeek));
        
        // Отрисовываем дни
        let currentDayOfCalendar = new Date(startDay);
        
        while (currentDayOfCalendar <= endDay) {
            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day';
            dayEl.textContent = currentDayOfCalendar.getDate();
            
            // Если день не из текущего месяца, добавляем класс
            if (currentDayOfCalendar.getMonth() !== month) {
                dayEl.classList.add('other-month');
            }
            
            // Если это выбранный день, добавляем класс
            if (
                currentDayOfCalendar.getDate() === currentDate.getDate() &&
                currentDayOfCalendar.getMonth() === currentDate.getMonth() &&
                currentDayOfCalendar.getFullYear() === currentDate.getFullYear()
            ) {
                dayEl.classList.add('active');
            }
            
            // Для сохранения даты в замыкании
            const clickDate = new Date(currentDayOfCalendar);
            
            // Добавляем обработчик клика
            dayEl.addEventListener('click', function() {
                // Удаляем класс active у предыдущего выбранного дня
                const prevActive = document.querySelector('.calendar-day.active');
                if (prevActive) {
                    prevActive.classList.remove('active');
                }
                
                // Добавляем класс active к выбранному дню
                dayEl.classList.add('active');
                
                // Обновляем текущую дату на выбранную дату из календаря
                currentDate = new Date(clickDate);
                
                // Обновляем заголовок статистики
                updateStatisticsHeader(currentDate);
                
                // Загружаем данные для выбранной даты
                const formattedDate = formatDate(currentDate);
                
                // Добавляем случайный параметр для предотвращения кэширования
                const cacheBuster = `&_=${Date.now()}`;
                loadStats(formattedDate + cacheBuster);
                
                // Скрываем контейнер со сделками и показываем статистику
                dealsContainerEl.style.display = 'none';
                statsContainerEl.style.display = 'block';
            });
            
            calendarEl.appendChild(dayEl);
            
            // Переходим к следующему дню
            currentDayOfCalendar.setDate(currentDayOfCalendar.getDate() + 1);
        }
    }
    
    // Функция для загрузки статистики
    function loadStats(date) {
        console.log('Loading stats for date:', date);
        
        // Очистка cache buster если он есть
        const cleanDate = date.split('&')[0];
        
        // Для отладки
        console.log(`Requesting stats for: ${cleanDate}, AJAX URL: /api/stats?date=${date}`);
        
        // Если данных нет в кэше, загружаем с сервера
        fetch(`/api/stats?date=${date}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        })
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);
            
            // Отображаем данные
            displayStats(data, cleanDate);
        })
        .catch(error => {
            console.error('Ошибка при загрузке статистики:', error);
            // Отображаем пустые данные при ошибке
            displayStats([], cleanDate);
        });
    }
    
    // Функция для отображения статистики из данных
    function displayStats(data, date) {
        console.log('Displaying stats for:', date);
        
        // Очищаем список стадий
        stagesListEl.innerHTML = '';
        
        // Обновляем заголовок статистики с выбранной датой
        const dateObj = new Date(date);
        const displayDate = formatDisplayDate(dateObj);
        
        // Установка даты в заголовке статистики
        document.querySelector('.stats-header h2 span').textContent = displayDate;
        
        // Расчет итоговых значений
        let totalHooks = 0;
        let totalSum = 0;
        let confirmedSum = 0; // Сумма подтвержденных заказов
        
        // Создаем объект для хранения данных по стадиям
        const stagesData = {};
        
        // Заполняем объект стадий начальными нулевыми значениями
        stagesOrder.forEach(stage => {
            stagesData[stage] = { count: 0, total_summa: 0 };
        });
        
        // Заполняем данными из API
        if (Array.isArray(data)) {
            data.forEach(stage => {
                if (stage && stage.stage && stagesData[stage.stage]) {
                    stagesData[stage.stage] = {
                        count: stage.count || 0,
                        total_summa: stage.total_summa || 0
                    };
                    
                    // Сумма для "Все сделки" становится итоговой суммой
                    if (stage.stage === "Все сделки") {
                        totalSum = stage.total_summa || 0;
                    }
                    
                    // Суммируем только для подсчета количества вебхуков
                    totalHooks += (stage.count || 0);
                }
            });
        }
        
        // Считаем сумму подтвержденных заказов
        confirmedSum = (stagesData["Подтвердил заказ без предоплаты"].total_summa || 0) + 
                      (stagesData["Подтвердил заказ с предоплатой"].total_summa || 0) + 
                      (stagesData["Подтвердил заказ регион"].total_summa || 0);
        
        // Отображаем каждую стадию в заданном порядке
        stagesOrder.forEach((stageName, index) => {
            const stage = stagesData[stageName];
            const stageEl = document.createElement('div');
            stageEl.className = 'stage-item';
            stageEl.innerHTML = `
                <div class="stage-column">п.${index + 1}. ${stageName}</div>
                <div class="count-column">${stage.count}</div>
                <div class="sum-column">${stage.total_summa.toLocaleString()} ₽</div>
            `;
            
            // Добавляем обработчик клика для просмотра сделок по стадии
            stageEl.addEventListener('click', function() {
                selectedStage = stageName;
                selectedStageEl.textContent = selectedStage;
                
                // Загружаем сделки для выбранной стадии
                loadDeals(selectedStage, date);
                
                // Скрываем статистику и показываем контейнер со сделками
                statsContainerEl.style.display = 'none';
                dealsContainerEl.style.display = 'block';
            });
            
            stagesListEl.appendChild(stageEl);
        });
        
        // Обновляем итоговые значения
        totalHooksEl.textContent = totalHooks;
        totalSumEl.textContent = totalSum.toLocaleString() + ' ₽';
        document.getElementById('confirmedSum').textContent = confirmedSum.toLocaleString() + ' ₽';
        
        // Расчет процентов
        const allReadyCount = stagesData["Все готово"].count || 1; // Используем 1 для избежания деления на 0
        
        // Процент отмен
        const cancelCount = (stagesData["Отменил заказ без предоплаты"].count + 
                            stagesData["Отменил заказ с предоплатой"].count + 
                            stagesData["Отменил заказ регион"].count);
        const cancelPercent = (cancelCount / allReadyCount) * 100;
        document.getElementById('cancelPercent').textContent = cancelPercent.toFixed(2) + '%';
        
        // Процент недозвонов
        const missedCount = (stagesData["Не взял трубку без предоплаты"].count + 
                            stagesData["Не взял трубку с предоплатой"].count + 
                            stagesData["Не взял трубку регион"].count);
        const missedPercent = (missedCount / allReadyCount) * 100;
        document.getElementById('missedPercent').textContent = missedPercent.toFixed(2) + '%';
    }
    
    // Функция для загрузки сделок по стадии
    function loadDeals(stage, date) {
        console.log(`Loading deals for stage: ${stage}, date: ${date}`);
        
        // Очистка cache buster если он есть
        const cleanDate = date.split('&')[0];
        
        // Добавляем случайный параметр для предотвращения кэширования
        const cacheBuster = `&_=${Date.now()}`;
        
        fetch(`/api/deals/${encodeURIComponent(stage)}?date=${cleanDate}${cacheBuster}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received deals:', data);
            
            // Очищаем список сделок
            dealsListEl.innerHTML = '';
            
            // Если нет данных, показываем сообщение
            if (!data || data.length === 0) {
                const noDataEl = document.createElement('div');
                noDataEl.className = 'deal-item';
                noDataEl.innerHTML = '<div class="deal-name">Нет сделок для выбранной стадии</div><div class="deal-sum">-</div><div class="deal-time">-</div>';
                dealsListEl.appendChild(noDataEl);
            } else {
                // Отображаем данные по каждой сделке
                data.forEach(deal => {
                    const dealEl = document.createElement('div');
                    dealEl.className = 'deal-item';
                    
                    // Форматируем время (теперь указываем, что это время MSK)
                    const dealTime = new Date(deal.timestamp);
                    const formattedTime = dealTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
                    
                    dealEl.innerHTML = `
                        <div class="deal-name">${deal.name}</div>
                        <div class="deal-sum">${deal.summa.toLocaleString()} ₽</div>
                        <div class="deal-time">${formattedTime} (МСК)</div>
                    `;
                    
                    dealsListEl.appendChild(dealEl);
                });
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке сделок:', error);
            // Показываем сообщение об ошибке
            dealsListEl.innerHTML = '<div class="deal-item error">Ошибка загрузки данных</div>';
        });
    }
    
    // Обработчик клика на кнопку "Назад"
    backToStatsBtn.addEventListener('click', function() {
        // Скрываем контейнер со сделками и показываем статистику
        dealsContainerEl.style.display = 'none';
        statsContainerEl.style.display = 'block';
    });
    
    // Обработчики кликов на кнопки переключения месяцев
    prevMonthBtn.addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });
    
    nextMonthBtn.addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });
    
    // Инициализация
    renderCalendar(currentDate);
    updateStatisticsHeader(currentDate);
    
    // При инициализации добавляем случайный параметр для предотвращения кэширования
    const cacheBuster = `&_=${Date.now()}`;
    loadStats(formatDate(currentDate) + cacheBuster);
});