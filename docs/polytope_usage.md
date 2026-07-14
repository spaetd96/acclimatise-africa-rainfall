# Polytope Usage Guide

This guide explains how to use Polytope to browse and download Climate DT data from DestinE, focusing on the ICON and IFS-FESOM climate models.

## Access Methods

There are two ways to use Polytope:

### 1. `earthkit-data` (Recommended)

The high-level approach using ECMWF's `earthkit-data` library. Simplifies authentication and provides a clean `from_source()` API.

```python
import earthkit.data

data = earthkit.data.from_source(
    "polytope",                       # Source type
    "destination-earth",              # Collection name
    request_dict,                     # Request parameters (see below)
    address="polytope.mn5.apps.dte.destination-earth.eu",
    stream=False                      # True = stream, False = cache to local file
)
```

### 2. `polytope-client` (Low-Level)

Direct access to the Polytope REST API. Useful for advanced use cases.

```python
from polytope.api import Client

client = Client(
    address="polytope.mn5.apps.dte.destination-earth.eu",
    user_email="<email>",
    user_key="<api_key>"
)

client.revoke("all")  # Cancel any pending requests
files = client.retrieve("destination-earth", request_dict, output_path="./data")
```

## Request Structure: Data Keys

Every request is a Python dictionary containing keys that specify what data to retrieve. The exact keys depend on the model and simulation.

### Common Keys

| Key | Description | Example Values |
|-----|-------------|----------------|
| `activity` | Simulation activity | `projections`, `control` |
| `class` | Data class | `d1` |
| `dataset` | Dataset identifier | `climate-dt` |
| `date` | Date in `YYYYMMDD` format | `20200102` |
| `experiment` | Experiment/Scenario | `SSP3-7.0`, `control-1950`, `historical` |
| `expver` | Experiment version | `0001` |
| `generation` | Model generation | `2` |
| `levtype` | Level type | `sfc` (surface), `pl` (pressure levels), `hl` (height levels) |
| `model` | Climate model | `ICON`, `IFS-FESOM`, `IFS-NEMO` |
| `param` | Parameter/variable codes | `134/165/166` (SP/T/U at surface) |
| `realization` | Ensemble member | `1`, `2`, `3` |
| `resolution` | Grid resolution | `standard`, `high` |
| `stream` | Data stream | `clte` |
| `time` | Time in `HHMM` format | `0100`, `0000/0300/0600/.../2100` |
| `type` | Forecast type | `fc` |

### Additional Keys for Subsetting

| Key | Description | Example |
|-----|-------------|---------|
| `feature` | Named geographic feature | `{ "type": "Feature", "geometry": {...} }` |
| `grid` | Grid specification | `healpix` |
| `step` | Forecast step | `0`, `1-6` |

## Model-Specific Examples

### ICON — Control Simulation

```python
request = {
    'activity': 'control',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20200102',
    'experiment': 'control-1950',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'ICON',
    'param': '134',           # Surface pressure
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000/0300/0600/0900/1200/1500/1800/2100',
    'type': 'fc'
}
```

### ICON — Historical Simulation

```python
request = {
    'activity': 'projections',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20000115',
    'experiment': 'historical',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'ICON',
    'param': '165/166',       # 10u/10v wind
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '1200',
    'type': 'fc'
}
```

### IFS-FESOM — Projections (SSP3-7.0)

```python
request = {
    'activity': 'projections',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20500101',
    'experiment': 'SSP3-7.0',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'IFS-FESOM',
    'param': '134/165/166',
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000',
    'type': 'fc'
}
```

### IFS-FESOM — Control Simulation

```python
request = {
    'activity': 'control',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20000601',
    'experiment': 'control-1950',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'IFS-FESOM',
    'param': '134',
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '1200',
    'type': 'fc'
}
```

## Common Parameter Codes (Surface)

| Code | Variable | Short Name |
|------|----------|------------|
| `134` | Surface pressure | SP |
| `165` | 10m U wind component | 10U |
| `166` | 10m V wind component | 10V |
| `167` | 2m temperature | 2T |
| `168` | 2m dewpoint temperature | 2D |
| `228228` | Total precipitation | TP |
| `151` | Mean sea level pressure | MSL |

## Output Formats

| Format | Description |
|--------|-------------|
| GRIB | Native meteorological data format |
| CoverageJSON | JSON-based spatio-temporal coverage |
| netCDF | Common scientific data format |

Use `earthkit-data` to convert to xarray:

```python
import earthkit.data

data = earthkit.data.from_source("polytope", "destination-earth", request,
                                  address="polytope.mn5.apps.dte.destination-earth.eu")
ds = data.to_xarray()  # Convert to xarray Dataset
```

## Browsing Data (Climate DT Explorer)

The [polytope-examples](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt) repository provides explorer notebooks for lazy browsing:

- **[Monthly catalogue](https://github.com/destination-earth-digital-twins/polytope-examples/blob/main/climate-dt/explorer/03_lazy_browse_portfolio.ipynb)** — Browse the full monthly catalogue
- **[Hourly catalogue](https://github.com/destination-earth-digital-twins/polytope-examples/blob/main/climate-dt/explorer/04_lazy_browse_portfolio_hourly.ipynb)** — Browse the full hourly catalogue
- **[Variable lookup](https://github.com/destination-earth-digital-twins/polytope-examples/blob/main/climate-dt/explorer/05_variable_lookup.ipynb)** — Search for available variables

## Quota Limits

| Limit | Value |
|-------|-------|
| API rate | Up to 50 requests/second |
| Concurrent downloads | Max 2 active |

## Best Practices

1. **Start small**: Request a single time step with one parameter to validate your setup.
2. **Use time ranges sparingly**: Requesting many time steps or parameters in a single call increases download time.
3. **Respect quota limits**: Submit no more than 2 concurrent download requests.
4. **Use the Explorer notebooks**: They help understand available data and generate valid request dictionaries.
5. **Cache data locally**: Set `stream=False` to save retrieved data as local files for reuse.
6. **Prefetch time ranges**: For multi-day analyses, download broader temporal chunks to avoid repeated small requests.

## Related Resources

- [Polytope Documentation](https://polytope.readthedocs.io/en/latest/)
- [earthkit-data Polytope Reference](https://earthkit-data.readthedocs.io/en/stable/guide/sources.html#polytope)
- [polytope-examples GitHub](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt)
- [DestinE Platform](https://platform.destine.eu/)