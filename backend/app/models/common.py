from pydantic import BaseModel


class ApiError(BaseModel):
    """Structured error returned by the API."""

    code: str
    message: str
    exception_type: str | None = None
