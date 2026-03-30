"""
Chat Quality Checker - Lightweight heuristic validation for LLM responses.

Detects common issues like:
- Truncated/empty responses
- Excessive repetition
- Generic non-sense patterns
- Incoherence with prompt context
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityScore:
    """Quality assessment result."""

    score: float  # 0.0 (poor) to 1.0 (excellent)
    is_acceptable: bool  # True if score >= 0.5
    issues: list[str]  # List of detected problems


class ChatQualityChecker:
    """Validate LLM responses without requiring extra LLM calls."""

    def __init__(
        self,
        min_length: int = 10,
        max_repetition_allowed: float = 0.35,
        generic_threshold: float = 0.8,
    ):
        """
        Args:
            min_length: Minimum acceptable response length
            max_repetition_allowed: Max fraction of text that can be repetitive (0.0-1.0)
            generic_threshold: Threshold for generic response detection
        """
        self.min_length = min_length
        self.max_repetition_allowed = max_repetition_allowed
        self.generic_threshold = generic_threshold

        # Patterns for generic/non-sense responses
        self.generic_patterns = [
            r"^(i\s+)?don't\s+(know|understand)",
            r"^(lo\s+)?siento|no\s+puedo|no\s+sé",
            r"^(error|oops|whoops|sorry)",
            r"^(not\s+applicable|n/a|n\.a\.)",
            r"^\.+$|^,+$|^-+$",  # Only punctuation
        ]

        # Common non-sentential completions
        self.nonsense_markers = [
            r".*\?{3,}.*",  # 3 or more question marks anywhere
            r".*(::::|====|>>>+).*",  # Excessive special char sequences
            r"^[a-z]{1,2}\s*[a-z]{1,2}\s*$",  # Very short letter combinations
        ]

    def check_response(
        self,
        response: str,
        context: Optional[str] = None,
    ) -> QualityScore:
        """
        Validate a model response.

        Args:
            response: The text to validate
            context: Optional original prompt (for coherence checks)

        Returns:
            QualityScore with assessment
        """
        issues: list[str] = []
        score = 1.0

        # Check 1: Length
        response_clean = response.strip()
        if len(response_clean) < self.min_length:
            issues.append(f"Respuesta muy corta ({len(response_clean)} caracteres)")
            score -= 0.4

        # Check 2: Empty/only whitespace
        if not response_clean:
            issues.append("Respuesta vacía")
            return QualityScore(score=0.0, is_acceptable=False, issues=issues)

        # Check 3: Generic patterns
        response_lower = response_clean.lower()
        for pattern in self.generic_patterns:
            if re.match(pattern, response_lower):
                issues.append("Respuesta demasiado genérica")
                score -= 0.55
                break

        # Check 4: Nonsense patterns
        for pattern in self.nonsense_markers:
            if re.search(pattern, response_lower):
                issues.append("Patrón de respuesta sin sentido detectado")
                score -= 0.65
                break

        # Check 5: Repetition detection
        repeat_score = self._measure_repetition(response_clean)
        if repeat_score > self.max_repetition_allowed:
            issues.append(f"Excesiva repetición detectada ({repeat_score:.0%})")
            score -= 0.45

        # Check 6: Context coherence (if context provided)
        if context:
            coherence = self._check_coherence(response_clean, context)
            if coherence < 0.3:
                issues.append("Respuesta poco coherente con la pregunta")
                score -= 0.40

        # Ensure score is in [0, 1]
        score = max(0.0, min(1.0, score))

        return QualityScore(
            score=score,
            is_acceptable=score > 0.65,  # Threshold > 0.65 (stricter)
            issues=issues,
        )

    def _measure_repetition(self, text: str) -> float:
        """Detect repeated sequences in text."""
        if len(text) < 20:
            return 0.0

        # Look for repeated phrases (3+ word sequences)
        words = text.lower().split()
        if len(words) < 6:
            return 0.0

        total_repeated = 0
        seen_phrases: dict[str, int] = {}

        for i in range(len(words) - 2):
            phrase = " ".join(words[i : i + 3])
            if phrase not in seen_phrases:
                seen_phrases[phrase] = 0
            seen_phrases[phrase] += 1

        # Calculate proportion of repeated text
        for count in seen_phrases.values():
            if count > 1:
                total_repeated += (count - 1) * 3  # 3 words per phrase

        return total_repeated / len(words) if words else 0.0

    def _check_coherence(self, response: str, prompt: str) -> float:
        """
        Simple coherence check: do key terms from prompt appear in response?
        Returns 0.0-1.0 where 1.0 = perfectly coherent.
        """
        if not prompt or not response:
            return 1.0

        # Extract keywords from prompt (nouns, verbs)
        prompt_words = set(
            w.lower() for w in re.findall(r"\b[a-záéíóúñ]{3,}\b", prompt.lower())
        )
        response_words = set(
            w.lower() for w in re.findall(r"\b[a-záéíóúñ]{3,}\b", response.lower())
        )

        if not prompt_words:
            return 1.0

        # Overlap metric
        overlap = len(prompt_words & response_words)
        return overlap / len(prompt_words)

    def get_quality_summary(self, score: QualityScore) -> str:
        """Human-readable quality summary."""
        if score.score >= 0.8:
            return "✓ Respuesta de calidad"
        elif score.score >= 0.5:
            return f"⚠ Respuesta aceptable ({score.score:.0%})"
        else:
            return f"✗ Respuesta de baja calidad ({score.score:.0%})"
