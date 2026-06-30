from unittest.mock import MagicMock

from extractor import extract_specification
from models import LLMConfig, SpecificationDocument, SpecItem


def test_extract_specification_mocked():
    # 1. фейковый ответ, который мы ожидаем от LLM
    fake_response = SpecificationDocument(
        items=[SpecItem(sku="A1", name="Тест", quantity=5, unit="шт", description="")]
    )

    # 2. фейковый клиент instructor (тот, у которого есть .chat.completions.create)
    mock_instructor_client = MagicMock()
    # настраиваем его так, чтобы при вызове .chat.completions.create() он возвращал fake_response
    mock_instructor_client.chat.completions.create.return_value = fake_response

    # 3. создаем конфигурацию
    llm_config = LLMConfig()

    # 4. Вызываем нашу функцию
    result = extract_specification(
        document_markdown="Какой-то текст документа",
        instructor_client=mock_instructor_client,
        llm_config=llm_config,
    )

    assert result is not None
    assert len(result.items) == 1
    assert result.items[0].name == "Тест"
