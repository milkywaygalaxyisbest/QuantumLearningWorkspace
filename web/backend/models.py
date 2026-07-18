from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Upload(BaseModel):
    filename: str = Field(..., min_length=1)
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_type: str = Field(..., min_length=1)
    status: str = Field(default="uploaded")
    metadata: Optional[dict] = None
