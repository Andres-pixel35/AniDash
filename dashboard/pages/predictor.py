import json
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st
from dashboard import components as ui, predict
from dashboard.data import _pretty
from src.pipeline.helpers import SEASON_NAMES

CONFIG = json.loads(Path("config.json").read_text())
SEARCH, MANUAL = "Search AniList", "Enter manually"
# one manual step per field: (field, short label, question, guidance)
STEPS = [
    ("type", "Format", "What format is it?",
     "As AniList lists it. Music videos can't be predicted, the model never saw one."),
    ("source", "Source material", "What is it based on?",
     "If AniList shows a more specific source (novel, web novel, doujinshi...) pick the closest one or Other."),
    ("episodes", "Episodes", "How many episodes will it have?",
     "Movies have 1. If it hasn't been announced, use your best guess: most TV seasons have 12 or 13."),
    ("duration", "Minutes per episode", "How long is each episode, in minutes?",
     "Leave it empty if you don't know, the model fills it with the usual length of its format."),
    ("season", "Season", "In which season does it start?",
     "Winter is January to March, Spring April to June, Summer July to September and Fall October to December."),
    ("season_year", "Year", "In which year does it start?", "The year of that season."),
    ("has_english_title", "English title", "Does it have an official English title?",
     "Only an English title shown on its AniList page counts."),
    ("is_adult", "Adult", "Is it adult (18+) content?", "Only hentai is adult on AniList, ecchi works are not."),
    ("genres", "Genres", "Which genres does it have?", "AniList genres, pick every one that applies."),
    ("tags", "Tags", "Which tags does it have?",
     "AniList tags, the most used first. Only the common ones weigh in the model, so there's no need to add them all."),
    ("studios", "Studios involved", "Which companies are involved?",
     "Everything listed under **Studios** and **Producers** on the AniList page: the animation studios plus "
     "producers and licensors. Only how many there are is used. Type a name to add one that isn't in the list."),
    ("main_studios", "Main studios", "Which of them are the main studios?",
     "The ones listed under **Studios** on the AniList page (not under Producers), usually a single animation studio."),
    ("main_staff", "Top staff", "Who are its top 5 staff?",
     "The first five people of the **Staff** section on AniList, usually the original creator, director, series "
     "composition, character design and music. Type a name to add one that isn't in the list."),
    ("streaming_sites", "External links", "Which external links does it have?",
     "Every link under **External & Streaming links** on AniList: streaming sites, but also the official site and "
     "social accounts, the model was trained counting all of them. Only how many there are is used."),
]
LABELS = {field: label for field, label, _, _ in STEPS}

st.session_state.setdefault("pred_mode", SEARCH)
st.session_state.setdefault("pred_work", dict(predict.BLANK))
st.session_state.setdefault("pred_step", 0)


def describe(field, value):
    if value is None:
        return "Don't know" if field == "duration" else "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(value) or "None"
    return _pretty(value) if isinstance(value, str) else str(value)


def show_prediction(work, current=None):
    """predicted score with its typical error; current is the mean score the work already has on AniList"""
    score = predict.predict(work)
    low, high = max(score - predict.TEST_RMSE, 0), min(score + predict.TEST_RMSE, 100)
    cards = [("Predicted score", f"{score:.0f}", f"Most likely between {low:.0f} and {high:.0f}")]
    if current is not None:
        cards.append(("Mean score on AniList now", f"{current:.0f}", f"{current - score:+.0f} points off the prediction"))
    ui.kpis(cards, per_row=2)
    with st.expander("What the model received"):
        st.dataframe(predict.to_features(work).T.astype(str).rename(columns={0: "Value"}), width="stretch")


def go_manual(work):
    """open the manual entry with work filled in, at its first missing step"""
    st.session_state.pred_work = work
    missing = predict.missing(work)
    fields = [field for field, *_ in STEPS]
    st.session_state.pred_step = fields.index(missing[0]) if missing else len(STEPS)
    st.session_state.pred_mode = MANUAL


def start_over():
    st.session_state.pred_work = dict(predict.BLANK)
    st.session_state.pred_step = 0


def ask(field, question, value):
    """the single input of a manual step, starting at value"""
    key = f"pred_in_{field}"
    if field in ("type", "source", "season"):
        options = {"type": predict.TYPES, "source": predict.SOURCES, "season": SEASON_NAMES}[field]
        return st.segmented_control(question, options, default=value, key=key,
                                    format_func=lambda v: "Don't know" if v == "UNKNOWN" else _pretty(v))
    if field in ("has_english_title", "is_adult"):
        return st.segmented_control(question, [True, False], default=value, key=key,
                                    format_func=lambda v: "Yes" if v else "No")
    if field == "episodes":
        return st.number_input(question, min_value=1, max_value=2000, step=1, value=value, key=key)
    if field == "duration":
        return st.number_input(question, min_value=1, max_value=240, step=1, value=value, key=key,
                               placeholder="Don't know")
    if field == "season_year":
        return st.number_input(question, min_value=1940, max_value=date.today().year + 5, step=1,
                               value=value or date.today().year, key=key)

    work = st.session_state.pred_work
    if field == "main_studios":
        options = work["studios"]
        if not options:
            st.info("No studios were entered in the previous step, go back to add them or continue without any.",
                    icon=":material/info:")
        # a studio removed from the previous step can't stay as main
        return st.multiselect(question, options, default=[s for s in value if s in options], key=key)
    # what the work already has goes first, so it is always a valid option
    options = list(dict.fromkeys(value + predict.suggestions(CONFIG["path_historical_csv"])[field]))
    return st.multiselect(question, options, default=value, key=key,
                          accept_new_options=field in ("studios", "main_staff", "streaming_sites"),
                          max_selections=predict.N_STAFF if field == "main_staff" else None)


