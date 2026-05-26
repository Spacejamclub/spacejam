# Telegram бот для курсов по сноуборду

Минимальный бот на `aiogram`, который показывает приветственное сообщение с картинкой и кнопками:

- `КУРС`
- `МОЙ ПРОГРЕСС`
- `ОПЛАТА`
- `ПОМОЩЬ`

## Запуск

1. Создать виртуальное окружение:

```bash
python3 -m venv .venv
```

2. Установить зависимости:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Запустить бота:

```bash
.venv/bin/python bot.py
```

## Настройки

Токен и ссылка на стартовую картинку лежат в `.env`.

## Контент курса

Структура уроков вынесена в:

- [content/courses.json](/Users/space_plug/Desktop/SPACE_JAM/content/courses.json)

В каждом уроке можно заполнять:

- `title`
- `text`
- `video_file_id`
- `video_url`
- `video_caption`

Если у урока есть `video_file_id`, бот отправит видео прямо в чат Telegram.
Если вместо этого заполнен `video_url`, бот покажет кнопку на внешнее видео.

## Оплата

В проекте есть Mini App оплаты с тремя кнопками выбора:

- `Оплата картой`
- `Telegram Stars`
- `Крипта`

Сейчас логика устроена так:

- Stars открывают Telegram invoice,
- карта ведет на внешний checkout через `CARD_PAYMENT_URL`,
- крипта открывает внешнюю ссылку `CRYPTO_PAYMENT_URL` или создает invoice через Crypto Pay API.

Что нужно заполнить в `.env`:

```bash
RUN_BOT=1
RUN_WEB=1
MINI_APP_HOST=127.0.0.1
MINI_APP_PORT=8080
WEB_HOST=127.0.0.1
WEB_PORT=8080
MINI_APP_URL=http://127.0.0.1:8080/miniapp
MINI_APP_DEV_MODE=1
PAYMENT_PROVIDER_TOKEN=381764678:TEST:12345
PAYMENT_LINK_URL=
CARD_PAYMENT_URL=
CARD_PROVIDER_TOKEN=
CARD_TITLE=Курс SPACEJAM
CARD_DESCRIPTION=Доступ к курсу SPACEJAM по сноуборду
CARD_PAYLOAD=spacejam-card
CARD_CURRENCY=RUB
CARD_AMOUNT=9900
PAYMENT_TITLE=Курс SPACEJAM
PAYMENT_DESCRIPTION=Доступ к курсу SPACEJAM по сноуборду
PAYMENT_PAYLOAD=spacejam-course
PAYMENT_CURRENCY=RUB
PAYMENT_AMOUNT=9900
CRYPTO_PAYMENT_URL=
CRYPTO_PAY_API_TOKEN=
CRYPTO_PAY_API_BASE=https://pay.crypt.bot/api
CRYPTO_INVOICE_FIAT=USD
CRYPTO_INVOICE_AMOUNT=24.99
CRYPTO_ACCEPTED_ASSETS=USDT,TON,BTC
```

Примечания:

- `RUN_BOT=1` и `RUN_WEB=1` запускают локально и polling-бота, и Mini App сервер.
- для отдельного хостинга Mini App используйте `RUN_BOT=0` и `RUN_WEB=1`.
- `MINI_APP_DEV_MODE=1` включает локальный preview Mini App вне Telegram, чтобы можно было тестировать интерфейс и генерацию ссылок до появления публичного домена.
- чтобы кнопка `ОПЛАТА` открывала именно Telegram Mini App, `MINI_APP_URL` должен быть публичным `https://...` URL. `http://127.0.0.1...` подходит только для локальной разработки.
- `CARD_PAYMENT_URL` включает внешний checkout по карте, а `CARD_PROVIDER_TOKEN` включает Telegram invoice для карт внутри card-сценария Mini App.
- `PAYMENT_AMOUNT` задается в минимальных единицах валюты: `9900` означает `99.00 RUB`.
- для Telegram Stars используйте `PAYMENT_CURRENCY=XTR`, тогда `PAYMENT_PROVIDER_TOKEN` можно оставить пустым.
- `PAYMENT_PROVIDER_TOKEN` выдается через `@BotFather` после подключения платежного провайдера.
- для цифровых товаров внутри Telegram основной способ оплаты должен быть `XTR`. Карта и крипта обычно используются как внешние сценарии оплаты.

## Cloudflare Tunnel

В проект уже подготовлены локальные файлы tunnel:

- [.cloudflared/config.yml](/Users/space_plug/Desktop/SPACE_JAM/.cloudflared/config.yml)
- [tools/start_cloudflare_tunnel.sh](/Users/space_plug/Desktop/SPACE_JAM/tools/start_cloudflare_tunnel.sh)

Быстрый запуск:

```bash
/Users/space_plug/Desktop/SPACE_JAM/tools/start_cloudflare_tunnel.sh
```

Если tunnel не поднимается и в логах видно таймауты до `198.41.x.x:7844`, значит текущая сеть режет исходящее соединение к Cloudflare edge. В таком случае tunnel нужно запускать из другой сети или после снятия сетевого ограничения.

## Render Deploy

Для боевого HTTPS без tunnel в проект добавлен [render.yaml](/Users/space_plug/Desktop/SPACE_JAM/render.yaml).

Схема запуска:

- локально проект работает как `RUN_BOT=1` и `RUN_WEB=1`,
- на Render поднимается только Mini App и его API как `RUN_BOT=0` и `RUN_WEB=1`,
- polling бота остаётся локально, поэтому конфликта `getUpdates` не будет.

Порядок действий:

1. Создать GitHub-репозиторий и загрузить туда проект.
2. В Render создать `Web Service` из этого репозитория.
3. Использовать настройки из `render.yaml` или указать вручную:

```bash
Build Command: pip install -r requirements.txt
Start Command: python bot.py
```

4. В переменных окружения Render указать как минимум:

```bash
BOT_TOKEN=...
RUN_BOT=0
RUN_WEB=1
MINI_APP_DEV_MODE=0
PAYMENT_CURRENCY=XTR
PAYMENT_AMOUNT=750
PAYMENT_TITLE=Курс SPACEJAM
PAYMENT_DESCRIPTION=Доступ к курсу SPACEJAM по сноуборду
PAYMENT_PAYLOAD=spacejam-course
CARD_PAYMENT_URL=
CARD_PROVIDER_TOKEN=
CRYPTO_PAYMENT_URL=
CRYPTO_PAY_API_TOKEN=
```

5. После первого деплоя Render даст публичный `onrender.com` URL.
6. На время проверки можно поставить его в `MINI_APP_URL`.
7. Затем в Render добавить custom domain `pay.spacejam.by`.
8. В DNS домена создать запись, которую подскажет Render, и нажать Verify.
9. После этого обновить `MINI_APP_URL` на `https://pay.spacejam.by/miniapp`.

Если захотите, следующим шагом можно добавить:

- каталог курсов,
- оплату через Telegram,
- хранение прогресса в базе данных,
- выдачу доступа после покупки,
- отдельные карточки уроков с видео и текстом.
