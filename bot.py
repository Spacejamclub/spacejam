import asyncio
import html
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl

from aiohttp import ClientSession, web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    MenuButtonDefault,
    MenuButtonWebApp,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MINIAPP_DIR = BASE_DIR / "miniapp"
DATA_DIR = BASE_DIR / "data"
CONTENT_DIR = BASE_DIR / "content"
STATE_PATH = DATA_DIR / "course_state.json"
COURSES_PATH = CONTENT_DIR / "courses.json"
BOT_TOKEN = os.getenv("BOT_TOKEN")
WELCOME_IMAGE_PATH = os.getenv("WELCOME_IMAGE_PATH")
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL")
MINI_APP_HOST = os.getenv("MINI_APP_HOST", "127.0.0.1").strip()
MINI_APP_PORT = int(os.getenv("MINI_APP_PORT", "8080").strip())
MINI_APP_URL = os.getenv("MINI_APP_URL", f"http://{MINI_APP_HOST}:{MINI_APP_PORT}/miniapp").strip()
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip()
PAYMENT_LINK_URL = os.getenv("PAYMENT_LINK_URL", "").strip()
CARD_PAYMENT_URL = os.getenv("CARD_PAYMENT_URL", PAYMENT_LINK_URL).strip()
PAYMENT_TITLE = os.getenv("PAYMENT_TITLE", "Курс SPACEJAM").strip()
PAYMENT_DESCRIPTION = os.getenv(
    "PAYMENT_DESCRIPTION",
    "Доступ к курсу SPACEJAM по сноуборду",
).strip()
PAYMENT_PAYLOAD = os.getenv("PAYMENT_PAYLOAD", "spacejam-course").strip()
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "RUB").strip().upper()
CARD_PROVIDER_TOKEN = os.getenv("CARD_PROVIDER_TOKEN", PAYMENT_PROVIDER_TOKEN).strip()
CARD_TITLE = os.getenv("CARD_TITLE", PAYMENT_TITLE).strip()
CARD_DESCRIPTION = os.getenv("CARD_DESCRIPTION", PAYMENT_DESCRIPTION).strip()
CARD_PAYLOAD = os.getenv("CARD_PAYLOAD", "spacejam-card").strip()
CARD_CURRENCY = os.getenv("CARD_CURRENCY", "RUB").strip().upper()
PROMO_CODE = os.getenv("PROMO_CODE", "space").strip()
CRYPTO_PAYMENT_URL = os.getenv("CRYPTO_PAYMENT_URL", "").strip()
CRYPTO_PAY_API_TOKEN = os.getenv("CRYPTO_PAY_API_TOKEN", "").strip()
CRYPTO_PAY_API_BASE = os.getenv("CRYPTO_PAY_API_BASE", "https://pay.crypt.bot/api").strip().rstrip("/")
CRYPTO_INVOICE_FIAT = os.getenv("CRYPTO_INVOICE_FIAT", "USD").strip().upper()
CRYPTO_INVOICE_AMOUNT = os.getenv("CRYPTO_INVOICE_AMOUNT", "24.99").strip()
CRYPTO_ACCEPTED_ASSETS = os.getenv("CRYPTO_ACCEPTED_ASSETS", "USDT,TON,BTC").strip()
active_panels: dict[int, int] = {}
keyboard_hosts: dict[int, int] = {}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")


def read_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip() in {"1", "true", "TRUE", "yes", "on"}


def read_positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        logging.warning("%s=%r is invalid, fallback to %s", name, raw_value, default)
        return default

    if value <= 0:
        logging.warning("%s=%r must be positive, fallback to %s", name, raw_value, default)
        return default

    return value


PAYMENT_AMOUNT = read_positive_int_env("PAYMENT_AMOUNT", 9900)
CARD_AMOUNT = read_positive_int_env("CARD_AMOUNT", 9900)
MINI_APP_DEV_MODE = read_bool_env("MINI_APP_DEV_MODE", False)
RUN_BOT = read_bool_env("RUN_BOT", True)
RUN_WEB = read_bool_env("RUN_WEB", True)
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0" if os.getenv("PORT") else MINI_APP_HOST).strip()
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", str(MINI_APP_PORT))).strip())

COURSE_TEXT = """
<b>Курс по сноуборду</b>

Выберите направление и откройте нужное занятие.
""".strip()

PROGRESS_TEXT = """
<b>Мой прогресс</b>

Пока прогресс считается в демо-режиме.
Когда добавим базу данных, здесь можно будет видеть:
- пройденные уроки,
- просмотренные видео,
- процент завершения курса,
- достижения ученика.
""".strip()

PAYMENT_TEXT = """
<b>Оплата</b>

Кнопка <b>ОПЛАТА</b> открывает Mini App с тремя вариантами:
- карта,
- Telegram Stars,
- крипта.
""".strip()

HELP_TEXT = """
<b>Помощь</b>

Если вам нужна помощь:
- нажмите нужный раздел в меню,
- вернитесь в начало командой /start,
- напишите администратору: @your_support
""".strip()

