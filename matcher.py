from typing import List

import instructor
from google import genai
from google.genai import types

from models import (
    SpecItem,
    ReconciliationRow,
    MatchStatus,
    LLMMatchpair,
    LLMMatchResult,
)


def compare_items(base: SpecItem, target: SpecItem) -> ReconciliationRow:
    """
    Сравнивает две конкретные позиции и формирует строку отчета.
    Проверяет количество, единицы измерения и описание.
    """

    notes = []

    # 1. проверка артикула
    # внимание: сравниваются значения, приведенные к нижнему регистру
    if base.sku.strip().lower() != target.sku.strip().lower():
        notes.append(f"Артикул: {base.sku} -> {target.sku}")

    # 2. проверка наименования
    # внимание: сравниваются значения, приведенные к нижнему регистру
    if base.name.strip().lower() != target.name.strip().lower():
        notes.append(f"Наименование: {base.name} -> {target.name}")

    # 3. проверка количества
    if base.quantity != target.quantity:
        notes.append(f"Количество: {base.quantity} -> {target.quantity}.")

    # 4. проверка ед. измерения
    if base.unit.strip().lower() != target.unit.strip().lower():
        notes.append(f"Ед. измерения: {base.unit} -> {target.unit}.")

    # 5. проверка описания
    # внимание: сравниваются значения, приведенные к нижнему регистру
    base_description_clean = base.description.strip().lower()
    target_description_clean = target.description.strip().lower()

    if base_description_clean != target_description_clean:
        if base_description_clean and target_description_clean:
            notes.append("Описания отличаются.")
        elif base_description_clean and not target_description_clean:
            notes.append(
                "В целевом документе отсутствует описание, которое есть в эталоне."
            )
        elif not base_description_clean and target_description_clean:
            notes.append(
                "В целевой документ добавлено описание, которого нет в эталоне."
            )

    status = MatchStatus.PARTIAL_MATCH if notes else MatchStatus.PERFECT_MATCH

    return ReconciliationRow(
        status=status,
        baseline_sku=base.sku,
        baseline_name=base.name,
        baseline_qty=base.quantity,
        baseline_unit=base.unit,
        baseline_description=base.description,
        target_sku=target.sku,
        target_name=target.name,
        target_qty=target.quantity,
        target_unit=target.unit,
        target_description=target.description,
        difference_notes="; ".join(notes),
    )


def llm_fuzzy_match(
    base_orphans: List[SpecItem],
    target_orphans: List[SpecItem],
    client: genai.Client,
) -> List[LLMMatchpair]:
    """
    Отправляет ненайденные остатки в LLM для семантического поиска пар.
    """

    # паттерн Guard Clause: "Вышибала" на входе. Нет данных? Сразу до свидания.
    if not base_orphans or not target_orphans:
        return []

    # составляем списки наименований позиций из исходного списка спецификаций
    base_names = [item.name for item in base_orphans]
    target_names = [item.name for item in target_orphans]

    prompt = f"""
    Твоя задача - сопоставить позиции из двух списков номенклатуры.
    Найди пары, которые означают один и тот же товар, но могут быть написаны по-разному (синонимы, перестановка слов, сокращения).
    
    ПРАВИЛА:
    1. Используй ТОЧНО ТЕ ЖЕ строки наименований, что переданы в списках.
    2. Если позиция из Списка А не имеет логичной пары в Списке Б, просто проигнорируй ее. Не выдумывай пары.
    
    СПИСОК А (Исходный документ (Эталон)):
    {base_names}
    
    СПИСОК Б (Целевой документ):
    {target_names}
    """

    instructor_client = instructor.from_genai(
        client=client,
        mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,  # используем нативный структурированный вывод genai
    )
    model = "gemini-3-flash-preview"

    try:
        response = instructor_client.chat.completions.create(
            model=model,
            response_model=LLMMatchResult,
            config=types.GenerateContentConfig(temperature=0.0),
            messages=[{"role": "user", "content": prompt}],
            max_retries=3,
        )
        return response.matches
    except Exception as e:
        print(f"Ошибка при LLM-сверке: {e}")
        return []


