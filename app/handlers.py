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


# Регулярное выражение для проверки ввода (целые и десятичные числа)
number_pattern = re.compile(r"^\d+(\.\d+)?$")

router = Router()


# Обработка команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id)
    await message.answer(f'Привет, {message.from_user.first_name}!\n\n'
                         'Чтобы начать запись тренировок, просто выберите необходимое действие на клавиатуре или '
                         'введите фразу «Записать тренировку».\n\n'
                         'Для просмотра прогресса также выберите нужное действие или введите фразу «Посмотреть прогресс».',
                         reply_markup=kb.main_kb)

# Определяем состояния
class WorkoutStates(StatesGroup):
    ChoosingNextExercise = State()  # Состояние ожидания выбора упражнения или завершения тренировки


# Обработка команды /finish в любом состоянии
@router.message(Command('finish_exercise'),  StateFilter(any_state))
async def finish_exercise(message: Message, state: FSMContext):
    # Извлекаем все данные о подходах
    user_data = await state.get_data()
    sets = user_data.get('sets', [])
    exercise = user_data.get("exercise")  # Проверяем, задано ли упражнение

    # Если упражнение не начато
    if not exercise:
        await message.answer("У вас нет начатого упражнения. Сначала выберите упражнение.")
        return

    # Проверка, есть ли активная тренировка
    if not sets:
        # Сообщение о необходимости начать упражнение, если подходов нет
        await message.answer("Упражнение прервано")
        await state.clear()
        await message.answer(
            "Для продолжения тренировки выберите следующее упражнение или введите команду /finish_workout чтобы закончить тренировку.",
            reply_markup=await kb.inline_muscle())
        return

    # Формируем итоговое сообщение с данными по подходам для завершенного упражнения
    exercise_name = await rq.get_name_exercise(user_data.get("exercise"))
    result_message = f"Данные по упражнению ({exercise_name.name}):\n"
    for idx, set_data in enumerate(sets, start=1):
        result_message += (f"Подход {set_data['set_number']}: "
                           f"Вес: {set_data['weight']} кг, "
                           f"Повторения: {set_data['reps']}\n")


    # Отправляем результат пользователю
    await message.answer(result_message)

    # Сохраняем данные упражнения в список завершённых
    completed_exercises = user_data.get('completed_exercises', [])
    completed_exercises.append(exercise_name.name)
    await state.update_data(completed_exercises=completed_exercises)

    # Очищаем данные FSM и сбрасываем состояние
    await state.update_data(sets=[], exercise=None)  # Очищаем подходы текущего упражнения

    # Переходим в состояние выбора нового упражнения
    await state.set_state(WorkoutStates.ChoosingNextExercise)

    # Предлагаем выбор следующего упражнения
    await message.answer("Для продолжения тренировки выберите следующее упражнение или введите команду /finish_workout чтобы закончить тренировку.",
                         reply_markup=await kb.inline_muscle())

# Обработка команды /finish_workout
@router.message(Command('finish_workout'))
async def finish_workout(message: Message, state: FSMContext):
    # Извлекаем данные о завершённых упражнениях
    user_data = await state.get_data()
    completed_exercises = user_data.get('completed_exercises', [])
    completed_exercises = list(dict.fromkeys(completed_exercises))

    # Формируем итоговое сообщение
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

    # Отправляем результат и очищаем данные FSM
    await message.answer(workout_summary, reply_markup=kb.main_kb)
    await state.clear()


# Обработка сообщения "записать тренировку"
@router.message(F.text.lower() == 'записать тренировку')
async def add_workout(message: Message):
    await message.answer('Выберите группу мышц для записи тренировки', reply_markup=await kb.inline_muscle())


# Начало включения включение FSM и выбор группы мышц
@router.callback_query(F.data.regexp(r"^muscle_group_"))
async def muscle_group_handler(callback: CallbackQuery, state: FSMContext):
    muscle_group = await rq.get_name_muscle_group(callback.data.split("_")[2])
    await callback.answer(muscle_group.name)
    await state.update_data(muscle_group_id=muscle_group.id)
    exercises = await rq.get_exercises(muscle_group.id)
    await callback.message.edit_text('Выберите упражнение для записи тренировки', reply_markup=await kb.inline_exercises_keyboard(exercises=exercises))


# Обработка кнопки назад при выборе упражнения во записи тренировки
@router.callback_query(F.data == 'muscle_list')
async def button_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите группу мышц для записи тренировки', reply_markup=await kb.inline_muscle())