FAQ_TEXT = """
<b>Часто задаваемые вопросы</b>

--------------------
<b>КАК МОЖНО НАУЧИТЬСЯ КАТАТЬСЯ ОНЛАЙН?</b>

Удивительно, но можно научиться кататься даже без видеоуроков и инструктора. Вопрос - насколько это будет эффективно?

Наше обучение - это пошаговая система упражнений, дополненных графикой, подробными объяснениями и стоп-кадрами. После просмотра видео постепенно отрабатывай каждое упражнение на склоне.

А чтобы еще лучше видеть свои ошибки, попроси друга снять твое катание со стороны - так ты заметишь все неточности в технике.

--------------------
<b>ПОЧЕМУ ЭТО ПЛАТНО? ЕСТЬ МНОГО БЕСПЛАТНЫХ ВИДЕОУРОКОВ.</b>

Мы не спорим. Бесплатный бывает даже сыр... в мышеловке.

А если серьезно - наш курс построен на большом практическом опыте школы, профессионально снят, смонтирован и озвучен, а уроки собраны в удобную пошаговую систему.

Профессиональный продукт не может быть бесплатным. Посмотрев наши уроки в свободном доступе, можно самому убедиться в его преимуществах.

--------------------
<b>ГДЕ ГАРАНТИЯ, ЧТО Я НАУЧУСЬ?</b>

В наше время на абсолютные гарантии рассчитывать сложно. Но мы точно можем гарантировать стабильный доступ к обучению: тренировка не сорвется из-за болезни тренера, не нужно платить за пропуск или договариваться о переносе, а заниматься можно в любом месте и в удобное время.

Со своей стороны тебе важно регулярно практиковаться, внимательно разбирать ошибки и качественно отрабатывать каждый урок. При таком подходе прогресс обязательно будет, и результат не заставит себя ждать.

--------------------
<b>ДЛЯ КОГО ПОДОЙДУТ ЭТИ КУРСЫ?</b>

Для всех - от начинающего райдера до инструктора. Главное понять свои цели и выстроить программу обучения, исходя из них.

--------------------
<b>ЭТО ТОЛЬКО ОНЛАЙН?</b>

Нет, SPACEJAM - это офлайн-школа с дополнительным онлайн-форматом. Бот и курсы здесь - это удобное продолжение обучения, которое помогает заниматься в своем темпе и возвращаться к материалу в любое время.

--------------------
""".strip()

WELCOME_TEXT = (
    "<b>Добро пожаловать в SPACEJAM!</b>\n\n"
    "SPACEJAM - это школа сноубординга и онлайн-уроки для прогресса "
    "в своем темпе.\n\n"
    "Здесь можно разобрать базу, повороты, контроль доски, технику "
    "и трюки для склона и парка.\n\n"
    "Выберите нужный раздел в меню ниже."
)

DEFAULT_TRACKS = [
    ("basics", "Основы", "База, стойка, баланс и контроль доски."),
    ("carving", "Карвинг", "Контроль дуги, закантовка и чистые повороты."),
    ("flat_freestyle", "Флэт фристайл", "Трюки на плоскости, координация и контроль доски."),
    ("park", "Парк", "Подготовка к фигурам, прыжки и парк."),
]
DEFAULT_LESSONS_PER_TRACK = 15


def build_default_course_catalog() -> dict[str, Any]:
    return {
        "tracks": [
            {
                "key": key,
                "title": title,
                "description": description,
                "lessons": [
                    {
                        "number": lesson_number,
                        "title": f"Урок {lesson_number}",
                        "text": "Добавьте описание урока и ключевые тезисы.",
                        "video_file_id": "",
                        "video_url": "",
                        "video_caption": "",
                    }
                    for lesson_number in range(1, DEFAULT_LESSONS_PER_TRACK + 1)
                ],
            }
            for key, title, description in DEFAULT_TRACKS
        ]
    }


def normalize_course_catalog(raw_catalog: Any) -> dict[str, Any]:
    if not isinstance(raw_catalog, dict):
        return build_default_course_catalog()

    raw_tracks = raw_catalog.get("tracks")
    if not isinstance(raw_tracks, list) or not raw_tracks:
        return build_default_course_catalog()

    normalized_tracks = []
    for raw_track in raw_tracks:
        if not isinstance(raw_track, dict):
            continue

        track_key = str(raw_track.get("key", "")).strip()
        track_title = str(raw_track.get("title", "")).strip()
        if not track_key or not track_title:
            continue

        track_description = str(raw_track.get("description", "")).strip()
        raw_lessons = raw_track.get("lessons")
        if not isinstance(raw_lessons, list):
            raw_lessons = []

        normalized_lessons = []
        for index, raw_lesson in enumerate(raw_lessons, start=1):
            if not isinstance(raw_lesson, dict):
                continue

            lesson_number_raw = raw_lesson.get("number", index)
            try:
                lesson_number = int(lesson_number_raw)
            except (TypeError, ValueError):
                lesson_number = index

            normalized_lessons.append(
                {
                    "number": lesson_number,
                    "title": str(raw_lesson.get("title", f"Урок {lesson_number}")).strip() or f"Урок {lesson_number}",
                    "text": str(raw_lesson.get("text", "")).strip(),
                    "video_file_id": str(raw_lesson.get("video_file_id", "")).strip(),
                    "video_url": str(raw_lesson.get("video_url", "")).strip(),
                    "video_caption": str(raw_lesson.get("video_caption", "")).strip(),
                }
            )

        normalized_lessons.sort(key=lambda lesson: lesson["number"])
        normalized_tracks.append(
            {
                "key": track_key,
                "title": track_title,
                "description": track_description,
                "lessons": normalized_lessons,
            }
        )

    if not normalized_tracks:
        return build_default_course_catalog()

    return {"tracks": normalized_tracks}


def load_course_catalog() -> dict[str, Any]:
    if not COURSES_PATH.exists():
        default_catalog = build_default_course_catalog()
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        with COURSES_PATH.open("w", encoding="utf-8") as file:
            json.dump(default_catalog, file, ensure_ascii=False, indent=2)
        return default_catalog

    try:
        with COURSES_PATH.open("r", encoding="utf-8") as file:
            raw_catalog = json.load(file)
    except (OSError, json.JSONDecodeError):
        logging.exception("Failed to load course catalog from %s", COURSES_PATH)
        return build_default_course_catalog()

    return normalize_course_catalog(raw_catalog)


COURSE_CATALOG = load_course_catalog()
TRACKS = {track["key"]: track["title"] for track in COURSE_CATALOG["tracks"]}
TOTAL_LESSONS = sum(len(track["lessons"]) for track in COURSE_CATALOG["tracks"])


