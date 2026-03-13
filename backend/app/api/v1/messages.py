from fastapi import APIRouter
from app.schemas.message import MessagePreviewRequest

router = APIRouter()


@router.post("/preview")
def preview_message(payload: MessagePreviewRequest):
    rendered = payload.template
    for k, v in payload.variables.items():
        rendered = rendered.replace("{" + k + "}", str(v))
    return {"rendered": rendered}
