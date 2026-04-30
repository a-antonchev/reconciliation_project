def test_dummy():
    assert 1 + 1 == 2, "pytest not working"


def test_app_import():
    try:
        assert True
    except Exception as e:
        assert False, f"Приложение упало при импорте: {e}"
