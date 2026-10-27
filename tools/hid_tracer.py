# Windows only. Minimal debugger: attach to a running 32-bit (WoW64) vendor app, breakpoint its HID write APIs
# (HidD_SetOutputReport, HidD_SetFeature, WriteFile), log every packet it sends, then detach and leave the app running.
# Use it to learn a keyboard's lighting protocol: run it, change one setting in the vendor app, read the log.
# usage: python tools/hid_tracer.py <pid> <logfile> <seconds>
import ctypes, struct, sys, time
from ctypes import wintypes as W

k = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi')
k.OpenProcess.restype = W.HANDLE
k.OpenThread.restype = W.HANDLE

class FLOAT_SAVE(ctypes.Structure):
    _fields_ = [('c', W.DWORD * 7), ('RegisterArea', ctypes.c_ubyte * 80), ('Cr0NpxState', W.DWORD)]

class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [('ContextFlags', W.DWORD), ('Dr', W.DWORD * 6), ('FloatSave', FLOAT_SAVE),
                ('SegGs', W.DWORD), ('SegFs', W.DWORD), ('SegEs', W.DWORD), ('SegDs', W.DWORD),
                ('Edi', W.DWORD), ('Esi', W.DWORD), ('Ebx', W.DWORD), ('Edx', W.DWORD), ('Ecx', W.DWORD), ('Eax', W.DWORD),
                ('Ebp', W.DWORD), ('Eip', W.DWORD), ('SegCs', W.DWORD), ('EFlags', W.DWORD), ('Esp', W.DWORD), ('SegSs', W.DWORD),
                ('Ext', ctypes.c_ubyte * 512)]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [('code', W.DWORD), ('pid', W.DWORD), ('tid', W.DWORD), ('pad', W.DWORD), ('u', ctypes.c_ubyte * 176)]

CTX_FULL = 0x10007
BP_CODES = (0x80000003, 0x4000001F)   # breakpoint, WX86 breakpoint
SS_CODES = (0x80000004, 0x4000001E)   # single step, WX86 single step
DBG_CONTINUE, DBG_NOT_HANDLED = 0x00010002, 0x80010001

pid, logpath, secs = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
hp = k.OpenProcess(0x1F0FFF, False, pid)
log = open(logpath, 'a', encoding='utf-8')

def rd(addr, n):
    buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
    k.ReadProcessMemory(W.HANDLE(hp), ctypes.c_void_p(addr), buf, n, ctypes.byref(got))
    return buf.raw[:got.value]

def wr(addr, data):
    k.WriteProcessMemory(W.HANDLE(hp), ctypes.c_void_p(addr), data, len(data), None)
    k.FlushInstructionCache(W.HANDLE(hp), ctypes.c_void_p(addr), len(data))

def modules32():
    arr = (ctypes.c_void_p * 1024)(); need = W.DWORD()
    psapi.EnumProcessModulesEx(W.HANDLE(hp), arr, ctypes.sizeof(arr), ctypes.byref(need), 1)  # LIST_MODULES_32BIT
    out = {}
    for m in arr[:need.value // ctypes.sizeof(ctypes.c_void_p)]:
        name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(W.HANDLE(hp), ctypes.c_void_p(m), name, 260)
        out[name.value.lower()] = m
    return out

def export(base, want):
    nt = base + struct.unpack('<I', rd(base + 0x3C, 4))[0]
    erva = struct.unpack('<I', rd(nt + 0x78, 4))[0]
    e = rd(base + erva, 40)
    n, funcs, names, ords = struct.unpack('<IIII', e[0x18:0x28])
    nrvas = struct.unpack(f'<{n}I', rd(base + names, 4 * n))
    for i, r in enumerate(nrvas):
        if rd(base + r, len(want) + 1) == want.encode() + b'\0':
            o = struct.unpack('<H', rd(base + ords + 2 * i, 2))[0]
            return base + struct.unpack('<I', rd(base + funcs + 4 * o, 4))[0]

assert k.DebugActiveProcess(pid), ctypes.get_last_error()
k.DebugSetProcessKillOnExit(False)
mods = modules32()
targets = {}
for mod, fn, argi in (('hid.dll', 'HidD_SetOutputReport', (1, 2)), ('kernelbase.dll', 'WriteFile', (1, 2)), ('hid.dll', 'HidD_SetFeature', (1, 2))):
    if mod in mods:
        a = export(mods[mod], fn)
        if a:
            targets[a] = (fn, argi, rd(a, 1))
print('targets', {fn: hex(a) for a, (fn, _, _) in targets.items()}, flush=True)
for a in targets:
    wr(a, b'\xCC')

rearm = {}  # tid -> addr to re-arm after single-step
ev = DEBUG_EVENT()
end = time.time() + secs
while time.time() < end:
    if not k.WaitForDebugEvent(ctypes.byref(ev), 300):
        continue
    status = DBG_CONTINUE
    if ev.code == 1:  # exception
        code, addr = struct.unpack('<I', bytes(ev.u[0:4]))[0], struct.unpack('<Q', bytes(ev.u[16:24]))[0]
        if code in BP_CODES and addr in targets:
            fn, (ib, il), orig = targets[addr]
            ht = k.OpenThread(0x1FFFFF, False, ev.tid)
            ctx = WOW64_CONTEXT(); ctx.ContextFlags = CTX_FULL
            k.Wow64GetThreadContext(W.HANDLE(ht), ctypes.byref(ctx))
            args = struct.unpack('<5I', rd(ctx.Esp, 20))  # ret, a1, a2, a3, a4
            buf, n = args[1 + ib], args[1 + il]
            if 8 <= n <= 65:
                log.write(f'{time.time():.3f} {fn} n={n} {rd(buf, n).hex(" ")}\n'); log.flush()
            wr(addr, orig)
            ctx.Eip = addr; ctx.EFlags |= 0x100
            k.Wow64SetThreadContext(W.HANDLE(ht), ctypes.byref(ctx))
            k.CloseHandle(W.HANDLE(ht))
            rearm[ev.tid] = addr
        elif code in SS_CODES and ev.tid in rearm:
            wr(rearm.pop(ev.tid), b'\xCC')
        elif code not in BP_CODES:
            status = DBG_NOT_HANDLED
    elif ev.code in (3, 6):  # create process / load dll: close the file handle we were given
        h = struct.unpack('<Q', bytes(ev.u[0:8]))[0]
        if h:
            k.CloseHandle(W.HANDLE(h))
    k.ContinueDebugEvent(ev.pid, ev.tid, status)

for a, (_, _, orig) in targets.items():
    wr(a, orig)
# drain pending single-steps briefly, then detach
t = time.time() + 1
while rearm and time.time() < t:
    if k.WaitForDebugEvent(ctypes.byref(ev), 100):
        code = struct.unpack('<I', bytes(ev.u[0:4]))[0]
        rearm.pop(ev.tid, None) if ev.code == 1 and code in SS_CODES else None
        k.ContinueDebugEvent(ev.pid, ev.tid, DBG_CONTINUE)
k.DebugActiveProcessStop(pid)
print('detached', flush=True)
