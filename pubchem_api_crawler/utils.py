import re

from pubchem_api_crawler.constants import ELEMENTS

PATTERN = re.compile(r"(?:{})\d*-?\d*".format("|".join(ELEMENTS)))


def is_molecular_formula_input_valid(atoms: list[str]) -> bool:
    for atom in atoms:
        res = re.fullmatch(PATTERN, atom)
        if res is None:
            return False
    return True
