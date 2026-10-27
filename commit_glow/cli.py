"""commit-glow: your GitHub contribution graph on your keyboard and mouse RGB."""
import argparse, datetime, pathlib, subprocess, sys, time

from . import core
from .backends import discover

POLL = 300  # seconds


def render(devices, today, weeks):
    now = datetime.datetime.now()
    for d in list(devices):
        try:
            if hasattr(d, 'show_days'):
                d.show_days([core.green(n) if n else core.MISSED for _, n in core.days(weeks, today, now)])
            elif hasattr(d, 'show_grid'):
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


def keymap(_):
    """Which key shows which day (one-key-per-day keyboards)."""
    today, weeks = core.fetch()
    ds = core.days(weeks, today, datetime.datetime.now())
    for d in discover():
        if hasattr(d, 'labels'):
            print(d.name)
            for label, (date, n) in zip(d.labels[-len(ds):], ds[-len(d.labels):]):
                print(f'  {label:<7} {date}  {n:>4}  {"missed" if n == 0 else ""}')


def devices(_):
    found = discover()
    for d in found:
        kind = (f'{len(d.keys)} keys, one per day' if hasattr(d, 'show_days') else
                f'{d.rows}x{d.cols} grid' if hasattr(d, 'show_grid') else 'single color')
        print(f'{d.name}: {kind}')
    if not found:
        print('No devices. For non-native hardware, start OpenRGB with its SDK server enabled.')


def restore(_):
    for d in discover():
        d.restore()


def probe(_):
    """Every HID device and interface, as JSON: the starting point for supporting new hardware."""
    import hid, json
    rows = [{'vid': f"{d['vendor_id']:04x}", 'pid': f"{d['product_id']:04x}", 'product': d['product_string'],
             'manufacturer': d['manufacturer_string'], 'interface': d['interface_number'],
             'usage_page': f"{d['usage_page']:04x}", 'usage': f"{d['usage']:04x}",
             'vendor_defined': d['usage_page'] >= 0xFF00} for d in hid.enumerate()]
    print(json.dumps(sorted(rows, key=lambda r: (r['vid'], r['pid'], r['usage_page'])), indent=1))


def autostart(args):
    home = pathlib.Path(__file__).resolve().parent.parent  # so `-m commit_glow` resolves even without pip install
    if sys.platform == 'win32':
        lnk = pathlib.Path.home() / r'AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\commit-glow.lnk'
        if args.remove:
            lnk.unlink(missing_ok=True)
            return print('autostart removed')
        exe = pathlib.Path(sys.executable).with_name('pythonw.exe')
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
              f"$s.TargetPath='{exe}';$s.Arguments='-m commit_glow run';$s.WorkingDirectory='{home}';$s.Save()")
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
        print(f'autostart: {lnk}')
    elif sys.platform == 'darwin':
        plist = pathlib.Path.home() / 'Library/LaunchAgents/com.commit-glow.plist'
        if args.remove:
            subprocess.run(['launchctl', 'unload', str(plist)])
            plist.unlink(missing_ok=True)
            return print('autostart removed')
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.commit-glow</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>-m</string><string>commit_glow</string><string>run</string></array>
<key>WorkingDirectory</key><string>{home}</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
</dict></plist>
''')
        subprocess.run(['launchctl', 'load', '-w', str(plist)], check=True)
        print(f'autostart: {plist}')
    else:  # Linux: systemd user service
        unit = pathlib.Path.home() / '.config/systemd/user/commit-glow.service'
        if args.remove:
            subprocess.run(['systemctl', '--user', 'disable', '--now', 'commit-glow'])
            unit.unlink(missing_ok=True)
            return print('autostart removed')
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text(f'[Unit]\nDescription=commit-glow\nAfter=network-online.target\n\n'
                        f'[Service]\nExecStart={sys.executable} -m commit_glow run\nWorkingDirectory={home}\nRestart=on-failure\n\n'
                        f'[Install]\nWantedBy=default.target\n')
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', '--now', 'commit-glow'], check=True)
        print(f'autostart: {unit}')


def main():
    p = argparse.ArgumentParser(prog='commit-glow', description=__doc__)
    sub = p.add_subparsers(required=True)
    for name, fn in [('run', run), ('demo', demo), ('devices', devices), ('map', keymap), ('probe', probe), ('restore', restore)]:
        sub.add_parser(name, help=fn.__doc__).set_defaults(fn=fn)
    a = sub.add_parser('autostart', help='start `run` at login')
    a.add_argument('--remove', action='store_true')
    a.set_defaults(fn=autostart)
    args = p.parse_args()
    args.fn(args)
