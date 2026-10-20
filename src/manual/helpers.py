import pandas as pd
import re
from prompt_toolkit.completion import WordCompleter, ThreadedCompleter

def fast_completer(choices_list):
    """
    Creates a threaded, space-aware completer for large lists.
    """
    # This regex pattern treats the entire input line as a single word,
    # which is what allows spaces to be searched correctly.
    everything_pattern = re.compile(r"^.*$")

    # We wrap the WordCompleter in a ThreadedCompleter so 
    # the UI doesn't lag
    return ThreadedCompleter(
        WordCompleter(
            choices_list,
            ignore_case=True,
            match_middle=True,
            pattern=everything_pattern
        )
    )

def get_choices(df):
    """
    get a df and return a dict {label: anime_id}, the labels are the native and english titles plus its type, e.g.
    "Adachi to Shimamura (TV)". If the same label belongs to different works, their anime_id is added to tell them apart
    """
    ids_by_label = {}
    for _, row in df.iterrows():
        for name in (row["title"], row["english_title"]):
            if pd.notna(name):
                ids_by_label.setdefault(f"{name} ({row['type']})", set()).add(row["anime_id"])

    choices = {}
    for label, ids in ids_by_label.items():
        if len(ids) == 1:
            choices[label] = ids.pop()
        else:
            choices.update({f"{label} [{anime_id}]": anime_id for anime_id in ids})

    return choices
