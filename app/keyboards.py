from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import select_muscle_group

# Клавиатура под вводом сообщения
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Записать тренировку'), KeyboardButton(text='Посмотреть прогресс')],

        ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите действие из меню",
    selective=True,
)

async def inline_muscle():
    """Инлайн-Клавиатура для выбора группы мышц, при записи тренировки"""
    all_muscle_groups = await select_muscle_group()
    keyboard = InlineKeyboardBuilder()

    for muscle_group in all_muscle_groups:
        keyboard.add(InlineKeyboardButton(text=muscle_group.name, callback_data=f"muscle_group_{muscle_group.id}"))
    return keyboard.adjust(2).as_markup()

async def inline_exercises_keyboard(exercises):
    """Инлайн-Клавиатура для выбора упражнения, при записи тренировки"""
    keyboard = InlineKeyboardBuilder()
    for exercise in exercises:
        keyboard.add(InlineKeyboardButton(text=exercise.name, callback_data=f'exercise_{exercise.id}'))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="muscle_list"))
    return keyboard.adjust(2).as_markup()

async def inline_muscle_for_progression():
    """Инлайн-Клавиатура для выбора группы мышц, при просмотре прогресса"""
    all_muscle_groups = await select_muscle_group()
    keyboard = InlineKeyboardBuilder()
    for muscle_group in all_muscle_groups:
        keyboard.add(InlineKeyboardButton(text=muscle_group.name, callback_data=f"m_g_f_p_{muscle_group.id}"))
    return keyboard.adjust(2).as_markup()

async def inline_exercises_keyboard_for_progression(exercises):
    """Инлайн-Клавиатура для выбора упражнения, при просмотре прогресса"""
    keyboard = InlineKeyboardBuilder()
    for exercise in exercises:
        keyboard.add(InlineKeyboardButton(text=exercise.name, callback_data=f'e_p_{exercise.exercise_id}'))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="muscle_list_progress"))
    return keyboard.adjust(2).as_markup()
