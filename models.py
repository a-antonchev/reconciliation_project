from __future__ import annotations

from enum import Enum
from typing import List, Optional

import streamlit as st
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
    # данные из исходного документа (Эталона)
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
    difference_notes: str = Field(
        default="",
        description="Описание расхождений (например: 'Количество: 5 -> 4')",
    )


class LLMMatchpair(BaseModel):
    baseline_name: str = Field(description="Точное наименование из списка исходного документа (Эталона)")
    target_name: str = Field(description="Точное наименование из списка целевого документа")
    reason: str = Field(description="Краткое объяснение, почему это одна и та же позиция")


class LLMMatchResult(BaseModel):
    matches: List[LLMMatchpair] = Field(description="Список пар совпадающих позиций", default_factory=list)


# --- конфигурация модели ---


class LLMConfig(BaseModel):
    model_name: str = Field(default="gemini-3-flash-preview", description="Имя модели")
    max_retries: int = Field(default=3, ge=1, le=5, description="Максимальное количество попыток")

    @classmethod
    def from_secrets(cls) -> LLMConfig:
        """
        Фабричный метод. Читает секцию [llm_settings] из st.secrets.
        Если секции нет, возвращает пустой словарь, и Pydantic использует все default-значения.
        """
        # Безопасно получаем словарь настроек. Если секции [llm_settings] нет, вернется {}
        # Используем `or {}` на случай, если секция есть, но она пустая (вернет None)
        llm_settings = st.secrets.get("llm_settings") or {}

        # распаковываем словарь в конструктор pydantic
        # если в словаре нет ключей, то Pydantic использует default-значения
        return cls(**llm_settings)
