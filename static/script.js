document.addEventListener('DOMContentLoaded', function() {
    // Инициализация переменных
    let currentDate = new Date();
    let selectedStage = null;
    
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
    
    // Массив с названиями месяцев
    const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    
    // Массив с названиями дней недели
    const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    
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
        fetch(`/api/stats?date=${date}`)
            .then(response => response.json())
            .then(data => {
                // Очищаем список стадий
                stagesListEl.innerHTML = '';
                
                // Расчет итоговых значений
                let totalHooks = 0;
                let totalSum = 0;
                
                // Если нет данных, показываем сообщение
                if (data.length === 0) {
                    const noDataEl = document.createElement('div');
                    noDataEl.className = 'stage-item';
                    noDataEl.innerHTML = '<div class="stage-column">Нет данных за выбранную дату</div><div class="count-column">-</div><div class="sum-column">-</div>';
                    stagesListEl.appendChild(noDataEl);
                } else {
                    // Отображаем данные по каждой стадии
                    data.forEach(stage => {
                        const stageEl = document.createElement('div');
                        stageEl.className = 'stage-item';
                        stageEl.innerHTML = `
                            <div class="stage-column">${stage.stage}</div>
                            <div class="count-column">${stage.count}</div>
                            <div class="sum-column">${stage.total_summa.toLocaleString()} ₽</div>
                        `;
                        
                        // Добавляем обработчик клика для просмотра сделок по стадии
                        stageEl.addEventListener('click', function() {
                            selectedStage = stage.stage;
                            selectedStageEl.textContent = selectedStage;
                            
                            // Загружаем сделки для выбранной стадии
                            loadDeals(selectedStage, date);
                            
                            // Скрываем статистику и показываем контейнер со сделками
                            statsContainerEl.style.display = 'none';
                            dealsContainerEl.style.display = 'block';
                        });
                        
                        stagesListEl.appendChild(stageEl);
                        
                        // Суммируем для итогов
                        totalHooks += stage.count;
                        totalSum += stage.total_summa;
                    });
                }
                
                // Обновляем итоговые значения
                totalHooksEl.textContent = totalHooks;
                totalSumEl.textContent = totalSum.toLocaleString() + ' ₽';
            })
            .catch(error => {
                console.error('Ошибка при загрузке статистики:', error);
            });
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