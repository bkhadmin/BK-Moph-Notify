FORBIDDEN = ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create ", "grant ", "revoke ", "into outfile", ";", "--", "/*", "*/"]


def ensure_safe_select(sql: str):
    s = (sql or "").strip().lower()
    if not s.startswith("select "):
        return False, "Only SELECT is allowed"
    for token in FORBIDDEN:
        if token in s:
            return False, f"Forbidden token: {token.strip()}"
    return True, "ok"
