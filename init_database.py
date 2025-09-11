import duckdb
from dotenv import load_dotenv
import os

load_dotenv()

database_path = os.getenv('database_path')

# Connecting to duckdb database
conn = duckdb.connect(database_path)

print("Initializing League of Legends database...")

# Creating matches table
conn.execute("""
CREATE OR REPLACE TABLE matches (
             match_id VARCHAR PRIMARY KEY,
             game_duration INTEGER,
             patch_version VARCHAR
)
          
""")
# Creating match_participants table
conn.execute("""
    CREATE OR REPLACE TABLE match_participants (
        match_id VARCHAR,
        participant_id INTEGER,
        win BOOLEAN,
        summoner_name VARCHAR,
        champion_name VARCHAR,
        role VARCHAR,
        team_id INTEGER,
        kills INTEGER,
        deaths INTEGER,
        assists INTEGER,
        is_first_blood_kill BOOLEAN,
        longest_time_living INTEGER,
        total_time_dead INTEGER,
        minion_cs INTEGER,
        total_cs INTEGER,
        all_in_pings INTEGER,
        assist_pings INTEGER,
        mia_pings INTEGER,
        get_back_pings INTEGER,
        need_vision_pings INTEGER,
        push_pings INTEGER,
        turret_kills INTEGER,
        turret_takedowns INTEGER,
        dragon_kills INTEGER,
        baron_kills INTEGER,
        objectives_stolen INTEGER,
        consumables_purchased INTEGER,
        sight_wards_bought INTEGER,
        vision_wards_bought INTEGER,
        vision_score INTEGER,
        wards_placed INTEGER,
        pink_wards_placed INTEGER,
        wards_killed INTEGER,
        PRIMARY KEY (match_id, participant_id)
    )
""")

# Creating objectives table
conn.execute("""
    CREATE OR REPLACE TABLE match_objectives (
        match_id VARCHAR,
        team_id INTEGER,
        is_my_team BOOLEAN,
        is_first_dragon BOOLEAN,
        total_dragon_kills INTEGER,
        total_baron_kills INTEGER,
        total_grub_kills INTEGER,
        rift_herald_kills INTEGER,
        atakhan_kills INTEGER,
        PRIMARY KEY (match_id, team_id)
)
          
""")

print("✓ Database tables created successfully!")

conn.close()