def get_track_entries() -> list[dict[str, Any]]:
    return COURSE_CATALOG["tracks"]


def get_track_entry(track_key: str) -> Optional[dict[str, Any]]:
    for track in get_track_entries():
        if track["key"] == track_key:
            return track
    return None


def get_track_lessons(track_key: str) -> list[dict[str, Any]]:
    track = get_track_entry(track_key)
    if not track:
        return []
    return track["lessons"]


def get_lesson_entry(track_key: str, lesson_number: int) -> Optional[dict[str, Any]]:
    for lesson in get_track_lessons(track_key):
        if lesson["number"] == lesson_number:
            return lesson
    return None


def get_user_key(user_id: int) -> str:
    return str(user_id)


def load_course_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"users": {}}

    try:
        with STATE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        logging.exception("Failed to load course state from %s", STATE_PATH)
        return {"users": {}}

    if not isinstance(data, dict):
        return {"users": {}}

    users = data.get("users")
    if not isinstance(users, dict):
        data["users"] = {}

    return data


def save_course_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
    temp_path.replace(STATE_PATH)


def get_user_record(user_id: int) -> dict[str, Any]:
    state = load_course_state()
    return state.get("users", {}).get(get_user_key(user_id), {})


def ensure_user_record(state: dict[str, Any], user_id: int) -> dict[str, Any]:
    users = state.setdefault("users", {})
    return users.setdefault(
        get_user_key(user_id),
        {
            "has_access": False,
            "payments": [],
            "opened_lessons": [],
            "completed_lessons": [],
            "activated_at": None,
            "last_lesson": None,
        },
    )


def user_has_course_access(user_id: int) -> bool:
    return bool(get_user_record(user_id).get("has_access"))


def build_lesson_code(track_key: str, lesson_number: int) -> str:
    return f"{track_key}:{lesson_number}"


def lesson_sort_key(lesson_code: str) -> tuple[int, int]:
    track_key, lesson_number_raw = lesson_code.split(":", 1)
    try:
        track_index = list(TRACKS.keys()).index(track_key)
    except ValueError:
        track_index = len(TRACKS)
    return (track_index, int(lesson_number_raw))


def grant_course_access(
    user_id: int,
    *,
    amount: int,
    currency: str,
    telegram_charge_id: str,
    provider_charge_id: str,
    payload: str,
) -> None:
    state = load_course_state()
    record = ensure_user_record(state, user_id)
    record["has_access"] = True
    if not record.get("activated_at"):
        record["activated_at"] = int(time.time())

    payments = record.setdefault("payments", [])
    already_exists = any(payment.get("telegram_charge_id") == telegram_charge_id for payment in payments)
    if not already_exists:
        payments.append(
            {
                "amount": amount,
                "currency": currency,
                "payload": payload,
                "telegram_charge_id": telegram_charge_id,
                "provider_charge_id": provider_charge_id,
                "paid_at": int(time.time()),
            }
        )

    save_course_state(state)


def grant_course_access_via_promo(user_id: int, promo_code: str) -> bool:
    state = load_course_state()
    record = ensure_user_record(state, user_id)
    promo_code_normalized = promo_code.strip().casefold()
    promo_activations = record.setdefault("promo_activations", [])

    already_used = any(item.get("code", "").casefold() == promo_code_normalized for item in promo_activations)
    had_access = bool(record.get("has_access"))
    record["has_access"] = True
    if not record.get("activated_at"):
        record["activated_at"] = int(time.time())

    if not already_used:
        promo_activations.append(
            {
                "code": promo_code,
                "activated_at": int(time.time()),
            }
        )

    save_course_state(state)
    return not had_access


def register_lesson_open(user_id: int, track_key: str, lesson_number: int) -> None:
    state = load_course_state()
    record = ensure_user_record(state, user_id)
    lesson_code = build_lesson_code(track_key, lesson_number)

    opened_lessons = set(record.get("opened_lessons", []))
    opened_lessons.add(lesson_code)
    record["opened_lessons"] = sorted(opened_lessons, key=lesson_sort_key)

    completed_lessons = set(record.get("completed_lessons", []))
    completed_lessons.add(lesson_code)
    record["completed_lessons"] = sorted(completed_lessons, key=lesson_sort_key)
    record["last_lesson"] = lesson_code

    save_course_state(state)


def format_timestamp(timestamp: Optional[int]) -> str:
    if not timestamp:
        return "—"

    return time.strftime("%d.%m.%Y %H:%M", time.localtime(timestamp))


def build_locked_course_text() -> str:
    return (
        "<b>Курс пока закрыт</b>\n\n"
        "Сначала открой доступ через оплату, и после этого здесь появятся направления и уроки."
    )


def build_locked_course_keyboard() -> InlineKeyboardMarkup:
    if mini_app_launch_ready():
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть оплату", web_app=WebAppInfo(url=MINI_APP_URL))],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплата пока недоступна", callback_data="payment:unavailable")],
        ]
    )


def build_progress_text(user_id: int) -> str:
    record = get_user_record(user_id)
    has_access = bool(record.get("has_access"))
    activated_at = format_timestamp(record.get("activated_at"))
    completed_lessons = record.get("completed_lessons", [])
    completed_count = len(completed_lessons)
    progress_percent = int((completed_count / TOTAL_LESSONS) * 100) if TOTAL_LESSONS else 0
    last_lesson = record.get("last_lesson")

    if last_lesson:
        track_key, lesson_number_raw = last_lesson.split(":", 1)
        last_lesson_label = f"{TRACKS.get(track_key, track_key)} · урок {lesson_number_raw}"
    else:
        last_lesson_label = "Пока ни один урок не открыт"

    if not has_access:
        return (
            "<b>Мой прогресс</b>\n\n"
            "<b>Доступ:</b> пока не открыт\n"
            f"<b>Прогресс:</b> 0 из {TOTAL_LESSONS}\n"
            "<b>Следующий шаг:</b> открыть оплату и получить доступ к курсу"
        )

    return (
        "<b>Мой прогресс</b>\n\n"
        "<b>Доступ:</b> открыт\n"
        f"<b>Активирован:</b> {activated_at}\n"
        f"<b>Пройдено:</b> {completed_count} из {TOTAL_LESSONS}\n"
        f"<b>Процент:</b> {progress_percent}%\n"
        f"<b>Последний урок:</b> {last_lesson_label}"
    )


