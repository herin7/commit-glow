"""commit-glow: your GitHub contribution graph on your keyboard and mouse RGB."""
import argparse, datetime, pathlib, subprocess, sys, time

from . import core
from .backends import discover

POLL = 300  # seconds


def render(devices, today, weeks):
    now = datetime.datetime.now()
    for d in list(devices):
        try:
            if hasattr(d, 'show_grid'):
                d.show_grid(core.grid(weeks, today, now, d.rows, d.cols))
            else:
                d.show_color(core.status_color(today, now))
        except Exception as e:
            print(f'{d.name}: {e}', file=sys.stderr)
            devices.remove(d)  # unplugged / mode switched: rediscover next poll


def run(_):
    devices, today, weeks = [], 0, []
    while True:
        try:
            today, weeks = core.fetch()
        except Exception as e:
            print(f'github: {e}', file=sys.stderr)  # offline: keep last data
        devices = devices or discover()
        render(devices, today, weeks)
        time.sleep(POLL)


def demo(_):
    """Today shown as a missed day for 15 s, then the real picture."""
    devices, (today, weeks) = discover(), core.fetch()
    render(devices, 0, weeks)
    time.sleep(15)
    render(devices, today, weeks)


def devices(_):
    found = discover()
    for d in found:
        print(f"{d.name}: {f'{d.rows}x{d.cols} grid' if hasattr(d, 'show_grid') else 'single color'}")
    if not found:
        print('No devices. For non-native hardware, start OpenRGB with its SDK server enabled.')


def restore(_):
    for d in discover():
        d.restore()


def autostart(args):
    cmd = f'{pathlib.Path(sys.executable).with_name("pythonw.exe")} -m commit_glow run'
    if sys.platform == 'win32':
        lnk = pathlib.Path.home() / r'AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\commit-glow.lnk'
        if args.remove:
            lnk.unlink(missing_ok=True)
            return print('autostart removed')
        exe = pathlib.Path(sys.executable).with_name('pythonw.exe')
        home = pathlib.Path(__file__).resolve().parent.parent  # so `-m commit_glow` resolves even without pip install
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
              f"$s.TargetPath='{exe}';$s.Arguments='-m commit_glow run';$s.WorkingDirectory='{home}';$s.Save()")
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
        print(f'autostart: {lnk}')
    else:
        print('Add this to your login items / a systemd user service:\n  ' + cmd.replace('pythonw.exe', 'python3'))


def main():
    p = argparse.ArgumentParser(prog='commit-glow', description=__doc__)
    sub = p.add_subparsers(required=True)
    for name, fn in [('run', run), ('demo', demo), ('devices', devices), ('restore', restore)]:
        sub.add_parser(name, help=fn.__doc__).set_defaults(fn=fn)
    a = sub.add_parser('autostart', help='start `run` at login')
    a.add_argument('--remove', action='store_true')
    a.set_defaults(fn=autostart)
    args = p.parse_args()
    args.fn(args)
