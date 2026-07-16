# Polytope Setup Guide

This guide covers setting up Polytope — the DestinE data extraction service — on your local machine or HPC environment to access Climate Digital Twin (Climate DT) data.

## Prerequisites

- A **DestinE Platform account with upgraded access**. [Apply here](https://platform.destine.eu/access-policy-upgrade/).
- **Python >= 3.10**
- **Conda** (Miniconda or Anaconda) for environment management.

## Step 1: Create a Dedicated Conda Environment

Create and activate a new environment named `destine` (recommended over using an existing environment to avoid dependency conflicts):

```bash
conda create -n destine python=3.11 jupyter jupyterlab -y
conda activate destine
```

## Step 2: Install Dependencies

### Quick Install (recommended)

```bash
pip install -r requirements.txt
```

### Manual Install

If you prefer to install packages individually:

```bash
pip install earthkit-data polytope-client covjsonkit "zarr>=2.18,<3" "numcodecs<0.16"
```

Then install visualisation and analysis packages:

```bash
conda install -c conda-forge matplotlib cartopy healpy xarray pandas cfgrib netcdf4 -y
pip install earthkit-geo
```

| Package | Version | Purpose |
|---------|---------|---------|
| `earthkit-data` | ≥0.13 | High-level Polytope data access |
| `polytope-client` | ≥0.7 | Low-level REST API client |
| `covjsonkit` | ≥0.2 | CoverageJSON format support |
| `zarr` | ≥2.18, <3 | Zarr v2 backend for xarray (required by `PolytopeZarrStore`) |
| `numcodecs` | <0.16 | Codec for zarr string arrays |
| `healpy` | ≥1.17 | HEALPix grid visualisation (all Climate DT fields are HEALPix) |
| `earthkit-geo` | ≥1.0 | Geographic feature extraction (country polygons, etc.) |
| `cfgrib` | ≥0.9 | GRIB to xarray conversion |

> **Important:** `zarr` must be **v2** (`zarr<3`). zarr v3 does not support the legacy `MutableMapping` store interface used by `PolytopeZarrStore`.

### Register the Environment as a Jupyter Kernel

To make the `destine` environment available as a kernel in Jupyter, register it:

```bash
python -m ipykernel install --user --name destine --display-name "Python 3.11 (destine)"
```

Verify it appears:

```bash
jupyter kernelspec list | grep destine
```

> **Note**: The `desp-authentication.py` script (Step 3) additionally requires `lxml`:
> ```bash
> pip install lxml
> ```

## Step 3: Set Up Authentication

A DestinE Platform authentication token is required. The recommended approach is to create a `~/.polytopeapirc` configuration file.

### Option A: Configuration File (Recommended)

Run the official authentication script from the polytope-examples repository:

```bash
# Clone the examples repo (can be done anywhere)
git clone https://github.com/destination-earth-digital-twins/polytope-examples.git /tmp/polytope-examples
cd /tmp/polytope-examples

# Run the script — it will prompt for your DestinE Platform API key
python desp-authentication.py
```

This creates `~/.polytopeapirc` which both `earthkit-data` and `polytope-client` pick up automatically.

### Option B: Direct Credentials

Pass credentials directly in code (only works with `polytope-client`, not `earthkit-data`):

```python
from polytope.api import Client

client = Client(
    address="polytope.mn5.apps.dte.destination-earth.eu",
    user_email="<YOUR EMAIL>",
    user_key="<YOUR API KEY>"
)
```

> **⚠️ Warning**: Never commit API keys or credentials to version control.

## Step 4: Verify the Setup

Test your setup with a minimal request using `earthkit-data`:

```python
import earthkit.data

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

data = earthkit.data.from_source(
    "polytope",
    "destination-earth",
    request,
    address="polytope.mn5.apps.dte.destination-earth.eu",
    stream=False
)

print(data)
```

If successful, this retrieves surface temperature and wind data from the IFS-NEMO model.

## Polytope Service Details

| Property | Value |
|----------|-------|
| Server address | `polytope.mn5.apps.dte.destination-earth.eu` |
| Collection | `destination-earth` |
| Rate limit | Up to 50 requests/sec |
| Concurrent downloads | Max 2 active |

## Troubleshooting

- **Authentication errors**: Re-run `desp-authentication.py` and verify `~/.polytopeapirc` exists.
- **Connection errors**: Verify you have internet access and the server address is correct.
- **Quota errors**: Wait for active downloads to complete; respect the 2-concurrent-download limit.
- **Package conflicts**: If using an existing environment, consider creating a fresh one as described above.
- **`zarr` version**: The `03_lazy_browse_portfolio.ipynb` notebook requires **zarr v2** (`zarr<3`). zarr v3 does not support the legacy `MutableMapping` store interface used by `PolytopeZarrStore`. If you installed zarr v3 by mistake, downgrade with `pip install "zarr<3"`.
- **Lazy browse notebook errors**: If `store.open()` fails with `TypeError: Unsupported type for store_like`, either `zarr` is not installed or the wrong version (v3) is present. Install/repair with `pip install "zarr<3"`.
- **Plots show no data / all NaN**: This is the most common issue. Use the built-in diagnostics:
  1. Run `store.verify()` in `03_lazy_browse_portfolio.ipynb`
  2. Check that `~/.polytopeapirc` exists and is valid
  3. Verify the `model` + `levtype` + `experiment` combination exists for the requested time
  4. For `PolytopeZarrStore`, check the printed log for `⚠ fetch` errors — these indicate failed requests
- **Plotting wrong visuals**: Climate DT data is on the HEALPix grid. Use `healpy.mollview(field, nest=True, flip='geo')` for correct global rendering. Avoid `ax.scatter()` or xarray `.plot()` on HEALPix data — they don't handle the nested pixel ordering correctly.
- **`earthkit-data` API changes**: If `list(data)` or iteration over GribData fails, the data access layer uses `to_xarray()` as fallback.  Report issues with the earthkit-data version.

## Next Steps

- Run `03_lazy_browse_portfolio.ipynb` for lazy monthly data access with `PolytopeZarrStore`
- See [Polytope Usage Guide](polytope_usage.md) for detailed request syntax and examples
- See [Data Catalogue](data_catalogue.md) for available datasets and variables
- Browse the [polytope-examples repository](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt) for ready-to-run notebooks
