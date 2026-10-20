import json
from pathlib import Path
import pandas as pd
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())

df1 = pd.read_csv(CONFIG["path_historical_csv"])
df2 = pd.read_csv(CONFIG["path_modified_airing"])
# the works of the next season stay out of anime.csv until their season starts
df2 = helpers.filter_season(df2)

# I keep the information from df2 because is the one with the update information
df = helpers.merge(df1, df2)

helpers.save_csv(df, CONFIG["path_historical_csv"])
print(f"\nanime.csv was succesfully saved at {CONFIG['path_historical_csv']}")
