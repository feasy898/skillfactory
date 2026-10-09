"""Field resolution for the two 文书 templates.

Blank handling is deliberately explicit and recorded, because both fixtures are
empty/blank inputs and the brief asks for the unfilled parts to be handled
truthfully rather than aborting.

Statuses
  filled  - key present, value has non-whitespace content
  blank   - key present, value is empty / whitespace-only / an all-blank list
  missing - key absent from the input object
"""

import json

# Whitespace that must count as "not filled": ASCII space, ideographic space
# (U+3000), NBSP, tabs, newlines, plus any other Unicode space character.
WS = set(" \t\r\n\v\f 　   ")
WS |= {chr(c) for c in range(0x00A0, 0x00B0)}
WS |= {chr(c) for c in range(0x2000, 0x200B)}
WS |= {"⁠", "﻿"}


def is_blank_str(s):
    return s is None or all(ch in WS for ch in s)


def codepoints(v):
    if isinstance(v, str):
        return [f"U+{ord(c):04X}" for c in v]
    if isinstance(v, list):
        return [[f"U+{ord(c):04X}" for c in s] if isinstance(s, str) else [repr(s)]
                for s in v]
    return [repr(v)]


def resolve(data, key, placeholder):
    """Resolve one template slot against the input object.

    Returns a dict that is both the render decision and the audit record.
    """
    present = key in data
    raw = data.get(key)
    kind = "list" if isinstance(raw, list) else "string"

    if not present:
        status, resolved, items = "missing", placeholder, None
    elif kind == "list":
        if not isinstance(raw, list):
            # Wrong type but present: never abort, treat as unusable.
            status, resolved, items = "invalid", placeholder, None
        else:
            items = [s for s in raw if isinstance(s, str) and not is_blank_str(s)]
            status = "filled" if items else "blank"
            # renderer consumes `items` as a numbered list when non-empty
            resolved = items[0] if len(items) == 1 else (
                "｜".join(items) if items else placeholder)
    else:
        if raw is None:
            status, resolved = "blank", placeholder
        elif not isinstance(raw, str):
            status, resolved = "invalid", placeholder
        elif is_blank_str(raw):
            status, resolved = "blank", placeholder
        else:
            status, resolved = "filled", raw

    rec = {
        "key": key,
        "placeholder": placeholder,
        "status": status,
        "present_in_input": present,
        "input_type": kind if present else None,
        "raw": raw,
        "raw_repr": repr(raw),
        "raw_codepoints": codepoints(raw) if present else [],
        "rendered": resolved,
    }
    if kind == "list" and present and isinstance(raw, list):
        rec["items_total"] = len(raw)
        rec["items"] = items
        rec["items_kept"] = len(items)
        rec["items_dropped_as_blank"] = len(raw) - len(items)
    return rec


def write_fields_json(path, *, template_id, template_name, out_dir, source_file,
                      data, fields, notes):
    counts = {"filled": 0, "blank": 0, "missing": 0, "invalid": 0}
    for f in fields:
        counts[f["status"]] += 1
    payload = {
        "schema": "office-doc-fields/1",
        "template_id": template_id,
        "template_name": template_name,
        "source_input": source_file,
        "output_dir": out_dir,
        "artifacts": {"docx": "文书.docx"},
        "input_shape": {
            "top_level_keys": sorted(data.keys()),
            "key_count": len(data),
        },
        "blank_policy": {
            "whitespace_treated_as_blank": True,
            "whitespace_chars": ["U+0020", "U+3000", "U+00A0", "U+0009-000D",
                                 "U+2000-200A", "U+FEFF"],
            "placeholder_format": "【字段名】",
            "on_missing_key": "render 【字段名】 placeholder; never abort",
            "on_blank_string": "render 【字段名】 placeholder",
            "on_empty_or_all_blank_list": "render a single 【字段名】 placeholder paragraph",
            "on_unusable_type": "render 【字段名】 placeholder; record status=invalid",
            "no_fabrication": "no issuing body, date, subject or figure was invented",
        },
        "field_count": len(fields),
        "status_counts": counts,
        "fields": fields,
        "notes": notes,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return payload