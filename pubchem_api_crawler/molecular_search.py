import requests
import pandas as pd


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
        max_results: int = 50000,
    ):
        # todo: check list of atoms is valid format
        url = MolecularFormulaSearch.PUBCHEM_SEARCH_URL + "".join(atoms)
        if properties:
            url += "/property/" + ",".join(properties)
        else:
            url += "/cids"

        url += f"/JSON?AllowOtherElements={str(allow_other_elements).lower()}&MaxRecords={max_results}"

    def search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] = None,
        max_results: int = 2000000,
    ):
        """
        Faire une recherche par formule avec les atomes spécifiés. Renvoyer un df pandas avec les cids et les propriétés demandées.

        Description de l'api fastsearch https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Molecular-Formula
        Syntaxe de la liste des atomes https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf
        Liste des propriétés à request https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables

        Args:
            atoms (list[str]): _description_
            allow_other_elements (bool): _description_
            properties (list[str]): _description_
            max_results (int, optional): _description_. Defaults to 50000.
        """
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
