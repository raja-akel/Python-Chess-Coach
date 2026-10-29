import requests
import time
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# User-specific settings
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "parameters.env")
USERNAME = os.getenv("USERTAG", "").strip()
CONTACT_EMAIL = os.getenv("EMAIL", "").strip() # Replace with your contact email
IMPORT_OPPONENT_COUNTRIES = os.getenv("IMPORT_OPPONENT_COUNTRIES", "").strip().lower() == "true"

COUNTRIES_FILE = BASE_DIR / "data" / "opponent_countries.json"
LEGACY_COUNTRIES_FILE = BASE_DIR / "opponent_countries.json" # old location, read once and migrated to data/
GAME_ARCHIVE_FILE = BASE_DIR / "data" / "mygames_dataframe.csv"

# Set up headers to mimic a browser request and include a user-agent with contact info
headers = {
'User-Agent': f'my-profile-tool/1.2 (username: {USERNAME}; contact: {CONTACT_EMAIL})',
'Accept-Encoding': 'gzip',
'Accept': 'application/json, text/plain, */*'
}

# Function to fetch the list of archives (months/years with games)
def fetch_archives(username):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            return response.json().get('archives', [])
        except requests.exceptions.JSONDecodeError:
            print("Error: Received non-JSON response")
            print(response.text) # Debug: Print the raw response for further inspection
            return []
    else:
        print(f"Error: Failed to fetch archives. Status Code: {response.status_code}")
        print(response.text) # Debug: Print the raw response for further inspection
        return []

# Function to fetch PGNs from a list of archive URLs
def fetch_pgns(archive_list):
    all_pgns = ""
    for archive_url in archive_list:
        # Delay between requests to avoid rate limiting
        time.sleep(1)

        pgn_response = requests.get(f"{archive_url}/pgn", headers=headers)
        print(f"Fetching PGNs from {archive_url}, Status Code: {pgn_response.status_code}")
        if pgn_response.status_code == 200:
            all_pgns += pgn_response.text + "\n\n" # Add some space between games
        elif pgn_response.status_code == 429:
            print(f"Rate limit exceeded. Retrying after a delay.")
            time.sleep(60) # Wait for 60 seconds before retrying
            pgn_response = requests.get(f"{archive_url}/pgn", headers=headers)
        if pgn_response.status_code == 200:
            all_pgns += pgn_response.text + "\n\n"
        else:
            print(f"Failed to fetch PGNs from {archive_url}")

    return all_pgns

    # Main function to run the script


def load_opponent_cache():
    for path in (COUNTRIES_FILE, LEGACY_COUNTRIES_FILE):
        if path.exists():
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
    return {}


def extract_opponents(pgn_text, username):
    """Extract unique opponent usernames from PGN headers."""
    opponents = set()

    for white, black in re.findall(
        r'^\[White "([^"]+)"\]\s*\n\[Black "([^"]+)"\]',
        pgn_text,
        re.MULTILINE
    ):
        if white.lower() == username.lower():
            opponents.add(black)
        elif black.lower() == username.lower():
            opponents.add(white)

    return opponents


def fetch_opponent_countries(pgn_text, username):
    cache = load_opponent_cache()
    opponents = extract_opponents(pgn_text, username)

    print(f"Found {len(opponents)} unique opponents.")

    for opponent in sorted(opponents):
        # Skip opponents whose country has already been checked.
        if opponent.lower() in cache:
            continue

        time.sleep(0.5)

        url = f"https://api.chess.com/pub/player/{opponent}"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 429:
                print("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                response = requests.get(
                    url, headers=headers, timeout=30
                )

            response.raise_for_status()
            profile = response.json()

            country_url = profile.get("country")
            country_code = (
                country_url.rstrip("/").split("/")[-1]
                if country_url else None
            )

            cache[opponent.lower()] = {
                "username": profile.get("username", opponent),
                "country_code": country_code,
                "country_url": country_url
            }

            # Save incrementally so progress survives interruptions.
            COUNTRIES_FILE.parent.mkdir(exist_ok=True)
            with open(COUNTRIES_FILE, "w", encoding="utf-8") as file:
                json.dump(cache, file, indent=4, ensure_ascii=False)

            print(f"{opponent}: {country_code or 'Country unavailable'}")

        except (requests.RequestException, ValueError) as error:
            print(f"Could not retrieve {opponent}: {error}")

    return cache


def main():
    print(f"Fetching game archives for user: {USERNAME}")
    archive_list = fetch_archives(USERNAME)
    if archive_list:

        ###
        if os.path.exists(GAME_ARCHIVE_FILE):
            import pandas as pd
            mygames_df = pd.read_csv(GAME_ARCHIVE_FILE)
            latest_month = mygames_df.iloc[-1, 0][0:7].replace("-", "/")
            latest_api_month = f"https://api.chess.com/pub/player/{USERNAME.lower()}/games/" + latest_month

            archive_list = archive_list[archive_list.index(latest_api_month):] #start from the latest month (inclusive)
        ###

        print(f"Found {len(archive_list)} archives. Fetching games...")
        all_pgns = fetch_pgns(archive_list)
        if IMPORT_OPPONENT_COUNTRIES:
            fetch_opponent_countries(all_pgns, USERNAME)
        # Write all PGNs to a single file
        filename = f"{USERNAME}_all_games.pgn"
        with open(filename, "a") as pgn_file:
            if all_pgns.strip(): # Ensure there is something to write
                pgn_file.write(all_pgns)
                print(f"All games have been saved to {filename}")
            else:

                print("No PGNs were fetched.")
    else:
            print("No archives found or unable to fetch archive list.")




if __name__ == "__main__":
    main()