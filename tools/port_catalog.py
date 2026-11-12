#!/usr/bin/env python3
"""Port the Classic Skin's catalog.bin additions (appended keys/locations in the Windows catalog)
onto the current Mac catalog. Output: packages/fm27-classic-mac/catalog.bin"""
import struct, collections, sys
W = open('windows-originals/fm_Data/StreamingAssets/aa/catalog.bin', 'rb').read()
P = open('debug/winpatched/catalog.bin', 'rb').read()
N = open('backups/27.0.1.2503222-steam26577676/aa/catalog.bin', 'rb').read()
FLAGS = 0xC0000000
u = lambda b, o, n=1: struct.unpack_from(f'<{n}I', b, o)
ptr = lambda v: v & ~FLAGS


def keys(b):
    off = u(b, 8)[0]; ln = u(b, off - 4)[0]
    return [u(b, off + i * 8, 2) for i in range(ln // 8)], off


def locs(b, setoff):
    return [u(b, lo, 7) for lo in u(b, setoff, u(b, setoff - 4)[0] // 4)]


kw, ow = keys(W); kp, op = keys(P); kn, on = keys(N)
assert P[12:len(W)] == W[12:] and kp[:len(kw)] == kw and len(kw) == len(kn)

# 1. map old-region Windows offsets to Mac offsets by walking both stock key tables in parallel
m = collections.defaultdict(collections.Counter)
for (wk, wl), (nk, nl) in zip(kw, kn):
    m[u(W, wk)[0]][u(N, nk)[0]] += 1                       # key type object
    lw, ln_ = locs(W, wl), locs(N, nl)
    assert len(lw) == len(ln_)
    for a, b in zip(lw, ln_):
        for i in (2, 3, 6):                                # provider, dependency set, resource type
            if a[i] != 0xFFFFFFFF:
                m[a[i]][b[i]] += 1
amb = {k: v for k, v in m.items() if len(v) > 1}
print('mapped offsets:', len(m), 'ambiguous:', len(amb))

# 2. walk the skin's new keys, classifying every word of the appended block
shift = len(N) - len(W)
tail = bytearray(P[len(W):op - 4])
role = {}
def mark(off, r):
    assert role.setdefault(off, r) == r, (off, r)
def fix_new(off):   # pointer into the appended block
    v = u(P, off)[0]; assert len(W) <= ptr(v) < len(P), hex(v); mark(off, ('new', v))
def fix_old(off):
    v = u(P, off)[0]
    if v == 0xFFFFFFFF: mark(off, ('raw', v)); return
    assert v in m and len(m[v]) == 1, ('unmapped/ambiguous', hex(v), dict(m.get(v, {})))
    mark(off, ('old', v))
def raw(off, n=4):
    for i in range(0, n, 4): mark(off + i, ('raw', None))
def string(off):
    n = u(P, off - 4)[0]; raw(off - 4, 4 + (n + 3) // 4 * 4)
used = collections.Counter()
for ko, lo in kp[len(kw):]:
    fix_old(ko); fix_new(ko + 4)                           # key object: type, data
    d = u(P, ko + 4)[0]
    so, sep = u(P, d, 2); assert sep == 0 and not so & FLAGS
    fix_new(d); raw(d + 4); string(so)
    n = u(P, lo - 4)[0]; raw(lo - 4)
    for i in range(n // 4):
        fix_new(lo + i * 4)
        l = u(P, lo + i * 4)[0]; f = u(P, l, 7)
        for j in (0, 1):
            assert not f[j] & FLAGS; fix_new(l + j * 4); string(f[j])
        fix_old(l + 8); fix_old(l + 12); raw(l + 16); fix_old(l + 24)
        assert f[5] == 0xFFFFFFFF; raw(l + 20)
        used[(f[2], f[3], f[6])] += 1
covered = sorted(role)
assert covered == list(range(len(W), op - 4, 4)), 'appended block has bytes this script does not understand'
print('location kinds (provider, deps, type):', {tuple(hex(x) for x in k): v for k, v in used.items()})

out = bytearray(N)
for off, (r, v) in role.items():
    if r == 'new': nv = v + shift
    elif r == 'old': nv = next(iter(m[v]))
    else: continue
    struct.pack_into('<I', tail, off - len(W), nv)
out += tail
new_keys = b''.join(struct.pack('<II', a, b) for a, b in kn) + \
           b''.join(struct.pack('<II', a + shift, b + shift) for a, b in kp[len(kw):])
out += struct.pack('<I', len(new_keys)) + new_keys
struct.pack_into('<I', out, 8, len(N) + len(tail) + 4)
assert len(out) - len(N) == len(P) - len(W)
open('packages/fm27-classic-mac/catalog.bin', 'wb').write(out)

# 3. verify: every new key resolves in the Mac catalog to the same thing as in the Windows one
def s(b, o): return b[o:o + u(b, o - 4)[0]]
def deps_names(b, dso):
    import re
    names = []
    for lo in u(b, dso, u(b, dso - 4)[0] // 4):
        f = u(b, lo, 7); names.append(re.sub(rb'[^\x20-\x7e]', b'', b[ptr(f[0]) - 0:ptr(f[0]) + 0] ) or lo)
    return len(names)
ko2, _ = keys(bytes(out)), None
k2 = ko2[0]
assert k2[:len(kn)] == kn
bad = 0
for (pk, pl), (mk, ml) in zip(kp[len(kw):], k2[len(kn):]):
    ps = s(P, u(P, u(P, pk + 4)[0])[0]); ms = s(out, u(out, u(out, mk + 4)[0])[0])
    pls, mls = locs(P, pl), locs(out, ml)
    ok = ps == ms and len(pls) == len(mls) and all(s(P, a[0]) == s(out, b[0]) and s(P, a[1]) == s(out, b[1]) and
        u(P, a[3] - 4) == u(out, b[3] - 4) for a, b in zip(pls, mls))
    bad += not ok
print('new keys:', len(k2) - len(kn), 'mismatching:', bad, 'size', len(out))
