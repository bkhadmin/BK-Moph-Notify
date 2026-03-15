FORBIDDEN = [
    'insert ','update ','delete ','drop ','alter ','truncate ','create ',
    'grant ','revoke ','into outfile','--','/*','*/','load_file(',
    'sleep(','benchmark('
]

def normalize_sql(sql:str)->str:
    s = (sql or '').strip()
    if s.endswith(';'):
        s = s[:-1].rstrip()
    return s

def ensure_safe_select(sql:str):
    s = normalize_sql(sql).lower()
    if not s.startswith('select '):
        return False, 'Only SELECT is allowed'
    for token in FORBIDDEN:
        if token in s:
            return False, f'Forbidden token: {token.strip()}'
    if ';' in s:
        return False, 'Forbidden token: ;'
    return True, 'ok'
