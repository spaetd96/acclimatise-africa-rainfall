#!/usr/bin/env python3
"""
Generic DestinE Climate DT Data Download Script

Downloads climate model data from DestinE using Polytope / earthkit-data.
Supports ICON, IFS-FESOM, and IFS-NEMO models with configurable temporal,
spatial, and variable selection.

Usage Examples:
    # Download ICON control simulation precipitation for one day
    python download_destine.py --model ICON --activity control \
        --experiment control-1950 --date 20200102 --param 228228

    # Download IFS-FESOM projections for multiple days
    python download_destine.py --model IFS-FESOM --activity projections \
        --experiment SSP3-7.0 --date 20500601 --end-date 20500605 \
        --param 228228/167 --time 0000/0600/1200/1800 \
        --output ./data/fesom_proj

    # Download with custom request keys
    python download_destine.py --model ICON --activity control \
        --experiment control-1950 --date 20200102 --param 134 \
        --request-key stream=clte --request-key generation=3

Requirements:
    conda activate destine
    pip install earthkit-data polytope-client covjsonkit
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any


# ---- Configuration ----

POLYTOPE_ADDRESS = "polytope.mn5.apps.dte.destination-earth.eu"
COLLECTION = "destination-earth"

# Default request template — most keys are standard across all Climate DT data
DEFAULT_REQUEST = {
    "class": "d1",
    "dataset": "climate-dt",
    "expver": "0001",
    "generation": "2",
    "resolution": "standard",
    "stream": "clte",
    "type": "fc",
}

# Parameter code reference
PARAM_CODES = {
    "sp": "134",         # Surface pressure
    "10u": "165",        # 10m U wind
    "10v": "166",        # 10m V wind
    "2t": "167",         # 2m temperature
    "2d": "168",         # 2m dewpoint
    "tp": "228228",      # Total precipitation
    "msl": "151",        # Mean sea level pressure
    "skt": "235",        # Surface temperature (skin)
}


def build_request(
    model: str,
    activity: str,
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
    activity : str
        'control' or 'projections'
    experiment : str
        Experiment name: 'control-1950', 'historical', 'SSP3-7.0', etc.
    date : str
        Date in YYYYMMDD format.
    param : str
        Parameter code(s), slash-separated, e.g. '134' or '228228/167'.
        Can also use short names: 'tp' -> '228228'.
    time : str
        Time(s) in HHMM format, e.g. '0000' or '0000/0300/.../2100'.
    levtype : str
        'sfc' (surface), 'pl' (pressure levels), 'hl' (height levels).
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
        "activity": activity,
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

        print(f"Downloading from Polytope...")
        print(f"  Model:      {request.get('model', 'N/A')}")
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
            address=POLYTOPE_ADDRESS,
            stream=stream,
        )

        print(f"✓ Download successful! Retrieved {len(data)} fields.")
        return True

    except ImportError:
        print("ERROR: earthkit-data is not installed.", file=sys.stderr)
        print("Install with: pip install earthkit-data polytope-client covjsonkit",
              file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Download failed: {e}", file=sys.stderr)
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

        kwargs = {"address": POLYTOPE_ADDRESS}
        if email and api_key:
            kwargs["user_email"] = email
            kwargs["user_key"] = api_key

        client = Client(**kwargs)
        client.revoke("all")  # Cancel any pending requests

        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading via polytope-client to {output_dir}...")
        files = client.retrieve(COLLECTION, request, output_dir)
        print(f"✓ Downloaded {len(files)} file(s):")
        for f in files:
            print(f"  {f}")
        return True

    except ImportError:
        print("ERROR: polytope-client is not installed.", file=sys.stderr)
        print("Install with: pip install polytope-client", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Download failed: {e}", file=sys.stderr)
        return False


def parse_key_value_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parse 'key=value' strings into a dictionary."""
    result = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid key=value pair: '{pair}'. Expected format: key=value")
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
  %(prog)s --model ICON --activity control --experiment control-1950 \\
           --date 20200102 --param 228228

  # Date range with multiple parameters
  %(prog)s --model IFS-FESOM --activity projections \\
           --experiment SSP3-7.0 --date 20500601 --end-date 20500630 \\
           --param tp/2t --time 0000/0600/1200/1800

  # Use short parameter names
  %(prog)s --model ICON --activity control --experiment control-1950 \\
           --date 20200102 --param tp/10u/10v

  # Override request keys
  %(prog)s --model ICON --activity projections --experiment historical \\
           --date 20000115 --param tp --request-key generation=3 \\
           --request-key resolution=high

  # Use low-level polytope-client
  %(prog)s --model IFS-FESOM --activity projections \\
           --experiment SSP3-7.0 --date 20500101 --param 134 \\
           --use-client

Parameter short names:
  sp=134 (surface pressure), 10u=165, 10v=166, 2t=167,
  2d=168, tp=228228 (precipitation), msl=151, skt=235
        """,
    )

    # Required arguments
    parser.add_argument(
        "--model", required=True,
        choices=["ICON", "IFS-FESOM", "IFS-NEMO"],
        help="Climate model to query"
    )
    parser.add_argument(
        "--activity", required=True,
        choices=["control", "projections"],
        help="Simulation activity type"
    )
    parser.add_argument(
        "--experiment", required=True,
        help="Experiment name (e.g., control-1950, historical, SSP3-7.0)"
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
        choices=["sfc", "pl", "hl"],
        help="Level type (default: sfc)"
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
             "Example: --request-key generation=3 --request-key stream=clte"
    )
    parser.add_argument(
        "--email",
        help="DestinE Platform email (for polytope-client, optional if ~/.polytopeapirc exists)"
    )
    parser.add_argument(
        "--api-key",
        help="DestinE Platform API key (for polytope-client, optional if ~/.polytopeapirc exists)"
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

    # Generate date list
    if args.end_date:
        try:
            dates = generate_date_range(args.date, args.end_date)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        dates = [args.date]

    print(f"{'='*60}")
    print(f"DestinE Climate DT Data Download")
    print(f"{'='*60}")
    print(f"Dates to download: {len(dates)} day(s)")
    print()

    success_count = 0
    fail_count = 0

    for day in dates:
        request = build_request(
            model=args.model,
            activity=args.activity,
            experiment=args.experiment,
            date=day,
            param=args.param,
            time=args.time,
            levtype=args.levtype,
            realization=args.realization,
            extra_keys=extra_keys if extra_keys else None,
        )

        if args.dry_run:
            print(f"\n--- Request for {day} ---")
            for key, value in sorted(request.items()):
                print(f"  {key}: {value}")
            continue

        print(f"\n--- Processing {day} ({dates.index(day) + 1}/{len(dates)}) ---")

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
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {fail_count} failed "
          f"(out of {len(dates)} day(s))")
    print(f"{'='*60}")

    if args.dry_run:
        print("\nThis was a dry run. Remove --dry-run to actually download data.")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()