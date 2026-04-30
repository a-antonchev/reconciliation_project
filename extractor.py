import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from models import SpecificationDocument


def extract_specification(
    document_markdown: str, client: genai.Client, max_retries: int = 3
) -> SpecificationDocument | None:
    """
    Извлекает спецификацию из сырого текста/markdown документа.
    """

    prompt = f"""
    Ты - эксперт по закупкам и анализу документов.
    Твоя задача: найти спецификацию номенклатуры в предоставленном тексте документа и извлечь её.

    ПРАВИЛА:
    1. Игнорируй шапки договоров, реквизиты, подписи, печати и прочий юридический мусор.
    2. Извлеки только список товаров/услуг.
    3. Если артикула нет, возвращай пустую строку "".
    4. Если описание встроено в наименование, постарайся разделить их, но главное - не потеряй суть.
    5. Единицы измерения приводи к единому стандарту (шт, кг, м, упак).
    6. Ответ должен быть в формате JSON, без каких-либо вводных слов или пояснений.

    ТЕКСТ ДОКУМЕНТА:
    {document_markdown}
    """

    model = "gemini-3-flash-preview"

    config = types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=SpecificationDocument,
    )

    # создаем чат, чтобы LLM помнила контент, т.к. `model.generate_content` каждый раз начинает с чистого листа,
    # а нам нужно сделать несколько запросов в цикле (если что-то пойдет не так), но при этом сохранить контент
    chat = client.chats.create(model=model, config=config)

    current_message = types.Part.from_text(text=prompt)

    # цикл, если модель будет ошибаться:
    for attempt in range(1, max_retries):
        print(f"Попытка {attempt} из {max_retries}:")

        try:
            response = chat.send_message(
                current_message
            )  # метод send_message спроектирован исключительно для отправки сообщений от пользователя

            if response.text:
                specification = SpecificationDocument.model_validate_json(  # -> class Pydantic
                    response.text
                )
                return specification
        except ValidationError as e:
            errors = e.errors()
            if errors and errors[0].get("type") == "json_invalid":
                print(f"Ошибка валидации ответа Pydantic: {e}.")
            prompt = (
                f"Твой предыдущий JSON не прошел валидацию по схеме. Ошибки: {e}."
                "Пожалуйста, внимательно пересмотри схему и текст документа и верни исправленный JSON."
            )
            current_message = types.Part.from_text(text=prompt)

        except Exception as e:
            print(f"Ошибка при извлечении данных: {e}")
            time.sleep(1)

    print("Не удалось извлечь данные после нескольких попыток.")
    return None


if __name__ == "__main__":
    from constants import API_KEY

    if not API_KEY:
        print("API_KEY не найден. Тест отменен.")
        exit(1)

    test_client = genai.Client(api_key=API_KEY)

    test_md_good = """
    ДОГОВОР ПОСТАВКИ №123
    г. Москва
    ...
    Спецификация:
    1. Гайка М8 оцинкованная (арт. G-88) - 100 шт. ГОСТ 12345
    2. Болт М8х20 - 50 кг.
    ...
    Подписи сторон: ________
    """

    print("------- Тест с хорошими данными -------")

    result_good = extract_specification(test_md_good, client=test_client)
    if result_good:
        print(result_good.model_dump_json(indent=2))

    test_md_bad = """
    Счет-фактура
    Поставщик: ООО "Рога и копыта"
    Покупатель: ...
    1. Шуруп универсальный. Кол-во: Пятьсот штук. Арт: SH-01
    """

    print("------- Тест с плохими данными -------")

    result_bad = extract_specification(test_md_bad, client=test_client)
    if result_bad:
        print(result_bad.model_dump_json(indent=2))
