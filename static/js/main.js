(function () {
    'use strict';

    const productPrice = document.querySelector('[data-product-price]');
    if (productPrice) {
        const currentPrice = productPrice.querySelector('[data-current-price]');
        const regularPrice = productPrice.querySelector('[data-regular-price]');
        const discountBadge = document.querySelector('[data-variant-discount]');
        const discountPercent = discountBadge?.querySelector('[data-discount-percent]');

        document.querySelectorAll('.product-detail__variants input[name="variant_id"]').forEach((input) => {
            input.addEventListener('change', () => {
                const hasDiscount = Boolean(input.dataset.regularPrice);
                currentPrice.textContent = input.dataset.price;
                regularPrice.textContent = hasDiscount ? input.dataset.regularPrice : '';
                regularPrice.hidden = !hasDiscount;
                if (discountBadge) discountBadge.hidden = !hasDiscount;
                if (discountPercent) discountPercent.textContent = input.dataset.discountPercent;
            });
        });
    }

    /* Mobile menu */
    const menuToggle = document.querySelector('.menu-toggle');
    const siteNav = document.querySelector('.site-nav');

    if (menuToggle && siteNav) {
        menuToggle.addEventListener('click', () => {
            const isOpen = siteNav.classList.toggle('is-open');
            menuToggle.classList.toggle('is-open', isOpen);
            menuToggle.setAttribute('aria-expanded', String(isOpen));
            menuToggle.setAttribute('aria-label', isOpen ? 'Закрити меню' : 'Відкрити меню');
        });

        siteNav.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                siteNav.classList.remove('is-open');
                menuToggle.classList.remove('is-open');
                menuToggle.setAttribute('aria-expanded', 'false');
            });
        });
    }

    /* Mobile search toggle */
    const searchToggle = document.querySelector('.header-search-toggle');
    const headerSearch = document.querySelector('.header-search');

    if (searchToggle && headerSearch) {
        searchToggle.addEventListener('click', (event) => {
            event.stopPropagation();
            const isOpen = headerSearch.classList.toggle('is-open');
            searchToggle.classList.toggle('is-open', isOpen);
            searchToggle.setAttribute('aria-expanded', String(isOpen));
            searchToggle.setAttribute('aria-label', isOpen ? 'Закрити пошук' : 'Відкрити пошук');
        });

        document.addEventListener('click', (event) => {
            const target = event.target;
            if (!headerSearch.contains(target) && !searchToggle.contains(target)) {
                headerSearch.classList.remove('is-open');
                searchToggle.classList.remove('is-open');
                searchToggle.setAttribute('aria-expanded', 'false');
                searchToggle.setAttribute('aria-label', 'Відкрити пошук');
            }
        });

        headerSearch.querySelector('input').addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                headerSearch.classList.remove('is-open');
                searchToggle.classList.remove('is-open');
                searchToggle.setAttribute('aria-expanded', 'false');
                searchToggle.setAttribute('aria-label', 'Відкрити пошук');
            }
        });
    }

    /* Add to cart without leaving the current page. */
    const cartCount = document.querySelector('[data-cart-count]');

    function showCartMessage(message, isError = false) {
        const notice = document.createElement('p');
        notice.className = `cart-notice${isError ? ' cart-notice--error' : ''}`;
        notice.textContent = message;
        notice.setAttribute('role', 'status');
        document.body.appendChild(notice);
        window.setTimeout(() => notice.remove(), 3000);
    }

    document.querySelectorAll('.js-cart-add').forEach((form) => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true;

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    credentials: 'same-origin',
                });
                if (!response.ok) throw new Error('Cart request failed');

                const data = await response.json();
                if (!data.ok) throw new Error('Cart response failed');
                if (cartCount) cartCount.textContent = data.cart_quantity;
                showCartMessage(data.message);
            } catch (error) {
                showCartMessage('Не вдалося додати товар. Спробуйте ще раз.', true);
            } finally {
                button.disabled = false;
            }
        });
    });

    document.querySelectorAll('.js-favorite-toggle').forEach((form) => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const button = form.querySelector('button[type="submit"]');
            const currentText = button.textContent.trim();
            button.disabled = true;

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    credentials: 'same-origin',
                });
                if (!response.ok) throw new Error('Favorite request failed');

                const data = await response.json();
                if (!data.ok) throw new Error('Favorite response failed');

                if (button.classList.contains('product-card__favorite')) {
                    button.textContent = data.is_favorite ? '♥' : '♡';
                    button.setAttribute('aria-label', data.is_favorite ? 'Видалити з улюблених' : 'Додати до улюблених');
                } else {
                    button.textContent = data.is_favorite ? 'Видалити з улюблених' : 'Додати до улюблених';
                }

                showCartMessage(data.message);
            } catch (error) {
                showCartMessage('Не вдалося оновити улюблені товари. Спробуйте ще раз.', true);
                button.textContent = currentText;
            } finally {
                button.disabled = false;
            }
        });
    });

    const checkoutForm = document.querySelector('.checkout-form');
    if (checkoutForm) {
        const deliveryMethod = checkoutForm.querySelector('select[name="delivery_method"]');
        const cityInput = checkoutForm.querySelector('input[name="city"]');
        const addressInput = checkoutForm.querySelector('input[name="delivery_address"]');
        const cityRefInput = checkoutForm.querySelector('input[name="city_ref"]');
        const warehouseRefInput = checkoutForm.querySelector('input[name="warehouse_ref"]');
        const citySuggestions = document.getElementById('np-city-suggestions');
        const warehouseSuggestions = document.getElementById('np-warehouse-suggestions');
        const cityHelp = checkoutForm.querySelector('[data-np-city-help]');
        const warehouseHelp = checkoutForm.querySelector('[data-np-warehouse-help]');
        const endpoint = checkoutForm.dataset.npEndpoint;
        const cityRefsByName = new Map();

        function isNovaPoshtaDelivery() {
            return !deliveryMethod || deliveryMethod.value === 'nova_poshta';
        }

        function setHelp(element, message, isError = false) {
            if (!element) return;
            element.textContent = message;
            element.classList.toggle('form-help--error', isError);
        }

        function escapeHtml(value) {
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        function getCityRef() {
            return cityRefInput?.value || cityRefsByName.get(cityInput?.value.trim()) || '';
        }

        async function fetchNpSuggestions(type, query, cityRef) {
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('type', type);
            url.searchParams.set('q', query || '');
            if (cityRef) url.searchParams.set('city_ref', cityRef);

            try {
                const response = await fetch(url.toString(), {credentials: 'same-origin'});
                if (!response.ok) throw new Error('NP request failed');
                const json = await response.json();
                if (json.error) throw new Error(json.error);
                return Array.isArray(json.items) ? json.items : [];
            } catch (error) {
                const message = 'Не вдалося завантажити дані Нової пошти. Можна спробувати ще раз за кілька секунд.';
                setHelp(type === 'city' ? cityHelp : warehouseHelp, message, true);
                return [];
            }
        }

        function hideSuggestions(container) {
            if (!container) return;
            container.hidden = true;
            container.innerHTML = '';
        }

        function showSuggestions(container, items, onSelect) {
            if (!container || !items.length) {
                hideSuggestions(container);
                return;
            }

            container.innerHTML = items
                .slice(0, 10)
                .map((item, index) => {
                    const label = item.area ? `${item.name} — ${item.area}` : item.name;
                    return `<button type="button" class="np-suggestion" data-index="${index}" role="option">${escapeHtml(label)}</button>`;
                })
                .join('');
            container.hidden = false;

            container.querySelectorAll('.np-suggestion').forEach((button) => {
                button.addEventListener('mousedown', (event) => event.preventDefault());
                button.addEventListener('click', () => {
                    const item = items[Number(button.dataset.index)];
                    onSelect(item);
                    hideSuggestions(container);
                });
            });
        }

        if (cityInput && citySuggestions) {
            let cityTimer;
            cityInput.addEventListener('input', () => {
                clearTimeout(cityTimer);
                const query = cityInput.value.trim();
                if (cityRefInput) cityRefInput.value = '';
                if (warehouseRefInput) warehouseRefInput.value = '';
                if (addressInput) addressInput.value = '';
                hideSuggestions(warehouseSuggestions);
                if (!isNovaPoshtaDelivery()) return;
                cityTimer = window.setTimeout(async () => {
                    if (!query) {
                        hideSuggestions(citySuggestions);
                        return;
                    }
                    setHelp(cityHelp, 'Шукаємо місто у базі Нової пошти...');
                    const items = await fetchNpSuggestions('city', query);
                    cityRefsByName.clear();
                    items.forEach((item) => {
                        if (item.name && item.ref) cityRefsByName.set(item.name, item.ref);
                    });
                    setHelp(
                        cityHelp,
                        items.length ? 'Оберіть місто зі списку.' : 'Місто не знайдено. Уточніть назву.',
                        !items.length,
                    );
                    showSuggestions(citySuggestions, items, (item) => {
                        cityInput.value = item.name;
                        if (cityRefInput) cityRefInput.value = item.ref || '';
                        if (addressInput) addressInput.value = '';
                        if (warehouseRefInput) warehouseRefInput.value = '';
                        setHelp(cityHelp, item.area ? `Обрано: ${item.name}, ${item.area} область.` : `Обрано: ${item.name}.`);
                        setHelp(warehouseHelp, 'Почніть вводити номер або адресу відділення.');
                        hideSuggestions(warehouseSuggestions);
                    });
                }, 250);
            });

            cityInput.addEventListener('change', () => {
                if (cityRefInput) cityRefInput.value = cityRefsByName.get(cityInput.value.trim()) || '';
                if (warehouseRefInput) warehouseRefInput.value = '';
                if (addressInput) addressInput.value = '';
                hideSuggestions(warehouseSuggestions);
            });

            cityInput.addEventListener('blur', () => {
                window.setTimeout(() => hideSuggestions(citySuggestions), 150);
            });
        }

        if (addressInput && warehouseSuggestions) {
            let warehouseTimer;
            const loadWarehouses = async () => {
                if (!isNovaPoshtaDelivery()) return;
                const cityRef = getCityRef();
                const query = addressInput.value.trim();
                if (warehouseRefInput) warehouseRefInput.value = '';
                if (!cityRef) {
                    hideSuggestions(warehouseSuggestions);
                    setHelp(warehouseHelp, 'Спочатку оберіть місто зі списку Нової пошти.', true);
                    return;
                }
                setHelp(warehouseHelp, 'Шукаємо відділення...');
                const items = await fetchNpSuggestions('warehouse', query, cityRef);
                setHelp(
                    warehouseHelp,
                    items.length ? 'Оберіть відділення зі списку.' : 'Відділення не знайдено. Спробуйте інший запит.',
                    !items.length,
                );
                showSuggestions(warehouseSuggestions, items, (item) => {
                    addressInput.value = item.name;
                    if (warehouseRefInput) warehouseRefInput.value = item.ref || '';
                    setHelp(warehouseHelp, `Обрано: ${item.name}.`);
                });
            };

            addressInput.addEventListener('focus', loadWarehouses);
            addressInput.addEventListener('input', () => {
                clearTimeout(warehouseTimer);
                warehouseTimer = window.setTimeout(loadWarehouses, 250);
            });

            addressInput.addEventListener('blur', () => {
                window.setTimeout(() => hideSuggestions(warehouseSuggestions), 150);
            });
        }

        function updateDeliveryFields() {
            const method = deliveryMethod?.value;
            hideSuggestions(citySuggestions);
            hideSuggestions(warehouseSuggestions);

            if (method === 'pickup') {
                if (cityInput) {
                    cityInput.value = 'Самовивіз';
                    cityInput.disabled = true;
                }
                if (addressInput) {
                    addressInput.value = 'Самовивіз';
                    addressInput.disabled = true;
                }
                if (cityRefInput) cityRefInput.value = '';
                if (warehouseRefInput) warehouseRefInput.value = '';
                setHelp(cityHelp, 'Для самовивозу місто не потрібне.');
                setHelp(warehouseHelp, 'Ми узгодимо деталі самовивозу після замовлення.');
            } else {
                if (cityInput) cityInput.disabled = false;
                if (addressInput) addressInput.disabled = false;
                if (method === 'courier') {
                    if (cityRefInput) cityRefInput.value = '';
                    if (warehouseRefInput) warehouseRefInput.value = '';
                    setHelp(cityHelp, 'Вкажіть місто доставки.');
                    setHelp(warehouseHelp, 'Вкажіть адресу доставки кур’єром.');
                } else {
                    setHelp(cityHelp, 'Почніть вводити місто та оберіть варіант зі списку.');
                    setHelp(warehouseHelp, 'Спочатку оберіть місто, потім відділення або поштомат.');
                }
            }
        }

        deliveryMethod?.addEventListener('change', updateDeliveryFields);
        updateDeliveryFields();
    }

    /* Hero slider */
    const heroSlider = document.querySelector('[data-hero-slider]');
    if (!heroSlider) return;

    const slides = heroSlider.querySelectorAll('.hero-slide');
    const images = heroSlider.querySelectorAll('.hero-image');
    const indicators = heroSlider.querySelectorAll('.hero-indicators button');
    let current = 0;
    let timer;

    function goTo(index) {
        current = index;

        slides.forEach((slide, i) => slide.classList.toggle('is-active', i === index));
        images.forEach((img, i) => img.classList.toggle('is-active', i === index));
        indicators.forEach((btn, i) => btn.classList.toggle('is-active', i === index));
    }

    function next() {
        goTo((current + 1) % slides.length);
    }

    function startAutoplay() {
        timer = setInterval(next, 6000);
    }

    function resetAutoplay() {
        clearInterval(timer);
        startAutoplay();
    }

    indicators.forEach((btn) => {
        btn.addEventListener('click', () => {
            goTo(Number(btn.dataset.goTo));
            resetAutoplay();
        });
    });

    startAutoplay();
})();