# Обработка кнопки назад при выборе упражнения во время просмотра прогресса
@router.callback_query(F.data == 'muscle_list_progress')
async def leg(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text('Выберите группу мышц для просмотра прогресса', reply_markup=await kb.inline_muscle_for_progression())


# Машина состояний для отслеживания сета
class ExerciseForm(StatesGroup):
    sets = State()
    weight = State()
    reps = State()
    finish = State()

# Обработка ввода после выбора упражнения на запись тренировки
@router.callback_query(F.data.regexp(r"^exercise_"))
async def choose_exercise(callback: CallbackQuery, state: FSMContext):
    exercise = await rq.get_name_exercise(callback.data.split("_")[1])
    await callback.answer(exercise.name)

    # Запоминаем выбранное упражнение и группу мышц в FSM
    await state.update_data(exercise=exercise.id, sets=[], set_number=1)

    # Удаляем сообщение с инлайн-клавиатурой
    await callback.message.delete()

    await callback.message.answer(f"Начато упражнение - {exercise.name}", reply_markup=None)
    await callback.message.answer("Введите вес (в кг) для подхода 1:")
    await state.set_state(ExerciseForm.weight)


@router.message(WorkoutStates.ChoosingNextExercise)  # Обработка других текстовых сообщений в состоянии ожидания выбора упражнения
async def handle_invalid_input(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, выберите упражнение из списка или введите команду /finish_workout для завершения тренировки."
    )

# Обработка получения веса
@router.message(ExerciseForm.weight)
async def process_weight(message: Message, state: FSMContext):
    if not number_pattern.match(message.text):
        await message.answer("Пожалуйста, введите корректное значение веса (целое или с плавающей точкой).")
        return

    # Сохраняем вес
    await state.update_data(weight=float(message.text))

    # Переходим в состояние ожидания количества повторений
    await message.answer("Введите количество повторений:")
    await state.set_state(ExerciseForm.reps)

# Обработка получения количества повторений
@router.message(ExerciseForm.reps)
async def process_reps(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное целое значение для количества повторений.")
        return

    # Сохраняем количество повторений
    await state.update_data(reps=int(message.text))

    # Извлекаем все данные
    user_data = await state.get_data()
    current_set = {
        'set_number': user_data['set_number'],
        'weight': user_data['weight'],
        'reps': user_data['reps'],
        'exercise': user_data['exercise'],
        'muscle_group_id': user_data['muscle_group_id']
    }

    # Добавляем текущий подход в общий список
    sets = user_data['sets']
    sets.append(current_set)
    await state.update_data(sets=sets)

    # Получение текущего пользователя по telegram_id
    user_id = message.from_user.id

    # Добавляем текущий подход в БД
    await rq.add_set(
        set_number=int(current_set['set_number']),
        weight=float(current_set['weight']),
        reps=int(current_set['reps']),
        exercise_id=int(current_set['exercise']),
        user_id=user_id,
    )

    # Увеличиваем номер подхода и обновляем состояние
    next_set_number = user_data['set_number'] + 1
    await state.update_data(set_number=next_set_number)

    # Сообщаем о сохранении и предлагаем продолжить
    await message.answer(
        f"Подход {next_set_number - 1} сохранен. "
        f"Введите вес для подхода {next_set_number} или введите /finish_exercise для завершения упражнения."
    )
    await state.set_state(ExerciseForm.weight)

# Обработка сообщения "посмотреть прогресс"
@router.message(F.text.lower() == 'посмотреть прогресс')
async def add_workout(message: Message):
    await message.answer('Выберите группу мышц для просмотра прогресса', reply_markup=await kb.inline_muscle_for_progression())

# Обработка выбора группы мышц при просмотре прогресса
@router.callback_query(F.data.regexp(r"^m_g_f_p_"))
async def progress(callback: CallbackQuery):
    muscle_group = await rq.get_name_muscle_group(callback.data.split("_")[4])
    await callback.answer(muscle_group.name)
    user_id = callback.from_user.id
    exercises = await rq.get_exercises_by_user_and_muscle_group(user_id, muscle_group.id)
    await callback.message.edit_text('Выберите упражнение для просмотра прогресса',
                                     reply_markup=await kb.inline_exercises_keyboard_for_progression(exercises=exercises))

# Обработка выбора упражнения при просмотре прогресса
@router.callback_query(F.data.regexp(r"^e_p_"))
async def progress_max(callback: CallbackQuery):
    exercise_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    await callback.answer()

    exercise_progress = await rq.select_progress_exercise(user_id, exercise_id)
    plot_image = draw.generate_progress_plot(exercise_progress)
    image = BufferedInputFile(plot_image.getvalue(), filename="plot.png")
    exercise_name = exercise_progress[0][4]  # Название упражнения
    text = f"Прогресс по упражнению - {exercise_name}"
    await callback.bot.send_photo(chat_id=callback.from_user.id, photo=image,caption=text, reply_markup=kb.main_kb)

    plot_image.close()
    del image
    await callback.message.delete()


# Обработка сообщения "планы тренировок"
@router.message(F.text.lower() == "планы тренировок")
async def add_workout(message: Message):
    await message.answer("Данный раздел находится в разработке. Выберите что-то другое.", reply_markup=kb.main_kb)

# Обработка любого другого сообщения
@router.message(F.text)
async def add_workout(message: Message):
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


