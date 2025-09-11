import requests
import json
import duckdb
import time
from dotenv import load_dotenv
import os

load_dotenv()

conn = duckdb.connect("league_data.db")

# API Structures
riotapi="https://americas.api.riotgames.com"
puuidapi="/riot/account/v1/accounts/by-riot-id/"
matchapi="/lol/match/v5/matches/by-puuid/"
breakdownapi = "/lol/match/v5/matches/"

# Team Members
gameName=["Grumby", "T1 Ruler jr", "FlareStriker", "Serezal", "MopishSeeker"]
tagLine=["GRMBY", "NA1", "NA1", "7777", "NA1"]
apikey = os.getenv('apikey')
startTime="0"
matchCount="100"

# List of PUUIDs pulled from game names and tagline API call
puuid_list = []

for player, tag in zip(gameName, tagLine):
    r = requests.get(riotapi + puuidapi + player + "/" + tag + "?api_key=" + apikey)

    if r.status_code != 200:
        print(f"Error getting PUUID for {player}#{tag}: {r.status_code}")
        if r.status_code == 404:
            print(f"Player {player}#{tag} not found")
        elif r.status_code == 403:
            print("Invalid API key")
        elif r.status_code == 429:
            print("Rate limited - need to slow down requests")
        else:
            print(f"Response: {r.text}")
        continue

    data = json.loads(r.text)
    puuid = data["puuid"]
    puuid_list.append(puuid)

# Dictionary of gamer name + PUUID for easier associations
gamerDict = {}

for player, id in zip(gameName, puuid_list):
    gamerDict[player] = id

# Dictionary of lists - each key (player) has a value (list) of all matches they have played
matchDict = {}

for player, id in gamerDict.items():
    r = requests.get(riotapi + matchapi + id + "/ids?type=ranked&start=" + startTime + "&count=" + matchCount + "&api_key=" + apikey)
    matches = json.loads(r.text)
    matchDict.update({player:matches})

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
    if count >= 4:
        shared_games.append(match)

print("Shared games found:", len(shared_games))

# If shared games exist in the list - get the match data for the first game
if shared_games:
    for match in shared_games:
        r = requests.get(riotapi + breakdownapi + match + "?api_key=" + apikey)
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
            if participant["puuid"] in puuid_list:
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
            if participant["puuid"] in puuid_list:
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