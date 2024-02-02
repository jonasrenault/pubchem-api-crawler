import logging
import urllib.parse
from collections import defaultdict
from collections.abc import Iterable
from itertools import product
from typing import Any

import numpy as np
import pandas as pd
from requests import HTTPError
from tqdm import tqdm

from pubchem_api_crawler.molecular_search import MolecularFormulaSearch
from pubchem_api_crawler.rest_api import _send_rest_query
from pubchem_api_crawler.utils import are_compound_properties_valid

LOGGER = logging.getLogger(__name__)


class Annotations:
    PUGVIEW_ANNOTATIONS_URL = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/annotations/heading/JSON"
    )
    PUGVIEW_COMPOUND_ANNOTATIONS_URL = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/"
    )

    def get_compound_annotations(
        self,
        cids: pd.DataFrame | Iterable[int] | int,
        heading: str = "Experimental Properties",
    ) -> pd.DataFrame | None:
        """
        Get annotations for given list of cids. A specific annotation heading
        can be given.

        Args:
            cids (pd.DataFrame | Iterable[int] | int): list of cids or dataframe containing a cid column
            heading (str, optional): annotation heading to get. Defaults to "Experimental Properties".

        Raises:
            ValueError: if dataframe does not have a CID column

        Returns:
            pd.DataFrame | None: annotations for given cids
        """
        if isinstance(cids, pd.DataFrame):
            if "CID" not in cids.columns:
                raise ValueError("Input dataframe must have a CID column.")
            cids = set(cids["CID"].values)
        else:
            if not isinstance(cids, Iterable):
                cids = {cids}
            else:
                cids = set(cids)

        dfs = []
        params = {"heading": heading}
        LOGGER.info(f"Getting {heading} annotations for compounds.")
        for cid in tqdm(cids):
            try:
                url = f"{Annotations.PUGVIEW_COMPOUND_ANNOTATIONS_URL}{str(cid)}/JSON?{urllib.parse.urlencode(params)}"
                results = _send_rest_query(url)
            except HTTPError as exc:
                if "PUGVIEW.NotFound" in exc.response.text:
                    LOGGER.debug(
                        f"No data on PubChem for cid {cid} and heading {heading}."
                    )
                else:
                    LOGGER.warning(
                        f"An error occured while fetching data for cid {cid} and heading {heading}: {exc.response.text}"
                    )
                continue
            data = _extract_compound_annotations(results)
            df = pd.DataFrame.from_dict(data, orient="index").stack().to_frame()
            df = pd.DataFrame(df[0].values.tolist(), index=df.index)
            df.loc["CID", :] = cid
            dfs.append(df.transpose())

        if not dfs:
            LOGGER.error(f"Unable to get any {heading} annotations for provided ids.")
            return None
        return pd.concat(dfs).fillna(value=np.nan).reset_index(drop=True)

    def get_annotations(
        self, heading: str, properties: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Get all annotations available on PubChem for given annotation heading,
        and optionally fetch additionnal compound properties for the results.

        Args:
            heading (str): the annotation heading
            properties (list[str] | None, optional): the compound properties. Defaults to None.

        Returns:
            pd.DataFrame: result dataframe
        """
        if properties:
            assert are_compound_properties_valid(
                properties
            ), "Invalid list of properties given. See https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables for list of compound properties."

        annotations = self._get_annotations(heading)
        df = _annotations_to_df(annotations)
        if properties:
            df = _get_properties_for_cids(df, properties)
        return df

    def _get_annotations(self, heading: str) -> list[dict[str, Any]]:
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

        LOGGER.info(f"Getting {heading} annotations.")
        try:
            res = _send_rest_query(url)
        except HTTPError as exc:
            if "PUGVIEW.NotFound" in exc.response.text:
                LOGGER.error(
                    "PubChem was unable to find the requested heading. "
                    "Check available headings at https://pubchem.ncbi.nlm.nih.gov/rest/pug/annotations/headings/JSON."
                )
            raise exc

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

    if "Unit" in data["Value"] and "Value" in value:
        value["Value"] += " " + data["Value"]["Unit"]

    if "Reference" in data:
        value["Reference"] = "\n".join(data["Reference"])

    return value


def _get_properties_for_cids(
    df: pd.DataFrame, properties: list[str], max_cids: int = 20000
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


def _extract_compound_annotations(
    data: dict[str, Any]
) -> dict[str, dict[str, list[str]]]:
    """
    Parse annotations for a compound returned by PubChem PUG View API
    into a dict.

    Args:
        data (dict[str, Any]): the annotations

    Returns:
        dict[str, dict[str, list[str]]]: the parsed dict
    """
    top_section = data["Record"]["Section"][0]
    sections = _parse_section(top_section)
    data = defaultdict(lambda: defaultdict(list))
    for section in sections:
        if "Value" in section:
            data[section["heading"]]["Value"].append(section["Value"])
        if "Reference" in section:
            data[section["heading"]]["Reference"].append(section["Reference"])

    return data


def _parse_section(section: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse a section and its subsections

    Args:
        section (dict[str, Any]): the section

    Returns:
        list[dict[str, Any]]: the parsed data
    """
    if "Information" in section:
        return [
            {"heading": section["TOCHeading"], **_parse_annotations_data(info)}
            for info in section["Information"]
        ]
    if "Section" in section:
        subsections = []
        for subsection in section["Section"]:
            subsections.extend(_parse_section(subsection))
        return subsections
    return []
