import json
from pathlib import Path
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())

df = helpers.read_csv(CONFIG["path_original_airing"])

# placeholders turn into null, then episodes, season_year and season are filled where possible (notes/fillin.md)
df = helpers.clean(df)

# merge with nothing: the dates get the same YYYY-MM-DD format and order as anime.csv
df = helpers.merge(None, df)

helpers.save_csv(df, CONFIG["path_modified_airing"])
print(f"\nairing_anime.csv succesfully saved at {CONFIG['path_modified_airing']}.")
