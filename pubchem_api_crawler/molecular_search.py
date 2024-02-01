from json import JSONDecodeError
import logging
import time
import urllib.parse

import pandas as pd
from requests import HTTPError
from tqdm import tqdm

from pubchem_api_crawler.rest_api import _send_rest_query
from pubchem_api_crawler.utils import (
    is_molecular_formula_input_valid,
    are_compound_properties_valid,
)

LOGGER = logging.getLogger(__name__)


class MolecularFormulaSearch:
    PUBCHEM_SEARCH_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Accept": "application/json",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }

    def search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] | None = None,
        max_results: int = 2000000,
        _async: bool = False,
        async_max_query_results: int = 50000,
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
            _async (bool, optional): use async REST API. Default to False.
            async_max_query_results (int, optional): max results per query for async search. Defaults to 50000.

        Returns:
            pd.DataFrame | None: a pandas DataFrame with search results; None if no results
        """
        assert is_molecular_formula_input_valid(
            atoms
        ), "Invalid list of atoms given. See https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf for valid molecular formula search inputs."

        if properties:
            assert are_compound_properties_valid(
                properties
            ), "Invalid list of properties given. See https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables for list of compound properties."

        try:
            if _async:
                return self._async_search(
                    atoms,
                    allow_other_elements,
                    properties,
                    max_results,
                    async_max_query_results,
                )

            return self._rest_api_search(
                atoms, allow_other_elements, properties, max_results
            )
        except HTTPError as exc:
            if "Search returned no hits" in exc.response.text:
                LOGGER.warning("Your search returned no hits.")
                return None
            if "PUGREST.Timeout" in exc.response.text:
                LOGGER.error(
                    "Timeout error for REST API Molecular Search Query. You should try using the async REST API with _async=True."
                )
            raise exc

    def _rest_api_search(
        self,
        atoms: list[str],
        allow_other_elements: bool,
        properties: list[str] | None,
        max_results: int,
    ) -> pd.DataFrame | None:
        """
        Perform molecular formula search using REST API.
        https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Molecular-Formula

        Args:
            atoms (list[str]): molecular formula search input
            allow_other_elements (bool): allow other elements than those specified in list of atoms
            properties (list[str]): list of compound properties to retrieve
            max_results (int, optional): max results. Defaults to 2000000.

        Returns:
            pd.DataFrame: a pandas DataFrame with search results
        """
        url = _get_rest_query_url(
            atoms, allow_other_elements, properties, max_results, False
        )
        LOGGER.info("Executing Molecular Formula Search query")
        results = _send_rest_query(url)

        if "IdentifierList" in results:
            cids = results["IdentifierList"]["CID"]
            df = pd.DataFrame(cids, columns=("CID",))
            return df

        if "PropertyTable" in results and "Properties" in results["PropertyTable"]:
            props = results["PropertyTable"]["Properties"]
            df = pd.DataFrame(props)
            return df

        return None

    def _async_search(
        self,
        atoms: list[str],
        allow_other_elements: bool,
        properties: list[str] | None,
        max_results: int,
        max_query_results: int,
    ):
        url = _get_rest_query_url(
            atoms, allow_other_elements, properties, max_results, True
        )
        LOGGER.info("Executing Molecular Formula Async Search query")
        result = _send_rest_query(url)
        try:
            listkey = result["Waiting"]["ListKey"]
        except KeyError:
            LOGGER.error(
                f"An error occured while submitting Async Molecular Formula Search request: {result}"
            )
            return None

        _poll_async_query_results(listkey)

        return _retrieve_async_query_results(
            listkey, properties, max_results, max_query_results
        )


def _get_rest_query_url(
    atoms: list[str],
    allow_other_elements: bool,
    properties: list[str] = None,
    max_results: int = 2000000,
    _async: bool = False,
) -> str:
    """
    Get molecular formula search query url

    Args:
        atoms (list[str]): molecular formula search input
        allow_other_elements (bool): allow other elements
        properties (list[str], optional): list of properties. Defaults to None.
        max_results (int, optional): max results. Defaults to 2000000.

    Returns:
        str: _description_
    """
    url = MolecularFormulaSearch.PUBCHEM_SEARCH_URL
    if _async:
        url += "formula/"
    else:
        url += "fastformula/"

    url += "".join(atoms)

    if properties:
        url += "/property/" + ",".join(properties)
    else:
        url += "/cids"

    url += f"/JSON?AllowOtherElements={str(allow_other_elements).lower()}&MaxRecords={max_results}"
    return url


def _get_rest_polling_url(
    listkey: str,
    properties: list[str] | None,
    results_start: int | None = None,
    max_results: int | None = None,
) -> str:
    """
    Get molecular formula search polling url, used for polling and retrieving
    results after an async search query has been submitted.

    Args:
        listkey (str): listkey id
        properties (list[str] | None): list of properties to fetch
        results_start (int | None, optional): pagination offset. Defaults to None.
        max_results (int | None, optional): pagination limit. Defaults to None.

    Returns:
        str: the polling url
    """
    url = MolecularFormulaSearch.PUBCHEM_SEARCH_URL + "listkey/" + listkey

    if properties:
        url += "/property/" + ",".join(properties)
    else:
        url += "/cids"

    url += f"/JSON"

    params = {}
    if max_results:
        params["listkey_count"] = max_results
    if results_start:
        params["listkey_start"] = results_start
    if params:
        url += "?" + urllib.parse.urlencode(params)

    return url


def _poll_async_query_results(listkey: str, poll_interval: int = 10):
    """
    Poll REST API after an async search query has been submitted.
    This function will wait until the async query has completed,
    returning the result of the first finished response.

    Args:
        listkey (str): the listkey id
        poll_interval (int, optional): the polling interval. Defaults to 10.

    Returns:
        _type_: _description_
    """
    waiting = True
    url = _get_rest_polling_url(listkey, None, max_results=2)
    while waiting:
        time.sleep(poll_interval)
        LOGGER.info(f"Checking status for query {listkey}.")
        result = _send_rest_query(url)
        waiting = "Waiting" in result
        if waiting:
            LOGGER.info("Query is still running.")
        else:
            LOGGER.info("Query is done.")

    return result


def _retrieve_async_query_results(
    listkey: str, properties: list[str] | None, max_results: int, max_query_results: int
):
    LOGGER.info("Retrieving async search results.")
    values = []
    for i in tqdm(range(0, max_results, max_query_results)):
        url = _get_rest_polling_url(
            listkey, properties, results_start=i, max_results=max_query_results
        )
        try:
            results = _send_rest_query(url)
        except HTTPError as exc:
            LOGGER.error(f"error while retrieving async query results: {exc}")
            break
        except JSONDecodeError as exc:
            LOGGER.error(
                f"error while reading async query results: {exc}. "
                "This is probably due to fetching too many results at a time, "
                "try setting async_max_query_results param lower. "
                "Current results will be partial"
            )
            break

        chunk = None
        if "IdentifierList" in results:
            chunk = results["IdentifierList"]["CID"]
        elif "PropertyTable" in results and "Properties" in results["PropertyTable"]:
            chunk = results["PropertyTable"]["Properties"]
        else:
            break

        values.extend(chunk)
        if len(chunk) < max_query_results:
            LOGGER.info(f"Retrieved all results.")
            break

    df = None
    if values:
        if properties:
            df = pd.DataFrame(values)
        else:
            df = pd.DataFrame(values, columns=("CID",))
    return df
