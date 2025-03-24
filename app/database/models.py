import datetime

from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger)
    # username = mapped_column(String(255))

class MuscleGroup(Base):
    __tablename__ = 'muscle_groups'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class Exercise(Base):
    __tablename__ = 'exercises'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    muscle_group_id: Mapped[int] = mapped_column(ForeignKey('muscle_groups.id'))


class Sets(Base):
    __tablename__ = 'sets'

    id: Mapped[int] = mapped_column(primary_key=True)
    set_number: Mapped[int]
    weight: Mapped[float]
    reps: Mapped[int]
    exercise_id: Mapped[int] = mapped_column(ForeignKey('exercises.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    # workout_id: Mapped[int] = mapped_column(ForeignKey('workouts.id'), nullable=False)


# Создание всех таблиц
async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
