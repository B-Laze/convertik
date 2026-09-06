from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


class SplitPDF(StatesGroup):
    waiting_for_file = State()
    waiting_for_pages = State()


class RotatePDF(StatesGroup):
    waiting_for_file = State()
    waiting_for_angle = State()
    waiting_for_pages = State()


class MergePDF(StatesGroup):
    waiting_for_files = State()


rotate_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="↺ 90° против часовой", callback_data="rotate_270"),
        InlineKeyboardButton(text="↻ 90° по часовой", callback_data="rotate_90")
    ],
    [
        InlineKeyboardButton(text="🔄 180°", callback_data="rotate_180")
    ]
])

merge_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Склеить файлы"), KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)