#!/usr/bin/env python3
"""Build Mac versions of the Classic Skin's three layout bundles with Mac element ids.

Windows and Mac builds give layout elements different ids. Objects the skin left alone are taken
from the Mac stock bundle; objects the skin changed or added get their ids translated.
"""
import sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import UnityPy
import vtapatch  # noqa: installs the null managed-reference write fix
from winport import normalise, to_platform

W = 'windows-originals/fm_Data/StreamingAssets/aa/StandaloneWindows64/'
P = 'debug/winpatched/'
N = 'backups/27.0.1.2503222-steam26577676/aa/StandaloneOSX/'
OUT = 'packages/fm27-classic-mac/'
NAMES = ['ui-visualtreeassets_assets_%svisualtreeassetpreload.bundle' % x for x in ('gameworld', 'global', 'match')]
OWN = {'m_Id'}
REF = {'m_ParentId', 'uxmlAssetId', 'm_ElementId', 'm_ElementIdsPath', 'm_ContentContainerId'}
HASH = {'m_ContentHash'}
IDF = OWN | REF | HASH
s32 = lambda v: (v + 2**31) % 2**32 - 2**31


def pairs(a, b, key=None, path=''):
    """Yield (key, a_val, b_val) for every int leaf of two same-shaped trees; flag shape/other diffs."""
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), path
        for k in a: yield from pairs(a[k], b[k], k, path + '.' + k)
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for x, y in zip(a, b): yield from pairs(x, y, key, path)
    elif key in IDF and isinstance(a, int):
        yield key, a, b
    else:
        assert a == b, (path, a, b)


def walk(t, fn, key=None):
    if isinstance(t, dict):
        for k, v in t.items():
            if isinstance(v, (dict, list)): walk(v, fn, k)
            elif k in IDF and isinstance(v, int): t[k] = fn(k, v)
    elif isinstance(t, list):
        for i, v in enumerate(t):
            if isinstance(v, (dict, list)): walk(v, fn, key)
            elif key in IDF and isinstance(v, int): t[i] = fn(key, v)


load = lambda d, f: UnityPy.load(d + f)
envs = {f: (load(W, f), load(P, f), load(N, f)) for f in NAMES}
idmap = collections.defaultdict(set)     # windows id -> mac id(s), all layout assets
delta = {}                                # (bundle, path_id) -> mac minus windows offset of the asset's own ids
for f, (we, pe, ne) in envs.items():
    n = {o.path_id: o for o in ne.objects}
    for o in we.objects:
        if o.type.name != 'MonoBehaviour' or o.get_raw_data() == n[o.path_id].get_raw_data():
            continue
        ds = set()
        for k, a, b in pairs(o.read_typetree(), n[o.path_id].read_typetree()):
            if k in HASH: continue
            idmap[a].add(b)
            if k in OWN: ds.add((b - a) % 2**32)
        assert len(ds) <= 1, (f, o.path_id, ds)
        if ds: delta[(f, o.path_id)] = ds.pop()
amb = {k: v for k, v in idmap.items() if len(v) > 1}
print('ids mapped:', len(idmap), 'ambiguous:', len(amb), 'assets with own ids:', len(delta))
for k in amb: del idmap[k]
idmap = {k: next(iter(v)) for k, v in idmap.items()}

# pass 1: ids of elements the skin added to existing assets follow that asset's offset
todo = []
for f, (we, pe, ne) in envs.items():
    w = {o.path_id: o for o in we.objects}
    for o in pe.objects:
        if o.type.name != 'MonoBehaviour': continue
        if o.path_id in w and o.get_raw_data() == w[o.path_id].get_raw_data(): continue
        tree = o.read_typetree(); todo.append((f, o, tree))
        d = delta.get((f, o.path_id))
        if d is None: continue   # new asset (keeps its ids) or sheet without elements
        def own(k, v, d=d):
            if k in OWN and v not in idmap and v not in amb: idmap[v] = s32(v + d)
            return v
        walk(tree, own)

# pass 2: translate
stats = collections.Counter()
for f, o, tree in todo:
    d = delta.get((f, o.path_id))
    def fix(k, v, d=d, f=f, o=o):
        if k in HASH: return v
        if v in amb:
            # same windows id used by several assets: use this asset's own offset
            assert d is not None, ('ambiguous id in new asset', f, o.path_id, v)
            stats['by offset'] += 1; return s32(v + d)
        if v in idmap:
            stats['mapped' if idmap[v] != v else 'same'] += 1; return idmap[v]
        stats['kept (skin-new)'] += 1; return v
    walk(tree, fix)
    o.save_typetree(tree)
print(dict(stats))

for f, (we, pe, ne) in envs.items():
    w = {o.path_id: o for o in we.objects}; n = {o.path_id: o for o in ne.objects}
    c = collections.Counter()
    for o in pe.objects:
        if o.path_id in w and o.get_raw_data() == w[o.path_id].get_raw_data():
            o.set_raw_data(n[o.path_id].get_raw_data()); c['mac stock'] += 1
        else:
            c['skin ' + o.type.name] += 1
    open(OUT + f, 'wb').write(to_platform(normalise(pe.file.save()), 2))
    print(f, dict(c))
