#!/usr/bin/env python3
"""Patch FM27 layout assets (VisualTreeAssets) from a skin's layout.json.

  vtapatch.py <skin_dir> <bundles_dir> <out_dir> [--dry-run]

layout.json is a list of edits:
  {
    "asset": "MenuBar",                    VisualTreeAsset name
    "element": "ButtonGroup",              element type (last part of the full type name)
    "has_class": "row-direction-normal",   optional: only elements carrying this class
    "replace_class": ["row-direction-normal", "column-direction-normal"],   optional
    "add_class": ["some-class"],           optional
    "inline_enum": {"131083": "column"},   optional: inline style, numeric property id -> enum keyword
    "inline_px": {"131105": 200}           optional: inline style, numeric property id -> pixels
  }
Bundles are only read from bundles_dir; patched copies go to out_dir.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import UnityPy

from UnityPy.helpers import TypeTreeHelper as _tth

V_DIM = 3
V_ENUM = 7

# UnityPy 1.25 cannot write the null managed reference (rid -2, no "data"); skip its data like the reader does.
_orig_write_value = _tth.write_value


def _write_value(value, node, writer, config):
    if node.m_Type == "ReferencedObject" and "data" not in value:
        for child in node.m_Children:
            if child.m_Type != "ReferencedObjectData":
                _tth.write_value(value[child.m_Name], child, writer, config)
        return
    return _orig_write_value(value, node, writer, config)


_tth.write_value = _write_value
GLOB = "ui-visualtreeassets_*.bundle"


def set_inline(sheet, rule_index, prop_id, keyword=None, px=None):
    rule = sheet["m_Rules"][rule_index]
    if keyword is not None:
        if keyword not in sheet["strings"]:
            sheet["strings"].append(keyword)
        value = {"m_ValueType": V_ENUM, "valueIndex": sheet["strings"].index(keyword)}
    else:
        sheet["dimensions"].append({"unit": 1, "value": float(px)})
        value = {"m_ValueType": V_DIM, "valueIndex": len(sheet["dimensions"]) - 1}
    for p in rule["m_Properties"]:
        if p.get("m_Id") == prop_id:
            p["m_Values"] = [value]
            return "replaced"
    if not rule["m_Properties"]:
        raise ValueError("inline rule has no property to use as a template")
    p = copy.deepcopy(rule["m_Properties"][-1])
    p["m_Id"] = prop_id
    if "m_CustomName" in p:
        p["m_CustomName"] = ""
    p["m_Values"] = [value]
    rule["m_Properties"].append(p)
    return "added"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skin")
    ap.add_argument("bundles")
    ap.add_argument("out")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec_path = Path(args.skin) / "layout.json"
    edits = json.loads(spec_path.read_text())
    wanted = {e["asset"] for e in edits}
    done = {id(e): 0 for e in edits}
    out = Path(args.out)

    for bundle in sorted(Path(args.bundles).glob(GLOB)):
        env = UnityPy.load(str(bundle))
        by_id = {o.path_id: o for o in env.objects}
        dirty = False
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                name = obj.peek_name()
            except Exception:
                continue
            if name not in wanted:
                continue
            tree = obj.read_typetree()
            if "m_VisualTree" not in tree:
                continue
            sheet_obj = by_id.get(tree["inlineSheet"]["m_PathID"])
            sheet = sheet_obj.read_typetree() if sheet_obj else None
            tree_dirty = sheet_dirty = False
            for e in edits:
                if e["asset"] != name:
                    continue
                for ref in tree["references"]["RefIds"]:
                    d = ref.get("data") or {}
                    if d.get("m_FullTypeName", "").split(".")[-1] != e["element"]:
                        continue
                    classes = d.get("m_Classes", [])
                    if e.get("has_class") and e["has_class"] not in classes:
                        continue
                    notes = []
                    if e.get("replace_class"):
                        old, new = e["replace_class"]
                        if old in classes:
                            classes[classes.index(old)] = new
                            tree_dirty = True
                            notes.append(f"class {old} -> {new}")
                    for c in e.get("add_class", []):
                        if c not in classes:
                            classes.append(c)
                            tree_dirty = True
                            notes.append(f"class +{c}")
                    for pid, kw in (e.get("inline_enum") or {}).items():
                        if sheet is None or d.get("m_RuleIndex", -1) < 0:
                            notes.append(f"inline {pid} SKIPPED (element has no inline rule)")
                            continue
                        how = set_inline(sheet, d["m_RuleIndex"], int(pid), keyword=kw)
                        sheet_dirty = True
                        notes.append(f"inline {pid}: {kw} ({how})")
                    for pid, px in (e.get("inline_px") or {}).items():
                        if sheet is None or d.get("m_RuleIndex", -1) < 0:
                            notes.append(f"inline {pid} SKIPPED (element has no inline rule)")
                            continue
                        how = set_inline(sheet, d["m_RuleIndex"], int(pid), px=px)
                        sheet_dirty = True
                        notes.append(f"inline {pid}: {px}px ({how})")
                    if notes:
                        done[id(e)] += 1
                        print(f"  {bundle.name} / {name} / {e['element']} rid {ref['rid']}: " + "; ".join(notes))
            if tree_dirty:
                obj.save_typetree(tree)
            if sheet_dirty:
                sheet_obj.save_typetree(sheet)
            dirty = dirty or tree_dirty or sheet_dirty
        if dirty and not args.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            (out / bundle.name).write_bytes(env.file.save(packer="lz4"))
            print(f"wrote {out / bundle.name}")

    missed = [e for e in edits if not done[id(e)]]
    print(f"\n{sum(done.values())} elements changed by {len(edits) - len(missed)} of {len(edits)} edits" + (" (dry run)" if args.dry_run else ""))
    if missed:
        print("NO MATCH for: " + json.dumps(missed))
        sys.exit(2)


if __name__ == "__main__":
    main()