def build_course_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=track["title"], callback_data=f"track:{track['key']}")]
        for track in get_track_entries()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_track_text(track_key: str) -> str:
    track = get_track_entry(track_key)
    if not track:
        return "<b>Раздел не найден</b>"

    lines = [f"<b>{html.escape(track['title'])}</b>"]
    if track.get("description"):
        lines.append("")
        lines.append(html.escape(track["description"]))

    lines.append("")
    lines.append(f"Выберите занятие из {len(track['lessons'])} уроков:")
    return "\n".join(lines)


def build_lessons_keyboard(track_key: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    lessons = get_track_lessons(track_key)
    for lesson in lessons:
        lesson_number = lesson["number"]
        row.append(
            InlineKeyboardButton(
                text=str(lesson_number),
                callback_data=f"lesson:{track_key}:{lesson_number}",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="Назад к направлениям", callback_data="course:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_lesson_keyboard(track_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад к занятиям", callback_data=f"track:{track_key}")],
            [InlineKeyboardButton(text="Назад к направлениям", callback_data="course:menu")],
        ]
    )


def build_lesson_text(track_key: str, lesson_number: int) -> str:
    track = get_track_entry(track_key)
    lesson = get_lesson_entry(track_key, lesson_number)
    if not track or not lesson:
        return "<b>Урок не найден</b>"

    lines = [
        f"<b>{html.escape(track['title'])}</b>",
        f"<b>Урок {lesson_number}. {html.escape(lesson['title'])}</b>",
    ]

    lesson_text = lesson.get("text")
    if lesson_text:
        lines.extend(["", html.escape(lesson_text)])

    if lesson.get("video_file_id"):
        lines.extend(["", "Видео прикреплено ниже в чате."])
    elif lesson.get("video_url"):
        lines.extend(["", "Для этого урока есть отдельная ссылка на видео ниже."])
    else:
        lines.extend(["", "Видео для этого урока можно добавить позже через video_file_id или video_url."])

    return "\n".join(lines)


def build_lesson_video_caption(track_key: str, lesson: dict[str, Any]) -> str:
    track = get_track_entry(track_key)
    track_title = track["title"] if track else track_key
    title = lesson.get("title") or f"Урок {lesson['number']}"
    return f"{track_title} · урок {lesson['number']}\n{title}"


def mini_app_ready() -> bool:
    return bool(MINI_APP_URL)


def mini_app_launch_ready() -> bool:
    return MINI_APP_URL.startswith("https://")


def mini_app_dev_mode() -> bool:
    return MINI_APP_DEV_MODE


def build_main_keyboard() -> ReplyKeyboardMarkup:
    payment_button = KeyboardButton(text="ОПЛАТА")
    if mini_app_launch_ready():
        payment_button = KeyboardButton(text="ОПЛАТА", web_app=WebAppInfo(url=MINI_APP_URL))

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="КУРС"), KeyboardButton(text="МОЙ ПРОГРЕСС")],
            [payment_button, KeyboardButton(text="ПОМОЩЬ")],
            [KeyboardButton(text="ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ")],
        ],
        is_persistent=True,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )


def payment_provider_ready() -> bool:
    return PAYMENT_CURRENCY == "XTR" or bool(PAYMENT_PROVIDER_TOKEN)


def payment_ready() -> bool:
    return payment_provider_ready() and PAYMENT_AMOUNT > 0


def build_payment_prices() -> list[LabeledPrice]:
    return [LabeledPrice(label=PAYMENT_TITLE, amount=PAYMENT_AMOUNT)]


def format_payment_amount(amount: int, currency: str) -> str:
    if currency == "XTR":
        return f"{amount} Stars"

    return f"{amount / 100:.2f} {currency}"


def card_payment_ready() -> bool:
    return bool(CARD_PAYMENT_URL or CARD_PROVIDER_TOKEN)


def crypto_payment_ready() -> bool:
    return bool(CRYPTO_PAYMENT_URL or CRYPTO_PAY_API_TOKEN)


def build_mini_app_policy_note() -> str:
    return (
        "Для цифровых товаров внутри Telegram основной вариант оплаты — Stars. "
        "Карта и крипта обычно используются как внешние сценарии."
    )


def build_dev_banner_text() -> str:
    return (
        "Локальный dev-режим: Mini App открыт вне Telegram и использует preview-поток. "
        "Для боевого запуска по кнопке ОПЛАТА понадобится публичный HTTPS URL."
    )


def build_payment_text() -> str:
    lines = [
        PAYMENT_TEXT,
        "",
        f"<b>Товар:</b> {PAYMENT_TITLE}",
        f"<b>Валюта:</b> {PAYMENT_CURRENCY}",
        f"<b>Сумма:</b> {format_payment_amount(PAYMENT_AMOUNT, PAYMENT_CURRENCY)}",
    ]

    if mini_app_launch_ready():
        lines.extend(
            [
                "",
                "Нажмите кнопку <b>ОПЛАТА</b> в нижнем меню.",
                "Откроется Mini App с тремя кнопками выбора: карта, Stars и крипта.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Mini App уже собран локально, но для открытия из Telegram нужен публичный HTTPS URL.",
                "Как только MINI_APP_URL будет вида <b>https://...</b>, кнопка <b>ОПЛАТА</b> сможет открывать Mini App напрямую.",
            ]
        )

    return "\n".join(lines)


