from unittest.mock import MagicMock

from google import genai
from pytest_mock import MockerFixture

from extractor import extract_specification
from models import SpecificationDocument, SpecItem


def test_extract_specification_mocked(mocker: MockerFixture):
    # 1. фейковый ответ, который мы ожидаем от LLM
    fake_response = SpecificationDocument(
        items=[SpecItem(sku="A1", name="Тест", quantity=5, unit="шт", description="")]
    )

    # 2. фейковый клиент instructor (тот, у которого есть .chat.completions.create)
    mock_instructor_client = MagicMock()
    # настраиваем его так, чтобы при вызове .chat.completions.create() он возвращал fake_response
    mock_instructor_client.chat.completions.create.return_value = fake_response

    # 3. подменяем функцию from_genai внутри модуля extractor
    # когда extractor вызовет instructor.from_genai,
    # он получит наш mock_instructor_client вместо настоящего.
    mocker.patch("extractor.instructor.from_genai", return_value=mock_instructor_client)

    # 4. создаем фейкового базового клиента
    # так как мы замокали from_genai, проверка isinstance больше не страшна,
    # но для строгости типов (чтобы линтер не ругался) используем spec=genai.Client
    fake_client = MagicMock(spec=genai.Client)

    # 5. Вызываем нашу функцию
    result = extract_specification(document_markdown="Какой-то текст документа", client=fake_client)

    assert result is not None
    assert len(result.items) == 1
    assert result.items[0].name == "Тест"
