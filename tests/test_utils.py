from pubchem_api_crawler.utils import is_molecular_formula_input_valid


def test_is_molecular_formula_input_valid():
    assert is_molecular_formula_input_valid(["C1-8"])
    assert is_molecular_formula_input_valid(["C-8"])
    assert is_molecular_formula_input_valid(["C7"])
    assert is_molecular_formula_input_valid(["C"])
    assert is_molecular_formula_input_valid(["C1"])
    assert is_molecular_formula_input_valid(["C-"])
    assert is_molecular_formula_input_valid(["C"])

    assert is_molecular_formula_input_valid(["C", "He-7", "H1-", "C3"])

    assert not is_molecular_formula_input_valid(["CU"])
    assert not is_molecular_formula_input_valid(["X"])
    assert not is_molecular_formula_input_valid(["XE"])
    assert not is_molecular_formula_input_valid(["C1a3"])
