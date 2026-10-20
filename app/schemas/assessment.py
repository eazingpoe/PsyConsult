from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


ScaleType = Literal["PHQ-9", "GAD-7"]


class AssessmentScoreRequest(BaseModel):
    scale_type: ScaleType
    answers: list[
        Annotated[int, Field(strict=True, ge=0, le=3)]
    ] = Field(min_length=1, max_length=9)

    @model_validator(mode="after")
    def validate_answer_count(self):
        expected = 9 if self.scale_type == "PHQ-9" else 7
        if len(self.answers) != expected:
            raise ValueError(
                f"{self.scale_type} 必须提供 {expected} 个答案"
            )
        return self
