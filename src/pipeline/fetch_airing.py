import json
from pathlib import Path
import pandas as pd
from api import anilist
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())

# every releasing work, no matter when it started, plus the ones yet to release from the current and next season and
# the ones with only the current year as start date
seasons = [helpers.season_offset(0), helpers.season_offset(1)]
pending = [f for s in seasons for f in helpers.season_filters(*s)] + [helpers.year_only_filter(seasons[0][1])]
filters = ["status: RELEASING"] + [f"{f}, status: NOT_YET_RELEASED" for f in pending]

print(f"Fetching every releasing work and the ones yet to release from {', '.join(f'{s} {y}' for s, y in seasons)} "
      f"or with only {seasons[0][1]} as start date")
df = pd.concat([anilist.fetch_media(f) for f in filters], ignore_index=True)

# works anime.csv still has as airing that are not in the fetch anymore (finished, cancelled, on hiatus) are refetched
# once, so their final status, episodes and scores reach anime.csv. The ones on hiatus are refetched every day, since
# they can be cancelled without releasing again
anime = pd.read_csv(CONFIG["path_historical_csv"], usecols=["anime_id", "status"])
pending = anime["status"].isin(["RELEASING", "NOT_YET_RELEASED", "HIATUS"])
left = anime.loc[pending & ~anime["anime_id"].isin(df["anime_id"]), "anime_id"]
if len(left):
    print(f"Refetching {len(left)} works that are no longer airing")
    df = pd.concat([df, anilist.fetch_media(f"id_in: [{', '.join(map(str, left))}]")], ignore_index=True)

# a work may change its status between requests and come twice
df = df.drop_duplicates(subset="anime_id", keep="last")

helpers.save_csv(df, CONFIG["path_original_airing"])
print(f"\n{len(df)} works saved at {CONFIG['path_original_airing']}")
