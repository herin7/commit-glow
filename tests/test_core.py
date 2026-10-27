import datetime

from commit_glow.core import MISSED, grid, green, row_of, status_color

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


if __name__ == '__main__':
    test_colors(); test_rows(); test_grid()
    print('ok')
