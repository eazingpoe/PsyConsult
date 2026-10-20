from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


Sex = Literal["female", "male", "other", "unknown"]


class PatientCreate(BaseModel):
    patient_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    sex: Sex | None = None
    birth_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("patient_code", "display_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("该字段不能为空")
        return value

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class PatientUpdate(BaseModel):
    patient_code: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    sex: Sex | None = None
    birth_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("patient_code", "display_name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("该字段不能为空")
        return value

    @field_validator("notes")
    @classmethod
    def strip_optional_notes(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个需要更新的字段")
        for required_field in ("patient_code", "display_name"):
            if required_field in self.model_fields_set and getattr(self, required_field) is None:
                raise ValueError(f"{required_field} 不能设置为 null")
        return self
