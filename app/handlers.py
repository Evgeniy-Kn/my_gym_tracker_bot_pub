import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, any_state
from aiogram.types import Message, CallbackQuery, BufferedInputFile

import app.database.requests as rq
import app.draw_progress as draw
import app.keyboards as kb

number_pattern = re.compile(r"^\d+(\.\d+)?$")

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.answer(
        f'Привет, {message.from_user.first_name}!\n\n'
        'Чтобы начать запись тренировок, просто выберите необходимое действие на клавиатуре или '
        'введите фразу «Записать тренировку».\n\n'
        'Для просмотра прогресса также выберите нужное действие или введите фразу «Посмотреть прогресс».',
        reply_markup=kb.main_kb
    )


class WorkoutStates(StatesGroup):
    ChoosingNextExercise = State()


class ExerciseForm(StatesGroup):
    sets = State()
    weight = State()
    reps = State()
    finish = State()


class ExerciseManageStates(StatesGroup):
    WaitingExerciseName = State()


# --- Завершение упражнения ---

@router.message(Command('finish_exercise'), StateFilter(any_state))
async def finish_exercise(message: Message, state: FSMContext):
    user_data = await state.get_data()
    sets = user_data.get('sets', [])
    exercise = user_data.get("exercise")

    if not exercise:
        await message.answer("У вас нет начатого упражнения. Сначала выберите упражнение.")
        return

    if not sets:
        await message.answer("Упражнение прервано")
        await state.clear()
        await message.answer(
            "Для продолжения тренировки выберите следующее упражнение или введите команду /finish_workout чтобы закончить тренировку.",
            reply_markup=await kb.inline_muscle()
        )
        return

    exercise_name = await rq.get_name_exercise(user_data.get("exercise"))
    if not exercise_name:
        await message.answer("Упражнение было удалено.")
        await state.clear()
        return

    result_message = f"Данные по упражнению ({exercise_name.name}):\n"
    for set_data in sets:
        result_message += (
            f"Подход {set_data['set_number']}: "
            f"Вес: {set_data['weight']} кг, "
            f"Повторения: {set_data['reps']}\n"
        )

    await message.answer(result_message)

    completed_exercises = user_data.get('completed_exercises', [])
    completed_exercises.append(exercise_name.name)
    await state.update_data(completed_exercises=completed_exercises)
    await state.update_data(sets=[], exercise=None)
    await state.set_state(WorkoutStates.ChoosingNextExercise)

    await message.answer(
        "Для продолжения тренировки выберите следующее упражнение или введите команду /finish_workout чтобы закончить тренировку.",
        reply_markup=await kb.inline_muscle()
    )


@router.message(Command('finish_workout'))
async def finish_workout(message: Message, state: FSMContext):
    user_data = await state.get_data()
    completed_exercises = list(dict.fromkeys(user_data.get('completed_exercises', [])))

    if completed_exercises:
        workout_summary = "Тренировка завершена!\nВыполненные упражнения:\n- "
        workout_summary += "\n- ".join(completed_exercises)
    else:
        workout_summary = "Вы еще не завершили ни одного упражнения."

    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    except TelegramBadRequest:
        pass

    await message.answer(workout_summary, reply_markup=kb.main_kb)
    await state.clear()


# --- Запись тренировки ---

@router.message(F.text.lower() == 'записать тренировку')
async def start_workout(message: Message):
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    except TelegramBadRequest:
        pass
    await message.answer('Выберите группу мышц для записи тренировки', reply_markup=await kb.inline_muscle())


@router.callback_query(F.data.regexp(r"^muscle_group_"))
async def muscle_group_handler(callback: CallbackQuery, state: FSMContext):
    muscle_group_id = int(callback.data.split("_")[2])
    muscle_group = await rq.get_name_muscle_group(muscle_group_id)
    await callback.answer(muscle_group.name)
    await state.update_data(muscle_group_id=muscle_group.id)

    user_id = await rq.get_user_id(callback.from_user.id)
    exercises = await rq.get_user_exercises(user_id, muscle_group.id)

    await callback.message.edit_text(
        'Выберите упражнение для записи тренировки',
        reply_markup=await kb.inline_exercises_keyboard(exercises=exercises, muscle_group_id=muscle_group.id)
    )


@router.callback_query(F.data == 'muscle_list')
async def button_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите группу мышц для записи тренировки', reply_markup=await kb.inline_muscle())


