import json
import sys
from pathlib import Path
import pandas as pd
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())
final_csv = Path(CONFIG["path_final_csv"]).name

def update_rows(df_f, df_src):
    """
    the rows of df_f that are in df_src get df_src's information, matched by column name so the column order of the
    files doesn't matter. A column final.csv has and df_src lacks raises a KeyError instead of being left stale
    """

    src = df_src.assign(complete_duration=df_src["duration"] * df_src["episodes"]).set_index("anime_id")
    mask = df_f["anime_id"].isin(src.index)

    updated = src.loc[df_f.loc[mask, "anime_id"]].reset_index().set_axis(df_f.index[mask])[df_f.columns]
    # concat instead of .loc assignment: a NaN coming into an int column upcasts it instead of raising
    return pd.concat([df_f[~mask], updated]).sort_index()

def no_longer_airing(df_f, df_a, df_h):
    """
    rows of df_h for the works df_f still has as RELEASING or NOT_YET_RELEASED that are not in df_a, most likely because
    they finished airing or their release moved
    """

    pending = df_f["status"].isin(["RELEASING", "NOT_YET_RELEASED"])
    ids = df_f.loc[pending & ~df_f["anime_id"].isin(df_a["anime_id"]), "anime_id"]
    return df_h[df_h["anime_id"].isin(ids)]

if __name__ == "__main__":
    df_a = pd.read_csv(CONFIG["path_modified_airing"])
    df_h = pd.read_csv(CONFIG["path_historical_csv"])
    df_f = pd.read_csv(CONFIG["path_final_csv"])

    # --all: every entry gets anime.csv's information
    if "--all" in sys.argv[1:]:
        df_f = update_rows(df_f, df_h)
    else:
        df_f = update_rows(df_f, df_a)
        df_f = update_rows(df_f, no_longer_airing(df_f, df_a, df_h))
    df_f = helpers.sort_final(df_f, CONFIG["sort_final"])

    helpers.save_csv(df_f, CONFIG["path_final_csv"])
    print(f"{final_csv} was successfully updated")
