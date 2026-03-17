import json
from app.services.flex_table_renderer import build_full_table_flex
from app.services.flex_transform import as_flex_message_payload

def build_dynamic_template_payload(template_type:str, content:str, alt_text:str|None, rows:list[dict]):
    tt = (template_type or "").strip().lower()
    if tt in ("flex_full_list", "dynamic_full_list"):
        try:
            cfg = json.loads(content or "{}")
        except Exception:
            cfg = {}
        title = cfg.get("title") or "จำนวนผู้ป่วยนัดแยกรายคลินิก"
        chunk_size = int(cfg.get("chunk_size") or 8)
        contents = build_full_table_flex(rows or [], title=title, chunk_size=chunk_size)
        return [{
            "type": "flex",
            "altText": alt_text or title,
            "contents": contents,
        }]
    if tt == "flex_top5":
        return as_flex_message_payload(rows or [], "top5")
    if tt == "flex_carousel":
        return as_flex_message_payload(rows or [], "carousel")
    return None
