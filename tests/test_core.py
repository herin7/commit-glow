import datetime

from commit_glow.backends import EVision
from commit_glow.core import MISSED, days, grid, green, row_of, status_color

T = datetime.datetime(2026, 1, 1)  # a Thursday


def weeks():
    w = [[{'weekday': d, 'contributionCount': 0} for d in range(7)] for _ in range(20)]
    w[-1][1]['contributionCount'] = 4  # Monday of the newest week
    w[-2][0]['contributionCount'] = w[-2][6]['contributionCount'] = 1  # weekend of the week before
    return w


def test_colors():
    assert status_color(0, T) == (26, 0, 0) and status_color(0, T.replace(hour=23))[0] == 255
    assert status_color(1, T) == green(1) and green(50) == (0x00, 0x80, 0x10)


def test_rows():
    assert [row_of(d, 6) for d in range(7)] == [5, 0, 1, 2, 3, 4, 5]
    assert [row_of(d, 7) for d in range(7)] == [6, 0, 1, 2, 3, 4, 5]


def test_grid():
    cells = grid(weeks(), 1, T, 6, 17)
    assert len(cells) == 17 * 6 and cells[0, 0] == MISSED
    assert cells[0, 16] == green(4) and cells[5, 15] == green(2)
    assert cells[3, 16] == green(1) and grid(weeks(), 0, T, 6, 17)[3, 16] == MISSED  # Thursday = today


def test_days():
    w = [[{'date': f'2026-01-0{d}', 'weekday': d % 7, 'contributionCount': d} for d in range(1, 8)]]
    assert days(w, 9, T)[0] == ('2026-01-01', 1)
    assert days([[{'date': '2026-01-01', 'weekday': 4, 'contributionCount': 3}]], 9, T) == [('2026-01-01', 9)]  # today overridden
    w2 = [[{'date': '2025-12-31', 'weekday': 3, 'contributionCount': 5}]]
    assert days(w2, 0, T) == [('2025-12-31', 5), ('2026-01-01', 0)]  # today appended when the calendar lags


def test_evision_keys():
    assert len(EVision.keys) == len(EVision.labels) == len(set(EVision.keys)) == 79
    assert EVision.labels[EVision.keys.index(13)] == 'Del' and EVision.labels[EVision.keys.index(44)] == 'PgUp'
    assert EVision.labels[-1] == 'Right' and EVision.keys[-1] == 89


if __name__ == '__main__':
    test_colors(); test_rows(); test_grid(); test_days(); test_evision_keys()
    print('ok')
