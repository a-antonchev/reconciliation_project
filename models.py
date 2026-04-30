from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# --- модели для извлечения из документа ---


class SpecItem(BaseModel):
    sku: str = Field(
        default="",
        description="Артикул товара. Если артикула нет, то верни пустую строку ''",
    )
    name: str = Field(description="Наименование товара")
    quantity: float = Field(description="Количество товара (только число)")
    unit: str = Field(
        description="Единица измерения товара (шт, г, кг, л, м, компл и т.д.). Привести к нижнему регистру."
    )
    description: str = Field(
        default="",
        description="Дополнительное описание товара, характеристики, ГОСТы. Если нет, верни пустую строку ''",
    )


class SpecificationDocument(BaseModel):
    items: List[SpecItem] = Field(description="Список всех позиций из спецификации")


# --- модели для результатов сверки ---


class MatchStatus(str, Enum):
    PERFECT_MATCH = "Полное совпадение"
    PARTIAL_MATCH = "Есть расхождения"
    EXTRA_IN_TARGET = "Отсутствует в исходном документе (Эталоне)"
    MISSING_IN_TARGET = "Отсутствует в целевом документе (Заявке)"


class ReconciliationRow(BaseModel):
    status: MatchStatus
    # данные из исходного документа (эталона)
    baseline_sku: Optional[str] = None
    baseline_name: Optional[str] = None
    baseline_qty: Optional[float] = None
    baseline_unit: Optional[str] = None
    baseline_description: Optional[str] = None
    # данные из целевого документа (Заявки)
    target_sku: Optional[str] = None
    target_name: Optional[str] = None
    target_qty: Optional[float] = None
    target_unit: Optional[str] = None
    target_description: Optional[str] = None
    # комментарий системы
    difference_notes: Optional[str] = Field(
        default=None,
        description="Описание расхождений (например: 'Количество: 5 -> 4')",
    )


class LLMMatchpair(BaseModel):
    baseline_name: str = Field(description="Точное наименование из списка исходного документа (Эталона)")
    target_name: str = Field(description="Точное наименование из списка целевого документа")
    reason: str = Field(description="Краткое объяснение, почему это одна и та же позиция")


class LLMMatchResult(BaseModel):
    matches: List[LLMMatchpair] = Field(description="Список пар совпадающих позиций", default_factory=list)