@router.callback_query(F.data == 'switch_to_progress')
async def switch_to_progress(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        'Выберите группу мышц для просмотра прогресса',
        reply_markup=await kb.inline_muscle_for_progression()
    )


@router.callback_query(F.data == 'switch_to_workout')
async def switch_to_workout(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        'Выберите группу мышц для записи тренировки',
        reply_markup=await kb.inline_muscle()
    )


@router.callback_query(F.data.regexp(r"^exercise_"))
async def choose_exercise(callback: CallbackQuery, state: FSMContext):
    exercise = await rq.get_name_exercise(callback.data.split("_")[1])
    await callback.answer(exercise.name)
    await state.update_data(exercise=exercise.id, sets=[], set_number=1)
    await callback.message.delete()
    await callback.message.answer(f"Начато упражнение - {exercise.name}", reply_markup=None)
    await callback.message.answer("Введите вес (в кг) для подхода 1:")
    await state.set_state(ExerciseForm.weight)


@router.message(WorkoutStates.ChoosingNextExercise)
async def handle_invalid_input(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, выберите упражнение из списка или введите команду /finish_workout для завершения тренировки."
    )


@router.message(ExerciseForm.weight)
async def process_weight(message: Message, state: FSMContext):
    if not number_pattern.match(message.text):
        await message.answer("Пожалуйста, введите корректное значение веса (целое или с плавающей точкой).")
        return
    await state.update_data(weight=float(message.text))
    await message.answer("Введите количество повторений:")
    await state.set_state(ExerciseForm.reps)


@router.message(ExerciseForm.reps)
async def process_reps(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное целое значение для количества повторений.")
        return

    await state.update_data(reps=int(message.text))
    user_data = await state.get_data()
    current_set = {
        'set_number': user_data['set_number'],
        'weight': user_data['weight'],
        'reps': user_data['reps'],
        'exercise': user_data['exercise'],
    }

    sets = user_data['sets']
    sets.append(current_set)
    await state.update_data(sets=sets)

    user_id = await rq.get_user_id(message.from_user.id)
    await rq.add_set(
        set_number=int(current_set['set_number']),
        weight=float(current_set['weight']),
        reps=int(current_set['reps']),
        exercise_id=int(current_set['exercise']),
        user_id=user_id,
    )

    next_set_number = user_data['set_number'] + 1
    await state.update_data(set_number=next_set_number)
    await message.answer(
        f"Подход {next_set_number - 1} сохранен. "
        f"Введите вес для подхода {next_set_number} или введите /finish_exercise для завершения упражнения."
    )
    await state.set_state(ExerciseForm.weight)


# --- Управление упражнениями (добавление / удаление) ---

@router.callback_query(F.data.regexp(r"^add_exercise_"))
async def add_exercise_handler(callback: CallbackQuery, state: FSMContext):
    muscle_group_id = int(callback.data.split("_")[2])
    await callback.answer()
    await state.update_data(muscle_group_id=muscle_group_id)
    await state.set_state(ExerciseManageStates.WaitingExerciseName)
    await callback.message.edit_text("Введите название нового упражнения:")


@router.message(ExerciseManageStates.WaitingExerciseName)
async def process_exercise_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) > 100:
        await message.answer("Название должно быть непустым и не длиннее 100 символов. Попробуйте снова:")
        return

    user_data = await state.get_data()
    muscle_group_id = user_data.get("muscle_group_id")
    user_id = await rq.get_user_id(message.from_user.id)

    await rq.add_user_exercise(user_id, muscle_group_id, name)
    await state.clear()

    exercises = await rq.get_user_exercises(user_id, muscle_group_id)
    await message.answer(
        f'Упражнение «{name}» добавлено. Выберите упражнение для записи:',
        reply_markup=await kb.inline_exercises_keyboard(exercises=exercises, muscle_group_id=muscle_group_id)
    )


@router.callback_query(F.data.regexp(r"^delete_exercise_mode_"))
async def delete_exercise_mode_handler(callback: CallbackQuery, state: FSMContext):
    muscle_group_id = int(callback.data.split("_")[3])
    await callback.answer()
    user_id = await rq.get_user_id(callback.from_user.id)
    exercises = await rq.get_user_exercises(user_id, muscle_group_id)
    await callback.message.edit_text(
        "Выберите упражнение для удаления:",
        reply_markup=await kb.inline_delete_exercise_keyboard(exercises=exercises, muscle_group_id=muscle_group_id)
    )


