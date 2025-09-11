import requests
import json
import duckdb
import time
from dotenv import load_dotenv
import os

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

# Team Members
TEAM_MEMBERS = [
    {"name": "Grumby", "tag": "GRMBY"},
    {"name": "T1 Ruler jr", "tag": "NA1"},
    {"name": "FlareStriker", "tag": "NA1"},
    {"name": "Serezal", "tag": "7777"},
    {"name": "MopishSeeker", "tag": "NA1"}
]

# Environment variables
apikey = os.getenv('apikey')
database_path = os.getenv('database_path')


# Connect to local db
conn = duckdb.connect(database_path)

# Dictionary of name & PUUIDs pulled from game names and tagline API call
gamer_dict = {}

for member in TEAM_MEMBERS:

    name = member["name"]
    tag = member["tag"]

    print(f"Collecting PUUID for {name}#{tag}")

    r = requests.get(RIOT_API_BASE + PUUID_API_ENDPOINT + name + "/" + tag + "?api_key=" + apikey)

    time.sleep(RATE_LIMIT_DELAY)

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

    data = json.loads(r.text)
    puuid = data["puuid"]
    gamer_dict[name] = puuid

print("PUUIDs collected")

# Dictionary of lists - each key (player) has a value (list) of all matches they have played
matchDict = {}

for player, id in gamer_dict.items():

    print(f"Collecting latest {MATCH_COUNT} matche IDs for {player}")

    r = requests.get(RIOT_API_BASE + MATCH_API_ENDPOINT + id + "/ids?type=ranked&start=" + START_TIME + "&count=" + MATCH_COUNT + "&api_key=" + apikey)

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

    matches = json.loads(r.text)
    matchDict.update({player:matches})

print("Match IDs collected")

# Dictionary with each key (matches) having an associated value (count of match appearances) to determine if it is a shared match 
match_counts = {}

for player in matchDict:
    for match in matchDict[player]:
        if match in match_counts:
            match_counts[match] = match_counts[match] + 1
        else:
            match_counts[match] = 1

# List of match IDs with 4 or more isntances in the match count dictionary
shared_games = []

for match, count in match_counts.items():
    if count >= MIN_SHARED_PLAYERS:
        shared_games.append(match)

print(f"{len(shared_games)} shared games found")

# If shared games exist in the list - get the match data for the first game
if shared_games:
    start_time = time.perf_counter()

    for count, match in enumerate(shared_games, start=1):

        if count <= 2:
            print(f"Processing match {count} of {len(shared_games)}")
        
        else:
            elapsed_time = time.perf_counter() - start_time
            avg_time_per_match = elapsed_time / count
            estimated_remaining = avg_time_per_match * (len(shared_games) - count)

            print(f"Processing match {count} of {len(shared_games)}. About {int(estimated_remaining)} seconds remaining")

        r = requests.get(RIOT_API_BASE + MATCH_BREAKDOWN_API_ENDPOINT + match + "?api_key=" + apikey)

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
        
        match_data = json.loads(r.text)
        current_match_id = match_data["metadata"]["matchId"]

        conn.execute("""INSERT OR REPLACE INTO matches (match_id, game_duration, patch_version)
                    VALUES (?, ?, ?)
        """, [
            match_data["metadata"]["matchId"],
            match_data["info"]["gameDuration"],
            match_data["info"]["gameVersion"]
        ]
        )

        # Captures participant json array to be parsed through later
        participants = match_data["info"]["participants"]

        # Check to see if the participant in the array is on our team, if yes, save the data
        for participant in participants:
            if participant["puuid"] in gamer_dict.values():
                conn.execute("""INSERT OR REPLACE INTO match_participants (
                        match_id,
                        participant_id,
                        win,
                        summoner_name,
                        champion_name,
                        role,
                        team_id,
                        kills,
                        deaths,
                        assists,
                        is_first_blood_kill,
                        longest_time_living,
                        total_time_dead,
                        minion_cs,
                        total_cs,
                        all_in_pings,
                        assist_pings,
                        mia_pings,
                        get_back_pings,
                        need_vision_pings,
                        push_pings,
                        turret_kills,
                        turret_takedowns,
                        dragon_kills,
                        baron_kills,
                        objectives_stolen,
                        consumables_purchased,
                        sight_wards_bought,
                        vision_wards_bought,
                        vision_score,
                        wards_placed,
                        pink_wards_placed,
                        wards_killed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    match,                           
                    participant["participantId"],          
                    participant["win"],                    
                    participant["riotIdGameName"],         
                    participant["championName"],
                    participant["role"],           
                    participant["teamId"],                 
                    participant["kills"],                  
                    participant["deaths"],                 
                    participant["assists"],                
                    participant["firstBloodKill"],         
                    participant["longestTimeSpentLiving"], 
                    participant["totalTimeSpentDead"],
                    participant["neutralMinionsKilled"],     
                    participant["totalMinionsKilled"],     
                    participant["allInPings"],             
                    participant["assistMePings"],          
                    participant["enemyMissingPings"],      
                    participant["getBackPings"],           
                    participant["needVisionPings"],        
                    participant["pushPings"],              
                    participant["turretKills"],            
                    participant["turretTakedowns"],        
                    participant["dragonKills"],            
                    participant["baronKills"],             
                    participant["objectivesStolen"],       
                    participant["consumablesPurchased"],   
                    participant["sightWardsBoughtInGame"], 
                    participant["visionWardsBoughtInGame"],
                    participant["visionScore"],            
                    participant["wardsPlaced"],            
                    participant["detectorWardsPlaced"],    
                    participant["wardsKilled"]             
                ]
                )

        # Identify team ID for match
        my_team_id = None

        for participant in participants:
            if participant["puuid"] in gamer_dict.values():
                my_team_id = participant["teamId"]
                break
        
        teams = match_data["info"]["teams"]
        for team in teams:
            is_my_team = (team["teamId"] == my_team_id)

            conn.execute("""INSERT OR REPLACE INTO match_objectives (
                match_id, 
                team_id, 
                is_my_team, 
                is_first_dragon, 
                total_dragon_kills, 
                total_baron_kills, 
                total_grub_kills, 
                rift_herald_kills, 
                atakhan_kills
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                match,
                team["teamId"],
                is_my_team,
                team["objectives"]["dragon"]["first"],
                team["objectives"]["dragon"]["kills"],
                team["objectives"]["baron"]["kills"],
                team["objectives"]["horde"]["kills"],
                team["objectives"]["riftHerald"]["kills"],
                team["objectives"]["atakhan"]["kills"]
            ]
            )
        
else:
    print("No shared matches found")

result = conn.execute("SELECT * FROM match_participants").fetchall()

print("Total participant records:", len(result))    

result = conn.execute("SELECT * FROM matches").fetchall()

print("Total match records:", len(result))    

result = conn.execute("SELECT * FROM match_objectives").fetchall()

print("Total objective records:", len(result))    

conn.close()