def build_payment_keyboard() -> InlineKeyboardMarkup:
    if mini_app_launch_ready():
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть Mini App оплаты", web_app=WebAppInfo(url=MINI_APP_URL))],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплата пока недоступна", callback_data="payment:unavailable")],
        ]
    )


def build_payment_kwargs(payload: Optional[str] = None) -> dict:
    provider_token = "" if PAYMENT_CURRENCY == "XTR" else PAYMENT_PROVIDER_TOKEN
    return {
        "title": PAYMENT_TITLE,
        "description": PAYMENT_DESCRIPTION,
        "payload": payload or PAYMENT_PAYLOAD,
        "currency": PAYMENT_CURRENCY,
        "prices": build_payment_prices(),
        "provider_token": provider_token,
    }


def build_card_payment_kwargs(payload: Optional[str] = None) -> dict:
    return {
        "title": CARD_TITLE,
        "description": CARD_DESCRIPTION,
        "payload": payload or CARD_PAYLOAD,
        "currency": CARD_CURRENCY,
        "prices": [LabeledPrice(label=CARD_TITLE, amount=CARD_AMOUNT)],
        "provider_token": CARD_PROVIDER_TOKEN,
    }


def build_user_payment_payload(base_payload: str, user_id: Optional[int] = None) -> str:
    suffix_parts = [str(int(time.time()))]
    if user_id is not None:
        suffix_parts.insert(0, str(user_id))
    return f"{base_payload}:{':'.join(suffix_parts)}"


def validate_webapp_init_data(
    init_data: str,
    *,
    allow_dev_bypass: bool = False,
    max_age_seconds: int = 3600,
) -> dict:
    if not init_data:
        if allow_dev_bypass and mini_app_dev_mode():
            return {"fields": {}, "user": None, "dev_bypass": True}

        raise web.HTTPUnauthorized(text=json.dumps({"ok": False, "error": "Откройте оплату из Telegram"}))

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise web.HTTPUnauthorized(text=json.dumps({"ok": False, "error": "Telegram hash не найден"}))

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise web.HTTPUnauthorized(text=json.dumps({"ok": False, "error": "Не удалось проверить Telegram initData"}))

    auth_date_raw = fields.get("auth_date")
    if auth_date_raw:
        try:
            auth_date = int(auth_date_raw)
        except ValueError as exc:
            raise web.HTTPUnauthorized(text=json.dumps({"ok": False, "error": "Некорректный auth_date"})) from exc

        if time.time() - auth_date > max_age_seconds:
            raise web.HTTPUnauthorized(text=json.dumps({"ok": False, "error": "Сессия оплаты устарела"}))

    user_raw = fields.get("user")
    user = json.loads(user_raw) if user_raw else None
    return {"fields": fields, "user": user, "dev_bypass": False}


async def create_crypto_invoice_link(user_id: Optional[int] = None) -> str:
    if CRYPTO_PAYMENT_URL:
        return CRYPTO_PAYMENT_URL

    if not CRYPTO_PAY_API_TOKEN:
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Крипто-оплата ещё не настроена"}))

    payload = {
        "currency_type": "fiat",
        "fiat": CRYPTO_INVOICE_FIAT,
        "amount": CRYPTO_INVOICE_AMOUNT,
        "accepted_assets": CRYPTO_ACCEPTED_ASSETS,
        "description": PAYMENT_DESCRIPTION,
        "payload": build_user_payment_payload(PAYMENT_PAYLOAD, user_id),
    }

    async with ClientSession() as session:
        async with session.post(
            f"{CRYPTO_PAY_API_BASE}/createInvoice",
            headers={"Crypto-Pay-API-Token": CRYPTO_PAY_API_TOKEN},
            json=payload,
        ) as response:
            data = await response.json()

    if not data.get("ok"):
        raise web.HTTPBadRequest(
            text=json.dumps({"ok": False, "error": data.get("error", "Crypto Pay не принял запрос")})
        )

    result = data["result"]
    return result.get("mini_app_invoice_url") or result.get("bot_invoice_url")


def build_miniapp_config() -> dict:
    stars_enabled = payment_ready()
    card_enabled = card_payment_ready()
    crypto_enabled = crypto_payment_ready()
    promo_enabled = bool(PROMO_CODE)
    dev_mode_enabled = mini_app_dev_mode()

    return {
        "title": PAYMENT_TITLE,
        "description": PAYMENT_DESCRIPTION,
        "display_price": format_payment_amount(PAYMENT_AMOUNT, PAYMENT_CURRENCY),
        "policy_note": build_mini_app_policy_note(),
        "dev_mode": dev_mode_enabled,
        "dev_banner": build_dev_banner_text() if dev_mode_enabled else "",
        "stars_enabled": stars_enabled,
        "stars_note": (
            "Нативная оплата внутри Telegram"
            if stars_enabled and not dev_mode_enabled
            else "Локальный preview Stars включён"
            if stars_enabled and dev_mode_enabled
            else "Stars пока не готовы"
        ),
        "card_enabled": card_enabled,
        "card_note": (
            f"Откроем внешний checkout на {format_payment_amount(CARD_AMOUNT, CARD_CURRENCY)}"
            if CARD_PAYMENT_URL
            else f"Откроем Telegram invoice на {format_payment_amount(CARD_AMOUNT, CARD_CURRENCY)}"
            if CARD_PROVIDER_TOKEN
            else "Ссылка или provider token для оплаты картой пока не настроены"
        ),
        "card_url": CARD_PAYMENT_URL or None,
        "crypto_enabled": crypto_enabled,
        "crypto_note": (
            "Откроем счёт через Crypto Bot"
            if CRYPTO_PAY_API_TOKEN
            else "Готово к внешней крипто-ссылке" if CRYPTO_PAYMENT_URL else "Крипто-счёт ещё не подключён"
        ),
        "crypto_url": CRYPTO_PAYMENT_URL or None,
        "promo_enabled": promo_enabled,
    }


