"""Homoglyph normalization — map lookalike characters to ASCII Latin.

Supplements unidecode for characters that may not map correctly.
Covers Cyrillic, Greek, and other scripts commonly used in homoglyph bypass attacks.
"""

from __future__ import annotations

# Map: confusable char (Unicode) -> ASCII Latin equivalent
# Covers Cyrillic, Greek, fullwidth, and other lookalikes used to bypass regex
CONFUSABLES_TO_LATIN = str.maketrans({
    # Cyrillic (common lookalikes)
    '\u0430': 'a',  # Cyrillic a
    '\u0435': 'e',  # Cyrillic e
    '\u043e': 'o',  # Cyrillic o
    '\u0440': 'p',  # Cyrillic r
    '\u0441': 'c',  # Cyrillic c
    '\u0443': 'y',  # Cyrillic u
    '\u0445': 'x',  # Cyrillic x
    '\u0454': 'e',  # Cyrillic ie
    '\u0456': 'i',  # Cyrillic i (dotted)
    '\u0457': 'yi',
    '\u0461': 'a',
    '\u0501': 'd',
    '\u051b': 'g',
    '\u051d': 'z',
    '\u0432': 'b',  # Cyrillic v (looks like b in some fonts)
    '\u043a': 'k',  # Cyrillic k
    '\u043c': 'm',  # Cyrillic m
    '\u043d': 'n',  # Cyrillic n
    '\u0442': 't',  # Cyrillic t
    '\u0410': 'A',  # Cyrillic A
    '\u0412': 'B',  # Cyrillic V
    '\u0415': 'E',  # Cyrillic E
    '\u041a': 'K',  # Cyrillic K
    '\u041c': 'M',  # Cyrillic M
    '\u041d': 'H',  # Cyrillic N
    '\u041e': 'O',  # Cyrillic O
    '\u0420': 'P',  # Cyrillic R
    '\u0421': 'C',  # Cyrillic S
    '\u0422': 'T',  # Cyrillic T
    '\u0423': 'Y',  # Cyrillic U
    '\u0425': 'X',  # Cyrillic Kh
    # Greek (lookalikes)
    '\u0391': 'A',  # Greek Alpha
    '\u0392': 'B',  # Greek Beta
    '\u0395': 'E',  # Greek Epsilon
    '\u0396': 'Z',  # Greek Zeta
    '\u0397': 'H',  # Greek Eta
    '\u0399': 'I',  # Greek Iota
    '\u039a': 'K',  # Greek Kappa
    '\u039c': 'M',  # Greek Mu
    '\u039d': 'N',  # Greek Nu
    '\u039f': 'O',  # Greek Omicron
    '\u03a1': 'P',  # Greek Rho
    '\u03a4': 'T',  # Greek Tau
    '\u03a5': 'Y',  # Greek Upsilon
    '\u03a7': 'X',  # Greek Chi
    '\u03b1': 'a',  # Greek alpha
    '\u03b2': 'b',  # Greek beta
    '\u03b5': 'e',  # Greek epsilon
    '\u03b6': 'z',  # Greek zeta
    '\u03b7': 'n',  # Greek eta (η)
    '\u03b9': 'i',  # Greek iota
    '\u03ba': 'k',  # Greek kappa
    '\u03bc': 'u',  # Greek mu (μ)
    '\u03bd': 'v',  # Greek nu
    '\u03bf': 'o',  # Greek omicron
    '\u03c1': 'p',  # Greek rho (ρ)
    '\u03c4': 't',  # Greek tau
    '\u03c5': 'u',  # Greek upsilon
    '\u03c7': 'x',  # Greek chi
    # IPA / extended Latin
    '\u0251': 'a',  # Latin small letter alpha
    '\u0261': 'g',  # Latin small letter script g
})


def normalize_confusables(text: str) -> str:
    """Replace confusable characters with ASCII Latin equivalents."""
    if not text:
        return text
    return text.translate(CONFUSABLES_TO_LATIN)
