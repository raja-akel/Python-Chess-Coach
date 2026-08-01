import requests
import time

# User-specific settings
username = "rajakel" # Replace with your Chess.com username
contact_email = "rajakel@hotmail.com" # Replace with your contact email

# Set up headers to mimic a browser request and include a user-agent with contact info
headers = {
'User-Agent': f'my-profile-tool/1.2 (username: {username}; contact: {contact_email})',
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
def main():
    print(f"Fetching game archives for user: {username}")
    archive_list = fetch_archives(username)
    if archive_list:
        print(f"Found {len(archive_list)} archives. Fetching games...")
        all_pgns = fetch_pgns(archive_list)
        # Write all PGNs to a single file
        filename = f"{username}_all_games.pgn"
        with open(filename, "w") as pgn_file:
            if all_pgns.strip(): # Ensure there is something to write
                pgn_file.write(all_pgns)
                print(f"All games have been saved to {filename}")
            else:

                print("No PGNs were fetched.")
    else:
            print("No archives found or unable to fetch archive list.")

if __name__ == "__main__":
    main()