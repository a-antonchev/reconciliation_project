import os

from streamlit.testing.v1 import AppTest


def test_app_loads_correctly():
    os.environ["GEMINI_API_KEY"] = "fake_test_key_789"

    # инициализируем приложение
    at = AppTest.from_file("app.py")

    # запускаем приложение
    at.run(timeout=10)

    # проверяем, что нет ошибок (exception)
    assert not at.exception

    # проверяем, что заголовок отрендерился
    assert at.title[0].value == "🤖 AI v.0.1.0 Сверка спецификаций"

    # проверяем наличие кнопок загрузки файлов
    assert len(at.file_uploader) == 2

    # проверяем наличие подзаголовков (Эталон и Заявка)
    assert len(at.subheader) == 2
    assert "Эталон" in at.subheader[0].value
    assert "Заявка" in at.subheader[1].value

    # проверяем наличие главной кнопки
    assert len(at.button) == 1
    assert at.button[0].label == "🚀 Запустить сверку"
