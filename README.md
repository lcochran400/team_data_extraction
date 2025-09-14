# League API Extractor

Extracts League of Legends match data for team analysis.

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your Riot API key
3. Run `python init_database.py`
4. Run `python pull_team_data.py`

## Usage
Currently, unless playing in a lobby with a tournament code, you cannot analyze custom game logic. This project can be used, however, to pull previous Flex games played by your team to gather performance history and begin leveraging the data to do team analytics.