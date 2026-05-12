import pytest

from parser import parse_file


def test_parse_unsupported_file():
    # тест на исключение при парсинге формата `.doc`
    with pytest.raises(ValueError, match="Старый формат Word"):
        parse_file("tests/fixtures/test_old_doc.doc")


def test_parse_excel():
    # тест парсинга excel
    md = parse_file("tests/fixtures/test.xlsx")

    assert "#### Лист Excel:" in md
    # проверка таблицы в файле markdown
    assert "|" in md


def test_parse_word():
    # тест парсинга word
    md = parse_file("tests/fixtures/test.docx")

    assert "### Таблицы из документа:" in md
    assert "|" in md
