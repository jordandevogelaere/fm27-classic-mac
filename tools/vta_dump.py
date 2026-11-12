#!/usr/bin/env python3
"""Print a UXML-like outline of FM27 VisualTreeAssets.  vta_dump.py <bundle> <name-regex> [--raw]"""
import re, sys, json, UnityPy

def load(bundle):
    env = UnityPy.load(bundle); out = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour":
            try: out.setdefault(o.peek_name(), o)
            except Exception: pass
    return out

def outline(t):
    refs = {r["rid"]: r for r in t["references"]["RefIds"]}
    lines = []
    def walk(rid, depth):
        r = refs.get(rid)
        if not r or "data" not in r: return
        d = r["data"]; kind = r["type"]["class"]
        name = d.get("m_FullTypeName", kind).split(".")[-1]
        props = d.get("m_Properties", [])
        attrs = " ".join(f'{props[i]}="{props[i+1]}"' for i in range(0, len(props) - 1, 2))
        cls = " ".join(d.get("m_Classes", []))
        extra = ""
        if kind == "TemplateAsset": extra = f' template="{d.get("m_TemplateAlias","")}"'
        if d.get("m_RuleIndex", -1) >= 0: extra += f' inline-rule={d["m_RuleIndex"]}'
        lines.append("  " * depth + f"<{name}{extra}" + (f' class="{cls}"' if cls else "") + (" " + attrs if attrs else "") + ">")
        for c in d.get("m_Children", []): walk(c["rid"], depth + 1)
    walk(t["m_VisualTree"]["rid"], 0)
    return lines

if __name__ == "__main__":
    objs = load(sys.argv[1]); pat = re.compile(sys.argv[2])
    for n in sorted(objs):
        if pat.search(n):
            t = objs[n].read_typetree()
            print(f"##### {n}  (templates: {[u.get('m_Alias') or u for u in t.get('m_Usings', [])][:20]})")
            print("\n".join(outline(t)))
