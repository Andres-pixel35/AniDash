import json
from pathlib import Path
import pandas as pd
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())
final_csv = Path(CONFIG["path_final_csv"]).name

def update_airing(df_f, df_a):
    """
    the rows of df_f that are in df_a get df_a's information, matched by column name so the column order of the files
    doesn't matter. A column final.csv has and airing_anime_M.csv lacks raises a KeyError instead of being left stale
    """

    airing = df_a.assign(complete_duration=df_a["duration"] * df_a["episodes"]).set_index("anime_id")
    mask = df_f["anime_id"].isin(airing.index)

    updated = airing.loc[df_f.loc[mask, "anime_id"]].reset_index().set_axis(df_f.index[mask])[df_f.columns]
    # concat instead of .loc assignment: a NaN coming into an int column upcasts it instead of raising
    return pd.concat([df_f[~mask], updated]).sort_index()

if __name__ == "__main__":
    df_a = pd.read_csv(CONFIG["path_modified_airing"])
    df_f = pd.read_csv(CONFIG["path_final_csv"])

    df_f = helpers.sort_final(update_airing(df_f, df_a), CONFIG["sort_final"])

    helpers.save_csv(df_f, CONFIG["path_final_csv"])
    print(f"{final_csv} was successfully updated")
