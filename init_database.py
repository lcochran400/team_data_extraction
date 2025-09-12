import duckdb
from dotenv import load_dotenv
import os

load_dotenv()

database_path = os.getenv('DATABASE_PATH')

# Connecting to duckdb database
conn = duckdb.connect(database_path)

print("Initializing League of Legends database...")

# Creating matches table
conn.execute("""
CREATE OR REPLACE TABLE matches (
             match_id VARCHAR PRIMARY KEY,
             match_json VARCHAR
)
          
""")
# Creating participants table
conn.execute("""
    CREATE OR REPLACE TABLE participants (
        match_id VARCHAR,
        puuid VARCHAR,
        participant_json VARCHAR,
        PRIMARY KEY (match_id, puuid)
    )
""")

# Creating teams table
conn.execute("""
    CREATE OR REPLACE TABLE teams (
        match_id VARCHAR,
        team_id VARCHAR,
        is_my_team BOOLEAN,
        team_json VARCHAR,
        bans_json VARCHAR,
        objectives_json VARCHAR,
        PRIMARY KEY (match_id, team_id)
)
          
""")

print("✅ Database tables created successfully!")

conn.close()