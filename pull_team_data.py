import requests
import json
import duckdb
import time
import os
import sys
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# API Structures
RIOT_API_BASE ="https://americas.api.riotgames.com"
PUUID_API_ENDPOINT ="/riot/account/v1/accounts/by-riot-id/"
MATCH_API_ENDPOINT ="/lol/match/v5/matches/by-puuid/"
MATCH_BREAKDOWN_API_ENDPOINT = "/lol/match/v5/matches/"
START_TIME="0" # This is mandatory for the API call - doesn't need to be changed
MATCH_COUNT="100" # The number of recent matches per puuid you want to pull
MIN_SHARED_PLAYERS = 4 # The number of team members that must be in a match for it to be considered
RATE_LIMIT_DELAY = 1.2 # This ensures that you won't hit the API limits (max 100 calls in 2 mins)

# Environment Variables
team_members_str = os.getenv("TEAM_MEMBERS")

# Variables
team_members = json.loads(team_members_str)
schema_checked = False

# Functions
# safe_api_request allows me to have a repeatable way to call APIs with consideration for errors and timeouts
def safe_api_request(url, timeout=5, breakdown=False, match_id=None):
    try:
        r = requests.get(url, timeout=timeout)
        return r
    except:
        print(f"Error connecting to network. Trying again.")

        time.sleep(5)
        # Second execution attempt
        try:
            r = requests.get(url, timeout=timeout)
            return r

        # Script exit on second failure
        except:
            if breakdown==False:
                sys.exit("Error connecting to network. Please try again later")
            else:
                print(f"Error collecting data for match ID {match_id}. Skipping to next match ID.")
                return None

# get_schema_fingerprint allows me to get a clear fingerprint of the keys available in the API
# and compare against the new dataset I'm pulling so I can alert when changes occur
def get_schema_fingerprint(data):
    keys_list = []
    keys_list.extend(data.keys())
    keys_list.extend(data["info"].keys())
    keys_list.extend(data["info"]["participants"][0].keys())
    keys_list.extend(data["info"]["participants"][0]["challenges"].keys())
    keys_list.extend(data["info"]["teams"][0].keys())
    keys_list.extend(data["info"]["teams"][0]["objectives"].keys())
    return keys_list

# Environment variables
apikey = os.getenv('API_KEY')
database_path = os.getenv('DATABASE_PATH')


# Connect to local db
conn = duckdb.connect(database_path)

# Dictionary of name & PUUIDs pulled from game names and tagline API call
gamer_dict = {}

for member in team_members:

    name = member["name"]
    tag = member["tag"]

    print(f"Collecting PUUID for {name}#{tag}")

    # Executing the API call for PUUID collection
    r = safe_api_request(RIOT_API_BASE + PUUID_API_ENDPOINT + name + "/" + tag + "?api_key=" + apikey)

    time.sleep(RATE_LIMIT_DELAY)

    # Error code printing
    if r.status_code != 200:
        print(f"Error getting PUUID for {name}#{tag}: {r.status_code}")
        if r.status_code == 404:
            print(f"Player {name}#{tag} not found")
        elif r.status_code == 403:
            print("Invalid API key")
        elif r.status_code == 429:
            print("Rate limited - need to slow down requests")
        else:
            print(f"Response: {r.text}")
        continue

    # Store & extract API json results
    try:
        data = json.loads(r.text)
    except:
        sys.exit(f"Failed to parse PUUID data for {name}#{tag}. Please try again.")

    if "puuid" not in data:
        sys.exit(f"PUUID missing for {name}#{tag}")
    
    puuid = data["puuid"]
    gamer_dict[name] = puuid

print("✅ PUUIDs collected")

# Dictionary of lists - each key (player) has a value (list) of all matches they have played
matchDict = {}

for player, id in gamer_dict.items():

    print(f"Collecting latest {MATCH_COUNT} match IDs for {player}")

    # Executing API call for player matches
    r = safe_api_request(RIOT_API_BASE + MATCH_API_ENDPOINT + id + "/ids?type=ranked&start=" + START_TIME + "&count=" + MATCH_COUNT + "&api_key=" + apikey)

    time.sleep(RATE_LIMIT_DELAY)

    if r.status_code != 200:
        print(f"Error getting match IDs for {player}: {r.status_code}")
        if r.status_code == 404:
            print(f"Player {player} matches not found")
        elif r.status_code == 403:
            print("Invalid API key")
        elif r.status_code == 429:
            print("Rate limited - need to slow down requests")
        else:
            print(f"Response: {r.text}")
        continue

    try:
        matches = json.loads(r.text)
    except:
        sys.exit(f"Failed to parse match data for {player}. Please try again.")

    matchDict.update({player:matches})

print("✅ Match IDs collected")

# Dictionary with each key (matches) having an associated value (count of match appearances) to determine if it is a shared match 
match_counts = Counter()

for player in matchDict:
    for match in matchDict[player]:
        match_counts[match] += 1

# List of match IDs with 4 or more isntances in the match count dictionary
shared_games = []

for match, count in match_counts.items():
    if count >= MIN_SHARED_PLAYERS:
        shared_games.append(match)

