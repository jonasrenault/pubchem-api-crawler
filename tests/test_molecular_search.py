import pytest
from pubchem_api_crawler.molecular_search import MolecularFormulaSearch


def test_molecular_formula_search_raises_error_for_invalid_search_input():
    mf = MolecularFormulaSearch()
    with pytest.raises(AssertionError) as exc:
        mf.search(
            ["XE", "H", "B"],
            allow_other_elements=False,
            properties=["MolecularFormula", "CanonicalSMILES"],
        )
