# PubChem API Crawler

This package provides a python client for crawling chemical compounds and their properties on [PubChem](https://pubchem.ncbi.nlm.nih.gov/).

## Installation

You can install the PubChem API Crawler directly with pip :

```console
pip install pubchem-api-crawler
```

Or you can clone the project from github and install it locally using [poetry](https://python-poetry.org/) with

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
from pubchem_api_crawler import MolecularFormulaSearch
df = MolecularFormulaSearch().search(["C1-", "H1-", "B1-", "Al1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"])
```

|    |       CID | MolecularFormula   | CanonicalSMILES                                                       |
|---:|----------:|:-------------------|:----------------------------------------------------------------------|
|  0 | 168084494 | CH5AlB2            | `[BH].[BH].C[Al]`                                                       |
|  1 | 163556649 | C16H14AlB          | `[B]CCC1=C2CCC=CC2=C(C3=CC=CC=C31)[Al]`                                 |
|  2 | 161576177 | C27H30AlB          | `[H+].[B-](C1=CC=CC=C1)(C2=CC=CC=C2)(C3=CC=CC=C3)C4=CC=CC=C4.C[Al](C)C` |
|  3 | 160352291 | C6H15AlB           | `[B].CC[Al](CC)CC`                                                      |
|  4 | 159123289 | C10H28AlB2         | `[B](C)C.[B](C)C.CCCC.C[Al]C`                                           |
|  5 | 158802573 | C11H29AlB          | `B(C)(C)C.CCCC.CC[Al]CC`                                                |
|  6 | 158250967 | C3H9AlB            | `[B].C[Al](C)C`                                                         |
|  7 | 158044531 | C2H6AlB            | `[B].C[Al]C`                                                            |
|  8 | 157093180 | C3H9AlB            | `B(C)(C)C.[Al]`                                                         |
|  9 | 156888304 | C12H14AlB          | `[B]C1=CC=CC=C1C2CCCCC2[Al]`                                            |
| 10 | 129859217 | C2H6AlB            | `[B].C[Al]C`                                                            |
| 11 | 129657578 | C2H6AlB            | `[B-].C[Al+]C`                                                          |
| 12 | 129657197 | CH3AlB2            | `[B-].[B-].C[Al+2]`                                                     |
| 13 |  59992955 | C7H9AlB            | `[BH2].C1=CC=C(C=C1)C[Al]`                                              |
| 14 |  22996618 | C12H30AlB          | `B(CC)(CC)CC.CC[Al](CC)CC`                                              |
| 15 |  19734271 | C8H18AlB           | `[B-].CC(C)C[Al+]CC(C)C`                                                |
| 16 | 155575130 | C8H8AlB            | `[B]C1=CC(=C(C=C1C)[Al])C`                                              |


#### Molecular Formula Search Input

The valid inputs for Molecular Formula Search are described [here](https://pubchem.ncbi.nlm.nih.gov/search/help_search.html#Mf).

```
The general MF query syntax consists of a series of valid atomic symbols
(please consult your periodical chart), each optionally followed by either
a number or a range.
The generic range syntax is "[atomic symbol][low count]-[high count]",
repeated for every specified element. Elements may be written in
arbitrary order.

Examples:
1. C7-8:	represents compounds with seven or eight carbons.
2. C-7:	represents compounds with up to seven carbons.
3. C7-:	represents compounds with seven or more carbons
4. C or C1:	represents compounds with exactly one carbon
5. C-:	represents any number of carbons, including none.
```

The search input must be provided as a list of `[atomic symbol][low count]-[high count]` strings to the search method.

**Note: specifying an open ended high count (i.e. C2-) does not seem to work correctly on PubChem. It is recommended to always specify a high count (i.e. C2-500).**

#### Molecular Formula Search Options

By default, the molecular formula search will return the cids of the matching compounds. Optionally, a list of properties can also be requested. The list of valid compound properties which can be requested is available [here](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables).

Aditionnaly, the `allow_other_elements` option lets you choose to allow other elements to be present in addition to those specified.

#### Request timeouts on the REST API

**REST requests made to PubChem time out after 30s**. Therefore, searches that are too broad will timeout on the server and raise an error. To overcome this limitation, it is possible to use PubChem's Async REST API. If your search request times out, you should retry it via the Async REST API with the `_async=True` parameter :

```python
df = MolecularFormulaSearch().search(["C1-", "H1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"], _async=True)
```

## Experimental Properties Annotations

When using PubChem's REST API, you can only retrieve computed compound properties (list is available [here](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables)).

If you want to retrieve experimental properties annotations, you can use the `Annotations` class of PubChem API Crawler. The list of annotation headings (and their types) for which PubChem has any data is available [here](https://pubchem.ncbi.nlm.nih.gov/rest/pug/annotations/headings/JSON).

PubChem API Crawler offers two ways to get annotations. You can get annotations for specific compounds individually by giving their cids. But there are no batch methods to fetch annotations on PubChem, so this requires sending a REST request per compound, which can be quite slow if you want to get properties for a lot of compounds. The alternative is to get all the data that PubChem has for a given annotation heading.

#### Getting annotations for a specific compound

The `get_compound_annotations` method will get a specific annotation heading for the given cids (if heading is unspecified, it will get the `Experimental Properties` section).

```python
from pubchem_api_crawler import Annotations
Annotations().get_compound_annotations(356, heading='Heat of Combustion')
```

|    | Heat of Combustion <br>          Value | Heat of Combustion <br>           Reference |   <br> CID |
|---:|:-----------------------------------------------|:-------------------------------------------------------------------------------------------------------------------|--------------:|
|  0 | 1,302.7 kg cal/g mol wt at 760 mm Hg and 20 °C | Weast, R.C. (ed.) Handbook of Chemistry and Physics. 69th ed. Boca Raton, FL: CRC Press Inc., 1988-1989., p. D-278 |           356 |

#### Getting all annotations for a specific heading

The `get_annotations` method will get all available data on PubChem for a given heading.

```python
from pubchem_api_crawler import Annotations
Annotations().get_annotations("Autoignition Temperature")
```

|    | SourceName                            |   SourceID | URL                                             | Value           | Reference                                                                                                                     |   CID |
|---:|:--------------------------------------|-----------:|:------------------------------------------------|:----------------|:------------------------------------------------------------------------------------------------------------------------------|------:|
|  0 | Hazardous Substances Data Bank (HSDB) |         30 | https://... | 270 °C (518 °F) | Fire Protection Guide to Hazardous Materials. ...      |  4510 |
|  1 | Hazardous Substances Data Bank (HSDB) |         35 | https://... | 928 °F (498 °C) | National Fire Protection Association;  Fire Protection Guide ... |   241 |
|  2 | Hazardous Substances Data Bank (HSDB) |         37 | https://... | 871 °F (466 °C) | National Fire Protection Association;  Fire Protection Guide ... |  2537 |
|  3 | Hazardous Substances Data Bank (HSDB) |         39 | https://... | 772 °F (411 °C) | Fire Protection Guide to Hazardous Materials. ...      |  7835 |
|  4 | Hazardous Substances Data Bank (HSDB) |         40 | https://... | 867 °F (463 °C) | National Fire Protection Association;  Fire Protection Guide ...  |   176 |

## Rate limits

You should first check the [rate limits](https://pubchem.ncbi.nlm.nih.gov/docs/dynamic-request-throttling) that PubChem imposes on requests to its API. On top of those dynamic request throttling policies, you should [not send more than 5 requests per second to the PubChem REST API](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial).

By default, PubChem API Crawler sets a rate limit of 5 calls per 3 seconds on REST API calls. These settings can be modified either by setting environment variables `RATE_LIMIT_CALLS` (integer) and `RATE_LIMIT_PERIOD` (integer, in seconds) or by creating a `.env` file in your working directory where those variables are set.

If you enable logging for the PubChem API Crawler namespace with log level set to `DEBUG`, the library will report request throttling status in the logs after each request.

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
