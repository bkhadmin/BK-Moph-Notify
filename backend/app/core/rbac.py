MENU_BY_ROLE = {
    "superadmin": {"dashboard", "users", "queries", "templates", "send", "audit"},
    "user": {"dashboard", "queries", "templates", "send"},
}


def allowed_menu(role: str, menu_code: str) -> bool:
    return menu_code in MENU_BY_ROLE.get(role or "", set())
