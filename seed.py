import asyncio
from app.database.models import async_main, async_session, MuscleGroup, Exercise

data = {
    "Плечи": ["Жим гантелей сидя", "Махи в стороны", "Тяга к подбородку"],
    "Грудь": ["Жим штанги лёжа", "Жим гантелей лёжа", "Разводка гантелей"],
    "Руки": ["Подъём штанги на бицепс", "Молотки", "Французский жим", "Отжимания на брусьях"],
    "Пресс": ["Скручивания", "Подъём ног", "Планка"],
    "Ноги": ["Приседания", "Жим ногами", "Выпады", "Румынская тяга"],
}

async def seed():
    await async_main()
    async with async_session() as session:
        async with session.begin():
            for group_name, exercises in data.items():
                group = MuscleGroup(name=group_name)
                session.add(group)
                await session.flush()
                for exercise_name in exercises:
                    session.add(Exercise(name=exercise_name, muscle_group_id=group.id))

asyncio.run(seed())
print("База данных заполнена.")
