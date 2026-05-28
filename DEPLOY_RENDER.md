# Deploy SPACE_JAM Mini App to Render

Этот документ разделяет шаги на две части:

- что уже подготовлено в проекте автоматически,
- что нужно сделать руками в GitHub, Render и DNS.

## Уже готово

В проекте уже настроены:

- [render.yaml](/Users/space_plug/Desktop/SPACE_JAM/render.yaml)
- [render.env.example](/Users/space_plug/Desktop/SPACE_JAM/render.env.example)
- [.python-version](/Users/space_plug/Desktop/SPACE_JAM/.python-version)
- web-only режим в [bot.py](/Users/space_plug/Desktop/SPACE_JAM/bot.py)
- health endpoint: `/healthz`

Смысл схемы:

- на Render держим и бота, и Mini App в одном сервисе как `RUN_BOT=1` и `RUN_WEB=1`
- локально для проверки Mini App лучше запускать `RUN_BOT=0` и `RUN_WEB=1`

Это важно, потому что polling бота должен работать только в одном месте. Если бот уже крутится на Render, локальный запуск с `RUN_BOT=1` нужно остановить, иначе два процесса будут бороться за `getUpdates`.

## Что сделать руками

### 1. Создать GitHub-репозиторий

1. Создай новый пустой репозиторий на GitHub.
2. Назови его, например, `space-jam-miniapp` или `SPACE_JAM`.
3. Не добавляй туда `.gitignore` и `README`, потому что они уже есть в проекте.

### 2. Инициализировать git локально

Если в папке проекта ещё нет git-репозитория, выполни:

```bash
cd /Users/space_plug/Desktop/SPACE_JAM
git init -b main
git add .
git commit -m "Prepare SPACEJAM Mini App for Render"
```

Потом привяжи GitHub-репозиторий:

```bash
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

Пример `YOUR_GITHUB_REPO_URL`:

```bash
https://github.com/<your-username>/space-jam-miniapp.git
```

### 3. Создать сервис в Render

1. Открой [Render Dashboard](https://dashboard.render.com/).
2. Нажми `New +`.
3. Выбери `Web Service`.
4. Подключи GitHub-репозиторий с проектом.
5. Выбери репозиторий.

Render должен либо сам подхватить [render.yaml](/Users/space_plug/Desktop/SPACE_JAM/render.yaml), либо ты можешь заполнить поля вручную:

- Runtime: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Plan: `Starter ($7/month)`

В проекте в [render.yaml](/Users/space_plug/Desktop/SPACE_JAM/render.yaml) уже выставлен `plan: starter`, чтобы сервис не засыпал как free-инстанс.

### 4. Заполнить Environment Variables в Render

Открой [render.env.example](/Users/space_plug/Desktop/SPACE_JAM/render.env.example) и перенеси значения в Render.

Обязательно задать:

```bash
PYTHON_VERSION=3.11.11
BOT_TOKEN=...
RUN_BOT=1
RUN_WEB=1
MINI_APP_DEV_MODE=0
MINI_APP_URL=https://pay.spacejam.by/miniapp
PAYMENT_CURRENCY=XTR
PAYMENT_AMOUNT=750
PAYMENT_TITLE=Курс SPACEJAM
PAYMENT_DESCRIPTION=Доступ к курсу SPACEJAM по сноуборду
PAYMENT_PAYLOAD=spacejam-course
```

Остальные переменные платежей по карте и крипте можешь пока оставить пустыми или заполнить позже.

Если после деплоя нужно открыть проект локально без конфликта с боевым ботом, используй:

```bash
RUN_BOT=0 RUN_WEB=1 python bot.py
```

### 5. Дождаться первого деплоя

После создания сервиса Render выдаст временный URL вида:

```text
https://your-service-name.onrender.com
```

Проверь:

- `https://your-service-name.onrender.com/healthz`
- `https://your-service-name.onrender.com/miniapp`

Если `/healthz` отвечает JSON и `/miniapp` открывается, значит сервис поднялся правильно.

### 6. Подключить домен `pay.spacejam.by`

1. В Render открой сервис.
2. Перейди в `Settings`.
3. Найди раздел `Custom Domains`.
4. Нажми `Add Custom Domain`.
5. Введи:

```text
pay.spacejam.by
```

6. Render покажет, какую DNS-запись нужно создать.

Обычно это `CNAME` на `your-service-name.onrender.com`.

### 7. Создать DNS-запись

Сделай это у провайдера DNS для `spacejam.by`:

- Type: `CNAME`
- Name: `pay`
- Target/Value: `the-value-from-render`

Если DNS уже в Cloudflare:

1. Открой `DNS`.
2. Нажми `Add record`.
3. Выбери `CNAME`.
4. В `Name` напиши `pay`.
5. В `Target` вставь адрес, который показал Render.
6. Сохрани.

### 8. Verify в Render

Вернись в Render и нажми `Verify`.

Когда верификация пройдёт:

- `https://pay.spacejam.by/miniapp` начнёт открываться
- TLS/HTTPS Render выпустит автоматически

### 9. Обновить бот локально

Когда домен реально заработает, обнови локальный [.env](/Users/space_plug/Desktop/SPACE_JAM/.env):

```bash
MINI_APP_URL=https://pay.spacejam.by/miniapp
```

И перезапусти бота:

```bash
cd /Users/space_plug/Desktop/SPACE_JAM
.venv/bin/python bot.py
```

## Что можно проверить после деплоя

1. Открывается ли `https://pay.spacejam.by/healthz`
2. Открывается ли `https://pay.spacejam.by/miniapp`
3. Открывает ли кнопка `ОПЛАТА` Mini App внутри Telegram
4. Работает ли кнопка `Telegram Stars`

## Частые ошибки

### Render поднялся, но бот не отвечает

Проверь, что:

- `RUN_BOT=1`
- `RUN_WEB=1`
- `BOT_TOKEN` вставлен без префикса `BOT_TOKEN=`
- `MINI_APP_URL=https://pay.spacejam.by/miniapp`
- сервис слушает `PORT`, который даёт Render

И отдельно проверь, что локальный бот на ноутбуке остановлен, если тот же токен уже работает на Render.

### Кнопка `ОПЛАТА` в боте не открывает Mini App

Проверь, что в локальном `.env` уже стоит:

```bash
MINI_APP_URL=https://pay.spacejam.by/miniapp
```

И что бот был перезапущен после изменения.

### Домен не верифицируется в Render

Обычно это одно из трёх:

- DNS-запись ещё не распространилась
- значение `CNAME` введено не так, как просит Render
- у поддомена уже есть конфликтующая запись
