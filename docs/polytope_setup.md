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

## Step 2: Install Polytope Dependencies

Install the core packages via pip:

```bash
pip install earthkit-data polytope-client covjsonkit
```

| Package | Purpose |
|---------|---------|
| `earthkit-data` | High-level library for data access, recommended for most use cases |
| `polytope-client` | Low-level REST API client for advanced control |
| `covjsonkit` | Handling CoverageJSON format output |

> **Note**: The `desp-authentication.py` script (Step 3) additionally requires `lxml`. Install it
> together with the other packages:
> ```bash
> pip install earthkit-data polytope-client covjsonkit lxml
> ```

### Optional: Full Installation

For a richer setup with additional data processing dependencies (xarray, matplotlib, cartopy, etc.), follow the instructions in the [polytope-examples repository](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt).

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

## Next Steps

- See [Polytope Usage Guide](polytope_usage.md) for detailed request syntax and examples.
- See [Data Catalogue](data_catalogue.md) for available datasets and variables.
- Browse the [polytope-examples repository](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main/climate-dt) for ready-to-run notebooks.