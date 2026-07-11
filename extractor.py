import instructor
from google import genai
from google.genai import types

from models import LLMConfig, SpecificationDocument


def extract_specification(
    document_markdown: str, instructor_client: instructor.Instructor, llm_config: LLMConfig
) -> SpecificationDocument:
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

    try:
        specification = instructor_client.chat.completions.create(
            model=llm_config.model_name,
            response_model=SpecificationDocument,
            messages=[{"role": "user", "content": prompt}],
            config=types.GenerateContentConfig(
                temperature=0.0,  # температура генерации, для парсинга всегда 0.0
            ),
            max_retries=llm_config.max_retries,
        )
        return specification
    except Exception as e:
        print(f"Ошибка при извлечении данных: {e}")
        raise


if __name__ == "__main__":
    import streamlit as st

    api_key = st.secrets.get("llm_settings", {}).get("GEMINI_API_KEY")

    if not api_key:
        print("API_KEY не найден. Тест отменен.")
        exit(1)

    test_client = genai.Client(api_key=api_key)
    instructor_client = instructor.from_genai(
        client=test_client,
        mode=instructor.Mode.JSON,
    )
    llm_config = LLMConfig()

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

    result = extract_specification(test_md, instructor_client, llm_config)
    print(result.model_dump_json(indent=2))  #
