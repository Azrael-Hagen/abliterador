"""Unit tests for ChatQualityChecker."""

import pytest

from abliterador_web.chat_quality import ChatQualityChecker


@pytest.fixture
def checker():
    return ChatQualityChecker(
        min_length=10,
        max_repetition_allowed=0.35,
        generic_threshold=0.8,
    )


def test_good_response(checker):
    """A well-formed, coherent response should score high."""
    response = "La inteligencia artificial es una rama de la informática que estudia la capacidad de las máquinas para realizar tareas que típicamente requieren inteligencia humana."
    score = checker.check_response(response)
    assert score.is_acceptable
    assert score.score >= 0.7
    assert len(score.issues) == 0


def test_empty_response(checker):
    """Empty responses should fail."""
    score = checker.check_response("")
    assert not score.is_acceptable
    assert score.score == 0.0


def test_very_short_response(checker):
    """Responses shorter than min_length should be flagged."""
    score = checker.check_response("nope")
    assert not score.is_acceptable
    assert "muy corta" in " ".join(score.issues).lower()


def test_generic_response(checker):
    """Generic 'I don't know' type responses should be downgraded."""
    response = "No sé qué responder a eso."
    score = checker.check_response(response)
    assert not score.is_acceptable
    assert "genérica" in " ".join(score.issues).lower()


def test_repeated_text(checker):
    """Highly repetitive responses should be flagged."""
    response = "hola hola hola " * 10 + "mundo"
    score = checker.check_response(response)
    assert not score.is_acceptable
    assert "repetición" in " ".join(score.issues).lower()


def test_nonsense_pattern(checker):
    """Responses with nonsense patterns should be flagged."""
    response = "hello world ??? ??? ???"
    score = checker.check_response(response)
    assert not score.is_acceptable


def test_coherence_check_with_context(checker):
    """Response coherence relative to prompt context."""
    prompt = "¿Cuál es la capital de Francia?"
    good_response = "París es la capital de Francia y también se conoce como la Ciudad de la Luz."
    score = checker.check_response(good_response, context=prompt)
    assert score.is_acceptable

    bad_response = "Los pájaros vuelan en el cielo azul y son muy bonitos."
    score = checker.check_response(bad_response, context=prompt)
    assert not score.is_acceptable


def test_quality_summary(checker):
    """Quality summary should reflect score."""
    good_score = checker.check_response("Esto es una respuesta de muy buena calidad y bien formada.")
    summary = checker.get_quality_summary(good_score)
    assert "✓" in summary or "aceptable" in summary.lower()

    bad_score = checker.check_response("no")
    summary = checker.get_quality_summary(bad_score)
    assert "✗" in summary or "baja" in summary.lower()
