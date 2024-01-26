import pandas as pd
import requests

from pubchem_api_crawler.utils import is_molecular_formula_input_valid


class MolecularFormulaSearch:
    PUBCHEM_SEARCH_URL = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula/"
    )
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Accept": "application/json",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }

    def __init__(self) -> None:
        pass

    def _get_request_url(
        self,
        atoms: list[str],
        allow_other_elements: bool,
        properties: list[str] = None,
        max_results: int = 2000000,
    ) -> str:
        """
        Get molecular formula search url

        Args:
            atoms (list[str]): molecular formula search input
            allow_other_elements (bool): allow other elements
            properties (list[str], optional): list of properties. Defaults to None.
            max_results (int, optional): max results. Defaults to 2000000.

        Returns:
            str: _description_
        """
        url = MolecularFormulaSearch.PUBCHEM_SEARCH_URL + "".join(atoms)
        if properties:
            url += "/property/" + ",".join(properties)
        else:
            url += "/cids"

        url += f"/JSON?AllowOtherElements={str(allow_other_elements).lower()}&MaxRecords={max_results}"
        return url

    def search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] = None,
        max_results: int = 2000000,
    ) -> pd.DataFrame | None:
        """
        Perform a fast molecular formula search using PubChem API.
        See https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Molecular-Formula
        for a description of molecular formula search, and
        https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf for
        a description of valid molecular formal search inputs.

        The search can retrieve a list of compound properties for each result.
        If no properties are given, only cids are returned.
        See https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables
        for a list of valid compound properties.

        Args:
            atoms (list[str]): molecular formula search input
            allow_other_elements (bool): allow other elements than those specified in list of atoms
            properties (list[str]): list of compound properties to retrieve
            max_results (int, optional): max results. Defaults to 2000000.

        Returns:
            pd.DataFrame | None: a pandas DataFrame with search results; None if no results
        """
        assert is_molecular_formula_input_valid(
            atoms
        ), "Invalid list of atom given. See https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf for valid molecular formula search inputs."

        url = self._get_request_url(
            atoms, allow_other_elements, properties, max_results
        )

        r = requests.get(url, headers=MolecularFormulaSearch.HEADERS)
        r.raise_for_status()
        print(r.headers)

        results = r.json()
        if "IdentifierList" in results:
            cids = results["IdentifierList"]["CID"]
            df = pd.DataFrame(cids, columns=("CID",)).set_index("CID")
            return df

        if "PropertyTable" in results and "Properties" in results["PropertyTable"]:
            props = results["PropertyTable"]["Properties"]
            df = pd.DataFrame(props).set_index("CID")
            return df

        return None
