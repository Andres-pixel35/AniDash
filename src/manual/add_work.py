import json
from pathlib import Path
import pandas as pd
from questionary import Style, autocomplete
from src.manual import helpers
from src.pipeline.helpers import sort_final as sort_final_df, save_csv

CONFIG = json.loads(Path("config.json").read_text())
blue_style = Style.from_dict(CONFIG["blue_style"])
final_csv = Path(CONFIG["path_final_csv"]).name

final_path = Path(CONFIG["path_final_csv"])
final_exists = final_path.is_file() and final_path.stat().st_size > 0
df = pd.read_csv(CONFIG["path_historical_csv"])

if final_exists:
    final_df = pd.read_csv(CONFIG["path_final_csv"])

choices = helpers.get_choices(df)

completer = helpers.fast_completer(list(choices))

# ids already in final.csv or added in this session
seen = set(final_df["anime_id"]) if final_exists else set()

new_entries = []

while True:
    answer = autocomplete(
        "Enter the title (or type 'exit' to finish): ",
        choices=[], 
        completer=completer,
        style=blue_style,
        qmark="💠",
    ).ask()

    # Break condition
    if not answer or answer.lower() == 'exit':
        break

    anime_id = choices.get(answer)
    if anime_id is None:
        print("ERROR: You need to choose the work you want to add, not just write it. Pleae try again.")
        continue

    if anime_id in seen:
        print(f"'{answer}' is already in your list!")
        continue

    # Grab the data from the source dataframe
    match = df[df["anime_id"] == anime_id].copy()

    if not match.empty:
        # Calculate duration and add to our temporary session list
        match["complete_duration"] = match["duration"] * match["episodes"]
        new_entries.append(match)
        seen.add(anime_id)
        print(f"Added: {answer}")

# Batch add everything at once
if new_entries:
    # Combine existing data (if any) with the new session entries
    final_df = pd.concat(([final_df] if final_exists else []) + new_entries, ignore_index=True)

    final_df = sort_final_df(final_df, CONFIG["sort_final"])

    save_csv(final_df, CONFIG["path_final_csv"])
    print("\n--- Summary ---")
    print(f"Success! {len(new_entries)} new rows saved to {final_csv}.")
else:
    print("No new changes to save.")
