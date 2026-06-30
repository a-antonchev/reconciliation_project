from unittest.mock import MagicMock

from extractor import extract_specification
from models import LLMConfig, SpecificationDocument, SpecItem


def test_extract_specification_mocked():
    # задаем фейковый ответ
    fake_response = SpecificationDocument(
        items=[SpecItem(sku="123", name="Test", quantity=10, unit="шт", description="Сталь")]
    )
    # задаем фейкового клиента для `instructor.from_genai()`
    mock_instructor_client = MagicMock()

    # перехватываем вызов `chat.completions.create()` и задаем возвращаемое значение на `fake_response`
    mock_instructor_client.chat.completions.create.return_value = fake_response

    # задаем конфигурацию LLM
    llm_config = LLMConfig()

    test_doc_text = "Какой-то документ"
    result = extract_specification(
        document_markdown=test_doc_text,
        instructor_client=mock_instructor_client,
        llm_config=llm_config,
    )

    assert result is not None
    assert len(result.items) == 1
    assert result.items[0].name == "Test"

    # проверяем, что метод был вызван только один раз
    mock_instructor_client.chat.completions.create.assert_called_once()

    # достаем аргументы, с которыми был вызван метод
    call_args = mock_instructor_client.chat.completions.create.call_args.kwargs

    # проверяем модель
    assert call_args["model"] == llm_config.model_name

    # проверяем температуру
    assert call_args["config"].temperature == llm_config.temperature

    # проверяем формат ответа
    assert call_args["response_model"] == SpecificationDocument

    # проверяем, что текст документа попал в запрос
    assert test_doc_text in call_args["messages"][0]["content"]
