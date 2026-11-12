#!/usr/bin/env python3
"""Carry the Classic Skin's edits to ui-styles_assets_common (made against Windows build 26385295)
onto the current Mac bundle, property by property. Output: packages/fm27-classic-mac/."""
import sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import UnityPy, fmpatch
from winport import normalise

W = 'windows-originals/fm_Data/StreamingAssets/aa/StandaloneWindows64/'
P = 'debug/winpatched/'
N = 'backups/27.0.1.2503222-steam26577676/aa/StandaloneOSX/'
f = 'ui-styles_assets_common.bundle'
objs = lambda d: {o.path_id: o for o in UnityPy.load(d + f).objects}
w, p = objs(W), objs(P)
env = UnityPy.load(N + f); n = {o.path_id: o for o in env.objects}
fmt = fmpatch.fmt_values
stats = collections.Counter()
for pid in p:
    if p[pid].get_raw_data() == w[pid].get_raw_data():
        continue
    ws, ps, ns = w[pid].read_typetree(), p[pid].read_typetree(), n[pid].read_typetree()
    assert len(ws['m_Rules']) == len(ps['m_Rules']) == len(ns['m_Rules'])
    where = {}  # stock value text -> location, for image references the skin re-points
    for ri, r in enumerate(ws['m_Rules']):
        for pi, pr in enumerate(r['m_Properties']):
            where.setdefault((pr['m_Id'], fmt(ws, pr['m_Values'])), (ri, pi))
    todo = []
    for ri, (rw, rp, rn) in enumerate(zip(ws['m_Rules'], ps['m_Rules'], ns['m_Rules'])):
        assert len(rw['m_Properties']) == len(rp['m_Properties']) == len(rn['m_Properties']), ri
        for pi, (a, b, c) in enumerate(zip(rw['m_Properties'], rp['m_Properties'], rn['m_Properties'])):
            assert a['m_Id'] == b['m_Id'] == c['m_Id']
            va, vb = fmt(ws, a['m_Values']), fmt(ps, b['m_Values'])
            if va != vb:
                todo.append((ri, pi, a, b, c, va, vb))
    for ri, pi, a, b, c, va, vb in todo:
        vals = b['m_Values']
        if len(vals) == 1 and vals[0]['m_ValueType'] == fmpatch.V_DIM:
            ns['dimensions'].append(dict(ps['dimensions'][vals[0]['valueIndex']]))
            c['m_Values'] = [{'m_ValueType': fmpatch.V_DIM, 'valueIndex': len(ns['dimensions']) - 1}]
            stats['dimension'] += 1
        else:
            # skin re-pointed an image at one another rule already uses: copy the current build's value from there
            sri, spi = where[(b['m_Id'], vb)]
            assert not any(t[0] == sri and t[1] == spi for t in todo)
            c['m_Values'] = [dict(v) for v in ns['m_Rules'][sri]['m_Properties'][spi]['m_Values']]
            stats['image re-point'] += 1
            print(f'  rule {ri}: {va} -> {vb}  (now {fmt(ns, c["m_Values"])})')
    n[pid].save_typetree(ns)
    print(ns['m_Name'], dict(stats)); stats.clear()
open('packages/fm27-classic-mac/' + f, 'wb').write(normalise(env.file.save()))
# verify
chk = {o.path_id: o for o in UnityPy.load('packages/fm27-classic-mac/' + f).objects}
print('objects differing from current stock:', [k for k in n if chk[k].get_raw_data() != objs(N)[k].get_raw_data()])
