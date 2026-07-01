import io
from datetime import timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def generate_progress_plot(data):
    dates = [entry[3].date() for entry in data]
    weights = [entry[1] for entry in data]
    reps = [entry[2] for entry in data]
    exercise_name = data[0][4]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))

    accent = '#00C9A7'

    ax.plot(dates, weights, color=accent, linewidth=2.5, marker='o',
            markersize=8, markerfacecolor='white', markeredgecolor=accent,
            markeredgewidth=2, zorder=3)

    # Градиентная заливка под линией
    ax.fill_between(dates, weights, alpha=0.15, color=accent)

    # Аннотации к точкам
    for i in range(len(dates)):
        ax.annotate(
            f'{weights[i]} кг × {reps[i]}',
            xy=(dates[i], weights[i]),
            xytext=(0, 12),
            textcoords='offset points',
            ha='center',
            fontsize=9,
            color='white',
            fontweight='bold',
        )

    # Диапазон осей с отступами
    if len(dates) > 1:
        padding = (max(dates) - min(dates)) * 0.1
        ax.set_xlim(min(dates) - padding, max(dates) + padding)
    else:
        ax.set_xlim(dates[0] - timedelta(days=7), dates[0] + timedelta(days=7))

    weight_range = max(weights) - min(weights) if len(weights) > 1 else max(weights) * 0.1 or 1
    ax.set_ylim(min(weights) - weight_range * 0.4, max(weights) + weight_range * 0.6)

    # Форматирование дат
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    plt.xticks(rotation=30, ha='right', fontsize=9)

    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))

    ax.set_xlabel('Дата тренировки', labelpad=10, fontsize=11)
    ax.set_ylabel('Вес (кг)', labelpad=10, fontsize=11)
    ax.set_title(f'{exercise_name}', fontsize=14, fontweight='bold', pad=15)

    ax.grid(True, linestyle='--', alpha=0.3, color='gray')
    ax.set_facecolor('#1a1a2e')
    fig.patch.set_facecolor('#1a1a2e')

    for spine in ax.spines.values():
        spine.set_edgecolor('#333355')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf
