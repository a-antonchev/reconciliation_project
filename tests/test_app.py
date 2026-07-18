from streamlit.testing.v1 import AppTest


def test_app_loads_correctly():
    # инициализируем приложение
    at = AppTest.from_file("app.py")

    # фейковый API_KEY для streamlit
    at.secrets["llm_settings"] = {
        "GEMINI_API_KEY": "fake_test_key_789",
        "model_name": "gemini-3-flash-preview",
    }

    # запускаем приложение
    at.run(timeout=20)

    # проверяем, что нет ошибок (exception)
    assert not at.exception

    # проверяем, что заголовок отрендерился
    assert "🤖 AI Сверка спецификаций" in at.title[0].value

    # проверяем наличие кнопок загрузки файлов
    assert len(at.file_uploader) == 2

    # проверяем наличие подзаголовков (Эталон и Заявка)
    assert len(at.subheader) == 2
    assert "Эталон" in at.subheader[0].value
    assert "Заявка" in at.subheader[1].value

    # проверяем наличие главной кнопки
    assert len(at.button) == 1
    assert at.button[0].label == "🚀 Запустить сверку"


def test_axiom_logger_console_fallback():
    """Test that setup_axiom_logger falls back to console handler when no axiom_settings."""
    at = AppTest.from_file("app.py")
    at.secrets["llm_settings"] = {
        "GEMINI_API_KEY": "fake_test_key",
    }
    at.secrets["axiom_settings"] = {}
    at.run(timeout=20)
    assert not at.exception


def test_axiom_logger_with_config():
    """Test app loads with full axiom_settings (axiom-py path)."""
    at = AppTest.from_file("app.py")
    at.secrets["llm_settings"] = {
        "GEMINI_API_KEY": "fake_test_key",
    }
    at.secrets["axiom_settings"] = {
        "TOKEN": "test-token",
        "DATASET": "test-dataset",
        "EDGE": "test.axiom.co",
    }
    at.run(timeout=20)
    assert not at.exception
