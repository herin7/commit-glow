"""GitHub contribution data and the colors drawn from it. No hardware here."""
import datetime, json, os, subprocess, sys, urllib.request

TODAY = 'query($f:DateTime!,$t:DateTime!){viewer{contributionsCollection(from:$f,to:$t){totalCommitContributions restrictedContributionsCount}}}'
CALENDAR = '{viewer{contributionsCollection{contributionCalendar{weeks{contributionDays{weekday contributionCount}}}}}}'
# Saturated take on GitHub's graph shades (theirs look washed-out on LEDs): min count -> color, darker = more.
GREENS = [(1, 0x78ff00), (3, 0x00ff00), (6, 0x00c020), (10, 0x008010)]
MISSED = (255, 0, 0)  # a day with zero contributions


def green(count):
    hexc = [c for n, c in GREENS if count >= n][-1]
    return tuple(hexc >> s & 0xFF for s in (16, 8, 0))


def red(now):
    return round(255 * (0.1 + 0.9 * now.hour / 23))  # hourly steps, so flash-backed devices aren't rewritten every poll


def status_color(today, now):
    """Single-color devices (mice etc.): red that brightens through the day until the first commit, then green."""
    return green(today) if today else (red(now), 0, 0)


def row_of(gh_weekday, rows):
    """GitHub weekday (0 = Sunday) -> grid row, Monday on top. 6 rows: Sat+Sun share the last row."""
    m = (gh_weekday - 1) % 7  # Monday = 0 .. Sunday = 6
    return m if rows >= 7 else min(m, 5) if rows == 6 else m * rows // 7


def grid(weeks, today, now, rows, cols):
    """(row, col) -> RGB. Column = week (newest on the right), row = weekday. `today` overrides the calendar's today."""
    cells = {}
    weeks = weeks[-cols:]
    for c, week in enumerate(weeks):
        sums = [0] * rows
        for d in week:
            n = today if c == len(weeks) - 1 and d['weekday'] == now.isoweekday() % 7 else d['contributionCount']
            sums[row_of(d['weekday'], rows)] += n
        for r, n in enumerate(sums):
            cells[r, c] = green(n) if n else MISSED
    return cells


def _graphql(query, variables):
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        req = urllib.request.Request('https://api.github.com/graphql', json.dumps({'query': query, 'variables': variables}).encode(),
                                     {'Authorization': f'bearer {token}', 'Content-Type': 'application/json'})
        out = urllib.request.urlopen(req, timeout=30).read()
    else:  # fall back to the gh CLI's login
        args = ['gh', 'api', 'graphql', '-f', f'query={query}'] + [a for k, v in variables.items() for a in ('-f', f'{k}={v}')]
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        out = subprocess.run(args, capture_output=True, text=True, timeout=30, creationflags=flags, check=True).stdout
    return json.loads(out)['data']['viewer']['contributionsCollection']


def fetch():
    """(today's contributions, calendar weeks). Today counts from local midnight; private-repo work is included."""
    now = datetime.datetime.now().astimezone()
    c = _graphql(TODAY, {'f': now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(), 't': now.isoformat()})
    weeks = [w['contributionDays'] for w in _graphql(CALENDAR, {})['contributionCalendar']['weeks']]
    return c['totalCommitContributions'] + c['restrictedContributionsCount'], weeks
