from app.utils.cleaning import clean_text, optimize_description_for_llm


def test_optimize_description_for_llm_keeps_urls_as_plain_text():
    text = "Voir https://example.com/ressource pour plus d'informations"

    result = optimize_description_for_llm(text)

    assert "https://example.com/ressource" in result
    assert "[URL]" not in result


def test_clean_text_preserves_anchor_href_as_plain_text():
    text = "<a href='https://example.com/doc'>Documentation</a>"

    result = clean_text(text)

    assert "Documentation" in result
    assert "https://example.com/doc" in result
    assert "<a" not in result


def test_clean_text_converts_literal_escaped_newlines_to_real_line_breaks():
    text = "Première ligne\\nDeuxième ligne"

    result = clean_text(text)

    assert result == "Première ligne\nDeuxième ligne"
    assert "\\n" not in result
