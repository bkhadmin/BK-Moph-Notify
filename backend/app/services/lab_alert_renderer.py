def build_lab_alert_carousel(rows):
    rows = rows or []
    bubbles = []
    for row in rows:
        bubbles.append({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "แจ้งเตือนค่า LAB วิกฤต",
                        "weight": "bold",
                        "size": "lg",
                        "wrap": True,
                        "color": "#b91c1c"
                    },
                    {
                        "type": "text",
                        "text": f"ผู้ป่วย {row.get('ptname','')}",
                        "weight": "bold",
                        "size": "sm",
                        "margin": "md",
                        "wrap": True,
                        "color": "#0f172a"
                    },
                    {
                        "type": "text",
                        "text": f"HN {row.get('hn','')} | {row.get('cur_dep','')}",
                        "size": "xs",
                        "color": "#64748b",
                        "margin": "sm",
                        "wrap": True
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"{row.get('lab_items_name','')} = {row.get('lab_order_result','')}",
                        "weight": "bold",
                        "size": "md",
                        "color": "#dc2626",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"วันที่ {row.get('report_date_text','')} เวลา {row.get('report_time_text','')}",
                        "size": "xs",
                        "color": "#64748b",
                        "margin": "sm",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"แพทย์ผู้สั่ง {row.get('แพทย์ผู้สั่ง','')}",
                        "size": "xs",
                        "color": "#64748b",
                        "margin": "sm",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"สถานะ {row.get('case_status_text','รอรับเคส')}",
                        "size": "xs",
                        "color": "#2563eb" if row.get("case_status") != "CLAIMED" else "#16a34a",
                        "margin": "sm",
                        "wrap": True
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary" if row.get("case_status") != "CLAIMED" else "secondary",
                        "action": {
                            "type": "uri",
                            "label": "รับเคส" if row.get("case_status") != "CLAIMED" else "ดูข้อมูลเคส",
                            "uri": row.get("claim_url","")
                        }
                    }
                ]
            }
        })
    if not bubbles:
        bubbles = [{
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "ไม่พบเคส LAB วิกฤตที่ต้องแจ้งเตือน", "weight": "bold", "size": "md", "wrap": True}
                ]
            }
        }]
    return [{
        "type": "flex",
        "altText": "แจ้งเตือนค่า LAB วิกฤต",
        "contents": {
            "type": "carousel",
            "contents": bubbles[:12]
        }
    }]