def error_in(field, value):
    if value is None and field in predict.REQUIRED:
        return "This one is needed to predict, pick or enter a value."
    bad = predict.invalid_names(value) if isinstance(value, list) else []
    if bad:
        return f"{', '.join(bad)} has no letters or digits, remove it."
    return None


ui.hero("Lab", "Score predictor", "Estimate the AniList mean score (0-100) of a work before it airs, from what is "
        "known about it in advance.", [f"Typical error ±{predict.TEST_RMSE:.0f} points",
                                       "Trained on finished Japanese works up to 2025"])

mode = st.segmented_control("How do you want to enter the work?", [SEARCH, MANUAL], required=True, key="pred_mode")

if mode == SEARCH:
    with st.form("pred_search"):
        title = st.text_input("Title", placeholder="e.g. Sousou no Frieren")
        work_type = st.segmented_control("Format", predict.TYPES, default="TV", required=True, format_func=_pretty)
        st.caption("Music videos can't be predicted, the model never saw one.")
        if st.form_submit_button("Search", icon=":material/search:"):
            st.session_state.pred_query = (title.strip(), work_type)

    query = st.session_state.get("pred_query")
    if not query:
        st.stop()
    if not query[0]:
        st.warning("Enter a title to search for.", icon=":material/warning:")
        st.stop()
    try:
        matches = predict.fetch(*query)
    except Exception as e:
        st.error(f"AniList couldn't be reached, try again in a minute. {e}", icon=":material/error:")
        st.stop()
    if matches.empty:
        st.info(f"No {_pretty(query[1])} on AniList matches '{query[0]}'. Check the title and format, or enter it "
                "manually.", icon=":material/search_off:")
        st.stop()

    row = matches.iloc[0]
    if len(matches) > 1:
        labels = [f"{r.title} ({r.english_title if pd.notna(r.english_title) else 'no English title'}) - "
                  f"{f'{r.season_year:.0f}' if pd.notna(r.season_year) else 'no year'} - id {r.anime_id}"
                  for r in matches.itertuples()]
        picked = st.selectbox("Several works match, which one do you want?", range(len(labels)),
                              format_func=labels.__getitem__, key=f"pred_pick_{query}")
        row = matches.iloc[picked]

    work = predict.from_anilist(row)
    st.markdown(f"#### {ui.esc(row['title'])}")
    st.caption(" · ".join(describe(field, work[field]) for field in ["type", "season", "season_year", "source"])
               + f" · {_pretty(row['status'])}")
    if row["country_of_origin"] != "JP":
        st.warning("This work isn't Japanese and the model only saw Japanese works, take the prediction with a grain "
                   "of salt.", icon=":material/public:")

    missing = predict.missing(work)
    if missing:
        st.warning(f"AniList doesn't have enough information to predict it yet, it's missing: "
                   f"{', '.join(LABELS[f].lower() for f in missing)}. You can fill them in yourself.",
                   icon=":material/warning:")
    else:
        current = row["mean_score"] if row["status"] in ("FINISHED", "RELEASING") and pd.notna(row["mean_score"]) else None
        show_prediction(work, current)
    st.button("Complete it manually" if missing else "Adjust it manually", icon=":material/edit:",
              type="primary" if missing else "secondary", on_click=go_manual, args=(work,))
    st.stop()

work = st.session_state.pred_work
step = st.session_state.pred_step

if step < len(STEPS):
    field, label, question, guidance = STEPS[step]
    st.progress(step / len(STEPS), text=f"Step {step + 1} of {len(STEPS)} · {label}")
    with st.container(border=True):
        value = ask(field, question, work[field])
        st.caption(guidance)
        back, next_ = st.columns(2)
        if back.button("Back", icon=":material/arrow_back:", disabled=step == 0, width="stretch"):
            work[field] = value
            st.session_state.pred_step -= 1
            st.rerun()
        if next_.button("Next", icon=":material/arrow_forward:", type="primary", width="stretch"):
            error = error_in(field, value)
            if error:
                st.error(error, icon=":material/error:")
            else:
                work[field] = value
                st.session_state.pred_step += 1
                st.rerun()
    st.button("Start over", icon=":material/restart_alt:", on_click=start_over)
    st.stop()

ui.section("Your work", "Go back to change anything.")
st.dataframe(pd.DataFrame({"Field": list(LABELS.values()), "Value": [describe(f, work[f]) for f in LABELS]}),
             hide_index=True, width="stretch")
# a work sent from the search may still miss a field the user skipped past with Back
missing = predict.missing(work)
if missing:
    st.warning(f"Still missing: {', '.join(LABELS[f].lower() for f in missing)}.", icon=":material/warning:")
else:
    show_prediction(work)
back, again = st.columns(2)
if back.button("Back", icon=":material/arrow_back:", width="stretch"):
    st.session_state.pred_step -= 1
    st.rerun()
again.button("Start over", icon=":material/restart_alt:", on_click=start_over, width="stretch")
