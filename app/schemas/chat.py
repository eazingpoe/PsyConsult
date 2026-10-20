from pydantic import BaseModel, Field, field_validator, model_validator

ID_PATTERN = r"^[A-Za-z0-9_.:-]{1,128}$"
PATIENT_ID_PATTERN = r"^[A-Fa-f0-9]{32}$"


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default_session", pattern=ID_PATTERN)
    patient_id: str | None = Field(default=None, pattern=PATIENT_ID_PATTERN)
    save_to_history: bool = False

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_history_target(self):
        if self.save_to_history and not self.patient_id:
            raise ValueError("保存历史记录时必须提供 patient_id")
        return self


class ChatResponse(BaseModel):
    status: str
    reply: str
    user_id: str
    session_id: str
