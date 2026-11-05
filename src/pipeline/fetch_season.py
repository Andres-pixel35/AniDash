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

df1 = helpers.read_csv(CONFIG["path_historical_csv"])

print(f"Fetching {', '.join(f'{s} {y}' for s, y in seasons)} from Anilist")
# plus the works of their years with only the year as start date
filters = [f for s in seasons for f in helpers.season_filters(*s)] + [helpers.year_only_filter(y) for y in {y for _, y in seasons}]
new_entries = pd.concat([anilist.fetch_media(f) for f in filters], ignore_index=True)
# most works match both the season and the start date filter
new_entries = new_entries.drop_duplicates(subset="anime_id", keep="last")

# same cleaning as the airing works. A new work starting in this season that AniList places in the next one waits for it
new_entries = helpers.filter_season(helpers.clean(new_entries), df1["anime_id"])

# the fetched works replace the ones already in anime.csv
df = helpers.merge(df1, new_entries)

helpers.save_csv(df, CONFIG["path_historical_csv"])
last_season.write_text(f"{current[0]} {current[1]}\n")
print(f"\n{len(new_entries)} works from {', '.join(f'{s} {y}' for s, y in seasons)} saved at {CONFIG['path_historical_csv']}")
