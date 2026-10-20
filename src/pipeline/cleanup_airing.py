import json
from pathlib import Path
import pandas as pd
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())

df = pd.read_csv(CONFIG["path_original_airing"])

df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")

# placeholders turn into null, then episodes, season_year and season are filled where possible (notes/fillin.md)
df = helpers.clean(df)

df = helpers.sort_by_date(df)

helpers.save_csv(df, CONFIG["path_modified_airing"])
print(f"\nairing_anime.csv succesfully saved at {CONFIG['path_modified_airing']}.")
