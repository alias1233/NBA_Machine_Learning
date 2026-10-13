"""SQLite stores for the collected data."""

import unicodedata

def searchable(name: str) -> str:
    """Returns the name in lowercase with accents removed, for search matching."""

    return "".join(
        character
        for character in unicodedata.normalize("NFD", name.lower())
        if unicodedata.category(character) != "Mn"
    )
