#!/usr/bin/env python3
"""Minimal FM27 stylesheet patcher (Unity 6000.3 StyleSheet layout).

  dump  <bundles_dir> <out_dir>            export every stylesheet as readable .uss
  build <skin_dir> <bundles_dir> <out_dir> write patched copies of the bundles a skin touches
        [--dry-run]

A skin is a folder of .uss/.css files containing custom-property overrides:
    :root { --brand-theme-primary: #2a6fdb; }
Only colour values (#rgb, #rrggbb, #rrggbbaa, rgb(), rgba()) are supported.
Every definition of a named variable, in every stylesheet and rule, is replaced.
The bundles_dir is only read; point it at the pristine backup.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import UnityPy

# UnityEngine.UIElements.StyleValueType
V_KEYWORD, V_FLOAT, V_DIM, V_COLOR, V_RES, V_ASSET, V_ENUM, V_VAR, V_STR, V_FUNC, V_COMMA = range(1, 12)
KEYWORDS = ["inherit", "initial", "auto", "unset", "true", "false", "none"]
UNITS = {0: "", 1: "px", 2: "%", 3: "s", 4: "ms", 5: "deg", 6: "grad", 7: "rad", 8: "turn"}
FUNCS = {1: "var", 2: "env", 3: "linear-gradient"}


def stylesheets(env):
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if "m_Rules" in tree and "colors" in tree and "strings" in tree:
            yield obj, tree


def hex_of(c):
    r, g, b, a = (max(0, min(255, round(c[k] * 255))) for k in "rgba")
    return f"#{r:02x}{g:02x}{b:02x}" + (f"{a:02x}" if a != 255 else "")


def fmt_values(sheet, values):
    out, i = [], 0
    while i < len(values):
        v = values[i]
        t, ix = v["m_ValueType"], v["valueIndex"]
        try:
            if t == V_COLOR:
                out.append(hex_of(sheet["colors"][ix]))
            elif t == V_FLOAT:
                out.append(f"{sheet['floats'][ix]:g}")
            elif t == V_DIM:
                d = sheet["dimensions"][ix]
                out.append(f"{d['value']:g}{UNITS.get(d['unit'], '?')}")
            elif t == V_KEYWORD:
                out.append(KEYWORDS[ix] if ix < len(KEYWORDS) else f"keyword({ix})")
            elif t in (V_ENUM, V_VAR):
                out.append(sheet["strings"][ix])
            elif t == V_STR:
                out.append(json.dumps(sheet["strings"][ix]))
            elif t == V_RES:
                out.append(f"resource({json.dumps(sheet['strings'][ix])})")
            elif t == V_ASSET:
                out.append(f"asset({ix})")
            elif t == V_COMMA:
                out.append(",")
            elif t == V_FUNC:
                # function, then a float holding the argument count, then the arguments
                n = int(sheet["floats"][values[i + 1]["valueIndex"]])
                args = fmt_values(sheet, values[i + 2 : i + 2 + n])
                out.append(f"{FUNCS.get(ix, f'func{ix}')}({args})")
                i += 1 + n
            else:
                out.append(f"type{t}({ix})")
        except (IndexError, KeyError):
            out.append(f"type{t}({ix})")
        i += 1
    return " ".join(out).replace(" ,", ",")


def fmt_selector(sel):
    s = ""
    for part in sel["m_Selectors"]:
        rel = part.get("m_PreviousRelationship", 0)
        if s:
            s += " > " if rel == 1 else " "
        for p in part["m_Parts"]:
            t, val = p.get("m_Type"), p.get("m_Value", "")
            s += {1: "*", 2: val, 3: "." + val, 4: ":" + val, 5: ":" + val, 6: "#" + val}.get(t, val)
    return s or "*"


def prop_name(p):
    return p.get("m_CustomName") or p.get("m_Name") or f"-unity-id({p.get('m_Id')})"


def cmd_dump(args):
    out = Path(args.out)
    for bundle in sorted(Path(args.bundles).glob(args.glob)):
        env = UnityPy.load(str(bundle))
        for _, sheet in stylesheets(env):
            lines = []
            for rule in sheet["m_Rules"]:
                sels = ", ".join(fmt_selector(s) for s in rule.get("m_ComplexSelectors", [])) or "/* no selector */"
                lines.append(f"{sels} {{")
                for p in rule["m_Properties"]:
                    lines.append(f"  {prop_name(p)}: {fmt_values(sheet, p['m_Values'])};")
                lines.append("}\n")
            dest = out / bundle.stem / f"{sheet['m_Name']}.uss"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("\n".join(lines))
            print(f"{bundle.name}: {sheet['m_Name']} ({len(sheet['m_Rules'])} rules)")


COLOR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def parse_color(text):
    text = text.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", text)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        vals = [int(h[i : i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return dict(zip("rgba", vals + [1.0] * (4 - len(vals))))
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", text)
    if m:
        r, g, b = (float(m.group(i)) / 255 for i in (1, 2, 3))
        return {"r": r, "g": g, "b": b, "a": float(m.group(4)) if m.group(4) else 1.0}
    raise ValueError(f"unsupported colour value: {text!r}")


def load_overrides(skin):
    overrides = {}
    files = sorted(p for p in Path(skin).rglob("*") if p.suffix in (".uss", ".css"))
    for f in files:
        text = re.sub(r"/\*.*?\*/", "", f.read_text(), flags=re.S)
        for name, value in COLOR_RE.findall(text):
            overrides[name] = parse_color(value)
    return overrides


def patch_sheet(sheet, overrides, log):
    changed = 0
    for rule in sheet["m_Rules"]:
        for p in rule["m_Properties"]:
            name = p.get("m_CustomName")
            if name not in overrides:
                continue
            old = fmt_values(sheet, p["m_Values"])
            # append a fresh colour so entries shared with other properties stay untouched
            sheet["colors"].append(dict(overrides[name]))
            p["m_Values"] = [{"m_ValueType": V_COLOR, "valueIndex": len(sheet["colors"]) - 1}]
            log.append((sheet["m_Name"], name, old, hex_of(overrides[name])))
            changed += 1
    return changed


def load_rule_edits(skin):
    """Optional <skin>/styles/rules.json: [{"sheet": "...", "selector": ":root", "set_dim": {"131099": [200, "px"]}}]
    Sets standard (numeric id) properties with a dimension value on the first rule matching the selector."""
    f = Path(skin) / "styles" / "rules.json"
    return json.loads(f.read_text()) if f.exists() else []


def apply_rule_edits(sheet, edits, log):
    import copy

    changed = 0
    units = {v: k for k, v in UNITS.items()}
    for e in edits:
        if e["sheet"] != sheet["m_Name"]:
            continue
        if e.get("create"):
            # new rule for a single-class selector, cloned from an existing single-class rule and appended last
            cls = e["selector"]
            assert re.fullmatch(r"\.[\w-]+", cls), "create only supports a single .class selector"

            def simple(r):
                cs = r.get("m_ComplexSelectors", [])
                return (len(cs) == 1 and len(cs[0]["m_Selectors"]) == 1 and len(cs[0]["m_Selectors"][0]["m_Parts"]) == 1
                        and cs[0]["m_Selectors"][0]["m_Parts"][0].get("m_Type") == 3 and r["m_Properties"])

            new = copy.deepcopy(next(r for r in sheet["m_Rules"] if simple(r)))
            new["m_ComplexSelectors"][0]["m_Selectors"][0]["m_Parts"][0]["m_Value"] = cls[1:]
            new["m_ComplexSelectors"][0]["ruleIndex"] = len(sheet["m_Rules"])
            new["m_Properties"] = new["m_Properties"][:1]
            new["m_Properties"][0]["m_Id"] = -999  # placeholder, replaced below
            sheet["m_Rules"].append(new)
        for rule in sheet["m_Rules"][::-1] if e.get("create") else sheet["m_Rules"]:
            if e["selector"] not in [fmt_selector(s) for s in rule.get("m_ComplexSelectors", [])]:
                continue
            for pid, (num, unit) in e.get("set_dim", {}).items():
                sheet["dimensions"].append({"unit": units[unit], "value": float(num)})
                value = [{"m_ValueType": V_DIM, "valueIndex": len(sheet["dimensions"]) - 1}]
                prop = next((p for p in rule["m_Properties"] if p.get("m_Id") in (int(pid), -999)), None)
                if prop is not None and prop["m_Id"] == -999:
                    prop["m_Id"] = int(pid)
                    prop["m_CustomName"] = ""
                    prop["m_Values"] = []
                old = fmt_values(sheet, prop["m_Values"]) if prop else "(unset)"
                if prop is None:
                    prop = copy.deepcopy(rule["m_Properties"][-1])
                    prop["m_Id"] = int(pid)
                    prop["m_CustomName"] = ""
                    rule["m_Properties"].append(prop)
                prop["m_Values"] = value
                log.append((sheet["m_Name"], f"{e['selector']} {{ id {pid} }}", old, f"{num}{unit}"))
                changed += 1
            e["_done"] = True
            break
    return changed


def cmd_build(args):
    overrides = load_overrides(args.skin)
    rule_edits = load_rule_edits(args.skin)
    if not overrides and not rule_edits:
        sys.exit("no colour overrides or rule edits found in skin")
    out = Path(args.out)
    seen, total = set(), 0
    for bundle in sorted(Path(args.bundles).glob(args.glob)):
        env = UnityPy.load(str(bundle))
        log, dirty = [], 0
        for obj, sheet in stylesheets(env):
            if patch_sheet(sheet, overrides, log) + apply_rule_edits(sheet, rule_edits, log):
                obj.save_typetree(sheet)
                dirty += 1
        if not dirty:
            continue
        for sheet_name, name, old, new in log:
            print(f"  {bundle.name} / {sheet_name}: {name}: {old} -> {new}")
            if name in overrides:
                seen.add(name)
        total += len(log)
        if not args.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            (out / bundle.name).write_bytes(env.file.save(packer="lz4"))
            print(f"wrote {out / bundle.name}")
    seen |= set(overrides) & {n for n in overrides if n in seen}
    missing = sorted(set(overrides) - seen) + [f"rule {e['sheet']} {e['selector']}" for e in rule_edits if not e.get("_done")]
    print(f"\n{total} definitions changed for {len(seen)} of {len(overrides)} variables" + (" (dry run)" if args.dry_run else ""))
    if missing:
        print("NOT FOUND in any stylesheet: " + ", ".join(missing))
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("bundles")
    d.add_argument("out")
    d.add_argument("--glob", default="ui-styles_*.bundle")
    d.set_defaults(fn=cmd_dump)
    b = sub.add_parser("build")
    b.add_argument("skin")
    b.add_argument("bundles")
    b.add_argument("out")
    b.add_argument("--glob", default="ui-styles_*.bundle")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(fn=cmd_build)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
