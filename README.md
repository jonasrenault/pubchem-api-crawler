# PubChem API Crawler

This package provides a python client for crawling chemical compounds and their properties on [PubChem](https://pubchem.ncbi.nlm.nih.gov/).

## Installation

You can install the project locally using [poetry](https://python-poetry.org/) with

```console
poetry install
```

## Notebooks

Example notebooks showing how to use the library are available in the [notebooks](./notebooks/) directory. To run the notebooks, run

```console
poetry run jupyter lab
```

and select the notebook in the browser window.

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

#### Request timeouts on the REST API

**Requests made via REST time out after 30s**. Searches that are too broad will timeout on the server and raise an error. To overcome this limitation, it is possible to use PubChem's Async REST API. If your search request times out, you should retry it via the Async REST API with the `_async=True` parameter :

```python
df = MolecularFormulaSearch().search(["C1-", "H1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"], _async=True)
```

## Experimental Properties Annotations

When using PubChem's REST API, you can only retrieve computed compound properties (list is available [here](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables)).

If you want to retrieve experimental properties annotations, you can use the `Annotations` class of `pubchem_api_crawler`. The list of annotation headings (and their types) for which PubChem has any data is available [here](https://pubchem.ncbi.nlm.nih.gov/rest/pug/annotations/headings/JSON).

`pubchem_api_crawler` offers two ways to get annotations. You can get annotations for specific compounds individually by giving their cids. But there are no batch methods to fetch annotations on PubChem, so this requires sending a REST request per compound, which can be quite slow if you want to get properties for a lot of compounds. The alternative is to get all the data that PubChem has for a given annotation heading.

#### Getting annotations for a specific compound

The `get_compound_annotations` method will get a specific annotation heading for the given cids.

```python
from pubchem_api_crawler.annotations import Annotations
Annotations().get_compound_annotations(356, heading='Heat of Combustion')
```

|    | ('Heat of Combustion', 'Value')                | ('Heat of Combustion', 'Reference')                                                                                |   ('CID', '') |
|---:|:-----------------------------------------------|:-------------------------------------------------------------------------------------------------------------------|--------------:|
|  0 | 1,302.7 kg cal/g mol wt at 760 mm Hg and 20 °C | Weast, R.C. (ed.) Handbook of Chemistry and Physics. 69th ed. Boca Raton, FL: CRC Press Inc., 1988-1989., p. D-278 |           356 |

#### Getting all annotations for a specific heading

The `get_annotations` method will get all available data on PubChem for a given heading.

```python
from pubchem_api_crawler.annotations import Annotations
Annotations().get_annotations("Autoignition Temperature")
```

|    | SourceName                            |   SourceID | URL                                             | Value           | Reference                                                                                                                     |   CID |
|---:|:--------------------------------------|-----------:|:------------------------------------------------|:----------------|:------------------------------------------------------------------------------------------------------------------------------|------:|
|  0 | Hazardous Substances Data Bank (HSDB) |         30 | https://pubchem.ncbi.nlm.nih.gov/source/hsdb/30 | 270 °C (518 °F) | Fire Protection Guide to Hazardous Materials. ...      |  4510 |
|  1 | Hazardous Substances Data Bank (HSDB) |         35 | https://pubchem.ncbi.nlm.nih.gov/source/hsdb/35 | 928 °F (498 °C) | National Fire Protection Association;  Fire Protection Guide ... |   241 |
|  2 | Hazardous Substances Data Bank (HSDB) |         37 | https://pubchem.ncbi.nlm.nih.gov/source/hsdb/37 | 871 °F (466 °C) | National Fire Protection Association;  Fire Protection Guide ... |  2537 |
|  3 | Hazardous Substances Data Bank (HSDB) |         39 | https://pubchem.ncbi.nlm.nih.gov/source/hsdb/39 | 772 °F (411 °C) | Fire Protection Guide to Hazardous Materials. ...      |  7835 |
|  4 | Hazardous Substances Data Bank (HSDB) |         40 | https://pubchem.ncbi.nlm.nih.gov/source/hsdb/40 | 867 °F (463 °C) | National Fire Protection Association;  Fire Protection Guide ...  |   176 |

## Rate limits

You should first check the [rate limits](https://pubchem.ncbi.nlm.nih.gov/docs/dynamic-request-throttling) that PubChem imposes on requests to its API. On top of those dynamic request throttling policies, you should [not send more than 5 requests per second to the PubChem REST API](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial).

By default, `pubchem_api_crawler` sets a rate limit of 5 calls per 3 seconds on REST API calls. These settings can be modified either by setting environment variables `RATE_LIMIT_CALLS` (integer) and `RATE_LIMIT_PERIOD` (integer, in seconds) or by creating a `.env` file in your working directory where those variables are set.

If you enable logging for the `pubchem_api_crawler` namespace with log level set to `DEBUG`, the library will report request throttling status in the logs after each request.

## Logs

Enable logging before calling the library's functions to see debugging and info messages.

```python
import logging

logger = logging.getLogger('pubchem_api_crawler')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)
```
