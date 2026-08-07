"""
Where collected data is held, and how it is read back.

One module per table, owning its columns, its writes and its queries, and knowing nothing about
where the rows came from. Everything downstream of collection reads from here, including the search
that turns a typed name into an id, so nothing has to ask a data service who someone is.
"""

import unicodedata

def searchable(name: str) -> str:
    """
    A name reduced to what someone would type: lower case and without accents, so searching for
    Luka Doncic finds Luka Dončić.
    """

    return "".join(
        character
        for character in unicodedata.normalize("NFD", name.lower())
        if unicodedata.category(character) != "Mn"
    )
