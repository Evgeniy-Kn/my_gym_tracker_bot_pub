from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import select_muscle_group

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
    """Инлайн-клавиатура для выбора группы мышц при записи тренировки"""
    all_muscle_groups = await select_muscle_group()
    keyboard = InlineKeyboardBuilder()
    for muscle_group in all_muscle_groups:
        keyboard.add(InlineKeyboardButton(text=muscle_group.name, callback_data=f"muscle_group_{muscle_group.id}"))
    keyboard.adjust(2)
    keyboard.row(InlineKeyboardButton(text="📊 Посмотреть прогресс", callback_data="switch_to_progress"))
    return keyboard.as_markup()

async def inline_exercises_keyboard(exercises: list, muscle_group_id: int):
    """Инлайн-клавиатура для выбора упражнения при записи тренировки"""
    exercises_kb = InlineKeyboardBuilder()
    for exercise in exercises:
        exercises_kb.add(InlineKeyboardButton(text=exercise.name, callback_data=f'exercise_{exercise.id}'))
    exercises_kb.adjust(2)

    controls = InlineKeyboardBuilder()
    if exercises:
        controls.row(
            InlineKeyboardButton(text="🗑 Удалить упражнение", callback_data=f"delete_exercise_mode_{muscle_group_id}"),
            InlineKeyboardButton(text="➕ Добавить упражнение", callback_data=f"add_exercise_{muscle_group_id}"),
        )
    else:
        controls.row(
            InlineKeyboardButton(text="➕ Добавить упражнение", callback_data=f"add_exercise_{muscle_group_id}"),
        )
    controls.row(InlineKeyboardButton(text="Назад", callback_data="muscle_list"))

    exercises_kb.attach(controls)
    return exercises_kb.as_markup()

async def inline_delete_exercise_keyboard(exercises: list, muscle_group_id: int):
    """Инлайн-клавиатура для выбора упражнения для удаления"""
    keyboard = InlineKeyboardBuilder()
    for exercise in exercises:
        keyboard.add(InlineKeyboardButton(
            text=exercise.name,
            callback_data=f'confirm_delete_{exercise.id}_{muscle_group_id}'
        ))
    keyboard.adjust(2)
    keyboard.row(InlineKeyboardButton(text="Отмена", callback_data=f"cancel_delete_{muscle_group_id}"))
    return keyboard.as_markup()

def inline_confirm_delete_keyboard(exercise_id: int, muscle_group_id: int):
    """Инлайн-клавиатура подтверждения удаления упражнения"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="Да, удалить", callback_data=f"do_delete_{exercise_id}_{muscle_group_id}"),
        InlineKeyboardButton(text="Отмена", callback_data=f"cancel_delete_{muscle_group_id}"),
    )
    return keyboard.as_markup()

async def inline_muscle_for_progression():
    """Инлайн-клавиатура для выбора группы мышц при просмотре прогресса"""
    all_muscle_groups = await select_muscle_group()
    keyboard = InlineKeyboardBuilder()
    for muscle_group in all_muscle_groups:
        keyboard.add(InlineKeyboardButton(text=muscle_group.name, callback_data=f"m_g_f_p_{muscle_group.id}"))
    keyboard.adjust(2)
    keyboard.row(InlineKeyboardButton(text="🏋 Записать тренировку", callback_data="switch_to_workout"))
    return keyboard.as_markup()

async def inline_exercises_keyboard_for_progression(exercises):
    """Инлайн-клавиатура для выбора упражнения при просмотре прогресса"""
    keyboard = InlineKeyboardBuilder()
    for exercise in exercises:
        keyboard.add(InlineKeyboardButton(text=exercise.name, callback_data=f'e_p_{exercise.exercise_id}'))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="muscle_list_progress"))
    return keyboard.adjust(2).as_markup()
