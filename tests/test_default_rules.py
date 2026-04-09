from app.config import DEFAULT_RULES


def test_documents_default_contains_pdf():
    assert "Documents" in DEFAULT_RULES
    assert ".pdf" in DEFAULT_RULES["Documents"]["extensions"]
