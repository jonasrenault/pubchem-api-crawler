import logging
import time
import urllib.parse

import pandas as pd
import requests
from lxml import etree
from lxml.etree import _ElementTree
from requests import HTTPError
from tqdm import tqdm

from pubchem_api_crawler.constants import PUG_XML_MOL_SEARCH_QUERY, PUG_XML_POLL_QUERY
from pubchem_api_crawler.utils import is_molecular_formula_input_valid

LOGGER = logging.getLogger(__name__)


class MolecularFormulaSearch:
    PUBCHEM_SEARCH_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
    PUBCHEM_PUG_SEARCH_URL = "https://pubchem.ncbi.nlm.nih.gov/pug/pug.cgi"
    PUBCHEM_ENTREZ_EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?retmode=text&rettype=uilist&WebEnvRq=1&db=pccompound&"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Accept": "application/json",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }

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
        url = (
            MolecularFormulaSearch.PUBCHEM_SEARCH_URL + "fastformula/" + "".join(atoms)
        )
        if properties:
            url += "/property/" + ",".join(properties)
        else:
            url += "/cids"

        url += f"/JSON?AllowOtherElements={str(allow_other_elements).lower()}&MaxRecords={max_results}"
        return url

    def _rest_api_search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] = None,
        max_results: int = 2000000,
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
        url = self._get_request_url(
            atoms, allow_other_elements, properties, max_results
        )

        LOGGER.info(f"Exceuting Molecular Formula Search request: {url}")
        r = requests.get(url, headers=MolecularFormulaSearch.HEADERS)
        r.raise_for_status()
        try:
            LOGGER.info(r.headers["X-Throttling-Control"])
        except KeyError:
            pass

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

    def search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] = None,
        max_results: int = 2000000,
        pug_xml: bool = False,
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
            pug_xml (bool, optional): use PUG XML API. Default to False.

        Returns:
            pd.DataFrame | None: a pandas DataFrame with search results; None if no results
        """
        assert is_molecular_formula_input_valid(
            atoms
        ), "Invalid list of atoms given. See https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf for valid molecular formula search inputs."

        if pug_xml:
            return self._pug_xml_search(
                atoms, allow_other_elements, properties, max_results
            )

        try:
            return self._rest_api_search(
                atoms, allow_other_elements, properties, max_results
            )
        except HTTPError as exc:
            if "PUGREST.Timeout" in exc.response.text:
                LOGGER.error(
                    "Timeout error for REST API Molecular Search Query. You should try using the PUG XML API with pug_xml=True."
                )
            raise exc

    def _get_properties_for_cids(
        self, df: pd.DataFrame, properties: list[str], max_cids: int = 100000
    ):
        """
        Get the requested compound properties for the given cids.
        Updates the dataframe inplace.

        Args:
            df (pd.DataFrame): a dataframe with cids as index
            properties (list[str]): the list of compound properties
            max_cids (int, optional): max cids to request at a time. Defaults to 50000.
        """
        total_cids = df.shape[0]
        for property in properties:
            if property not in df.columns:
                df[property] = pd.NA
        LOGGER.info("Retrieving properties for search results.")
        for i in tqdm(range(0, total_cids, max_cids)):
            cids = df.iloc[i : min(i + max_cids, total_cids)].index.values
            url = (
                MolecularFormulaSearch.PUBCHEM_SEARCH_URL
                + "cid/property/"
                + ",".join(properties)
                + "/JSON"
            )
            r = requests.post(
                url,
                headers=MolecularFormulaSearch.HEADERS,
                data="cid=" + ",".join(map(str, cids)),
            )
            r.raise_for_status()
            results = r.json()
            if "PropertyTable" in results and "Properties" in results["PropertyTable"]:
                props = results["PropertyTable"]["Properties"]
                df.update(pd.DataFrame(props).set_index("CID"))

        LOGGER.info("Done retrieving properties.")

    def _pug_xml_search(
        self,
        atoms: list[str],
        allow_other_elements: bool = False,
        properties: list[str] = None,
        max_results: int = 2000000,
    ) -> pd.DataFrame:
        """
        Perform molecular formula search using PUG XML API.
        https://pubchem.ncbi.nlm.nih.gov/docs/power-user-gateway

        Args:
            atoms (list[str]): molecular formula search input
            allow_other_elements (bool): allow other elements than those specified in list of atoms
            properties (list[str]): list of compound properties to retrieve
            max_results (int, optional): max results. Defaults to 2000000.

        Returns:
            pd.DataFrame: a pandas DataFrame with search results
        """
        # Build the Molecular Formula Search XML query for PUG
        query_data = "".join(atoms)
        pug_query = PUG_XML_MOL_SEARCH_QUERY.format(
            query_data=query_data,
            max_results=max_results,
            allow_other_elements=str(allow_other_elements).lower(),
        )
        res = _pug_post_query(pug_query)
        status = _get_pug_query_status(res)

        # PUG should respond with a "queued" response, containing a query id
        # in which case we start polling for query status
        if status == "queued":
            query_id = _get_pug_query_id(res)
            res, status = _poll_query_results(query_id)

        # Once polling is done, check query status
        if status == "hit-limit":
            LOGGER.warning(
                f"The search has hit the result limit you set ({max_results}) and was stopped. "
                "Only partial results are included. "
                "You can try searching again with a higher max_results param."
            )
        elif status != "success":
            LOGGER.error(f"Error during the search:\n{etree.tounicode(res)}")
            return None

        # Response should contain an entrez query key and webenv, which we can
        # use to retrieve a list of cids for the results
        LOGGER.info("Retrieving cids for search query results.")
        query_key, webenv = _get_pug_entrez_key(res)
        eutils_url = (
            MolecularFormulaSearch.PUBCHEM_ENTREZ_EUTILS_URL
            + urllib.parse.urlencode({"query_key": query_key, "WebEnv": webenv})
        )
        r = requests.get(eutils_url, headers=MolecularFormulaSearch.HEADERS)

        cids = map(int, r.text.strip().split("\n"))
        df = pd.DataFrame(cids, columns=("CID",)).set_index("CID")
        LOGGER.info(f"Sucessfully retrieved {df.shape[0]} cids.")

        if properties:
            self._get_properties_for_cids(df, properties)

        return df


def _poll_query_results(
    query_id: str, poll_interval: int = 10
) -> tuple[_ElementTree, str]:
    """
    Poll the PUG API until the query is finished.

    Args:
        query_id (str): the query id
        poll_interval (int, optional): the polling interval. Defaults to 10.

    Returns:
        tuple[_ElementTree, str]: the parsed xml response and status
    """
    status = "queued"
    pug_query = PUG_XML_POLL_QUERY.format(query_id=query_id)
    while status == "queued" or status == "running":
        time.sleep(poll_interval)
        LOGGER.info(f"Checking status for query {query_id}.")
        res = _pug_post_query(pug_query)
        status = _get_pug_query_status(res)
        LOGGER.info(f"Query {query_id} is {status}.")

    return res, status


def _pug_post_query(pug_query: str) -> _ElementTree:
    """
    Send a query to the PUG API. See
    https://pubchem.ncbi.nlm.nih.gov/docs/power-user-gateway#section=Interacting-with-PUG

    Args:
        pug_query (str): the xml string query

    Returns:
        _ElementTree: the parsed xml response
    """
    LOGGER.debug(f"Sending PUG query {pug_query}")

    r = requests.post(
        MolecularFormulaSearch.PUBCHEM_PUG_SEARCH_URL,
        headers=MolecularFormulaSearch.HEADERS,
        data=pug_query,
    )
    r.raise_for_status()
    res = etree.fromstring(r.text)

    LOGGER.debug(f"Received {etree.tounicode(res)}")
    return res


def _get_pug_query_status(response: _ElementTree) -> str | None:
    """
    Extract query status from PUG XML response

    Args:
        response (_ElementTree): the XML response

    Returns:
        str | None: the status
    """
    status = response.find(".//PCT-Status")
    if status is None:
        return None

    return status.attrib["value"]


def _get_pug_query_id(response: _ElementTree) -> str | None:
    """
    Extract query id from PUG XML response

    Args:
        response (_ElementTree): the XML response

    Returns:
        str | None: the query id
    """
    id = response.find(".//PCT-Waiting_reqid")
    if id is None:
        return None

    return id.text


def _get_pug_entrez_key(response: _ElementTree) -> tuple[str, str] | None:
    """
    Extract entrez query key and webenv from PUG XML response

    Args:
        response (_ElementTree): the XML response

    Returns:
        tuple[str, str] | None: the query key and webenv
    """
    key = response.find(".//PCT-Entrez_query-key")
    webenv = response.find(".//PCT-Entrez_webenv")
    if key is None or webenv is None:
        return None

    return key.text, webenv.text
