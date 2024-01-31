# PubChem API Crawler

This package provides a python client for crawling chemical compounds and their properties on [PubChem](https://pubchem.ncbi.nlm.nih.gov/).

## Installation

You can install the project locally using [poetry](https://python-poetry.org/) with

```console
poetry install
```

## Molecular Formula Search

The main entry point for PubChem API Crawler is the [Molecular Formula Search function of Pubchem](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Molecular-Formula) which lets you retrieve compounds given a molecular formula search input.

For example, if you wanted to find all compounds on PubChem containing carbon, hydrogen, aluminium and bore, you would use :

```python
df = MolecularFormulaSearch().search(["C1-", "H1-", "B1-", "Al1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"])
```

#### Molecular Formula Search Input

The valid inputs for Molecular Formula Search are described [here](https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf).

```
The general MF query syntax consists of a series of valid atomic symbols (please consult your periodical chart), each optionally followed by either a number or a range. The generic range syntax is "[atomic symbol][low count]-[high count]", repeated for every specified element. Elements may be written in arbitrary order.

Examples:
1. C7-8:	represents compounds with seven or eight carbons.
2. C-7:	represents compounds with up to seven carbons.
3. C7-:	represents compounds with seven or more carbons
4. C or C1:	represents compounds with exactly one carbon
5. C-:	represents any number of carbons, including none.
```

The search input must be provided as a list of `[atomic symbol][low count]-[high count]` strings to the search method.

**Note: specifying an open ended high count (i.e. C2-) does not seem to work correctly on PubChem. It is recommended to always specify a high count (i.e. C2-500)**

#### Molecular Formula Search Options

By default, the molecular formula search will return the cids of the matching compounds. Optionally, a list of properties can also be requested. The list of valid compound properties which can be requested is available [here](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables).

Aditionnaly, the `allow_other_elements` option lets you choose to allow other elements to be present in addition to those specified.

#### Rate limits

You should first check the [rate limits](https://pubchem.ncbi.nlm.nih.gov/docs/dynamic-request-throttling) that PubChem imposes on requests to its API. On top of those dynamic request throttling policies, you should not send more than 5 requests per second to the PubChem REST API.

If you enable logging for the `pubchem_api_crawler` namespace, the Molecular Formula Search class will report request throttling status in the logs after each request.

#### Request timeouts on the REST API

**Requests made via REST time out after 30s**. Searches that are too broad will timeout on the server and raise an error. To overcome this limitation, it is possible to use PubChem's Async REST API. If your search request times out, you should retry it via the Async REST API with the `_async=True` parameter :

```python
df = MolecularFormulaSearch().search(["C1-", "H1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"], _async=True)
```

## Logs

Enable logging to get information on the search status.

```python
import logging

logger = logging.getLogger('pubchem_api_crawler')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)
```
