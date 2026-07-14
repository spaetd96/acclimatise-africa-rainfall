# Polytope Usage Guide

This guide explains how to use Polytope to browse and download Climate DT data from DestinE, focusing on the ICON, IFS-FESOM, and IFS-NEMO climate models.

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
    address="polytope.lumi.apps.dte.destination-earth.eu",  # or MN5 for IFS-NEMO
    stream=False                      # True = stream, False = cache to local file
)
```

### 2. `polytope-client` (Low-Level)

Direct access to the Polytope REST API. Useful for advanced use cases.

```python
from polytope.api import Client

client = Client(
    address="polytope.lumi.apps.dte.destination-earth.eu",  # or MN5 for IFS-NEMO
    user_email="<email>",
    user_key="<api_key>"
)

client.revoke("all")  # Cancel any pending requests
files = client.retrieve("destination-earth", request_dict, output_path="./data")
```

## Server Addresses

| Model(s) | Server | Address |
|----------|--------|---------|
| ICON, IFS-FESOM | **LUMI** | `polytope.lumi.apps.dte.destination-earth.eu` |
| IFS-NEMO | **MN5** | `polytope.mn5.apps.dte.destination-earth.eu` |

## Request Structure: Data Keys

Every request is a Python dictionary containing keys that specify what data to retrieve. The exact keys depend on the model and simulation.

### Common Keys

| Key | Description | Example Values |
|-----|-------------|----------------|
| `activity` | Simulation activity | `baseline` (for hist/cont), `projections` (for SSP3-7.0) |
| `class` | Data class | `d1` |
| `dataset` | Dataset identifier | `climate-dt` |
| `date` | Date in `YYYYMMDD` format | `20000615` |
| `experiment` | Experiment/Scenario | `hist`, `cont`, `SSP3-7.0` |
| `expver` | Experiment version | `0001` |
| `generation` | Model generation | `2` |
| `levtype` | Level type | `sfc` (surface), `pl` (pressure levels), `hl` (height levels) |
| `model` | Climate model | `ICON`, `IFS-FESOM`, `IFS-NEMO` |
| `param` | Parameter/variable codes | `134/165/166` (SP/10U/10V at surface) |
| `realization` | Ensemble member | `1`, `2`, `3` |
| `resolution` | Grid resolution | `standard`, `high` |
| `stream` | Data stream | `clte` (hourly), `clmn` (monthly) |
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
    'activity': 'baseline',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '19900102',
    'experiment': 'cont',
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
    'activity': 'baseline',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20000615',
    'experiment': 'hist',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'ICON',
    'param': '134/165/166',   # SP, 10U, 10V
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000/1200',
    'type': 'fc'
}
```

### IFS-FESOM — Projections (SSP3-7.0)

```python
request = {
    'activity': 'projections',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20200615',
    'experiment': 'SSP3-7.0',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'IFS-FESOM',
    'param': '134/165/166',
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000/0600/1200/1800',
    'type': 'fc'
}
```

### IFS-FESOM — Control Simulation

```python
request = {
    'activity': 'baseline',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '19900615',
    'experiment': 'cont',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'IFS-FESOM',
    'param': '134/165/166',
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0000/0600/1200/1800',
    'type': 'fc'
}
```

### IFS-NEMO — Projections (SSP3-7.0)

```python
request = {
    'activity': 'projections',
    'class': 'd1',
    'dataset': 'climate-dt',
    'date': '20200102',
    'experiment': 'SSP3-7.0',
    'expver': '0001',
    'generation': '2',
    'levtype': 'sfc',
    'model': 'IFS-NEMO',
    'param': '134/165/166',
    'realization': '1',
    'resolution': 'standard',
    'stream': 'clte',
    'time': '0100',
    'type': 'fc'
}
```

Note: IFS-NEMO uses the **MN5** server — pass `address="polytope.mn5.apps.dte.destination-earth.eu"`.

