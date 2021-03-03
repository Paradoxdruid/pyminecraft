#!/usr/bin/env python3

"""Minecraft realms download tool, based on https://github.com/air/minecraft-tools

Usage: ./download-realm.py MINECRAFT-EMAIL MINECRAFT-PASSWORD


You must have overviewer (https://github.com/overviewer/Minecraft-Overviewer/),
as well as a working configuration file.  

This script assumes you use ssh to access your remote map host.
"""

import requests
import argparse
import shutil
import subprocess
from typing import Dict, Any, List, Tuple

# CONSTANTS
AUTH_SERVER: str = "https://authserver.mojang.com/authenticate"
CLIENT_TOKEN: str = "github.com/air/minecraft-tools"
REALMS_SERVER: str = "https://pc.realms.minecraft.net/worlds"

# USER CONSTANTS - Customize as needed
OUTPUT_FILE: str = "world.tar.gz"
MC_VERSION: str = "1.16.5"
WORLD_ID: int = 1  # change for different of multiple hosted realms
LOCAL_MAP_LOCATION: str = "/home/andrew/overviewer/map-covidia/"
RSYNC_USER: str = "bonham"
RSYNC_HOST: str = "paradoxdruid.com"
RSYNC_LOCATION: str = "~/paradoxdruid.com/meep/covidia"
OVERVIEWER_CONFIG_FILE: str = "covidia-config.py"
OVERVIEWER_CMD: str = "mc-ovw"


# Helper Functions
def get_wrapper(url: str, cookies_dict: Dict[str, str]) -> Any:
    """Wrapper for requests.get, catching errors and giving json output.

    Args:
        url (str): url for get request
        cookies_dict (Dict[str, str]): cookie in dict form

    Raises:
        SystemExit: HTTP Error catching
        SystemExit: Other Request Error catching

    Returns:
        Dict[str, str]: json output from get request
    """
    try:
        r: requests.models.Response = requests.get(url, cookies=cookies_dict)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return r.json()


def post_wrapper(url: str, json_payload: Any) -> Any:
    """Wrapper for requests.post, catching errors and giving json output.

    Args:
        url (str): url for post request
        json_payload (Dict[str, str]): dictionary of json values

    Raises:
        SystemExit: HTTP Error catching
        SystemExit: Other Request Error catching

    Returns:
        Dict[str, str]: json output from post request
    """
    try:
        r: requests.models.Response = requests.post(url, json=json_payload)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return r.json()


def download_wrapper(url: str) -> requests.models.Response:
    """Wrapper for requests.get to download a file.

    Args:
        url (str): file download url

    Raises:
        SystemExit: HTTP Error catching
        SystemExit: Other Request Error catching

    Returns:
        requests.Response: response object
    """
    try:
        r: requests.models.Response = requests.get(url, allow_redirects=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise SystemExit(e)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return r


def subprocess_wrapper(command: List[str]):
    """Helper function to run external shell tools.

    Args:
        command (List[str]): list of command arguments

    Returns:
        str: output from shell command, usually discarded
    """

    output: subprocess.CompletedProcess = subprocess.run(command, check=True)
    out: str = output.stdout
    return out


# Core Functions
def get_access_token(args: argparse.Namespace) -> Tuple[str, str, str]:
    """Retrieve minecraft access token.

    Args:
        args (namespace): Command line args, minecraft username and password

    Returns:
        Tuple[str, str, str]: return access token, username, and minecraft id
    """
    payload: Any = {
        "username": args.username,
        "password": args.password,
        "clientToken": CLIENT_TOKEN,
        "agent": {"name": "Minecraft", "version": "1"},
    }
    data: Any = post_wrapper(AUTH_SERVER, payload)

    token: str = data.get("accessToken")
    name: str = data.get("selectedProfile").get("name")
    mc_id: str = data.get("selectedProfile").get("id")
    print("Authentication Successful")
    return token, name, mc_id


def download_realm(token: str, name: str, mc_id: str, backup_num: str = "1") -> None:
    """Download a Minecraft Realms backup.

    Args:
        token (str): access token
        name (str): minecraft username
        mc_id (str): minecraft user id
        backup_num (str, optional): World backup number. Defaults to "1".
    """
    cookie_dict: Dict[str, str] = {
        "sid": f"token:{token}:{mc_id}",
        "user": name,
        "version": MC_VERSION,
    }

    # 1. get world ID
    data: Any = get_wrapper(REALMS_SERVER, cookie_dict)
    world_id: str = data.get("servers")[WORLD_ID].get("id")

    # 2. get download link
    dl_data: Any = get_wrapper(
        f"{REALMS_SERVER}/{world_id}/slot/{backup_num}/download", cookie_dict,
    )
    link: str = dl_data.get("downloadLink")

    # 3. download backup
    print("Downloading...\n")
    r: requests.models.Response = download_wrapper(link)
    open(OUTPUT_FILE, "wb").write(r.content)
    print("Download successful")


def unpack_download():
    """Decompress downloaded file in current working directory."""
    shutil.unpack_archive(OUTPUT_FILE)
    print("Unpacking of download successful")


def run_overviewer(config=OVERVIEWER_CONFIG_FILE, overviewer_cmd=OVERVIEWER_CMD):
    """Run overviewer, updating the map to latest data.

    Args:
        config (str): config file to use with overviewer
        overviewer_cmd (str): name of overviewer command
    """
    print("Running overviewer...\n")
    _: str = subprocess_wrapper([overviewer_cmd, f"--config={config}"])
    _: str = subprocess_wrapper([overviewer_cmd, f"--config={config}", "--genpoi"])
    print("\n\nOverviewer successful")


def upload_map(
    map_name=LOCAL_MAP_LOCATION,
    user=RSYNC_USER,
    host=RSYNC_HOST,
    location=RSYNC_LOCATION,
):
    print("Starting rsync upload...\n")
    _: str = subprocess_wrapper(
        ["rsync", "-ae", "ssh", map_name, f"{user}@{host}:{location}"]
    )
    print("\n\nUpload completed successfuly!")


# #####################################################################################
def main():
    """Parse args, obtain access token, and download realms backup file."""
    # Parse command line arguments
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("username", help="Minecraft email address")
    parser.add_argument("password", help="Minecraft password")
    args: argparse.Namespace = parser.parse_args()

    # Perform minecraft validation and download
    token: str
    name: str
    mc_id: str
    token, name, mc_id = get_access_token(args)
    download_realm(token, name, mc_id)
    unpack_download()
    run_overviewer()
    upload_map()


# #####################################################################################

if __name__ == "__main__":
    main()
