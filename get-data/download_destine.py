#!/usr/bin/env python3
"""
Generic DestinE Climate DT Data Download Script

Downloads climate model data from DestinE using Polytope / earthkit-data.
Supports ICON, IFS-FESOM, and IFS-NEMO models with configurable temporal,
spatial, and variable selection.

Usage Examples:
    # Download ICON control simulation surface pressure for one day
    python download_destine.py --model ICON --experiment cont \
        --date 19900102 --param 134

    # Download IFS-FESOM projections for multiple days
    python download_destine.py --model IFS-FESOM --experiment SSP3-7.0 \
        --date 20200601 --end-date 20200605 \
        --param 134/165/166 --time 0000/0600/1200/1800 \
        --output ./data/fesom_proj

    # Download monthly data (clmn stream)
    python download_destine.py --model IFS-FESOM --experiment hist \
        --date 20100601 --param avg_2t --data-stream clmn

    # Use parameter short names
    python download_destine.py --model IFS-NEMO --experiment SSP3-7.0 \
        --date 20200102 --param tp/2t

Requirements:
    conda activate destine
    pip install -r requirements.txt
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


# ---- Configuration ----

# Server addresses per model family
# ICON and IFS-FESOM -> LUMI  |  IFS-NEMO -> MN5
LUMI_ADDRESS = "polytope.lumi.apps.dte.destination-earth.eu"
MN5_ADDRESS  = "polytope.mn5.apps.dte.destination-earth.eu"
COLLECTION = "destination-earth"

# Default request template - most keys are standard across all Climate DT data
DEFAULT_REQUEST = {
    "class": "d1",
    "dataset": "climate-dt",
    "expver": "0001",
    "generation": "2",
    "resolution": "standard",
    "stream": "clte",
    "type": "fc",
}

# Map model -> correct Polytope server address
MODEL_ADDRESS = {
    "ICON":       LUMI_ADDRESS,
    "IFS-FESOM":  LUMI_ADDRESS,
    "IFS-NEMO":   MN5_ADDRESS,
}

# Map experiment -> correct activity keyword
EXPERIMENT_ACTIVITY = {
    "hist":      "baseline",
    "cont":      "baseline",
    "SSP3-7.0":  "projections",
}

# Parameter code reference — numeric codes for clte stream,
# shortNames for clmn stream (see destine_portfolio.py for full catalogue)
PARAM_CODES = {
    # clte hourly instantaneous
    "sp": "134",         # Surface pressure
    "10u": "165",        # 10m U wind
    "10v": "166",        # 10m V wind
    "2t": "167",         # 2m temperature
    "2d": "168",         # 2m dewpoint
    "tp": "228228",      # Total precipitation
    "msl": "151",        # Mean sea level pressure
    "skt": "235",        # Skin temperature
    # clmn monthly means (use with --data-stream clmn)
    "avg_2t": "avg_2t",          # 2m temperature (monthly mean)
    "avg_tprate": "avg_tprate",  # total precipitation rate (monthly mean)
    "avg_sp": "avg_sp",          # surface pressure (monthly mean)
    "avg_msl": "avg_msl",        # MSL pressure (monthly mean)
    "avg_tcc": "avg_tcc",        # total cloud cover (monthly mean)
    "avg_10u": "avg_10u",        # 10m U wind (monthly mean)
    "avg_10v": "avg_10v",        # 10m V wind (monthly mean)
    "avg_skt": "avg_skt",        # skin temperature (monthly mean)
}


def get_address(model: str) -> str:
    """Return the correct Polytope server address for a given model."""
    return MODEL_ADDRESS.get(model, LUMI_ADDRESS)


def get_activity(experiment: str) -> str:
    """Return the correct activity keyword for a given experiment."""
    return EXPERIMENT_ACTIVITY.get(experiment, "projections")


def safe_len(data) -> int:
    """Count fields in an earthkit-data result, even for GribData (no __len__/__iter__)."""
    try:
        return data.to_numpy().size
    except Exception:
        return 1


def build_request(
    model: str,
    experiment: str,
    date: str,
    param: str,
    time: str = "0000",
    levtype: str = "sfc",
    realization: str = "1",
    extra_keys: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build a Polytope request dictionary.

    Parameters
    ----------
    model : str
        Climate model: 'ICON', 'IFS-FESOM', 'IFS-NEMO'
    experiment : str
        Experiment name: 'cont' (control), 'hist' (historical), 'SSP3-7.0' (projections)
    date : str
        Date in YYYYMMDD format.
        'cont'/'hist' experiments typically use 1990-2014 dates,
        'SSP3-7.0' uses 2020-2050 dates.
    param : str
        Parameter code(s), slash-separated, e.g. '134' or '228228/167'.
        Can also use short names: 'tp' -> '228228', 'avg_2t' -> 'avg_2t'.
    time : str
        Time(s) in HHMM format, e.g. '0000' or '0000/0300/.../2100'.
    levtype : str
        'sfc' (surface), 'pl' (pressure levels), 'hl' (height levels),
        'sol' (soil/snow), 'o2d' (2D ocean), 'o3d' (3D ocean).
    realization : str
        Ensemble realization number.
    extra_keys : dict, optional
        Additional key-value pairs to add/override in the request.

    Returns
    -------
    dict
        Polytope request dictionary.
    """
    # Resolve parameter short names
    resolved_params = []
    for p in param.split("/"):
        resolved_params.append(PARAM_CODES.get(p.lower(), p))
    param_str = "/".join(resolved_params)

    request = {
        **DEFAULT_REQUEST,
        "activity": get_activity(experiment),
        "model": model,
        "experiment": experiment,
        "date": date,
        "param": param_str,
        "time": time,
        "levtype": levtype,
        "realization": realization,
    }

    if extra_keys:
        request.update(extra_keys)

    return request


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Generate a list of dates between start_date and end_date (inclusive)
    in YYYYMMDD format.

    Example:
        generate_date_range('20200101', '20200103')
        -> ['20200101', '20200102', '20200103']
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    if end < start:
        raise ValueError(f"end_date {end_date} is before start_date {start_date}")

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def download_data(
    request: Dict[str, Any],
    output_dir: str = "./data",
    stream: bool = False,
) -> bool:
    """
    Download data from Polytope using earthkit-data.

    Parameters
    ----------
    request : dict
        Polytope request dictionary.
    output_dir : str
        Directory to store downloaded data.
    stream : bool
        If True, stream data directly; if False, cache to local file.

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    try:
        import earthkit.data

        model = request.get("model", "ICON")
        address = get_address(model)

        print("Downloading from Polytope...")
        print(f"  Server:     {address}")
        print(f"  Model:      {model}")
        print(f"  Activity:   {request.get('activity', 'N/A')}")
        print(f"  Experiment: {request.get('experiment', 'N/A')}")
        print(f"  Date:       {request.get('date', 'N/A')}")
        print(f"  Time:       {request.get('time', 'N/A')}")
        print(f"  Param:      {request.get('param', 'N/A')}")
        print(f"  Output:     {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        data = earthkit.data.from_source(
            "polytope",
            COLLECTION,
            request,
            address=address,
            stream=stream,
        )

        print(f"Download successful - retrieved {safe_len(data)} values.")
        return True

    except ImportError:
        print("ERROR: earthkit-data is not installed.", file=sys.stderr)
        print("Install with: pip install -r requirements.txt", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        print("Check your authentication (~/.polytopeapirc) and request parameters.",
              file=sys.stderr)
        return False


def download_low_level(
    request: Dict[str, Any],
    output_dir: str = "./data",
    email: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bool:
    """
    Download data using the low-level polytope-client.

    Use this for advanced scenarios where earthkit-data is not suitable.

    Parameters
    ----------
    request : dict
        Polytope request dictionary.
    output_dir : str
        Directory for output files.
    email : str, optional
        DestinE Platform email. Reads from ~/.polytopeapirc if omitted.
    api_key : str, optional
        DestinE Platform API key. Reads from ~/.polytopeapirc if omitted.

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    try:
        from polytope.api import Client

        model = request.get("model", "ICON")
        address = get_address(model)

        kwargs = {"address": address}
        if email and api_key:
            kwargs["user_email"] = email
            kwargs["user_key"] = api_key

        client = Client(**kwargs)
        client.revoke("all")  # Cancel any pending requests

        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading via polytope-client to {output_dir}...")
        files = client.retrieve(COLLECTION, request, output_dir)
        print(f"Downloaded {len(files)} file(s):")
        for f in files:
            print(f"  {f}")
        return True

    except ImportError:
        print("ERROR: polytope-client is not installed.", file=sys.stderr)
        print("Install with: pip install polytope-client", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return False


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parse 'key=value' strings into a dictionary."""
    result = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(
                f"Invalid key=value pair: '{pair}'. Expected format: key=value"
            )
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Download DestinE Climate DT data via Polytope",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single date, single parameter
  %(prog)s --model ICON --experiment cont --date 19900102 --param 134

  # Date range with multiple parameters
  %(prog)s --model IFS-FESOM --experiment SSP3-7.0 \\
           --date 20200601 --end-date 20200630 \\
           --param tp/2t --time 0000/0600/1200/1800

  # Monthly data (clmn stream)
  %(prog)s --model IFS-FESOM --experiment hist \\
           --date 20100601 --param avg_2t --data-stream clmn

  # Use short parameter names
  %(prog)s --model ICON --experiment hist --date 20000615 --param tp/10u/10v

  # Override request keys
  %(prog)s --model ICON --experiment SSP3-7.0 --date 20200615 \\
           --param tp --request-key generation=2 \\
           --request-key resolution=standard

  # Use low-level polytope-client
  %(prog)s --model IFS-FESOM --experiment SSP3-7.0 \\
           --date 20200101 --param 134 --use-client

  # Dry-run: print request without downloading
  %(prog)s --model IFS-NEMO --experiment hist --date 20000615 \\
           --param 134 --dry-run

Experiment names:
  cont      = control simulation (activity=baseline)
  hist      = historical simulation (activity=baseline)
  SSP3-7.0  = future projections (activity=projections)

Server mapping:
  ICON, IFS-FESOM  -> LUMI (polytope.lumi.apps.dte.destination-earth.eu)
  IFS-NEMO         -> MN5  (polytope.mn5.apps.dte.destination-earth.eu)

Parameter short names (hourly clte):
  sp=134 (surface pressure), 10u=165, 10v=166, 2t=167,
  2d=168, tp=228228 (precipitation), msl=151, skt=235

Parameter short names (monthly clmn, use --data-stream clmn):
  avg_2t (2m temperature), avg_tprate (precipitation rate),
  avg_sp (surface pressure), avg_msl (MSLP), avg_tcc (cloud cover)
        """,
    )

    # Required arguments
    parser.add_argument(
        "--model", required=True,
        choices=["ICON", "IFS-FESOM", "IFS-NEMO"],
        help="Climate model to query"
    )
    parser.add_argument(
        "--experiment", required=True,
        help="Experiment name: cont (control), hist (historical), SSP3-7.0 (projections)"
    )
    parser.add_argument(
        "--date", required=True,
        help="Date in YYYYMMDD format (start date if used with --end-date)"
    )
    parser.add_argument(
        "--param", required=True,
        help="Parameter codes (slash-separated), e.g. '134/165/166' or 'tp/2t'"
    )

    # Optional arguments
    parser.add_argument(
        "--end-date",
        help="End date in YYYYMMDD format for date range (inclusive)"
    )
    parser.add_argument(
        "--time", default="0000",
        help="Time(s) in HHMM format (default: 0000). "
             "Use slash for multiple: '0000/0600/1200/1800'"
    )
    parser.add_argument(
        "--levtype", default="sfc",
        choices=["sfc", "pl", "hl", "sol", "o2d", "o3d"],
        help="Level type (default: sfc)"
    )
    parser.add_argument(
        "--data-stream", default="clte",
        choices=["clte", "clmn"],
        help="Data stream: clte (hourly instantaneous, default) or "
             "clmn (monthly means)"
    )
    parser.add_argument(
        "--realization", default="1",
        help="Ensemble realization number (default: 1)"
    )
    parser.add_argument(
        "--output", "-o", default="./data",
        help="Output directory (default: ./data)"
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream data directly instead of caching locally"
    )
    parser.add_argument(
        "--use-client", action="store_true",
        help="Use low-level polytope-client instead of earthkit-data"
    )
    parser.add_argument(
        "--request-key", action="append", default=[],
        metavar="KEY=VALUE",
        help="Additional request key-value pair (can be used multiple times). "
             "Example: --request-key generation=2 --request-key stream=clte"
    )
    parser.add_argument(
        "--email",
        help="DestinE Platform email (for polytope-client)"
    )
    parser.add_argument(
        "--api-key",
        help="DestinE Platform API key (for polytope-client)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the request dictionary without downloading"
    )

    args = parser.parse_args()

    # Parse extra request keys
    try:
        extra_keys = parse_key_value_pairs(args.request_key)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Inject data stream if not already in extra_keys (overrides DEFAULT_REQUEST)
    if "stream" not in extra_keys and args.data_stream:
        extra_keys["stream"] = args.data_stream

    # Generate date list
    if args.end_date:
        try:
            dates = generate_date_range(args.date, args.end_date)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        dates = [args.date]

    print("=" * 60)
    print("DestinE Climate DT Data Download")
    print("=" * 60)
    print(f"Model:      {args.model}")
    print(f"Experiment: {args.experiment}")
    print(f"Server:     {get_address(args.model)}")
    print(f"Data stream:{args.data_stream}")
    print(f"Dates to download: {len(dates)} day(s)")
    print()

    success_count = 0
    fail_count = 0

    for idx, day in enumerate(dates, start=1):
        request = build_request(
            model=args.model,
            experiment=args.experiment,
            date=day,
            param=args.param,
            time=args.time,
            levtype=args.levtype,
            realization=args.realization,
            extra_keys=extra_keys if extra_keys else None,
        )

        if args.dry_run:
            print(f"--- Request for {day} ---")
            for key, value in sorted(request.items()):
                print(f"  {key}: {value}")
            continue

        print(f"--- Processing {day} ({idx}/{len(dates)}) ---")

        if args.use_client:
            ok = download_low_level(
                request,
                output_dir=args.output,
                email=args.email,
                api_key=args.api_key,
            )
        else:
            ok = download_data(
                request,
                output_dir=args.output,
                stream=args.stream,
            )

        if ok:
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print()
    print("=" * 60)
    print(
        f"Summary: {success_count} succeeded, {fail_count} failed "
        f"(out of {len(dates)} day(s))"
    )
    print("=" * 60)

    if args.dry_run:
        print("\nThis was a dry run. Remove --dry-run to actually download data.")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()