def reconcile(
    base_items: List[SpecItem],
    target_items: List[SpecItem],
    client: genai.Client,
) -> List[ReconciliationRow]:
    """
    Главная функция сверки (алгоритм Водопад).
    """

    results: List[ReconciliationRow] = []

    # создаем копии списков, из которых будем удалять найденные позиции
    unmatched_base = base_items.copy()
    unmatched_target = target_items.copy()

    # --- ЭТАП 1: точное совпадение по SKU ---
    # внимание: сравниваются значения, приведенные к нижнему регистру
    # идем с конца для безопасного удаления элементов из списка
    # `remove` удаляет элемент и сдвигает индексы, при `reversed` мы удаляем элементы с конца,
    # индексы для тех элементов, которые остались, не сдвигаются
    for b_item in reversed(unmatched_base):
        if not b_item.sku:
            continue
        for t_item in reversed(unmatched_target):
            # если SKU полностью совпали, то мы нашли пару и передаем ее в `compare_items` для сверки
            if (
                t_item.sku
                and t_item.sku.strip().lower() == b_item.sku.strip().lower()
            ):
                results.append(compare_items(b_item, t_item))
                unmatched_base.remove(b_item)
                unmatched_target.remove(t_item)
                break

    # --- ЭТАП 2: точное совпадение по наименованию ---
    # внимание: сравниваются значения, приведенные к нижнему регистру
    for b_item in reversed(unmatched_base):
        for t_item in reversed(unmatched_target):
            # если наименования полностью совпали, то мы нашли пару и передаем ее в `compare_items` для сверки
            if t_item.name.strip().lower() == b_item.name.strip().lower():
                results.append(compare_items(b_item, t_item))
                unmatched_base.remove(b_item)
                unmatched_target.remove(t_item)
                break

    # --- ЭТАП 3: LLM Fuzzy Match (Нечеткое совпадение) ---
    # если списки не пустые, то передаем их в `llm_fuzzy_match` для семантического поиска совпадающих пар

    if unmatched_base and unmatched_target:
        llm_matches = llm_fuzzy_match(unmatched_base, unmatched_target, client)

        for match in llm_matches:
            # строим итератор по условию совпадения наименования позиции в осташихся элементах `unmatched_xxx`
            # и наименования в найденных парах в `llm_fuzzy_match` - в ней мы указывали LLM оставлять
            # оригинальные наименования найденных пар - так что мы можем сравнить
            # если итератор пуст, то возвращаем `None`
            b_item = next(
                (
                    item
                    for item in unmatched_base
                    if item.name == match.baseline_name
                ),
                None,
            )
            t_item = next(
                (
                    item
                    for item in unmatched_target
                    if item.name == match.target_name
                ),
                None,
            )

            if b_item and t_item:  # если нашли совпадающую пару
                row = compare_items(
                    b_item, t_item
                )  # прогоняем через сравнение
                row.difference_notes += f" [Сопоставлено ИИ: {match.reason}]"  # добавляем, что семантическое совпадение было по мнению LLM
                results.append(row)
                unmatched_base.remove(b_item)
                unmatched_target.remove(t_item)

    # --- ЭТАП 4: недостача и излишки ---
    # все позиции, которые остались определяем в недостачи и излишки
    for b_item in unmatched_base:
        results.append(
            ReconciliationRow(
                status=MatchStatus.MISSING_IN_TARGET,
                baseline_sku=b_item.sku,
                baseline_name=b_item.name,
                baseline_qty=b_item.quantity,
                baseline_unit=b_item.unit,
                baseline_description=b_item.description,
                difference_notes="Позиция есть в Эталоне, но отсутствует в Заявке.",
            )
        )

    for t_item in unmatched_target:
        results.append(
            ReconciliationRow(
                status=MatchStatus.EXTRA_IN_TARGET,
                target_sku=t_item.sku,
                target_name=t_item.name,
                target_qty=t_item.quantity,
                target_unit=t_item.unit,
                target_description=t_item.description,
                difference_notes="Позиция есть в Заявке, но отсутствует в Эталоне.",
            )
        )

    return results


if __name__ == "__main__":
    from constants import API_KEY

    if not API_KEY:
        print("API_KEY не найден. Тест отменен.")
        exit(1)

    test_client = genai.Client(api_key=API_KEY)

    # имитируем данные из Эталона
    baseline = [
        SpecItem(
            sku="A1",
            name="Гайка М8",
            quantity=100,
            unit="шт",
            description="Сталь",
        ),
        SpecItem(
            sku="", name="Болт 10х50", quantity=50, unit="кг", description=""
        ),
        SpecItem(
            sku="",
            name="Скоба усиленная 200 * 700",
            quantity=20,
            unit="шт",
            description="",
        ),
        SpecItem(
            sku="C3", name="Шайба", quantity=200, unit="шт", description=""
        ),
    ]

    # имитируем данные из Заявки (с ошибками и изменениями)
    target = [
        SpecItem(
            # артикул совпадает
            sku="A1",
            # ошибка: name="Гайка М8"
            name="Гайка М8 цинк",
            # ошибка: quantity=100
            quantity=90,
            # ошибка: unit="шт"
            unit="упак",
            # ошибка: description="Сталь",
            description="Цинк",
        ),
        SpecItem(
            # ошибка: sku=""
            sku="B2",
            name="Болт 10х50",
            quantity=50,
            unit="кг",
            description="",
        ),
        SpecItem(
            # ошибка: name="Скоба усиленная 200 * 700" - другое название для `llm_fuzzy_match`
            sku="",
            name="Скоба стальная 200x700",
            quantity=20,
            unit="шт",
            description="",
        ),
        SpecItem(
            # ошибка: излишек
            sku="",
            name="Гвозди",
            quantity=5,
            unit="кг",
            description="",
        ),
        # ошибка: недостача - шайба потерялась
    ]

    print("Начинаем сверку...\n")
    report = reconcile(baseline, target, client=test_client)

    for row in report:
        print(f"[{row.status.value}]")
        print(
            f"  Эталон: {row.baseline_name} ({row.baseline_qty} {row.baseline_unit})"
        )
        print(
            f"  Заявка: {row.target_name} ({row.target_qty} {row.target_unit})"
        )
        if row.difference_notes:
            print(f"  Заметки: {row.difference_notes}")
        print("-" * 40)
