// === SkyRoutes — клиентский JS ===

// ---------- Тосты ----------
function showToast(message, type = 'info', timeout = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'toast' + (type === 'error' ? ' toast-error' : type === 'success' ? ' toast-success' : '');
    toast.hidden = false;
    toast.style.opacity = '1';
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => { toast.hidden = true; }, 300);
    }, timeout);
}

// Показ тоста из URL параметра ?toast=...&type=...
(function () {
    const params = new URLSearchParams(window.location.search);
    const msg = params.get('toast');
    if (msg) {
        showToast(decodeURIComponent(msg), params.get('toast_type') || 'success');
        // Очистим URL
        params.delete('toast');
        params.delete('toast_type');
        const cleanUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.replaceState({}, '', cleanUrl);
    }
})();

// ---------- Динамическое добавление пассажиров ----------
(function () {
    const form = document.getElementById('bookingForm');
    if (!form) return;

    const passengersContainer = document.getElementById('passengers');
    const addBtn = document.getElementById('addPassenger');
    const template = document.getElementById('passengerTemplate');
    let counter = 0;

    function renumber() {
        const blocks = passengersContainer.querySelectorAll('.passenger-block');
        blocks.forEach((b, i) => {
            b.querySelector('.pnum').textContent = i + 1;
            b.querySelector('.remove-passenger').style.display =
                blocks.length > 1 ? 'inline-block' : 'none';
        });
    }

    function addPassenger() {
        counter += 1;
        if (counter > 9) {
            showToast('Максимум 9 пассажиров на одно бронирование.', 'error');
            counter -= 1;
            return;
        }
        const node = template.content.cloneNode(true);
        passengersContainer.appendChild(node);
        renumber();
    }

    passengersContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-passenger')) {
            e.target.closest('.passenger-block').remove();
            counter -= 1;
            renumber();
        }
    });

    addBtn.addEventListener('click', addPassenger);
    addPassenger(); // Один пассажир по умолчанию
})();

// ---------- Сортировка на странице рейсов ----------
(function () {
    const sortSelect = document.getElementById('sortSelect');
    if (!sortSelect) return;

    sortSelect.addEventListener('change', () => {
        const [by, order] = sortSelect.value.split(':');
        const url = new URL(window.location.href);
        url.searchParams.set('sort_by', by);
        url.searchParams.set('sort_order', order);
        window.location.href = url.toString();
    });

    // Восстановление значения из URL
    const params = new URLSearchParams(window.location.search);
    const currentBy = params.get('sort_by') || 'departure_at';
    const currentOrder = params.get('sort_order') || 'asc';
    sortSelect.value = `${currentBy}:${currentOrder}`;
})();

// ---------- Подсветка активной ссылки в меню ----------
(function () {
    const path = window.location.pathname;
    document.querySelectorAll('.main-nav a').forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
        }
    });
})();
