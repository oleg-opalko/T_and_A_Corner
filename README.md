# T&A Corner

Інтернет-магазин парфумів на Django.

## Вимоги

- Python 3.10+
- pip

## Швидкий старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py load_demo_data   # опційно: демо-товари з макету
python manage.py createsuperuser
python manage.py runserver
```

Перед запуском скопіюйте `.env.example` у `.env`. Для локальної розробки проєкт використовує SQLite.

Сайт: http://127.0.0.1:8000/  
Адмін-панель: http://127.0.0.1:8000/admin/

## Структура проєкту

```
config/                    # Налаштування Django
shop/                      # Каталог, бренди, парфуми
pages/                     # Статичні сторінки (головна, about, contact)
templates/
  base.html                # Базовий layout
  includes/                # header, footer, product_card
  pages/                   # home, about, contact, fragrance_guide
  shop/                    # catalog, category, perfume_detail
static/
  css/main.css             # Стилі за макетом
  js/main.js               # Hero-слайдер, мобільне меню
  images/                  # Статичні зображення
media/                     # Завантажені файли (товари, логотипи)
```

## Моделі

- **Category** — категорії парфумів
- **Brand** — бренди (з логотипом)
- **Perfume** — товари: назва, slug, бренд, категорія, опис, `product_type`, ціна, обʼєм (мл), зображення, `is_available`, `is_featured`

## Що додано

### Ініціалізація проєкту
- Django-проєкт `config` з `django-environ`, SQLite, uk-локаль, Europe/Kyiv
- Додатки `shop` (каталог) та `pages` (сторінки)
- `requirements.txt`: Django 5.1, django-environ, Pillow
- `.env.example` для локальних змінних середовища
- Міграції та адмін-панель для Category, Brand, Perfume

### Інтеграція макету дизайну
- **Header**: логотип T&A CORNER, навігація (Home, Collection, Fragrances, About Us, Fragrance Guide, Contact), іконки пошуку/акаунта, Cart (0)
- **Hero-секція**: слайдер з 3 слайдами, індикатори 01/02/03, CTA «Discover Collection»
- **Features bar**: 6 переваг (Premium Quality, Long Lasting, Exclusive Blends, Secure Payment, Free Shipping, Easy Returns)
- **Our Collection**: сітка з 4 продуктами, картки з типом (Extrait de Parfum) і ціною
- **Crafted With Passion**: блок «Every fragrance tells a story»
- **Promo**: Fragrance Guide + Gift Sets
- **Footer**: колонки Shop / Help / About, newsletter, соцмережі (Instagram, Facebook, TikTok)

### Стилі та інтерактив
- Шрифти: Cormorant Garamond (serif) + Jost (sans)
- Палітра: cream/beige фон, gold-акценти (`#b8956b`)
- Адаптив: hamburger-меню, 2-колонкова сітка продуктів на мобільному
- `static/js/main.js`: автопрокрутка hero-слайдера, мобільне меню

### Сторінки та маршрути
- `/` — головна
- `/catalog/` — каталог
- `/category/<slug>/` — категорія
- `/perfume/<slug>/` — картка товару
- `/about/`, `/contact/`, `/fragrance-guide/` — сторінки-заглушки
- `/admin/` — адмін-панель

### Додатково
- Поля моделі `product_type` та `is_featured` для відображення на головній
- Template tag `currency` для форматування ціни (`$180.00`)
- Команда `python manage.py load_demo_data` — 4 демо-товари з макету (Noir Éclat, Ambre Minuit, Velour Oud, Lunar Shadow)
- Placeholder-зображення через Unsplash (поки немає власних фото товарів)

## Що виправлено

- Помилка в `config/urls.py` — некоректний імпорт `settings` (синтаксична помилка після генерації проєкту)
- Помилка в `templates/includes/footer.html` — зламаний SVG-path для іконки TikTok
- Помилка в `templates/shop/perfume_detail.html` — некоректний закриваючий тег `</h1>`
- Оновлено `README`: прибрано застарілий пункт «Інтеграція макету дизайну» з «Наступних кроків» (макет уже інтегровано)

## Наступні кроки

- Підставити реальні фото замість placeholder-ів
- Кошик та оформлення замовлення
- Пошук і фільтри
- Fragrance Guide quiz
- Newsletter (збереження email у базу)

## Публікація на Wasmer Edge

Проєкт розпізнається Wasmer як Django-додаток за `manage.py` та `requirements.txt`.

1. Запуште репозиторій у GitHub або встановіть [Wasmer CLI](https://docs.wasmer.io/install/) і виконайте `wasmer login`.
2. Запустіть `wasmer deploy` у корені репозиторію та завершіть кроки CLI для створення застосунку.
3. У налаштуваннях застосунку Wasmer задайте секрет `SECRET_KEY` (згенеруйте окремий випадковий ключ) та `DEBUG=False`.
4. Під'єднайте керовану PostgreSQL-базу. Wasmer передає `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`; Django використовує їх автоматично.
5. Після першого деплою застосуйте міграції командою `python manage.py migrate` у терміналі застосунку, якщо платформа не виконала їх автоматично.

`collectstatic` обслуговується через WhiteNoise. SQLite годиться лише для локальної розробки; завантажені файли зберігаються в локальному `media/` і потребують окремого постійного сховища для production. SMTP, LiqPay і Nova Poshta credentials задаються як змінні середовища Wasmer, а не комітяться в репозиторій.
