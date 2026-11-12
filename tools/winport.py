"""Helpers to port FM Blog Classic Skin Windows XOR patches onto Mac bundles."""
import gzip, hashlib, struct, sys
import numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from unityfs import Bundle, sf_platform_offset

D = '/Users/jordandevogelaere/Downloads/FM27-Classic-Skin-Windows-Build134/Data'
BK = '/Users/jordandevogelaere/Sources/fm27/backups/27.0.1.2494769-steam26385295/aa/StandaloneOSX'
ROWS = {l.split('\t')[1].split('/')[-1]: l.rstrip('\n').split('\t') for l in open(D + '/files.tsv') if l.startswith('game\t')}


def to_platform(raw, plat):
    b = Bundle(raw); new = []
    for i, (off, sz, fl, name) in enumerate(b.nodes):
        sf = bytearray(b.node_bytes(i))
        if fl & 4:
            po, _ = sf_platform_offset(sf); sf[po:po + 4] = struct.pack('<i', plat)
        new.append(bytes(sf))
    b.replace_nodes(new); return b.save()


def delta(name):
    return np.frombuffer(gzip.decompress(open(f'{D}/payload/{ROWS[name][4]}', 'rb').read()), dtype=np.uint8)


def xor(base, d):
    pad = np.zeros(len(d), dtype=np.uint8); k = min(len(base), len(d))
    pad[:k] = np.frombuffer(base, dtype=np.uint8)[:k]
    return (pad ^ d).tobytes()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse_patched(P, wlen):
    """Parse a patched bundle P (flags 0xc2: LZ4, blocks info at end). Returns blocks with decoded data
    for those lying entirely beyond wlen (plaintext region), else None."""
    import lz4.block
    from unityfs import _cstr
    sig, p = _cstr(P, 0); p += 4; uv, p = _cstr(P, p); ur, p = _cstr(P, p)
    size, csz, usz, flags = struct.unpack('>QIII', P[p:p + 20]); p += 20
    p = (p + 15) // 16 * 16
    assert flags & 0x80
    bir = lz4.block.decompress(P[len(P) - csz:], uncompressed_size=usz)
    q = 16; nb = struct.unpack('>I', bir[q:q + 4])[0]; q += 4
    blocks = [struct.unpack('>IIH', bir[q + i * 10:q + i * 10 + 10]) for i in range(nb)]; q += nb * 10
    nn = struct.unpack('>I', bir[q:q + 4])[0]; q += 4
    nodes = []
    for _ in range(nn):
        off, sz, fl = struct.unpack('>QQI', bir[q:q + 20]); q += 20
        name, q = _cstr(bir, q); nodes.append((off, sz, fl, name))
    out = []; cpos = p; upos = 0
    for u, c, f in blocks:
        data = None
        if cpos >= wlen:
            ch = P[cpos:cpos + c]
            data = lz4.block.decompress(ch, uncompressed_size=u) if f & 0x3F in (2, 3) else ch
        out.append((upos, u, cpos, c, f, data)); cpos += c; upos += u
    return dict(header=(size, csz, usz, flags, p), nodes=nodes, blocks=out)


def find_tail_blocksinfo(P, max_csz=60000):
    import lz4.block
    for csz in range(20, max_csz):
        try:
            bir = lz4.block.decompress(P[len(P) - csz:], uncompressed_size=1 << 20)
        except Exception:
            continue
        nb = struct.unpack('>I', bir[16:20])[0]
        if 0 < nb < 200000 and len(bir) >= 24 + nb * 10:
            blocks = [struct.unpack('>IIH', bir[20 + i * 10:30 + i * 10]) for i in range(nb)]
            if all(0 < u <= 1 << 20 and 0 < c <= 1 << 21 for u, c, f in blocks) and \
                    len(P) - csz - sum(c for _, c, _ in blocks) in (48, 64, 80, 96):
                q = 20 + nb * 10; nn = struct.unpack('>I', bir[q:q + 4])[0]; q += 4
                nodes = []
                for _ in range(nn):
                    off, sz, fl = struct.unpack('>QQI', bir[q:q + 20]); q += 20
                    e = bir.index(b'\0', q); nodes.append((off, sz, fl, bir[q:e])); q = e + 1
                return csz, blocks, nodes, len(P) - csz - sum(c for _, c, _ in blocks)
    raise ValueError('blocks info not found')


