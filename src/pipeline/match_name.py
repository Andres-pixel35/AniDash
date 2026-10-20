import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process
from src.pipeline import helpers

CONFIG = json.loads(Path("config.json").read_text())
final_csv = Path(CONFIG["path_final_csv"]).name

def normalize_string(s):
    """Remove special chars, extra spaces, lowercase"""
    s = str(s).lower().strip()
    s = re.sub(r'[^\w\s]', '', s)  # Remove punctuation
    s = re.sub(r'\s+', ' ', s)      # Collapse multiple spaces
    return s

def match_dfs(df1, df2, similarity_threshold=85):
    # Pre-normalize df2 once 
    df2 = df2.copy()
    df2['name_norm'] = df2['title'].apply(normalize_string)
    df2['name_en_norm'] = df2['english_title'].apply(normalize_string)
    df2['type_norm'] = df2['type'].astype(str).str.strip().str.lower()
    
    # Build hash maps for exact matches: {(name, type): row_index}. Normalizing drops punctuation, so "K-ON!" and
    # "K-ON!!" become the same name: the lowercase titles with punctuation are tried first, the normalized ones after
    raw_match_dict, exact_match_dict = {}, {}
    for idx, row in df2.iterrows():
        type_val = row['type_norm']
        # Store by both names
        for col in ['title', 'english_title']:
            raw_match_dict[(str(row[col]).lower().strip(), type_val)] = idx
        exact_match_dict[(row['name_norm'], type_val)] = idx
        exact_match_dict[(row['name_en_norm'], type_val)] = idx
    
    matched_rows = []
    unmatched_rows = []
    unmatched_titles = []
    
    # Phase 1: Exact matching
    for idx, row in df1.iterrows():
        media_type = str(row.iloc[1]).strip().lower()
        
        # Skip if type not in mappings
        if media_type not in CONFIG["type_mappings"]:
            unmatched_titles.append(f"{row.iloc[0]} (unknown type: {row.iloc[1]})")
            continue
            
        identifier_raw = str(row.iloc[0]).lower().strip()
        identifier_norm = normalize_string(row.iloc[0])
        allowed_types = CONFIG["type_mappings"][media_type]
        
        # Try exact match for each allowed type
        found = False
        for match_dict, identifier in [(raw_match_dict, identifier_raw), (exact_match_dict, identifier_norm)]:
            for allowed_type in allowed_types:
                key = (identifier, allowed_type)
                if key in match_dict:
                    matched_rows.append(df2.loc[match_dict[key]])
                    found = True
                    break
            if found:
                break
        
        if not found:
            unmatched_rows.append((idx, row, identifier_norm, allowed_types))
    
    # Phase 2: Fuzzy matching for unmatched rows only
    # two of your works can't be the same one, so the works already matched are left out
    matched_ids = {r['anime_id'] for r in matched_rows}
    for idx, row, identifier_norm, allowed_types in unmatched_rows:
        # Filter df2 by allowed types
        type_matches = df2[df2['type_norm'].isin(allowed_types) & ~df2['anime_id'].isin(matched_ids)]

        # best of the romaji and english title for each candidate, the first one wins a tie
        scores = np.maximum(*(process.cdist([identifier_norm], type_matches[col], scorer=fuzz.ratio, dtype=np.float64)[0]
                              for col in ['name_norm', 'name_en_norm']))

        if len(scores) and scores.max() >= similarity_threshold:
            matched_rows.append(type_matches.iloc[scores.argmax()])
            matched_ids.add(matched_rows[-1]['anime_id'])
        else:
            unmatched_titles.append(row.iloc[0])
    
    # Create result dataframe (only df2 columns)
    df_result = pd.DataFrame(matched_rows).reset_index(drop=True)
    
    # Drop temporary normalization columns
    if not df_result.empty:
        df_result = df_result.drop(columns=['name_norm', 'name_en_norm', 'type_norm'])
    
    return df_result, unmatched_titles

def main():
    df1 = pd.read_csv(CONFIG["path_user_csv"])
    df2 = pd.read_csv(CONFIG["path_historical_csv"])

    df, unmatched_titles = match_dfs(df1, df2)

    if CONFIG["show_unmatched"]:
        if unmatched_titles:
            print("\n--- Unmatched Anime ---")
            for title in unmatched_titles:
                print(f"- {title}")
        else:
            print("All your Anime were successfully matched")

    if df.empty:
        print(f"None of the works in your csv could be matched, {final_csv} was not created")
        return

    df["complete_duration"] = df["duration"] * df["episodes"]

    df = helpers.sort_final(df, CONFIG["sort_final"])

    helpers.save_csv(df, CONFIG["path_final_csv"])
    print(f"\n{final_csv} was successfully created at {CONFIG['path_final_csv']}")

if __name__ == "__main__":
    main()


