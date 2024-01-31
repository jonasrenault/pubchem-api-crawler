import re

from pubchem_api_crawler.constants import ELEMENTS, COMPOUND_PROPERTIES

PATTERN = re.compile(r"(?:{})\d*-?\d*".format("|".join(ELEMENTS)))


def is_molecular_formula_input_valid(atoms: list[str]) -> bool:
    for atom in atoms:
        res = re.fullmatch(PATTERN, atom)
        if res is None:
            return False
    return True


def are_compound_properties_valid(properties: list[str]) -> bool:
    return all([p in COMPOUND_PROPERTIES for p in properties])
