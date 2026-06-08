import difflib
import re
import unicodedata


PLANO_ESTUDOS_BASES = {
    "plano de estudo",
    "plano de estudos",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def is_plano_estudos_module(name: str) -> bool:
    text = normalize_text(name)
    if not text:
        return False

    if text in PLANO_ESTUDOS_BASES:
        return True

    if "plano" in text and "estud" in text:
        return True

    return False


def module_names_equivalent(name_a: str, name_b: str, minimum_ratio: float = 0.92) -> bool:
    a = normalize_text(name_a)
    b = normalize_text(name_b)

    if not a or not b:
        return False

    if a == b:
        return True

    if is_plano_estudos_module(a) and is_plano_estudos_module(b):
        return True

    if a in b or b in a:
        return True

    return difflib.SequenceMatcher(None, a, b).ratio() >= minimum_ratio


def module_match_score(target_name: str, candidate_name: str, candidate_teacher: str = "") -> float:
    target = normalize_text(target_name)
    candidate = normalize_text(candidate_name)
    teacher = normalize_text(candidate_teacher)

    if not target or not candidate:
        return 0.0

    score = difflib.SequenceMatcher(None, target, candidate).ratio()

    if is_plano_estudos_module(target) and is_plano_estudos_module(candidate):
        score = max(score, 0.99)

    if teacher and "professor" in teacher:
        score += 0.01

    return min(score, 1.0)
