"""模型列表 OpenAI 兼容 Schemas。"""

from pydantic import BaseModel, Field


class ModelCard(BaseModel):
    id: str = Field(..., description="模型标识")
    object: str = Field(default="model", description="对象类型")
    created: int = Field(default=1700000000, description="创建时间戳")
    owned_by: str = Field(default="onetts", description="归属者")
    description: str | None = Field(default=None, description="模型描述")
    provider: str | None = Field(default=None, description="底层引擎")


class ModelListResponse(BaseModel):
    object: str = Field(default="list", description="列表对象")
    data: list[ModelCard]