async def miniapp_page_handler(_: web.Request) -> web.FileResponse:
    response = web.FileResponse(MINIAPP_DIR / "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


async def miniapp_styles_handler(_: web.Request) -> web.FileResponse:
    response = web.FileResponse(MINIAPP_DIR / "styles.css")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


async def miniapp_script_handler(_: web.Request) -> web.FileResponse:
    response = web.FileResponse(MINIAPP_DIR / "app.js")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


async def healthz_handler(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "ok": True,
            "run_bot": RUN_BOT,
            "run_web": RUN_WEB,
            "mini_app_url": MINI_APP_URL,
        }
    )


async def miniapp_config_handler(_: web.Request) -> web.Response:
    return web.json_response(build_miniapp_config())


async def miniapp_stars_link_handler(request: web.Request) -> web.Response:
    if not payment_ready():
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Stars-оплата ещё не настроена"}))

    request_data = await request.json()
    init_data = request_data.get("initData", "")
    validated = validate_webapp_init_data(init_data, allow_dev_bypass=True)
    user = validated.get("user") or {}
    payload = build_user_payment_payload(PAYMENT_PAYLOAD, user.get("id"))
    bot: Bot = request.app["bot"]
    invoice_url = await bot.create_invoice_link(**build_payment_kwargs(payload=payload))
    return web.json_response({"ok": True, "url": invoice_url, "dev_bypass": validated.get("dev_bypass", False)})


async def miniapp_card_link_handler(request: web.Request) -> web.Response:
    if CARD_PAYMENT_URL:
        return web.json_response({"ok": True, "url": CARD_PAYMENT_URL, "external": True, "dev_bypass": False})

    if not CARD_PROVIDER_TOKEN:
        raise web.HTTPBadRequest(
            text=json.dumps({"ok": False, "error": "Оплата картой ещё не настроена: нужен CARD_PAYMENT_URL или CARD_PROVIDER_TOKEN"})
        )

    request_data = await request.json()
    init_data = request_data.get("initData", "")
    validated = validate_webapp_init_data(init_data, allow_dev_bypass=True)
    user = validated.get("user") or {}
    payload = build_user_payment_payload(CARD_PAYLOAD, user.get("id"))
    bot: Bot = request.app["bot"]
    invoice_url = await bot.create_invoice_link(**build_card_payment_kwargs(payload=payload))
    return web.json_response(
        {"ok": True, "url": invoice_url, "external": False, "dev_bypass": validated.get("dev_bypass", False)}
    )


async def miniapp_crypto_link_handler(request: web.Request) -> web.Response:
    if not crypto_payment_ready():
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Крипто-оплата ещё не настроена"}))

    request_data = await request.json()
    init_data = request_data.get("initData", "")
    validated = validate_webapp_init_data(init_data, allow_dev_bypass=True)
    user = validated.get("user") or {}
    invoice_url = await create_crypto_invoice_link(user.get("id"))
    return web.json_response({"ok": True, "url": invoice_url, "dev_bypass": validated.get("dev_bypass", False)})


async def miniapp_promo_activate_handler(request: web.Request) -> web.Response:
    if not PROMO_CODE:
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Промокод сейчас недоступен"}))

    request_data = await request.json()
    init_data = request_data.get("initData", "")
    promo_code = str(request_data.get("promoCode", "")).strip()
    if not promo_code:
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Введите промокод"}))

    validated = validate_webapp_init_data(init_data, allow_dev_bypass=True)
    user = validated.get("user") or {}
    user_id = user.get("id")
    if not user_id:
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Не удалось определить пользователя Telegram"}))

    if promo_code.casefold() != PROMO_CODE.casefold():
        raise web.HTTPBadRequest(text=json.dumps({"ok": False, "error": "Промокод не подошёл"}))

    access_opened_now = grant_course_access_via_promo(user_id, PROMO_CODE)
    bot: Bot = request.app["bot"]

    previous_panel_message_id = active_panels.get(user_id)
    if previous_panel_message_id:
        await safe_delete_message(bot, user_id, previous_panel_message_id)
        active_panels.pop(user_id, None)

    sent_message = await bot.send_message(
        chat_id=user_id,
        text=f"{COURSE_TEXT}\n\nВыберите направление:",
        reply_markup=build_course_keyboard(),
    )
    active_panels[user_id] = sent_message.message_id

    return web.json_response(
        {
            "ok": True,
            "granted": access_opened_now,
            "message": "Доступ к курсу открыт" if access_opened_now else "Промокод уже применён, курс уже открыт",
        }
    )


