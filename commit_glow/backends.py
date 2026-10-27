"""Devices. Grid devices (keyboards) have rows/cols/show_grid(); color devices (mice etc.) have show_color().
Native drivers cover hardware OpenRGB doesn't; everything else goes through a running OpenRGB SDK server."""
import json, os, pathlib, sys

STATE = pathlib.Path(os.environ.get('APPDATA') or pathlib.Path.home() / '.config') / 'commit-glow'


class EVision:
    """EVision-chip keyboards with the EvoFox-style firmware (protocol in PROTOCOLS.md). Per-key, via Custom mode."""
    KNOWN = {(0x320F, 0x5055): 'EvoFox Ronin TKL'}
    rows, cols, stride = 6, 17, 21  # LED index = row * 21 + column

    def __init__(self, vid, pid, path):
        import hid
        self.name, self.h, self.last = self.KNOWN[vid, pid], hid.device(), None
        self.h.open_path(path)
        self.backup = STATE / f'evision-{vid:04x}-{pid:04x}.json'
        cfg = bytearray(self.query(0x05, size=0x27))
        if not self.backup.exists():  # first run: keep the user's settings for `commit-glow restore`
            STATE.mkdir(parents=True, exist_ok=True)
            colors = b''.join(self.query(0x0A, o, size=56) for o in range(0, 384, 56))
            self.backup.write_text(json.dumps({'config_0_0x27': cfg.hex(), 'custom_colorset0': colors.hex()}))
        if cfg[1] != 0x13 or cfg[2] != 4:
            cfg[1], cfg[2] = 0x13, 4  # Custom mode, max brightness. Never write 0x14: that's Off on this firmware.
            self.write_config(cfg)

    def query(self, cmd, offset=0, data=b'', size=None):
        b = bytearray(64)
        b[0], b[3], b[4], b[5], b[6] = 4, cmd, len(data) if size is None else size, offset & 0xFF, offset >> 8
        b[8:8 + len(data)] = data
        s = sum(b[3:])
        b[1], b[2] = s & 0xFF, s >> 8
        self.h.write(bytes(b))
        r = bytes(self.h.read(64, 1000))
        if not r or r[7]:
            raise IOError(f'{self.name} rejected cmd {cmd:#x}')
        return r[8:8 + r[4]]

    def write_config(self, cfg):
        self.query(0x01)
        self.query(0x06, 0, bytes(cfg))  # only the full block from offset 0 is accepted
        self.query(0x02)

    def write_colors(self, buf):
        for o in range(0, len(buf), 56):
            self.query(0x0B, o, bytes(buf[o:o + 56]))

    def show_grid(self, cells):
        buf = bytearray(384)
        for (r, c), rgb in cells.items():
            i = 3 * (r * self.stride + c)
            buf[i:i + 3] = bytes(rgb)
        if buf != self.last:  # colors live in flash: write only on change
            self.write_colors(buf)
            self.last = buf

    def restore(self):
        b = json.loads(self.backup.read_text())
        self.write_config(bytes.fromhex(b['config_0_0x27']))
        self.write_colors(bytes.fromhex(b['custom_colorset0']))


class LogitechG102:
    """Logitech G102/G203 LIGHTSYNC over HID++ (as in OpenRGB's G203L driver). Works in on-board memory mode,
    where G HUB's LED SDK has no effect."""
    KNOWN = {(0x046D, 0xC092): 'Logitech G102/G203 LIGHTSYNC'}

    def __init__(self, vid, pid, path):
        import hid
        self.name, self.h = self.KNOWN[vid, pid], hid.device()
        self.h.open_path(path)
        self.send(0x11, 0xFF, 0x0E, 0x50, 0x01, 0x03, 0x07)  # enable software control

    def send(self, *b):
        self.h.write(bytes(b) + bytes(20 - len(b)))
        self.h.read(20, 500)

    def show_color(self, rgb):
        self.send(0x11, 0xFF, 0x0E, 0x10, 0x00, 0x01, *rgb, 0x02, 0, 0, 0, 0, 0, 0, 0x01)

    def restore(self):
        print(f'{self.name}: unplug and replug to return to its on-board effect')


NATIVE = [(EVision, 0xFF1C, None), (LogitechG102, 0xFF00, 0x02)]  # driver, HID usage page, usage


class OpenRGBGrid:
    """An OpenRGB keyboard (or any device) with a matrix zone."""

    def __init__(self, dev, zone):
        self.name, self.dev, self.zone, self.last = dev.name, dev, zone, None
        self.rows, self.cols = zone.mat_height, zone.mat_width

    def show_grid(self, cells):
        colors = [(0, 0, 0)] * len(self.zone.leds)
        for (r, c), rgb in cells.items():
            led = self.zone.matrix_map[r][c]
            if led is not None and led < len(colors):
                colors[led] = rgb
        if colors != self.last:
            from openrgb.utils import RGBColor
            self.zone.set_colors([RGBColor(*c) for c in colors])
            self.last = colors

    def restore(self):
        print(f'{self.name}: pick a mode or profile in the OpenRGB app')


class OpenRGBColor:
    def __init__(self, dev):
        self.name, self.dev = dev.name, dev

    def show_color(self, rgb):
        from openrgb.utils import RGBColor
        self.dev.set_color(RGBColor(*rgb))

    def restore(self):
        print(f'{self.name}: pick a mode or profile in the OpenRGB app')


def discover():
    """Native devices first, then OpenRGB devices (skipping ones a native driver already took)."""
    import hid
    found, taken = [], set()
    for driver, page, usage in NATIVE:
        for vid, pid in driver.KNOWN:
            for d in hid.enumerate(vid, pid):
                if d['usage_page'] == page and usage in (None, d['usage']):
                    try:
                        found.append(driver(vid, pid, d['path']))
                        taken.add(f'vid_{vid:04x}&pid_{pid:04x}')
                    except Exception as e:
                        print(f'{driver.KNOWN[vid, pid]}: {e}', file=sys.stderr)
                    break
    try:
        from openrgb import OpenRGBClient
        from openrgb.utils import ZoneType
        client = OpenRGBClient(name='commit-glow')
    except Exception:
        return found  # OpenRGB not running: native devices only
    for dev in client.devices:
        if any(t in dev.metadata.location.lower() for t in taken):
            continue
        dev.set_custom_mode()  # direct/per-LED mode
        matrix = [z for z in dev.zones if z.type == ZoneType.MATRIX and z.matrix_map]
        found.append(OpenRGBGrid(dev, matrix[0]) if matrix else OpenRGBColor(dev))
    return found
