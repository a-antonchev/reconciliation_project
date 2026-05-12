from matcher import compare_items
from models import MatchStatus, SpecItem


def test_compare_items_perfect_match():
    # тест полного совпадения

    base = SpecItem(sku="123", name="Гайка", quantity=10, unit="шт", description="Сталь")
    target = SpecItem(sku="123", name="Гайка", quantity=10, unit="шт", description="Сталь")

    result = compare_items(base, target)

    assert result.status == MatchStatus.PERFECT_MATCH
    assert result.difference_notes == ""


def test_compare_items_partial_match():
    # тест частичного совпадения

    base = SpecItem(sku="123", name="Гайка", quantity=10, unit="шт", description="Сталь")
    # различие в количсевте и ед. измерения
    target = SpecItem(sku="123", name="Гайка", quantity=8, unit="КГ", description="Сталь")

    result = compare_items(base, target)

    assert result.status == MatchStatus.PARTIAL_MATCH
    assert "Ед. измерения: шт -> КГ." in result.difference_notes
    assert "Количество: 10.0 -> 8.0." in result.difference_notes
