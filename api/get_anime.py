import json
from pathlib import Path
from questionary import Style, select, confirm
import pandas as pd
from src.pipeline import helpers
from api import anilist

CONFIG = json.loads(Path("config.json").read_text())
blue_style = Style.from_dict(CONFIG["blue_style"])

df1 = pd.read_csv(CONFIG["path_historical_csv"])

title = input("Enter the title of the work you want to fetch: ")
work_type = select(
    "Select its type: ",
    choices=CONFIG["valid_type"],
    style=blue_style,
    qmark="💠",
).ask()

if title.strip() and work_type:
    new_entry = anilist.fetch_anime_info(title, work_type)
    if len(new_entry) > 1:
        # AniList has no seasonYear for ONAs/specials, fall back to the start_date year
        new_entry = helpers.fill_season_year(new_entry)
        years = new_entry["season_year"].astype("Int64")
        labels = [
            f"{r.title} ({r.english_title}) - {y} - id {r.anime_id}"
            for r, y in zip(new_entry.itertuples(), years)
        ]
        picked = select("Several works match, which one do you want?", choices=labels, style=blue_style).ask()
        new_entry = new_entry.iloc[[labels.index(picked)] if picked else []]
    if len(new_entry) != 0:
        # first check that this anime does not exists already in anime.csv
        title_val = new_entry["title"].item()
        type_val = new_entry["type"].item()
        id_val = new_entry["anime_id"].item()
        is_duplicate = (df1["anime_id"] == id_val).any()

        should_write = not is_duplicate
        success_msg = f"{title_val.title()} ({type_val.lower()}) was successfully added to anime.csv"

        if is_duplicate:
            should_write = confirm(
                f"{title_val.title()} ({type_val.lower()}) already exists in anime.csv, do you want to replace it?",
                default=False
            ).ask()
            success_msg = f"{title_val.title()} ({type_val.lower()}) was successfully replaced in anime.csv"

        if should_write:
            # the new entry replaces the old one, if any
            df = helpers.merge(df1, helpers.clean(new_entry).astype(df1.dtypes))

            helpers.save_csv(df, CONFIG["path_historical_csv"])
            print(success_msg)
        else:
            print(f"{title_val.title()} ({type_val.lower()}) already exists in anime.csv")
else:
    print("You either didn't enter a title or didn't select a type.")