# If shared games exist in the list - get the match data for the first game
if shared_games:

    if not schema_checked:
        print("Performing schema validation...")
        r = safe_api_request(RIOT_API_BASE + MATCH_BREAKDOWN_API_ENDPOINT + shared_games[0] + "?api_key=" + apikey, match_id=shared_games[0],breakdown=True)

        if r and r.status_code == 200:
            match_data = json.loads(r.text)

            current_fingerprint = get_schema_fingerprint(match_data)

            try:
                # Open the ref_sample.json (this is just checking to see if the file exists)
                with open("schema_reference.json") as fp:
                    # This is storing the json from the ref_sample.json into the variable reference_data
                    reference_data = json.load(fp)
                    reference_fingerprint = get_schema_fingerprint(reference_data)
                    # If reference data keys are the same as the API json keys, print confirmation
                    if current_fingerprint == reference_fingerprint:
                        print("✅ no schema changes identified")
                    # If reference data keys are different, notify user and then update the ref file
                    else:
                        print("⚠️ changes identified - update data models")
                        with open("schema_reference.json", "w") as fp:
                            current_set = set(current_fingerprint)
                            reference_set = set(reference_fingerprint)

                            new_keys = current_set - reference_set
                            missing_keys = reference_set - current_set

                            if new_keys:
                                print(f"➕ New keys added: {new_keys}")
                            if missing_keys:
                                print(f"➖ Keys removed: {missing_keys}")
                            json.dump(match_data, fp)
            # If the file doesn't exist, create a new file and add the json from the API call for future reference
            except:
                print("⚠️ File doesn't exist - creating file now...")
                with open("schema_reference.json", "x") as fp:
                    json.dump(match_data, fp)
                    print("Reference file created")
            
            schema_checked = True
        
        else:
            print("Schema check failed - exiting")
            sys.exit()

    for count, match in enumerate(shared_games, start=1):

        print(f"Processing match {count} of {len(shared_games)}")
        
        r = safe_api_request(RIOT_API_BASE + MATCH_BREAKDOWN_API_ENDPOINT + match + "?api_key=" + apikey, match_id=match,breakdown=True)
        
        if not r:
            continue

        time.sleep(RATE_LIMIT_DELAY)

        if r.status_code != 200:
            print(f"Error getting match data for  match ID: {match}: {r.status_code}")
            if r.status_code == 404:
                print(f"Match ID {match} not found")
            elif r.status_code == 403:
                print("Invalid API key")
            elif r.status_code == 429:
                print("Rate limited - need to slow down requests")
            else:
                print(f"Response: {r.text}")
            continue
        try:
            match_data = json.loads(r.text)
        except:
            print(f"Failed to parse match data for match ID {match}. Skipping to next match.")
            continue

        try:
            match_json = match_data["info"].copy()

            match_json.pop("participants", None)
            match_json.pop("teams", None)

            match_json = json.dumps(match_json)

            conn.execute("""INSERT OR REPLACE INTO matches (match_id, match_json)
                        VALUES (?, ?)
            """, [
                match_data["metadata"]["matchId"],
                match_json
            ]
            )

        # On failure, store error message and print > cancel operation
        except Exception as e:
            sys.exit(f"Database error while inserting match data: {e}")

        # Captures participant json array to be parsed through later
        if "info" not in match_data:
            print(f"Match ID {match} missing 'info' section. Skipping.")
            continue
        
        if "participants" not in match_data["info"]:
            print(f"Match ID {match} missing participants. Skipping")
            continue

        participants = match_data["info"]["participants"]

        # Check to see if the participant in the array is on our team, if yes, save the data
        for participant in participants:
            if participant["puuid"] in gamer_dict.values():
                is_sub = False
                for member in team_members:
                    if gamer_dict[member["name"]] == participant["puuid"]:
                        is_sub = (member["role"] == "sub")
                        break

                participant_json = json.dumps(participant)
                try:
                    conn.execute("""INSERT OR REPLACE INTO participants (
                            match_id,
                            puuid,
                            is_sub,
                            participant_json
                        ) VALUES (?, ?, ?, ?)
                    """, [
                        match,
                        participant["puuid"],
                        is_sub,                           
                        participant_json             
                    ]
                    )

                except Exception as e:
                    sys.exit(f"Database error while inserting participant data: {e}")

        # Identify team ID for match
        my_team_id = None

        for participant in participants:
            if participant["puuid"] in gamer_dict.values():
                my_team_id = participant["teamId"]
                break

        if "teams" not in match_data["info"]:
            print(f"Match ID {match} missing 'teams' section. Skipping")
            continue
        teams = match_data["info"]["teams"]

        for team in teams:
            team_json = team.copy()
            team_json.pop("bans", None)
            team_json.pop("objectives", None)

            bans_json = team["bans"]
            objectives_json = team["objectives"]

            is_my_team = (team["teamId"] == my_team_id)
            team_json = json.dumps(team_json)
            bans_json = json.dumps(bans_json)
            objectives_json = json.dumps(objectives_json)

            try:
                conn.execute("""INSERT OR REPLACE INTO teams (
                    match_id, 
                    team_id, 
                    is_my_team,
                    team_json,
                    bans_json,
                    objectives_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    match,
                    team["teamId"],
                    is_my_team,
                    team_json,
                    bans_json,
                    objectives_json
                ]
                )
            
            except Exception as e:
                sys.exit(f"Database error while inserting match objective data: {e}")

else:
    print("No shared matches found")

print("✅ data tables updated")

conn.close()