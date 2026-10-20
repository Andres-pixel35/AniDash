import re
import unicodedata
import joblib
import numpy as np
import pandas as pd
import streamlit as st
from api import anilist
from dashboard.data import _parse_staff, _split
from src.pipeline import helpers

# trained in the predict_anime_score repo; unpickling it needs anime_transformers.py at the root of this repo
MODEL_PATH = "model/pipe.pkl"
# error of the model on the 2026 works it never saw, in score points
TEST_RMSE = 7.28
# columns, in order, of the clean csv the model was trained with (predict_anime_score/notebooks/clean.ju.py)
FEATURES = [
    "type", "episodes", "episode_duration_min", "source", "release_season", "release_year", "main_staff",
    "is_adult", "main_studios", "genres", "tags", "has_english_title", "n_streaming_sites", "n_studios_involved",
]
LIST_FEATURES = ["main_staff", "main_studios", "genres", "tags"]
# music videos are left out, the model never saw one
TYPES = ["TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL"]
# the sources AniList reports by default and the model saw; a missing one is UNKNOWN, as in training
SOURCES = ["MANGA", "ORIGINAL", "LIGHT_NOVEL", "VISUAL_NOVEL", "VIDEO_GAME", "OTHER", "UNKNOWN"]
REQUIRED = ["type", "source", "episodes", "season", "season_year", "has_english_title", "is_adult"]
# AniList lists staff by relevance, the training data kept about the first five
N_STAFF = 5
LIST_FIELDS = ["genres", "tags", "studios", "main_studios", "main_staff", "streaming_sites"]
BLANK = {field: None for field in REQUIRED + ["duration"]} | {field: [] for field in LIST_FIELDS}


def clean_string(name):
    """'Slice of Life' -> 'sliceoflife', the same normalization the training data got"""
    name = unicodedata.normalize("NFKC", name).lower()
    return re.sub(r"[\W_]+", "", name)


def clean_names(names):
    """normalized, deduplicated and sorted names, the ones left empty are dropped"""
    return sorted({clean_string(n) for n in names} - {""})


def invalid_names(names):
    """names the normalization would leave empty, they have no letter or digit"""
    return [n for n in names if not clean_string(n)]


@st.cache_data(ttl=3600, show_spinner="Searching AniList...")
def fetch(title, work_type):
    """up to 10 AniList matches cleaned like the pipeline cleans fetched works, empty when nothing matched.
    Raises when AniList can't be reached"""
    medias = anilist.post(anilist.SEARCH_QUERY,{"search": title, "format": work_type}).get("media") or []
    if not medias:
        return pd.DataFrame()

    df = pd.DataFrame([anilist.build_row(m) for m in medias])
    # the training data counted every external link (official site, socials...), not only the streaming ones
    df["streaming_sites"] = [anilist.join(list(dict.fromkeys(l["site"] for l in m["externalLinks"]))) for m in medias]
    return helpers.fill_season(helpers.fill_season_year(helpers.clean_invalid(df)))


def _int(value):
    return None if pd.isna(value) else int(value)


def from_anilist(row):
    """a row of fetch -> work, the dict both the search and the manual entry fill"""
    return {
        "type": row["type"],
        "source": row["source"] if row["source"] in SOURCES else "UNKNOWN",
        "episodes": _int(row["episodes"]),
        "duration": _int(row["duration"]),
        "season": None if pd.isna(row["season"]) else row["season"],
        "season_year": _int(row["season_year"]),
        "has_english_title": bool(pd.notna(row["english_title"])),
        "is_adult": bool(row["is_adult"]),
        "main_staff": list(dict.fromkeys(name for name, _ in _parse_staff(row["main_staff"])[:N_STAFF])),
    } | {field: _split(row[field]) for field in LIST_FIELDS if field != "main_staff"}


def missing(work):
    return [field for field in REQUIRED if work[field] is None]


def _joined(names):
    return ";".join(names) or np.nan


def to_features(work):
    """work -> the one row DataFrame the model expects, transformed like clean.ju.py does"""
    row = {
        "type": work["type"],
        "episodes": float(work["episodes"]),
        "episode_duration_min": np.nan if work["duration"] is None else float(work["duration"]),
        "source": work["source"],
        "release_season": work["season"],
        "release_year": float(work["season_year"]),
        "main_staff": _joined(clean_names(work["main_staff"])),
        "is_adult": int(work["is_adult"]),
        "main_studios": _joined(clean_names(work["main_studios"])),
        # hentai was dropped in training, is_adult carries the same information
        "genres": _joined([g for g in clean_names(work["genres"]) if g != "hentai"]),
        "tags": _joined(clean_names(work["tags"])),
        "has_english_title": int(work["has_english_title"]),
        "n_streaming_sites": len(clean_names(work["streaming_sites"])),
        "n_studios_involved": len(clean_names(work["studios"])),
    }
    # object, so a list column that is only nan still works with the encoders' .str
    return pd.DataFrame([row], columns=FEATURES).astype({col: object for col in LIST_FEATURES})


@st.cache_resource
def model():
    return joblib.load(MODEL_PATH)


def predict(work):
    return float(np.clip(model().predict(to_features(work))[0], 0, 100))


@st.cache_data(show_spinner=False)
def suggestions(path):
    """names seen in the historical csv for each list field, most common first"""
    raw = pd.read_csv(path, usecols=LIST_FIELDS)
    out = {field: raw[field].map(_split).explode().dropna().value_counts().index.tolist()
           for field in LIST_FIELDS if field != "main_staff"}
    staff = raw["main_staff"].map(lambda v: [name for name, _ in _parse_staff(v)]).explode().dropna()
    out["main_staff"] = staff.value_counts().index.tolist()
    return out


if __name__ == "__main__":
    assert clean_names(["Slice of Life", "slice-of-life", "  ", "Kyoto Animation"]) == ["kyotoanimation", "sliceoflife"]
    assert invalid_names(["MAPPA", "!!"]) == ["!!"]
    features = to_features(BLANK | {"type": "TV", "source": "MANGA", "episodes": 12, "season": "FALL",
                                    "season_year": 2026, "has_english_title": True, "is_adult": False,
                                    "genres": ["Hentai", "Action"], "streaming_sites": ["Bilibili TV", "bilibili tv"]})
    assert features["genres"].item() == "action" and features["n_streaming_sites"].item() == 1
    assert pd.isna(features["main_staff"].item()) and pd.isna(features["episode_duration_min"].item())
    print("ok", predict(BLANK | {"type": "TV", "source": "MANGA", "episodes": 12, "season": "FALL",
                                 "season_year": 2026, "has_english_title": True, "is_adult": False}))
