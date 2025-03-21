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
        let currentDay = new Date(startDay);
        
        while (currentDay <= endDay) {
            const dayEl = document.createElement('div');
            dayEl.className = 'calendar-day';
            dayEl.textContent = currentDay.getDate();
            
            // Если день не из текущего месяца, добавляем класс
            if (currentDay.getMonth() !== month) {
                dayEl.classList.add('other-month');
            }
            
            // Если это выбранный день, добавляем класс
            if (
                currentDay.getDate() === currentDate.getDate() &&
                currentDay.getMonth() === currentDate.getMonth() &&
                currentDay.getFullYear() === currentDate.getFullYear()
            ) {
                dayEl.classList.add('active');
            }
            
            // Добавляем обработчик клика
            dayEl.addEventListener('click', function() {
                // Удаляем класс active у предыдущего выбранного дня
                const prevActive = document.querySelector('.calendar-day.active');
                if (prevActive) {
                    prevActive.classList.remove('active');
                }
                
                // Добавляем класс active к выбранному дню
                dayEl.classList.add('active');
                
                // Обновляем текущую дату
                currentDate = new Date(
                    currentDay.getFullYear(),
                    currentDay.getMonth(),
                    currentDay.getDate()
                );
                
                // Обновляем отображаемую дату
                currentDateEl.textContent = formatDisplayDate(currentDate);
                
                // Загружаем данные для выбранной даты
                loadStats(formatDate(currentDate));
                
                // Скрываем контейнер со сделками и показываем статистику
                dealsContainerEl.style.display = 'none';
                statsContainerEl.style.display = 'block';
            });
            
            calendarEl.appendChild(dayEl);
            
            // Переходим к следующему дню
            currentDay.setDate(currentDay.getDate() + 1);
        }
    }
    
    // Функция для загрузки статистики
    function loadStats(date) {
        // Проверяем, есть ли данные для этой даты в кэше
        if (cachedStatsData[date]) {
            displayStats(cachedStatsData[date], date);
            return;
        }
        
        // Если данных нет в кэше, загружаем с сервера
        fetch(`/api/stats?date=${date}`)
            .then(response => response.json())
            .then(data => {
                // Сохраняем данные в кэш
                cachedStatsData[date] = data;
                
                // Отображаем данные
                displayStats(data, date);
            })
            .catch(error => {
                console.error('Ошибка при загрузке статистики:', error);
            });
    }
    
    // Функция для отображения статистики из данных
    function displayStats(data, date) {
        // Очищаем список стадий
        stagesListEl.innerHTML = '';
        
        // Расчет итоговых значений
        let totalHooks = 0;
        let totalSum = 0;
        
        // Создаем объект для хранения данных по стадиям
        const stagesData = {};
        
        // Заполняем объект стадий начальными нулевыми значениями
        stagesOrder.forEach(stage => {
            stagesData[stage] = { count: 0, total_summa: 0 };
        });
        
        // Заполняем данными из API
        data.forEach(stage => {
            if (stagesData[stage.stage]) {
                stagesData[stage.stage] = {
                    count: stage.count,
                    total_summa: stage.total_summa
                };
            }
            
            // Суммируем для итогов
            totalHooks += stage.count;
            totalSum += stage.total_summa;
        });
        
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
        fetch(`/api/deals/${encodeURIComponent(stage)}?date=${date}`)
            .then(response => response.json())
            .then(data => {
                // Очищаем список сделок
                dealsListEl.innerHTML = '';
                
                // Если нет данных, показываем сообщение
                if (data.length === 0) {
                    const noDataEl = document.createElement('div');
                    noDataEl.className = 'deal-item';
                    noDataEl.innerHTML = '<div class="deal-name">Нет сделок для выбранной стадии</div><div class="deal-sum">-</div><div class="deal-time">-</div>';
                    dealsListEl.appendChild(noDataEl);
                } else {
                    // Отображаем данные по каждой сделке
                    data.forEach(deal => {
                        const dealEl = document.createElement('div');
                        dealEl.className = 'deal-item';
                        
                        // Форматируем время
                        const dealTime = new Date(deal.timestamp);
                        const formattedTime = dealTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
                        
                        dealEl.innerHTML = `
                            <div class="deal-name">${deal.name}</div>
                            <div class="deal-sum">${deal.summa.toLocaleString()} ₽</div>
                            <div class="deal-time">${formattedTime}</div>
                        `;
                        
                        dealsListEl.appendChild(dealEl);
                    });
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке сделок:', error);
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
    currentDateEl.textContent = formatDisplayDate(currentDate);
    loadStats(formatDate(currentDate));
});