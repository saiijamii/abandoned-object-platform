PERSON_NAMES = {"person"}
LUGGAGE_NAMES = {"backpack", "handbag", "suitcase", "luggage", "duffel"}


def semantic_class(name: str) -> str | None:
    name = name.strip().lower()
    if name in PERSON_NAMES:
        return "person"
    if name in LUGGAGE_NAMES:
        return "luggage"
    return None
