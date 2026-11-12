"""Minimal byte-exact UnityFS (version 8) reader/writer for FM27 bundles (LZ4HC level 12 blocks)."""
import struct
import lz4.block

HC = 12


def _cstr(b, p):
    e = b.index(b"\0", p)
    return b[p:e], e + 1


class Bundle:
    def __init__(self, raw):
        b = raw
        self.sig, p = _cstr(b, 0)
        self.ver = struct.unpack(">I", b[p:p + 4])[0]; p += 4
        self.uv, p = _cstr(b, p)
        self.ur, p = _cstr(b, p)
        self.size, csz, usz, self.flags = struct.unpack(">QIII", b[p:p + 20]); p += 20
        assert self.ver >= 7 and not self.flags & 0x80
        p = (p + 15) // 16 * 16
        bi = b[p:p + csz]; p += csz
        assert self.flags & 0x3F == 3
        bir = lz4.block.decompress(bi, uncompressed_size=usz)
        self.bi_hash = bir[:16]
        q = 16
        n = struct.unpack(">I", bir[q:q + 4])[0]; q += 4
        self.blocks = [struct.unpack(">IIH", bir[q + i * 10:q + i * 10 + 10]) for i in range(n)]; q += n * 10
        n = struct.unpack(">I", bir[q:q + 4])[0]; q += 4
        self.nodes = []
        for _ in range(n):
            off, sz, fl = struct.unpack(">QQI", bir[q:q + 20]); q += 20
            name, q = _cstr(bir, q)
            self.nodes.append([off, sz, fl, name])
        if self.flags & 0x200:
            p = (p + 15) // 16 * 16
        data = bytearray()
        for u, c, f in self.blocks:
            chunk = b[p:p + c]; p += c
            data += lz4.block.decompress(chunk, uncompressed_size=u) if f & 0x3F in (2, 3) else chunk
        self.data = bytes(data)
        self.block_size = self.blocks[0][0] if self.blocks else 131072

    def node_bytes(self, i):
        off, sz, _, _ = self.nodes[i]
        return self.data[off:off + sz]

    def replace_nodes(self, new):
        """new: list of bytes per node, same order. Re-lays nodes back to back."""
        data = bytearray(); off = 0
        for n, nb in zip(self.nodes, new):
            n[0], n[1] = off, len(nb); data += nb; off += len(nb)
        self.data = bytes(data)

    def save(self):
        blocks, comp = [], bytearray()
        for i in range(0, len(self.data), self.block_size):
            raw = self.data[i:i + self.block_size]
            c = lz4.block.compress(raw, mode="high_compression", compression=HC, store_size=False)
            if len(c) >= len(raw):
                blocks.append((len(raw), len(raw), 0x40)); comp += raw
            else:
                blocks.append((len(raw), len(c), 3)); comp += c
        bir = bytearray(self.bi_hash) + struct.pack(">I", len(blocks))
        for u, c, f in blocks:
            bir += struct.pack(">IIH", u, c, f)
        bir += struct.pack(">I", len(self.nodes))
        for off, sz, fl, name in self.nodes:
            bir += struct.pack(">QQI", off, sz, fl) + name + b"\0"
        bic = lz4.block.compress(bytes(bir), mode="high_compression", compression=HC, store_size=False)
        head = self.sig + b"\0" + struct.pack(">I", self.ver) + self.uv + b"\0" + self.ur + b"\0"
        hlen = len(head) + 20
        hpad = (hlen + 15) // 16 * 16 - hlen
        after_bi = hlen + hpad + len(bic)
        dpad = ((after_bi + 15) // 16 * 16 - after_bi) if self.flags & 0x200 else 0
        total = after_bi + dpad + len(comp)
        out = head + struct.pack(">QIII", total, len(bic), len(bir), self.flags) + b"\0" * hpad + bic + b"\0" * dpad + bytes(comp)
        return out


def sf_platform_offset(sf):
    """Offset of m_TargetPlatform in a SerializedFile (format >= 22)."""
    fmt = struct.unpack(">I", sf[8:12])[0]
    assert fmt >= 22, fmt
    p = 48  # 16 legacy + 4 metadata size + 8 file size + 8 data offset + 8 unknown + 4? -> v22 header is 48 bytes
    e = sf.index(b"\0", p)
    return e + 1, sf[p:e]