def build_web_application(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/healthz", healthz_handler)
    app.router.add_get("/miniapp", miniapp_page_handler)
    app.router.add_get("/miniapp/styles.css", miniapp_styles_handler)
    app.router.add_get("/miniapp/app.js", miniapp_script_handler)
    app.router.add_get("/miniapp/api/config", miniapp_config_handler)
    app.router.add_post("/miniapp/api/payment/stars-link", miniapp_stars_link_handler)
    app.router.add_post("/miniapp/api/payment/card-link", miniapp_card_link_handler)
    app.router.add_post("/miniapp/api/payment/crypto-link", miniapp_crypto_link_handler)
    app.router.add_post("/miniapp/api/payment/promo-activate", miniapp_promo_activate_handler)
    return app


async def start_web_server(bot: Bot) -> web.AppRunner:
    app = build_web_application(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    logging.info("Mini App server listening on http://%s:%s", WEB_HOST, WEB_PORT)
    logging.info("Mini App public URL set to %s", MINI_APP_URL)
    return runner


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def clear_previous_panel(message: Message) -> None:
    panel_message_id = active_panels.get(message.chat.id)
    if panel_message_id:
        await safe_delete_message(message.bot, message.chat.id, panel_message_id)
        active_panels.pop(message.chat.id, None)


async def try_update_existing_panel(
    message: Message,
    *,
    text: Optional[str] = None,
    reply_markup=None,
    photo=None,
    caption: Optional[str] = None,
) -> bool:
    panel_message_id = active_panels.get(message.chat.id)
    if not panel_message_id:
        return False

    try:
        if photo is None and text is not None:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=panel_message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return True

        if photo is not None and caption is not None:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=panel_message_id,
                caption=caption,
                reply_markup=reply_markup,
            )
            return True
    except Exception:
        return False

    return False


async def hide_user_menu_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def replace_panel(
    message: Message,
    *,
    text: Optional[str] = None,
    reply_markup=None,
    photo=None,
    caption: Optional[str] = None,
) -> None:
    if await try_update_existing_panel(
        message,
        text=text,
        reply_markup=reply_markup,
        photo=photo,
        caption=caption,
    ):
        return

    await clear_previous_panel(message)

    if photo is not None:
        sent_message = await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=reply_markup,
        )
    else:
        sent_message = await message.answer(
            text,
            reply_markup=reply_markup,
        )

    active_panels[message.chat.id] = sent_message.message_id


async def create_keyboard_host(message: Message) -> None:
    keyboard = build_main_keyboard()

    if WELCOME_IMAGE_PATH and os.path.exists(WELCOME_IMAGE_PATH):
        sent_message = await message.answer_photo(
            photo=FSInputFile(WELCOME_IMAGE_PATH),
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
        keyboard_hosts[message.chat.id] = sent_message.message_id
        return

    if WELCOME_IMAGE_URL:
        sent_message = await message.answer_photo(
            photo=WELCOME_IMAGE_URL,
            caption=WELCOME_TEXT,
            reply_markup=keyboard,
        )
        keyboard_hosts[message.chat.id] = sent_message.message_id
        return

    sent_message = await message.answer(WELCOME_TEXT, reply_markup=keyboard)
    keyboard_hosts[message.chat.id] = sent_message.message_id


async def ensure_keyboard_host(message: Message) -> None:
    if message.chat.id not in keyboard_hosts:
        await create_keyboard_host(message)


async def send_welcome(message: Message) -> None:
    await clear_previous_panel(message)

    previous_host_message_id = keyboard_hosts.pop(message.chat.id, None)
    if previous_host_message_id:
        await safe_delete_message(message.bot, message.chat.id, previous_host_message_id)

    await create_keyboard_host(message)


async def show_course_panel(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    if not user_has_course_access(user_id):
        await replace_panel(
            message,
            text=build_locked_course_text(),
            reply_markup=build_locked_course_keyboard(),
        )
        return

    await replace_panel(
        message,
        text=f"{COURSE_TEXT}\n\nВыберите направление:",
        reply_markup=build_course_keyboard(),
    )


async def show_progress_panel(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    await replace_panel(message, text=build_progress_text(user_id))


async def show_payment_panel(message: Message) -> None:
    await replace_panel(
        message,
        text=build_payment_text(),
        reply_markup=build_payment_keyboard(),
    )


async def show_help_panel(message: Message) -> None:
    await replace_panel(message, text=HELP_TEXT)


async def show_faq_panel(message: Message) -> None:
    await replace_panel(message, text=FAQ_TEXT)


async def handle_unknown(message: Message) -> None:
    await replace_panel(
        message,
        text=(
            "Я пока понимаю кнопки меню и команду /start. "
            "Выберите один из разделов ниже."
        ),
    )


async def send_lesson_attachment(message: Message, track_key: str, lesson_number: int) -> None:
    lesson = get_lesson_entry(track_key, lesson_number)
    if not lesson:
        return

    video_file_id = lesson.get("video_file_id", "").strip()
    video_url = lesson.get("video_url", "").strip()

    if video_file_id:
        await message.answer_video(
            video=video_file_id,
            caption=build_lesson_video_caption(track_key, lesson),
            supports_streaming=True,
        )
        return

    if video_url:
        await message.answer(
            "Открыть видео урока:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Смотреть видео", url=video_url)],
                ]
            ),
        )


dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await send_welcome(message)


@dp.message(F.text == "КУРС")
async def course_handler(message: Message) -> None:
    await hide_user_menu_message(message)
    await show_course_panel(message)


@dp.callback_query(F.data == "course:menu")
async def course_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not user_has_course_access(user_id):
        await callback.message.edit_text(
            build_locked_course_text(),
            reply_markup=build_locked_course_keyboard(),
        )
        return

    await callback.message.edit_text(
        f"{COURSE_TEXT}\n\nВыберите направление:",
        reply_markup=build_course_keyboard(),
    )


@dp.callback_query(F.data == "main:menu")
async def inline_main_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    if active_panels.get(callback.message.chat.id) == callback.message.message_id:
        active_panels.pop(callback.message.chat.id, None)

    await safe_delete_message(
        callback.message.bot,
        callback.message.chat.id,
        callback.message.message_id,
    )


@dp.callback_query(F.data == "main:course")
async def inline_course_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    if not user_has_course_access(user_id):
        await callback.message.edit_text(
            build_locked_course_text(),
            reply_markup=build_locked_course_keyboard(),
        )
        return

    await callback.message.edit_text(
        f"{COURSE_TEXT}\n\nВыберите направление:",
        reply_markup=build_course_keyboard(),
    )


@dp.callback_query(F.data == "main:progress")
async def inline_progress_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        build_progress_text(callback.from_user.id),
        reply_markup=None,
    )


@dp.callback_query(F.data == "main:payment")
async def inline_payment_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        build_payment_text(),
        reply_markup=build_payment_keyboard(),
    )


