from sqlalchemy.orm import aliased

from app.database.models import *
from sqlalchemy import select, desc, delete


async def set_user(tg_id):
    """Проверка наличия пользователя в бд"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            new_user = User(tg_id=tg_id)
            session.add(new_user)
            await session.commit()

async def get_user_id(tg_id):
    """Получение внутреннего ID пользователя по Telegram ID"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return user.id if user else None

async def add_set(set_number, weight, reps, exercise_id, user_id):
    """Добавление сета в бд"""
    async with async_session() as session:
        async with session.begin():
            new_set = Sets(
                set_number=set_number,
                weight=weight,
                reps=reps,
                exercise_id=exercise_id,
                user_id=user_id,
            )
            session.add(new_set)

async def get_user_exercises(user_id: int, muscle_group_id: int):
    """Персональные упражнения пользователя по группе мышц"""
    async with async_session() as session:
        result = await session.scalars(
            select(Exercise).where(
                Exercise.user_id == user_id,
                Exercise.muscle_group_id == muscle_group_id
            )
        )
        return result.all()

async def add_user_exercise(user_id: int, muscle_group_id: int, name: str) -> Exercise:
    """Добавить персональное упражнение"""
    async with async_session() as session:
        async with session.begin():
            exercise = Exercise(name=name.strip(), muscle_group_id=muscle_group_id, user_id=user_id)
            session.add(exercise)
        await session.refresh(exercise)
        return exercise

async def delete_user_exercise(user_id: int, exercise_id: int) -> bool:
    """Удалить упражнение пользователя вместе со всеми сетами"""
    async with async_session() as session:
        async with session.begin():
            exercise = await session.get(Exercise, exercise_id)
            if not exercise or exercise.user_id != user_id:
                return False
            await session.execute(delete(Sets).where(Sets.exercise_id == exercise_id))
            await session.delete(exercise)
        return True

async def select_muscle_group():
    """Получение групп мышц"""
    async with async_session() as session:
        return await session.scalars(select(MuscleGroup).order_by(MuscleGroup.sort_order))

async def get_name_muscle_group(muscle_group_id):
    """Получение одной группы мышц по id"""
    async with async_session() as session:
        return await session.get(MuscleGroup, int(muscle_group_id))

async def get_name_exercise(exercise_id):
    """Получение одного упражнения по id"""
    async with async_session() as session:
        return await session.get(Exercise, int(exercise_id))

async def get_exercise_and_group(exercise_name: str):
    """Получение таблицы упражнений с обозначением id групп мышц """
    async with async_session() as session:
        result = await session.execute(
            select(Exercise, MuscleGroup)
            .join(MuscleGroup, Exercise.muscle_group_id == MuscleGroup.id)
            .filter(Exercise.name == exercise_name)
        )
        exercise, muscle_group = result.first()
        return exercise.id, muscle_group.id


async def get_exercises_by_user_and_muscle_group(user_id, muscle_group_id):
    """Получение таблицы упражнений для конкретного пользователя и группы мышц.

    SLQ: SELECT sets.exercise_id, exercises.name, exercises.muscle_group_id FROM sets
        JOIN exercises ON exercises.id == sets.exercise_id
        WHERE Sets.user_id = user_id AND exercises.muscle_group_id = muscle_group_id
        GROUP BY exercise_id"""

    async with async_session() as session:
        query = (
            select(Sets.exercise_id, Exercise.name, Exercise.muscle_group_id)
            .join(Exercise, Exercise.id == Sets.exercise_id)
            .where(Sets.user_id == user_id, Exercise.muscle_group_id == muscle_group_id)
            .group_by(Sets.exercise_id)
        )
        result = await session.execute(query)
        return result.fetchall()

async def select_progress_exercise(user_id, exercise):
    """Извлекает прогресс пользователя по заданному упражнению."""
    async with async_session() as session:
        s = aliased(Sets)

        # Подзапрос с использованием оконной функции
        subquery = (
            select(
                s.exercise_id,
                s.weight.label('max_weight'),
                s.reps,
                s.created_at,
                Exercise.name,
                func.row_number().over(
                    partition_by=func.date(s.created_at),
                    order_by=[desc(s.weight), desc(s.reps)]
                ).label('row_number')
            )
            .join(Exercise, Exercise.id == s.exercise_id)
            .where(
                s.user_id == user_id,
                s.exercise_id == exercise
            )
        ).subquery()

        # Основной запрос: выбираем записи, где row_number == 1
        query = (
            select(
                subquery.c.exercise_id,
                subquery.c.max_weight,
                subquery.c.reps,
                subquery.c.created_at,
                subquery.c.name
            )
            .where(subquery.c.row_number == 1)
            .order_by(subquery.c.created_at)
        )

        result = await session.execute(query)
        return result.fetchall()