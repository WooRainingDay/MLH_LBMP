"""Download public ALS datasets into data/external/<name>/ (gitignored).

VOC-ALS: on synapse.org, open the VOC-ALS project -> Files, select
everything you need, "Add to Download List", then run this script.
It downloads your Synapse download list via synapseclient.

CLI:
    python research/fetch_data.py              # download VOC-ALS (default)
    python research/fetch_data.py --gait        # download PhysioNet Gait (~18 MB)
    python research/fetch_data.py --torgo        # download TORGO (~9.5 GB total, slow)
    python research/fetch_data.py --check         # print file counts per dataset, no download
"""
from __future__ import annotations

import io
import os
import sys
import zipfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXTERNAL_DIR = Path(__file__).parent.parent / "data" / "external"
DATASETS = ["voc-als", "torgo", "gait"]

GAIT_ZIP_URL = (
    "https://physionet.org/static/published-projects/gaitndd/"
    "gait-in-neurodegenerative-disease-database-1.0.0.zip"
)
# Each archive mixes ALS and cerebral palsy speakers; filter by speaker ID at feature time.
TORGO_ARCHIVE_URLS = {
    name: f"https://www.cs.toronto.edu/~complingweb/data/TORGO/{name}.tar.bz2"
    for name in ("F", "FC", "M", "MC")  # dysarthric female/male + matched controls
}


def fetch_voc_als() -> str:
    """Download everything in the user's Synapse download list. Returns the manifest CSV path."""
    from synapseclient import Synapse
    from synapseclient.operations import download_list_files

    token = os.getenv("SYNAPSE_AUTH_TOKEN")
    if not token:
        sys.exit("SYNAPSE_AUTH_TOKEN not set in .env (see docs/plans/als-data-models.md, Step 0)")

    syn = Synapse()
    syn.login(authToken=token)
    dest = EXTERNAL_DIR / "voc-als"
    dest.mkdir(parents=True, exist_ok=True)
    return download_list_files(download_location=str(dest), synapse_client=syn)


def fetch_gait() -> Path:
    """Download and extract the PhysioNet Gait in Neurodegenerative Disease database."""
    import requests

    dest = EXTERNAL_DIR / "gait"
    dest.mkdir(parents=True, exist_ok=True)
    r = requests.get(GAIT_ZIP_URL, timeout=120)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(dest)
    return dest


def fetch_torgo() -> Path:
    """Download the four TORGO archives (~9.5 GB total). Slow; run only when you need it."""
    import requests

    dest = EXTERNAL_DIR / "torgo"
    dest.mkdir(parents=True, exist_ok=True)
    for name, url in TORGO_ARCHIVE_URLS.items():
        out = dest / f"{name}.tar.bz2"
        if out.exists():
            print(f"{name}.tar.bz2 already downloaded, skipping")
            continue
        print(f"Downloading {name}.tar.bz2 from {url} ...")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
    return dest


def check() -> None:
    for name in DATASETS:
        d = EXTERNAL_DIR / name
        if not d.exists():
            print(f"{name}: not downloaded")
            continue
        n = sum(1 for p in d.rglob("*") if p.is_file())
        print(f"{name}: {n} files")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    elif "--gait" in sys.argv:
        print(f"Fetching PhysioNet Gait into {fetch_gait()} ...")
        check()
    elif "--torgo" in sys.argv:
        print("Fetching TORGO (~9.5 GB total, this is slow) ...")
        fetch_torgo()
        check()
    else:
        print("Fetching VOC-ALS from your Synapse download list...")
        manifest = fetch_voc_als()
        print(f"Done. Manifest: {manifest}")
        check()
