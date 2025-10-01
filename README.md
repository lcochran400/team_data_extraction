# League of Legends - Team Data Extraction

Python scripts to extract League of Legends match data from the Riot Games API and store it in DuckDB for team analysis. This is the **data ingestion layer** for a comprehensive LoL analytics pipeline.

## 📊 Data Pipeline Overview

This repository is the first step in a multi-stage analytics pipeline:

```
┌─────────────────────────┐
│  Riot Games API         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  team_data_extraction   │  ◄── YOU ARE HERE
│  (Python - Raw Data)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  league_analytics       │  ◄── NEXT STEP
│  (dbt - Transformations)│
│  github.com/lcochran400 │
│  /league_analytics      │
└─────────────────────────┘
```

**What this repo does:**
- Pulls raw match data from Riot Games API
- Extracts match history for your team members
- Stores complete JSON responses in DuckDB
- Handles API rate limiting and error management

**What happens next:**
After extraction, the [league_analytics dbt project](https://github.com/lcochran400/league_analytics) transforms this raw data into clean analytics tables for:
- Win rate analysis
- Player performance metrics
- Team composition effectiveness
- Match outcome prediction

## 🎯 Use Case

**Current Support:** Flex Queue Team Analysis

This project extracts Flex queue match data for your team members, allowing you to:
- Track team performance over time
- Analyze individual player statistics
- Identify winning patterns and strategies
- Build predictive models for match outcomes

**Limitation:** Custom game data cannot be accessed through the Riot API unless you're playing with a tournament code. This tool focuses on analyzing your team's Flex queue history.

## 🚀 Quick Start

### Prerequisites

- Python >= 3.8
- Riot Games API Key ([Get one here](https://developer.riotgames.com/))
- Git

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/lcochran400/team_data_extraction.git
cd team_data_extraction
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure your environment:**
```bash
cp .env.example .env
```

Edit the `.env` file with your actual credentials:

```bash
# Required: Your Riot API key from https://developer.riotgames.com/
API_KEY=RGAPI-your-actual-key-here

# Required: Database file path
DATABASE_PATH=league_data.db

# Required: Team members as JSON array (must be on one line)
TEAM_MEMBERS=[{"name": "Faker", "tag": "KR1", "role": "regular", "position": "mid"},{"name": "Zeus", "tag": "KR1", "role": "regular", "position": "top"},{"name": "Oner", "tag": "KR1", "role": "regular", "position": "jungle"},{"name": "Gumayusi", "tag": "KR1", "role": "regular", "position": "adc"},{"name": "Keria", "tag": "KR1", "role": "regular", "position": "support"},{"name": "Poby", "tag": "KR1", "role": "sub", "position": "mid"}]
```

**TEAM_MEMBERS Format:**
- `name`: Player's Riot ID name (e.g., "Faker")
- `tag`: Player's tagline (e.g., "KR1" for Faker#KR1)  
- `role`: `regular` for main roster players, `sub` for substitutes
- `position`: `top`, `jungle`, `mid`, `adc`, or `support`

⚠️ **Important:** 
- Name and tag are case-sensitive and must match exactly as they appear in your Riot ID
- The entire TEAM_MEMBERS array must be on a single line in the `.env` file
- You can include as many players as needed (the example shows 5 starters + 1 sub)

4. **Initialize the database:**
```bash
python init_database.py
```

This creates the DuckDB database and necessary tables for storing raw match data, but only needs to be run once to create the tables. In the future you will not need to run this step.

5. **Run the extraction:**
```bash
python pull_team_data.py
```

This will:
- Look up each team member's PUUID using their Riot ID (name#tag)
- Fetch their recent 100 ranked matches
- Identify "shared matches" where at least 4 team members played together
- Perform schema validation to detect API changes
- Store raw JSON data in your DuckDB database
- Track which players are subs vs regular roster members

## 📁 Project Structure

```
team_data_extraction/
├── pull_team_data.py      # Main extraction script
├── init_database.py       # Database initialization
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── data/                 # DuckDB database location
│   └── league.duckdb
└── README.md
```

## ⚙️ Configuration

All configuration is managed through environment variables in your `.env` file (created during setup step 3 above).

**Required Variables:**
- `API_KEY` - Your Riot Games API key (get one at https://developer.riotgames.com/)
- `DATABASE_PATH` - Database file location (e.g., `league_data.db`)
- `TEAM_MEMBERS` - JSON array of team member objects with `name`, `tag`, `role`, and `position` fields

## 📊 Database Schema

The extraction creates three tables in DuckDB:

### `matches`
Stores match-level information.

| Column | Type | Description |
|--------|------|-------------|
| match_id | VARCHAR | Unique match identifier (PRIMARY KEY) |
| match_json | VARCHAR | Complete match data (excluding participants and teams arrays) |

### `participants`
Stores player performance data for each match.

| Column | Type | Description |
|--------|------|-------------|
| match_id | VARCHAR | Match identifier |
| puuid | VARCHAR | Player UUID |
| is_sub | BOOLEAN | Whether this player is a substitute |
| participant_json | VARCHAR | Complete participant data from API |
| PRIMARY KEY | | (match_id, puuid) |

### `teams`
Stores team-level data (objectives, bans, etc.).

| Column | Type | Description |
|--------|------|-------------|
| match_id | VARCHAR | Match identifier |
| team_id | VARCHAR | Team identifier (100 or 200) |
| is_my_team | BOOLEAN | Whether this is your team |
| team_json | VARCHAR | Team data (excluding bans and objectives) |
| bans_json | VARCHAR | Champion bans array |
| objectives_json | VARCHAR | Objectives data (dragons, barons, towers, etc.) |
| PRIMARY KEY | | (match_id, team_id) |

## 🔄 Next Steps: Transform Your Data

Once you've extracted match data, head over to the **[league_analytics dbt project](https://github.com/lcochran400/league_analytics)** to transform this raw data into analytics-ready tables.

The dbt project will:
1. Parse the raw JSON into structured tables
2. Calculate advanced metrics (KDA, CS/min, damage ratios)
3. Create dimensional models (`dim_matches`, `fct_player_match_performance`)
4. Generate win rate reports and performance insights

### Running Transformations

```bash
# Clone the dbt project
git clone https://github.com/lcochran400/league_analytics.git
cd league_analytics

# Install dbt
pip install dbt-duckdb

# Run transformations
dbt run

# View documentation
dbt docs generate
dbt docs serve
```

The dbt project connects to the same `league.duckdb` database created by this extraction script.

## 🛠️ Advanced Usage

### Schema Change Detection

The script automatically monitors for Riot API schema changes:
- On first run, creates a `schema_reference.json` file with the current API structure
- On subsequent runs, compares against this reference
- Alerts you when new fields are added or removed
- Updates the reference file when changes are detected

```
⚠️ changes identified - update data models
➕ New keys added: {'newField1', 'newField2'}
➖ Keys removed: {'oldField1'}
```

### Customizing Match Criteria

You can modify constants in `pull_team_data.py`:

```python
MATCH_COUNT = "100"          # Number of recent matches per player (max 100)
MIN_SHARED_PLAYERS = 4       # Minimum team members required in a match
RATE_LIMIT_DELAY = 1.2       # Delay between API calls (seconds)
```

### What Counts as a "Shared Match"?

Only matches where at least `MIN_SHARED_PLAYERS` (default: 4) of your team members played together are extracted. This filters out solo queue games and focuses on team play.

## 📋 Data Flow Diagram

```
1. pull_team_data.py
   └─> Riot API (Match-v5, Summoner-v4)
       └─> Raw JSON stored in DuckDB
           └─> league_analytics (dbt)
               └─> Transformed tables:
                   ├─> dim_matches
                   ├─> fct_player_match_performance
                   └─> rpt_winrate_analysis
```

## 🐛 Troubleshooting

### API Key Issues
- **Error 403 (Invalid API key)**: Verify your key is active at https://developer.riotgames.com/
- Development keys expire after 24 hours - regenerate if needed
- Ensure there are no spaces/newlines in your `.env` file
- Check that the variable name in `.env` matches what the code expects

### Rate Limit Errors (429)
- The script has built-in rate limiting (`RATE_LIMIT_DELAY = 1.2` seconds)
- Development keys: 20 requests/second, 100 requests/2 minutes
- If you still hit limits, increase `RATE_LIMIT_DELAY` in `pull_team_data.py`

### Player Not Found (404)
- Verify Riot IDs are spelled correctly with proper capitalization
- Check that name and tag match exactly (e.g., "Faker#KR1" not "faker#kr1")
- Ensure players have played ranked matches recently

### No Shared Matches Found
- Your team needs at least `MIN_SHARED_PLAYERS` (default: 4) in the same match
- Check that team members have played Flex games together
- Only Flex matches are pulled (not normals or ARAM)

### Database Errors
- Ensure the directory for `DATABASE_PATH` exists
- Check file permissions on your database file
- Try deleting the database and running `python init_database.py` again
- Verify DuckDB is properly installed: `python -c "import duckdb; print(duckdb.__version__)"`

### Schema Changes Warning
- This is informational - the script continues to work
- Update your dbt models when you see: `⚠️ changes identified - update data models`
- The `schema_reference.json` file is automatically updated

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - feel free to use this for your own team analytics!

## 🔗 Related Projects

- **[league_analytics](https://github.com/lcochran400/league_analytics)** - dbt transformations and analytics models (recommended next step)
- **league-analytics-python** - Advanced Python analytics and ML models (coming soon)

## 📧 Support

- Issues: https://github.com/lcochran400/team_data_extraction/issues
- Riot API Docs: https://developer.riotgames.com/
- dbt Docs: https://docs.getdbt.com/

---

**Ready to transform your data?** Head to the [league_analytics dbt project](https://github.com/lcochran400/league_analytics) to turn this raw data into actionable insights! 🎮📈