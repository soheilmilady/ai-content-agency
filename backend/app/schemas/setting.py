from pydantic import BaseModel, ConfigDict

class SettingUpdate(BaseModel):
    value: str

class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: str
