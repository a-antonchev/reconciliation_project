from unittest.mock import MagicMock, patch

from google import genai

from extractor import extract_specification
from models import SpecificationDocument, SpecItem


# подменяем `extractor.instructor.from_genai` на 'mock_from_genai'
@patch("extractor.instructor.from_genai")
def test_extract_specification_mocked(mock_from_genai):
    fake_response = SpecificationDocument(
        items=[SpecItem(sku="123", name="Test", quantity=10, unit="шт", description="Сталь")]
    )

    # задаем фейкового клиента для `instructor.from_genai()`
    mock_instructor_client = MagicMock()

    # перехватываем вызов `chat.completions.create()` и задаем возвращаемое значение на fake_response
    mock_instructor_client.chat.completions.create.return_value = fake_response

    # при вызове `instructor.from_genai()` мы отдадим фейкового клиента
    mock_from_genai.return_value = mock_instructor_client

    # задаем базового фейкового клиента
    mock_client = MagicMock(spec=genai.Client)

    test_doc_text = "Какой-то документ"
    result = extract_specification(document_markdown=test_doc_text, client=mock_client)

    assert result is not None
    assert len(result.items) == 1
    assert result.items[0].name == "Test"

    # проверяем, что метод был вызван только один раз
    mock_instructor_client.chat.completions.create.assert_called_once()

    # достаем аргументы, с которыми был вызван метод
    call_args = mock_instructor_client.chat.completions.create.call_args.kwargs

    # проверяем модель
    assert call_args["model"] == "gemini-3-flash-preview"

    # проверяем температуру
    assert call_args["config"].temperature == 0.0

    # проверяем формат ответа
    assert call_args["response_model"] == SpecificationDocument

    # проверяем, что текст документа попал в запрос
    assert test_doc_text in call_args["messages"][0]["content"]