@router.callback_query(F.data.regexp(r"^confirm_delete_"))
async def confirm_delete_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    exercise_id = int(parts[2])
    muscle_group_id = int(parts[3])
    await callback.answer()
    exercise = await rq.get_name_exercise(exercise_id)
    await callback.message.edit_text(
        f'Удалить упражнение «{exercise.name}»?\nВсе данные тренировок по нему будут удалены.',
        reply_markup=kb.inline_confirm_delete_keyboard(exercise_id=exercise_id, muscle_group_id=muscle_group_id)
    )


@router.callback_query(F.data.regexp(r"^do_delete_"))
async def do_delete_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    exercise_id = int(parts[2])
    muscle_group_id = int(parts[3])
    user_id = await rq.get_user_id(callback.from_user.id)

    success = await rq.delete_user_exercise(user_id, exercise_id)
    exercises = await rq.get_user_exercises(user_id, muscle_group_id)

    if success:
        await callback.answer("Упражнение удалено")
    else:
        await callback.answer("Ошибка: упражнение не найдено", show_alert=True)

    await callback.message.edit_text(
        'Выберите упражнение для записи тренировки',
        reply_markup=await kb.inline_exercises_keyboard(exercises=exercises, muscle_group_id=muscle_group_id)
    )


@router.callback_query(F.data.regexp(r"^cancel_delete_"))
async def cancel_delete_handler(callback: CallbackQuery):
    muscle_group_id = int(callback.data.split("_")[2])
    await callback.answer()
    user_id = await rq.get_user_id(callback.from_user.id)
    exercises = await rq.get_user_exercises(user_id, muscle_group_id)
    await callback.message.edit_text(
        'Выберите упражнение для записи тренировки',
        reply_markup=await kb.inline_exercises_keyboard(exercises=exercises, muscle_group_id=muscle_group_id)
    )


# --- Просмотр прогресса ---

@router.message(F.text.lower() == 'посмотреть прогресс')
async def show_progress(message: Message):
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    except TelegramBadRequest:
        pass
    await message.answer('Выберите группу мышц для просмотра прогресса', reply_markup=await kb.inline_muscle_for_progression())


@router.callback_query(F.data == 'muscle_list_progress')
async def back_to_muscle_progress(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите группу мышц для просмотра прогресса', reply_markup=await kb.inline_muscle_for_progression())


@router.callback_query(F.data.regexp(r"^m_g_f_p_"))
async def progress(callback: CallbackQuery):
    muscle_group = await rq.get_name_muscle_group(callback.data.split("_")[4])
    await callback.answer(muscle_group.name)
    user_id = await rq.get_user_id(callback.from_user.id)
    exercises = await rq.get_exercises_by_user_and_muscle_group(user_id, muscle_group.id)
    await callback.message.edit_text(
        'Выберите упражнение для просмотра прогресса',
        reply_markup=await kb.inline_exercises_keyboard_for_progression(exercises=exercises)
    )


@router.callback_query(F.data.regexp(r"^e_p_"))
async def progress_max(callback: CallbackQuery):
    exercise_id = callback.data.split("_")[2]
    user_id = await rq.get_user_id(callback.from_user.id)
    await callback.answer()

    exercise_progress = await rq.select_progress_exercise(user_id, exercise_id)
    plot_image = draw.generate_progress_plot(exercise_progress)
    image = BufferedInputFile(plot_image.getvalue(), filename="plot.png")
    exercise_name = exercise_progress[0][4]
    await callback.bot.send_photo(
        chat_id=callback.from_user.id,
        photo=image,
        caption=f"Прогресс по упражнению - {exercise_name}",
        reply_markup=kb.main_kb
    )
    plot_image.close()
    del image
    await callback.message.delete()


# --- Прочие сообщения ---

@router.message(F.text.lower() == "планы тренировок")
async def workout_plans(message: Message):
    await message.answer("Данный раздел находится в разработке. Выберите что-то другое.", reply_markup=kb.main_kb)


@router.message(F.text)
async def unknown_message(message: Message):
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    except TelegramBadRequest:
        pass

    await message.answer(
        text="Я вас не понимаю.\nПожалуйста, выберите действие с клавиатуры для продолжения работы.",
        reply_markup=kb.main_kb
    )
