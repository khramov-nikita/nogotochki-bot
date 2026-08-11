# Бот студии «Ноготочки»

Telegram-бот бьюти-студии «Ноготочки»: витрина услуг, корзина, предоплата через [ЮKassa](https://yookassa.ru/), ответы на FAQ и консультации через [DeepSeek](https://api-docs.deepseek.com/). Стек — Python 3, [aiogram](https://docs.aiogram.dev/) 3, SQLite.

После успешной оплаты слот по-прежнему согласует мастер.

## Возможности

- **Постоянное меню** — reply-клавиатура и команды BotFather (`/start`, `/help`, `/services`, `/cart`, `/order`)
- **Витрина услуг** — карточки из базы знаний с ценой и кнопкой «Добавить в корзину»
- **Корзина** — список услуг, сумма, «Убрать» и «Оформить заказ»
- **Заказы и оплата** — ссылка ЮKassa → возврат в чат → «Я оплатил» → проверка статуса
- **Частые вопросы / О студии / Запись** — тексты из базы знаний
- **Свободные вопросы** — DeepSeek по файлу базы знаний; история диалога в SQLite
- **Связаться с человеком** — контакт администратора из `ADMIN_*`

## Структура

```
bot.py                 # точка входа, set_my_commands, DI сервисов
config.py              # BOT_TOKEN, DeepSeek, ЮKassa, DATABASE_PATH
app/
  db/                  # SQLite: схема, connection, репозитории
  handlers/            # user, cart, orders
  keyboards/           # reply + inline клавиатуры
  data/knowledge.py    # услуги с price_kopecks, FAQ, тексты
  services/            # cart, orders, payments, deepseek, guardrails
data/bot.db            # создаётся при запуске (в .gitignore)
tests/                 # unittest: guardrails, корзина/заказы/оплата
```

## Быстрый старт

1. Создайте бота у [@BotFather](https://t.me/BotFather) и скопируйте токен.
2. Получите API-ключ на [platform.deepseek.com](https://platform.deepseek.com/).
3. Для реальной оплаты создайте магазин в [ЮKassa](https://yookassa.ru/) (можно тестовый) и возьмите `shopId` и секретный ключ.

4. Установите зависимости:

```bash
pip install -r requirements.txt
```

5. Настройте окружение:

```bash
copy .env.example .env
```

В `.env` укажите:

```
BOT_TOKEN=ваш_токен
DEEPSEEK_API_KEY=ваш_ключ_deepseek
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
ADMIN_NAME=Администратор студии
ADMIN_TELEGRAM=username_без_собачки
ADMIN_PHONE=+79991234567
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_секретный_ключ
YOOKASSA_RETURN_URL=https://t.me/your_bot?start=paid_{order_id}
PAYMENTS_MOCK=0
```

Если `YOOKASSA_*` пустые, бот автоматически включает мок платежей (`PAYMENTS_MOCK`) — удобно для локальной разработки без ключей.

6. Запустите бота:

```bash
python bot.py
```

В Telegram откройте бота и отправьте `/start`.

## Сценарий оплаты

1. «Услуги и цены» → «Добавить в корзину».
2. «Корзина» → «Оформить заказ».
3. «Оплатить» → бот присылает ссылку ЮKassa.
4. Оплатите (в sandbox — [тестовой картой ЮKassa](https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing)).
5. Вернитесь в чат → «Я оплатил» → бот запрашивает статус платежа.

Проверки:

- успешная оплата тестовой картой → статус `succeeded`, заказ `paid`;
- «Я оплатил» без оплаты → бот **не** подтверждает заказ.

Граничные случаи корзины:

- «Оформить заказ» при пустой корзине → заказ не создаётся;
- двойное нажатие «Оформить заказ» → остаётся один заказ `awaiting_payment`.

## База данных

SQLite (`data/bot.db` или `DATABASE_PATH`):

| Таблица | Назначение |
|--------|------------|
| `users` | клиенты Telegram |
| `dialog_messages` | история диалога с ИИ (последние 20) |
| `cart_items` | корзина |
| `orders` / `order_items` | заказы и снимок позиций |

## Тесты

```bash
python -m unittest discover -s tests -v
```

Покрывают guardrails, корзину (add/remove/total), пустой checkout, двойной checkout, статусы оплаты `succeeded` / `pending`, сохранение истории диалога.

## Guardrails

Свободные ответы защищены ограничителями:

- жёсткие правила в системном промпте;
- детектор промпт-инъекций на входе;
- обёртка пользовательского текста как данных;
- фильтр утечек на выходе модели.

```bash
python scripts/check_prompt_injections.py
```

## Документы

- [Паспорт бота](claude.md)
- [База знаний студии](База%20знаний%20для%20бота%20бьюти-студии%20«Ноготочки».md)
- [Шаблон паспорта](Шаблон%20паспорта%20бота.md)

## Gitflow

- `master` — стабильная линия
- `develop` — интеграция
- `feature/*` — задачи (текущая: `feature/cart-orders-payments`)
