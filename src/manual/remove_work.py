import json
import pandas as pd
from pathlib import Path
from questionary import Style, autocomplete, confirm
from src.manual import helpers
from src.pipeline.helpers import save_csv

CONFIG = json.loads(Path("config.json").read_text())
blue_style = Style.from_dict(CONFIG["blue_style"])
final_csv = Path(CONFIG["path_final_csv"]).name

df = pd.read_csv(CONFIG["path_final_csv"])

choices = helpers.get_choices(df)

completer = helpers.fast_completer(list(choices))

# ids of the works we intend to remove
ids_to_drop = set()
# List of titles (for visual confirmation at the end)
removed_titles = []

while True:
    answer = autocomplete(
        "Enter the title you want to remove (or type 'exit' to finish): ",
        choices=list(choices),
        completer=completer,
        style=blue_style,
        qmark="💠", 
    ).ask()

    if not answer or answer.lower() == 'exit':
        break

    anime_id = choices.get(answer)
    if anime_id is None:
        print("ERROR: You need to choose the work you want to remove, not just write it. Pleae try again.")
        continue

    # Ask for confirmation
    is_confirmed = confirm(
        f"Are you sure you want to remove {answer}?",
        default=False
    ).ask()

    if is_confirmed:
        ids_to_drop.add(anime_id)
        removed_titles.append(answer)
        print(f"Marked '{answer}' for removal.")
    else:
        print("Deletion canceled.")

# Finalize: Drop all marked rows at once
if ids_to_drop:
    df = df[~df["anime_id"].isin(ids_to_drop)]

    # removes file if there is no information to avoid errors with dashboard and remoce_work itself in the future
    if len(df) == 0:
        Path.unlink(CONFIG["path_final_csv"])
        print(f"\nSince you deleted all the information from {final_csv}, that file was also removed.")
    else:
        save_csv(df, CONFIG["path_final_csv"])
        print("\n--- Summary ---")
        print(f"Successfully removed {len(removed_titles)} items:")
        for title in removed_titles:
            print(f" - {title}")
else:
    print("No items were removed.")
