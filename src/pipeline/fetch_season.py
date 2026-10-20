import json
from pathlib import Path
import pandas as pd
from api import anilist
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())
last_season = Path(CONFIG["path_last_season"])

current = helpers.season_offset(0)
previous = helpers.season_offset(-1)

# the first run of a new season also refetches the previous one, so its works get their final episodes and scores
seasons = [current]
if not last_season.exists() or last_season.read_text().strip() != f"{current[0]} {current[1]}":
    seasons.insert(0, previous)

df1 = pd.read_csv(CONFIG["path_historical_csv"])

print(f"Fetching {', '.join(f'{s} {y}' for s, y in seasons)} from Anilist")
new_entries = pd.concat([anilist.fetch_media(f"season: {s}, seasonYear: {y}") for s, y in seasons], ignore_index=True)

# same cleaning as the airing works
new_entries = helpers.clean(new_entries)

# the fetched works replace the ones already in anime.csv
df = helpers.merge(df1, new_entries.astype(df1.dtypes))

helpers.save_csv(df, CONFIG["path_historical_csv"])
last_season.write_text(f"{current[0]} {current[1]}\n")
print(f"\n{len(new_entries)} works from {', '.join(f'{s} {y}' for s, y in seasons)} saved at {CONFIG['path_historical_csv']}")