def decode_plain_blocks(P, wlen):
    import lz4.block
    csz, blocks, nodes, start = find_tail_blocksinfo(P)
    out = []; cpos = start; upos = 0
    for u, c, f in blocks:
        data = None
        if cpos >= wlen:
            ch = P[cpos:cpos + c]
            data = lz4.block.decompress(ch, uncompressed_size=u) if f & 0x3F in (2, 3) else ch
        out.append((upos, u, cpos, c, f, data)); cpos += c; upos += u
    return dict(csz=csz, nodes=nodes, start=start, blocks=out)


def port_to_mac(P_bytes):
    """Take a reconstructed Windows patched bundle and retag it for macOS (platform 2), LZ4HC blocks."""
    from unityfs import Bundle
    return to_platform(normalise(P_bytes), 2)


def normalise(raw):
    """Re-encode any UnityFS v8 bundle (blocks info at end / LZ4 fast) into the stock FM layout."""
    import lz4.block
    from unityfs import Bundle, _cstr
    sig, p = _cstr(raw, 0); p += 4; uv, p = _cstr(raw, p); ur, p = _cstr(raw, p)
    size, csz, usz, flags = struct.unpack('>QIII', raw[p:p + 20]); p += 20
    p = (p + 15) // 16 * 16
    if flags & 0x80:
        bi = raw[len(raw) - csz:]
    else:
        bi = raw[p:p + csz]; p += csz
    bir = lz4.block.decompress(bi, uncompressed_size=usz) if flags & 0x3F in (2, 3) else bi
    q = 16; nb = struct.unpack('>I', bir[q:q + 4])[0]; q += 4
    blocks = [struct.unpack('>IIH', bir[q + i * 10:q + i * 10 + 10]) for i in range(nb)]; q += nb * 10
    nn = struct.unpack('>I', bir[q:q + 4])[0]; q += 4
    nodes = []
    for _ in range(nn):
        off, sz, fl = struct.unpack('>QQI', bir[q:q + 20]); q += 20
        e = bir.index(b'\0', q); nodes.append([off, sz, fl, bir[q:e]]); q = e + 1
    if flags & 0x200:
        p = (p + 15) // 16 * 16
    data = bytearray()
    for u, c, f in blocks:
        ch = raw[p:p + c]; p += c
        data += lz4.block.decompress(ch, uncompressed_size=u) if f & 0x3F in (2, 3) else ch
    b = Bundle.__new__(Bundle)
    b.sig, b.ver, b.uv, b.ur = sig, 8, uv, ur
    b.flags = 0x243; b.bi_hash = bir[:16]; b.nodes = nodes; b.data = bytes(data); b.block_size = 131072
    return b.save()


def merge_objects(base_path, skin_bytes, old_path):
    """3-way object merge: start from base (new Mac stock), apply every object the skin changed/added
    relative to old (old Mac stock). Refuses objects changed by both. Returns new bundle bytes + report."""
    import UnityPy, tempfile, os
    def load(b):
        env = UnityPy.load(b); return env, {o.path_id: o for o in env.objects}
    _, old = load(old_path)
    tmp = tempfile.NamedTemporaryFile(suffix='.bundle', delete=False); tmp.write(skin_bytes); tmp.close()
    _, skin = load(tmp.name); os.unlink(tmp.name)
    env, base = load(base_path)
    report = {'replaced': [], 'conflicts': [], 'added': [], 'removed': []}
    for pid, so in skin.items():
        if pid not in old:
            report['added'].append(pid); continue
        sraw = so.get_raw_data(); oraw = old[pid].get_raw_data()
        if sraw == oraw:
            continue
        if base[pid].get_raw_data() != oraw:
            report['conflicts'].append((pid, so.type.name)); continue
        base[pid].set_raw_data(sraw); report['replaced'].append((pid, so.type.name))
    report['removed'] = [pid for pid in old if pid not in skin]
    if report['added'] or report['removed'] or report['conflicts']:
        return None, report
    return normalise(env.file.save()), report
