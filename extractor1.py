import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import instructor
from models import SpecificationDocument

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# оборачиваем клиента gemini в instructor
instructor_client = instructor.from_genai(
    client=client,
    mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,  # используем нативный структурированный вывод genai
)


def extract_specification(document_markdown: str) -> SpecificationDocument:
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
    
    ТЕКСТ ДОКУМЕНТА:
    {document_markdown}
    """

    model = "gemini-3-flash-preview"

    try:
        specification = instructor_client.chat.completions.create(
            model=model,
            response_model=SpecificationDocument,
            messages=[{"role": "user", "content": prompt}],
            config=types.GenerateContentConfig(
                temperature=0.0,  # максимально приближаем к поведению строгого алгоритма
            ),
            max_retries=3,
        )
        return specification
    except Exception as e:
        print(f"Ошибка при извлечении данных: {e}")
        raise


if __name__ == "__main__":
    test_md = """
    ДОГОВОР ПОСТАВКИ №123
    г. Москва
    ...
    Спецификация:
    1. Гайка М8 оцинкованная (арт. G-88) - 100 шт. ГОСТ 12345
    2. Болт М8х20 - 50 кг.
    ...
    Подписи сторон: ________
    """

    result = extract_specification(test_md)
    print(result.model_dump_json(indent=2))  #
