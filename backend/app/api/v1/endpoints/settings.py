from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db, require_admin
from app.models.setting import SystemSetting
from app.schemas.setting import SettingResponse, SettingUpdate
from app.models.user import User

router = APIRouter()

@router.get("/settings/{key}", response_model=SettingResponse)
def get_setting(key: str, db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(require_admin)]):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        if key == "global_daily_rate_limit":
            return SettingResponse(key=key, value="20/day")
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.put("/settings/{key}", response_model=SettingResponse)
def update_setting(
    request: Request,
    key: str, 
    body: SettingUpdate, 
    db: Annotated[Session, Depends(get_db)], 
    _: Annotated[User, Depends(require_admin)]
):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        setting = SystemSetting(key=key, value=body.value)
        db.add(setting)
    else:
        setting.value = body.value
    db.commit()
    db.refresh(setting)
    
    if key == "global_daily_rate_limit":
        request.app.state.global_limit = setting.value
        
    return setting
