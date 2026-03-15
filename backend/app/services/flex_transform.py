import json
from datetime import datetime

def sent_at_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M น.")

def _replace_tokens(obj, mapping):
    if isinstance(obj, dict):
        return {k: _replace_tokens(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_tokens(v, mapping) for v in obj]
    if isinstance(obj, str):
        out = obj
        for k, v in mapping.items():
            out = out.replace("{" + k + "}", str(v if v is not None else ""))
        return out
    return obj

def build_single_bubble(row:dict):
    mapping = {
        "clinic_name": row.get("clinic_name", ""),
        "department": row.get("department", ""),
        "total_appointment": row.get("total_appointment", 0),
        "sent_at": sent_at_text(),
    }
    bubble = {
        "type":"bubble",
        "body":{"type":"box","layout":"vertical","contents":[
            {"type":"text","text":"สรุปผู้ป่วยนัดหมาย","weight":"bold","size":"lg","wrap":True},
            {"type":"text","text":"ส่งเมื่อ {sent_at}","size":"sm","color":"#64748b","wrap":True,"margin":"md"},
            {"type":"separator","margin":"md"},
            {"type":"text","text":"คลินิก {clinic_name}","weight":"bold","wrap":True,"margin":"md"},
            {"type":"text","text":"แผนกที่นัด {department}","wrap":True,"size":"sm","color":"#475569","margin":"md"},
            {"type":"text","text":"จำนวนผู้ป่วยที่นัด {total_appointment} ราย","wrap":True,"size":"lg","weight":"bold","margin":"lg"}
        ]}
    }
    return _replace_tokens(bubble, mapping)

def build_carousel(rows:list[dict]):
    contents = [build_single_bubble(r) for r in rows[:10]]
    return {"type":"carousel","contents":contents}

def build_top5(rows:list[dict]):
    rows = rows[:5]
    mapping = {"sent_at": sent_at_text()}
    for idx, row in enumerate(rows, start=1):
        mapping[f"row{idx}_clinic_name"] = row.get("clinic_name", "")
        mapping[f"row{idx}_total_appointment"] = row.get("total_appointment", 0)
    for idx in range(len(rows)+1, 6):
        mapping[f"row{idx}_clinic_name"] = "-"
        mapping[f"row{idx}_total_appointment"] = 0
    bubble = {
        "type":"bubble",
        "body":{"type":"box","layout":"vertical","contents":[
            {"type":"text","text":"Top 5 นัดหมายวันนี้","weight":"bold","size":"lg","wrap":True},
            {"type":"text","text":"ส่งเมื่อ {sent_at}","size":"sm","color":"#64748b","wrap":True,"margin":"md"},
            {"type":"separator","margin":"md"},
            {"type":"text","text":"1. {row1_clinic_name} - {row1_total_appointment} ราย","wrap":True,"margin":"md"},
            {"type":"text","text":"2. {row2_clinic_name} - {row2_total_appointment} ราย","wrap":True,"margin":"sm"},
            {"type":"text","text":"3. {row3_clinic_name} - {row3_total_appointment} ราย","wrap":True,"margin":"sm"},
            {"type":"text","text":"4. {row4_clinic_name} - {row4_total_appointment} ราย","wrap":True,"margin":"sm"},
            {"type":"text","text":"5. {row5_clinic_name} - {row5_total_appointment} ราย","wrap":True,"margin":"sm"}
        ]}
    }
    return _replace_tokens(bubble, mapping)

def detect_mode_and_build(rows:list[dict], mode:str):
    if mode == "top5":
        return build_top5(rows)
    if mode == "carousel":
        return build_carousel(rows)
    if mode == "single":
        return build_single_bubble(rows[0] if rows else {})
    return build_single_bubble(rows[0] if rows else {})

def as_flex_message_payload(rows:list[dict], mode:str):
    contents = detect_mode_and_build(rows, mode)
    return [{"type":"flex","altText":"BK-Moph Notify Flex Message","contents":contents}]