@dp.callback_query(F.data == "payment:invoice")
async def payment_invoice_handler(callback: CallbackQuery) -> None:
    if not payment_ready():
        await callback.answer("Сначала настрой платежные переменные в .env", show_alert=True)
        return

    await callback.answer()
    await callback.message.bot.send_invoice(
        chat_id=callback.message.chat.id,
        **build_payment_kwargs(),
    )


@dp.callback_query(F.data == "payment:unavailable")
async def payment_unavailable_handler(callback: CallbackQuery) -> None:
    await callback.answer("Для Mini App нужен публичный HTTPS URL в MINI_APP_URL", show_alert=True)


@dp.callback_query(F.data == "payment:link")
async def payment_link_handler(callback: CallbackQuery) -> None:
    if PAYMENT_LINK_URL:
        await callback.answer()
        await callback.message.answer(
            f"Ссылка на оплату: {PAYMENT_LINK_URL}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть оплату", url=PAYMENT_LINK_URL)],
                ]
            ),
        )
        return

    if not payment_ready():
        await callback.answer("Сначала настрой платежные переменные в .env", show_alert=True)
        return

    invoice_link = await callback.message.bot.create_invoice_link(
        **build_payment_kwargs(),
    )
    await callback.answer("Ссылка на оплату готова")
    await callback.message.answer(
        "Вот ссылка на оплату:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть оплату", url=invoice_link)],
            ]
        ),
    )


@dp.callback_query(F.data == "main:help")
async def inline_help_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        HELP_TEXT,
        reply_markup=None,
    )


@dp.callback_query(F.data == "main:faq")
async def inline_faq_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        FAQ_TEXT,
        reply_markup=None,
    )


@dp.callback_query(F.data.startswith("track:"))
async def track_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    track_key = callback.data.split(":", 1)[1]
    if not user_has_course_access(callback.from_user.id):
        await callback.message.edit_text(
            build_locked_course_text(),
            reply_markup=build_locked_course_keyboard(),
        )
        return

    if not get_track_entry(track_key):
        await callback.answer("Раздел не найден", show_alert=True)
        return

    await callback.message.edit_text(
        build_track_text(track_key),
        reply_markup=build_lessons_keyboard(track_key),
    )


@dp.callback_query(F.data.startswith("lesson:"))
async def lesson_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    _, track_key, lesson_number = callback.data.split(":")
    lesson_number_int = int(lesson_number)
    if not user_has_course_access(callback.from_user.id):
        await callback.message.edit_text(
            build_locked_course_text(),
            reply_markup=build_locked_course_keyboard(),
        )
        return

    if not get_lesson_entry(track_key, lesson_number_int):
        await callback.answer("Урок не найден", show_alert=True)
        return

    register_lesson_open(callback.from_user.id, track_key, lesson_number_int)
    await callback.message.edit_text(
        build_lesson_text(track_key, lesson_number_int),
        reply_markup=build_lesson_keyboard(track_key),
    )
    await send_lesson_attachment(callback.message, track_key, lesson_number_int)


@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery) -> None:
    valid_payment_payload = pre_checkout_query.invoice_payload.startswith(f"{PAYMENT_PAYLOAD}:") or (
        pre_checkout_query.invoice_payload == PAYMENT_PAYLOAD
    )
    valid_card_payload = pre_checkout_query.invoice_payload.startswith(f"{CARD_PAYLOAD}:") or (
        pre_checkout_query.invoice_payload == CARD_PAYLOAD
    )

    if not valid_payment_payload and not valid_card_payload:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Не удалось проверить платеж. Попробуйте еще раз.",
        )
        return

    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    payment = message.successful_payment
    user_id = message.from_user.id if message.from_user else message.chat.id
    grant_course_access(
        user_id,
        amount=payment.total_amount,
        currency=payment.currency,
        telegram_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id,
        payload=payment.invoice_payload,
    )
    await message.answer(
        (
            "<b>Оплата прошла успешно</b>\n\n"
            f"Сумма: {format_payment_amount(payment.total_amount, payment.currency)}\n"
            f"Транзакция: <code>{payment.telegram_payment_charge_id}</code>\n\n"
            "Доступ к курсу уже открыт. Можно сразу переходить к занятиям."
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Открыть курс", callback_data="main:course")],
                [InlineKeyboardButton(text="Посмотреть прогресс", callback_data="main:progress")],
            ]
        ),
    )


@dp.message(F.text == "МОЙ ПРОГРЕСС")
async def progress_handler(message: Message) -> None:
    await hide_user_menu_message(message)
    await show_progress_panel(message)


@dp.message(F.text == "ОПЛАТА")
async def payment_handler(message: Message) -> None:
    await hide_user_menu_message(message)
    await show_payment_panel(message)


@dp.message(F.text == "ПОМОЩЬ")
async def help_handler(message: Message) -> None:
    await hide_user_menu_message(message)
    await show_help_panel(message)


@dp.message(F.text == "ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ")
async def faq_handler(message: Message) -> None:
    await hide_user_menu_message(message)
    await show_faq_panel(message)


@dp.message()
async def fallback_handler(message: Message) -> None:
    await handle_unknown(message)


async def configure_bot_for_chat(bot: Bot) -> None:
    await bot.delete_my_commands()

    if mini_app_launch_ready():
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Оплата",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        )
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not RUN_BOT and not RUN_WEB:
        raise RuntimeError("At least one of RUN_BOT or RUN_WEB must be enabled")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    web_runner: Optional[web.AppRunner] = None

    try:
        if RUN_WEB:
            web_runner = await start_web_server(bot)

        if RUN_BOT:
            await configure_bot_for_chat(bot)
            await dp.start_polling(bot)
        else:
            logging.info("RUN_BOT is disabled; web-only mode is active")
            await asyncio.Event().wait()
    finally:
        if web_runner is not None:
            await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
