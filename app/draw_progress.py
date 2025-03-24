import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io


# Функция для генерации графика прогресса
def generate_progress_plot(data):
    dates = [entry[3].date() for entry in data]  # Предполагаем, что entry[0] уже объект datetime
    weights = [entry[1] for entry in data]
    reps = [entry[2] for entry in data]
    exercise_name = data[0][4]

    plt.figure(figsize=(12, 6))  # Увеличиваем размер графика для лучшей визуализации
    plt.plot_date(dates, weights, 'g-', marker='o')
    # plt.plot(dates, weights, marker='o', color='b', label='Max Weight')

    # Добавляем аннотации к точкам
    for i, txt in enumerate(weights):
        plt.annotate(f'{txt}x{reps[i]}',(dates[i], weights[i]), xytext=(0, 5), textcoords='offset points', color='black')

    plt.xlabel("Дата тренировки")
    plt.ylabel("Вес (кг)")
    plt.title(f"Прогресс по максимальному весу - {exercise_name}")

    # Форматирование дат на оси X
    # Автоматическая подборка интервалов и формата дат на оси X
    ax = plt.gca()
    locator = mdates.AutoDateLocator()
    formatter = mdates.AutoDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.grid()

    # Легенда и сохранение графика
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close()

    return buf