## Common Parameter Codes (Surface)

| Code | Variable | Short Name | Stream |
|------|----------|------------|--------|
| `134` | Surface pressure | SP | clte (hourly) |
| `165` | 10m U wind component | 10U | clte (hourly) |
| `166` | 10m V wind component | 10V | clte (hourly) |
| `167` | 2m temperature | 2T | clmn (monthly) |
| `168` | 2m dewpoint temperature | 2D | clte (hourly) |
| `228228` | Total precipitation | TP | clmn (monthly) |
| `151` | Mean sea level pressure | MSL | clte (hourly) |

> **Note**: Precipitation (228228) and 2m temperature (167) are only available in the **monthly `clmn`** stream. The hourly `clte` stream contains instantaneous surface parameters like 134 (SP), 165 (10U), and 166 (10V). To browse and download monthly data, use the `PolytopeZarrStore` approach from the polytope-examples repository (see `03_lazy_browse_portfolio.ipynb`).

## Activity and Experiment Mapping

| Experiment | Activity | Date Range | Description |
|-----------|----------|------------|-------------|
| `cont` | `baseline` | ~1990–2014 | Control simulation (fixed 1950 forcing) |
| `hist` | `baseline` | ~1990–2014 | Historical simulation (observed forcing) |
| `SSP3-7.0` | `projections` | ~2015–2050+ | Future projections (SSP3-7.0 scenario) |

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
                                  address="polytope.lumi.apps.dte.destination-earth.eu")
ds = data.to_xarray()  # Convert to xarray Dataset
```

## Browsing Data (Climate DT Explorer)

The [polytope-examples](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt) repository provides explorer notebooks for lazy browsing. A local copy of the monthly catalogue notebook is included in `get-data/`:

| Notebook | Location | Description |
|----------|----------|-------------|
| `browse_destine_data.ipynb` | `get-data/` | Interactive browse & download for ICON, IFS-FESOM, IFS-NEMO |
| `03_lazy_browse_portfolio.ipynb` | `get-data/` | Monthly catalogue (from polytope-examples) |

Additional notebooks available online:
- **[Hourly catalogue](https://github.com/destination-earth-digital-twins/polytope-examples/blob/main/climate-dt/explorer/04_lazy_browse_portfolio_hourly.ipynb)**
- **[Variable lookup](https://github.com/destination-earth-digital-twins/polytope-examples/blob/main/climate-dt/explorer/05_variable_lookup.ipynb)**

## Quota Limits

| Limit | Value |
|-------|-------|
| API rate | Up to 50 requests/second |
| Concurrent downloads | Max 2 active |

## Best Practices

1. **Start small**: Request a single time step with one parameter to validate your setup.
2. **Use correct servers**: ICON/IFS-FESOM → LUMI, IFS-NEMO → MN5.
3. **Use correct activity**: `baseline` for hist/cont, `projections` for SSP3-7.0.
4. **Use abbreviated experiment names**: `hist`, `cont`, `SSP3-7.0`.
5. **Check stream availability**: Precipitation and temperature are only in the monthly `clmn` stream.
6. **Use time ranges sparingly**: Requesting many time steps or parameters in a single call increases download time.
7. **Respect quota limits**: Submit no more than 2 concurrent download requests.
8. **Use the Explorer notebooks**: They help understand available data and generate valid request dictionaries.
9. **Cache data locally**: Set `stream=False` to save retrieved data as local files for reuse.
10. **Handle `len()` safely**: Some earthkit-data objects (e.g., `GribData`) don't support `len()`. Use the `safe_len()` helper function provided in the notebooks and download script.

## Related Resources

- [Polytope Documentation](https://polytope.readthedocs.io/en/latest/)
- [earthkit-data Polytope Reference](https://earthkit-data.readthedocs.io/en/stable/guide/sources.html#polytope)
- [polytope-examples GitHub](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt)
- [DestinE Platform](https://platform.destine.eu/)