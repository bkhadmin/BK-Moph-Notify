import json
from sqlalchemy.orm import Session
from app.models.provider_profile import ProviderProfile

def _pick(profile:dict, *keys):
    for k in keys:
        value = profile.get(k)
        if value not in (None, ''):
            return value
    return None

def _nested(profile:dict, parent:str, child:str):
    block = profile.get(parent)
    if isinstance(block, dict):
        return block.get(child)
    return None

def upsert_profile(db:Session, user_id:int|None, profile:dict):
    account_id = profile.get('account_id')
    provider_id = profile.get('provider_id')
    row = None
    if account_id:
        row = db.query(ProviderProfile).filter(ProviderProfile.account_id == account_id).first()
    if not row and provider_id:
        row = db.query(ProviderProfile).filter(ProviderProfile.provider_id == provider_id).first()
    if not row and user_id:
        row = db.query(ProviderProfile).filter(ProviderProfile.user_id == user_id).first()
    if not row:
        row = ProviderProfile()
        db.add(row)

    row.user_id = user_id
    row.account_id = account_id
    row.provider_id = provider_id
    row.hash_cid = _pick(profile, 'hash_cid', 'cid_hash')
    row.title_name = _pick(profile, 'title_name', 'title', 'prefix')
    row.name_th = _pick(profile, 'name_th', 'display_name', 'name')
    row.first_name = _pick(profile, 'first_name', 'fname', 'first_name_th')
    row.last_name = _pick(profile, 'last_name', 'lname', 'last_name_th')
    row.position_name = _pick(profile, 'position_name', 'position')
    row.organization_name = _pick(profile, 'organization_name') or _nested(profile, 'organization', 'name')
    row.organization_code = _pick(profile, 'organization_code', 'hcode') or _nested(profile, 'organization', 'code')
    row.license_no = _pick(profile, 'license_no', 'license', 'medical_license')
    row.phone = _pick(profile, 'phone', 'mobile', 'tel')
    row.email = _pick(profile, 'email')
    row.raw_json = json.dumps(profile, ensure_ascii=False)
    db.commit()
    db.refresh(row)
    return row

def get_all(db:Session):
    return db.query(ProviderProfile).order_by(ProviderProfile.id.desc()).all()

def get_by_id(db:Session, item_id:int):
    return db.query(ProviderProfile).filter(ProviderProfile.id == item_id).first()
