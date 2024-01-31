import logging
import urllib.parse
from itertools import product
from typing import Any

import pandas as pd
from tqdm import tqdm

from pubchem_api_crawler.molecular_search import MolecularFormulaSearch
from pubchem_api_crawler.rest_api import _send_rest_query

LOGGER = logging.getLogger(__name__)


class Annotations:
    PUGVIEW_ANNOTATIONS_URL = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/annotations/heading/JSON"
    )

    def get_annotations(
        self, heading: str, properties: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Get all annotations available on PubChem for given annotation heading,
        and fetch additionnal compound properties for the results

        Args:
            heading (str): the annotation heading
            properties (list[str] | None, optional): the compound properties. Defaults to None.

        Returns:
            pd.DataFrame: result dataframe
        """
        annotations = self._get_annotation(heading)
        df = _annotations_to_df(annotations)
        if properties:
            df = _get_properties_for_cids(df, properties, max_cids=50)
        return df

    def _get_annotation(self, heading: str) -> list[dict[str, Any]]:
        """
        Get all anotations available on PubChem for given annotation heading.

        Args:
            heading (str): the annotation heading

        Returns:
            list[dict[str, Any]]: the list of available records on PubChem
        """
        params = {"heading": heading, "heading_type": "Compound"}
        url = Annotations.PUGVIEW_ANNOTATIONS_URL + "?" + urllib.parse.urlencode(params)
        results = []

        LOGGER.info(f"Getting {heading} annotation.")
        res = _send_rest_query(url)
        annotations = res["Annotations"]["Annotation"]
        total_pages = res["Annotations"]["TotalPages"]
        page = res["Annotations"]["Page"]
        results.extend(annotations)

        if page < total_pages:
            LOGGER.info(f"Fetching {total_pages - page} additional result pages.")
            for p in tqdm(range(page + 1, total_pages + 1)):
                params["page"] = p
                url = (
                    Annotations.PUGVIEW_ANNOTATIONS_URL
                    + "?"
                    + urllib.parse.urlencode(params)
                )
                res = _send_rest_query(url)
                annotations = res["Annotations"]["Annotation"]
                results.extend(annotations)

        return results


def _annotations_to_df(annotations: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Transform list of annotation records to a pandas DataFrame

    Args:
        annotations (list[dict[str, Any]]): the annotations

    Returns:
        pd.DataFrame: the dataframe
    """
    records = []
    for annotation in annotations:
        if "LinkedRecords" not in annotation:
            continue

        source = {
            "SourceName": annotation.get("SourceName", None),
            "SourceID": annotation.get("SourceID", None),
            "URL": annotation.get("URL", None),
        }
        values = [_parse_annotations_data(data) for data in annotation["Data"]]
        cids = annotation["LinkedRecords"].get("CID", [])
        for value, cid in product(values, cids):
            records.append({**source, **value, "CID": cid})

    df = pd.DataFrame(records)
    return df


def _parse_annotations_data(data: dict[str, Any]) -> dict[str, str]:
    """
    Parse an annotation data into Value and Reference

    Args:
        data (dict[str, Any]): the annotation data

    Returns:
        dict[str, str]: a dict with Reference and Value keys
    """
    value = {}
    if "StringWithMarkup" in data["Value"]:
        value["Value"] = "; ".join(
            [s["String"] for s in data["Value"]["StringWithMarkup"]]
        )
    elif "Number" in data["Value"]:
        value["Value"] = "; ".join(map(str, data["Value"]["Number"]))
        if "Unit" in data["Value"]:
            value["Value"] += " " + data["Value"]["Unit"]

    if "Reference" in data:
        value["Reference"] = "\n".join(data["Reference"])

    return value


def _get_properties_for_cids(
    df: pd.DataFrame, properties: list[str], max_cids: int = 50000
) -> pd.DataFrame:
    """
    Get compound properties for cids in given dataframe.

    Args:
        df (pd.DataFrame): dataframe with a CID column
        properties (list[str]): list of compound properties
        max_cids (int, optional): max cids to fetch at a time. Defaults to 50000.

    Returns:
        pd.DataFrame: the dataframe merged with properties
    """
    cids = list(set(df["CID"].values))
    total_cids = len(cids)

    LOGGER.info("Retrieving properties for search results.")
    prop_values = []
    for i in tqdm(range(0, total_cids, max_cids)):
        batch_ids = cids[i : min(i + max_cids, total_cids)]
        url = (
            MolecularFormulaSearch.PUBCHEM_SEARCH_URL
            + "cid/property/"
            + ",".join(properties)
            + "/JSON"
        )
        results = _send_rest_query(url, "cid=" + ",".join(map(str, batch_ids)))
        if "PropertyTable" in results and "Properties" in results["PropertyTable"]:
            prop_values.extend(results["PropertyTable"]["Properties"])

    LOGGER.info("Done retrieving properties.")
    return df.merge(pd.DataFrame(prop_values), how="right", on="CID")
