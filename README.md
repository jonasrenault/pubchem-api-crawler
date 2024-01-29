# PubChem API Crawler

This package provides a python client for crawling chemical compounds and their properties on [PubChem](https://pubchem.ncbi.nlm.nih.gov/).

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

#### Molecular Formula Search Options

By default, the molecular formula search will return the cids of the matching compounds. Optionally, a list of properties can also be requested. The list of valid compound properties which can be requested is available [here](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Compound-Property-Tables).

Aditionnaly, the `allow_other_elements` option lets you choose to allow other elements to be present in addition to those specified.


## Rate limits

You should first check the [rate limits](https://pubchem.ncbi.nlm.nih.gov/docs/dynamic-request-throttling) that PubChem imposes on requests to its API.

If you enable logging for the `pubchem_api_crawler` namespace, the Molecular Formula Search class will report request throttling status in the logs after each request.

## Request timeouts and PUG API

Requests made via REST time out after 30s. The PUG XML interface does not have this limitation. If your search request times out, you should retry it via the PUG XML API with the `pug_xml=True` parameter :

```python
df = MolecularFormulaSearch().search(["C1-", "H1-"], allow_other_elements=False, properties=["MolecularFormula", "CanonicalSMILES"], pug_xml=True)
```
