from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    dependencies: list[str] = Field(
        default_factory=list
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    failure_probability: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
    )

    duration_min: float = Field(
        default=1.0,
        gt=0,
    )

    duration_max: float = Field(
        default=5.0,
        gt=0,
    )

    timeout: float | None = Field(
        default=30.0,
        gt=0,
    )


class TaskResponse(BaseModel):
    id: str
    name: str
    status: str
    attempts: int
    max_retries: int
    dependencies: list[str]