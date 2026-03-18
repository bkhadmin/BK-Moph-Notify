import json
import re
from copy import deepcopy

FIELD_RE = re.compile(r"\{([a-zA-Z0-9_ก-๙]+)\}")

def _stringify(value):
    if value is None:
        return ""
    return str(value)

def get_available_fields(rows):
    seen = []
    for row in rows or []:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in seen:
                    seen.append(k)
    return seen

def render_text_template(text, row):
    if not isinstance(text, str):
        return text
    def repl(m):
        key = m.group(1)
        return _stringify((row or {}).get(key, ""))
    return FIELD_RE.sub(repl, text)

def render_node(node, row):
    if isinstance(node, dict):
        return {k: render_node(v, row) for k, v in node.items()}
    if isinstance(node, list):
        return [render_node(v, row) for v in node]
    if isinstance(node, str):
        return render_text_template(node, row)
    return node

def expand_repeaters(node, rows):
    if isinstance(node, dict):
        if node.get("_repeat") == "rows" and "template" in node:
            out = []
            tpl = node["template"]
            for row in rows or []:
                out.append(render_node(deepcopy(tpl), row))
            return out
        new_dict = {}
        for k, v in node.items():
            if k in ("_repeat", "template"):
                continue
            new_dict[k] = expand_repeaters(v, rows)
        return new_dict
    if isinstance(node, list):
        out = []
        for item in node:
            expanded = expand_repeaters(item, rows)
            if isinstance(expanded, list):
                out.extend(expanded)
            else:
                out.append(expanded)
        return out
    return node

def render_dynamic_flex_content(content, rows):
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            return None
    first_row = rows[0] if rows else {}
    content = render_node(content, first_row)
    content = expand_repeaters(content, rows)
    return content
