# Acclimatise Africa Rainfall

Analysis of DestinE Climate Digital Twin (Climate DT) model data for African rainfall climatology, using ICON and IFS-FESOM climate models accessed via the Polytope data extraction service.

## Repository Structure

```
acclimatise-africa-rainfall/
├── README.md                           # This file
├── docs/                               # Detailed documentation
│   ├── polytope_setup.md               # Step-by-step Polytope setup guide
│   ├── polytope_usage.md               # Polytope usage with ICON/IFS-FESOM examples
│   └── data_catalogue.md               # Available DestinE Climate DT datasets
├── get-data/                           # Data access tools
│   ├── browse_destine_data.ipynb       # Jupyter notebook for data browsing
│   └── download_destine.py            # Generic CLI download script
└── analysis/                           # Analysis scripts and notebooks
```

## Quick Start

### 1. Setup Environment

```bash
# Create and activate the dedicated conda environment
conda create -n destine python=3.11 jupyter jupyterlab -y
conda activate destine

# Install Polytope dependencies (lxml needed for authentication script)
pip install earthkit-data polytope-client covjsonkit lxml
```

See **[Polytope Setup Guide](docs/polytope_setup.md)** for detailed setup instructions including authentication.

### 2. Browse Data

Launch Jupyter and open the browsing notebook:

```bash
conda activate destine
jupyter lab get-data/browse_destine_data.ipynb
```

### 3. Download Data

Use the generic download script:

```bash
conda activate destine

# Download ICON precipitation data
python get-data/download_destine.py \
    --model ICON \
    --activity control \
    --experiment control-1950 \
    --date 20200102 \
    --param tp

# Show what a request would look like (dry run)
python get-data/download_destine.py \
    --model IFS-FESOM \
    --activity projections \
    --experiment SSP3-7.0 \
    --date 20500601 \
    --end-date 20500630 \
    --param tp/2t \
    --time 0000/0600/1200/1800 \
    --dry-run
```

## Documentation

| Document | Description |
|----------|-------------|
| [Polytope Setup](docs/polytope_setup.md) | How to set up the `destine` conda environment, install packages, and configure authentication for Polytope. |
| [Polytope Usage](docs/polytope_usage.md) | How to use Polytope with `earthkit-data` and `polytope-client`, including request structure, model-specific examples for ICON and IFS-FESOM, and common parameter codes. |
| [Data Catalogue](docs/data_catalogue.md) | Overview of available DestinE Climate DT datasets, key surface and pressure-level variables, and request templates for African rainfall analysis. |

## Climate Models Available

| Model | Type | Resolution |
|-------|------|------------|
| **ICON** | Atmosphere-only | ~5 km |
| **IFS-FESOM** | Coupled atmosphere-ocean | ~9 km atm / variable ocean |
| IFS-NEMO | Coupled atmosphere-ocean | ~9 km atm / ~1/12° ocean |

## DestinE Platform

- [DestinE Platform](https://platform.destine.eu/)
- [Climate DT User Guide](https://platform.destine.eu/docs/climate-dt-user-guide/doc/index.html)
- [Polytope Documentation](https://polytope.readthedocs.io/en/latest/)
- [Polytope Examples](https://github.com/destination-earth-digital-twins/polytope-examples)