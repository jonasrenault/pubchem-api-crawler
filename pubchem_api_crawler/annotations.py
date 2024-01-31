import urllib.parse
import logging
from typing import Any
import pandas as pd
from itertools import product

from pubchem_api_crawler.rest_api import _send_rest_query

LOGGER = logging.getLogger(__name__)


class Annotations:
    PUGVIEW_ANNOTATIONS_URL = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/annotations/heading/JSON"
    )

    # def _annotations_to_df(self, annotations: list[dict[str, Any]]):
    #     values = []
    #     for annotation in annotations:
    #         record = {
    #             "SourceName": annotation.get("SourceName", None),
    #             "SourceID": annotation.get("SourceID", None),
    #             "URL": annotation.get("URL", None),
    #         }
    #         for data in annotation["Data"]:
    #             for value, ref in zip(
    #                 data["Value"].get("StringWithMarkup", []), data.get("Reference", [])
    #             ):
    #                 record["Reference"] = ref
    #                 record["Value"] = value["String"]
    #                 break

    #             if "StringWithMarkup" not in data["Value"]:
    #                 print(annotation)

    #         for cid in annotation.get("LinkedRecords", {}).get("CID", []):
    #             record["CID"] = cid
    #             values.append(record)

    #     df = pd.DataFrame(values).set_index("CID")
    #     return df

    def _get_annotation(self, annotation: str) -> list[dict[str, Any]]:
        params = {"heading": annotation, "heading_type": "Compound"}
        url = Annotations.PUGVIEW_ANNOTATIONS_URL + "?" + urllib.parse.urlencode(params)
        results = []
        LOGGER.info(f"Getting annotation {annotation}")
        res = _send_rest_query(url)
        annotations = res["Annotations"]["Annotation"]
        total_pages = res["Annotations"]["TotalPages"]
        page = res["Annotations"]["Page"]
        results.extend(annotations)

        while page < total_pages:
            params["page"] = page + 1
            url = (
                Annotations.PUGVIEW_ANNOTATIONS_URL
                + "?"
                + urllib.parse.urlencode(params)
            )
            res = _send_rest_query(url)
            annotations = res["Annotations"]["Annotation"]
            page = res["Annotations"]["Page"]
            results.extend(annotations)

        return results

    def get_annotations(self, annotations: list[str]):
        for annotation in annotations:
            results = self._get_annotation(annotation)
            df = _annotations_to_df(results)
        return df


def _annotations_to_df(annotations: list[dict[str, Any]]):
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

    df = pd.DataFrame(records).set_index("CID")
    return df


def _parse_annotations_data(data):
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
