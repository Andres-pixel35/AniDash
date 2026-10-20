<div align="center">

# AniDash

![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
[![Data from AniList](https://img.shields.io/badge/Data-AniList-02A9FF?style=flat-square&logo=anilist&logoColor=white)](https://anilist.co)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue?style=flat-square)](LICENSE)

Turn the list of anime you have watched into an interactive dashboard.

[Overview](#overview) • [Getting started](#getting-started) • [Usage](#usage) • [Dashboard](#dashboard) • [Configuration](#configuration) • [Data](#data)

</div>

## Overview

You give AniDash a CSV with the titles you have watched and their format. It matches every one against a database of more
than 14,000 anime released since 1969 (`anime.csv`) and builds your own dataset (`final.csv`) with the start date, season,
episodes, duration, studios, staff, genres, tags, AniList scores and community numbers of each work. A Streamlit dashboard
then shows what your taste looks like, how much time you gave to anime, how your list compares with AniList users and what
is airing right now, and it can estimate the AniList score of any work.

See it live with my own list at **[here](https://anidash.streamlit.app)**.

### Features

- **Fuzzy matching** of your titles, romaji or English, against the whole database.
- **A CLI menu** to sync your list, add or remove works with autocomplete and fetch missing works from AniList.
- **A daily updated database**, with the airing works and the current season refreshed by GitHub Actions.
- **Nine dashboard pages** with sidebar filters that apply to all of them.
- **A score predictor** trained on the AniList data.

## Getting started

### Prerequisites

- [Python 3.13](https://www.python.org/downloads/)
- One of [uv](https://docs.astral.sh/uv/), pip or [conda](https://docs.conda.io/)
- A Bash shell to run `main.sh`

### Installation

Clone the repository:

```bash
git clone https://github.com/Andres-pixel35/Anime-dashboard.git
cd Anime-dashboard
```

Then create the environment with whichever tool you prefer.

<details open>
<summary><strong>uv</strong></summary>

```bash
uv venv --python 3.13 .venv
uv pip install -r requirements.txt
```

</details>

<details>
<summary><strong>pip</strong></summary>

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>conda</strong></summary>

```bash
conda env create -f conda/environment.yml
```

This creates an environment called `anidash`. `main.sh` looks for `.venv/` by default, so open it and follow the comments:
replace the `.venv` block at the top with `conda activate anidash` (sourcing your `conda.sh` before it) and `deactivate` in
`shutdown` with `conda deactivate`.

</details>

uv and pip create the environment in `.venv/`, which `main.sh` activates on its own every time you run it.

> [!IMPORTANT]
> Read `main.sh` before running it. I encourage you to always check what you are about to execute.

### Your list

The repository comes with my own list (`data/user/works.csv` and `data/final/final.csv`), replace them with yours.

Put your list at `data/user/works.csv` (or wherever `path_user_csv` points). It must be a CSV with exactly **two columns**
in this order: `title` and `type`. The header names don't matter, only the order.

```csv
title,type
Sousou no Frieren,tv
Kimi no Na wa.,movie
```

- The title can be the romaji or the English one, small differences in spelling are matched too.
- The type tells a series and a movie with the same name apart. The accepted types are the keys of `type_mappings` in
  `config.json`, add your own there if your list uses other words (see [Configuration](#configuration)).

> [!TIP]
> You don't need a CSV at all: start from scratch and add works one by one with **Add work**.

## Usage

Run the menu:

```bash
./main.sh
```

Or go straight to an option by passing its number:

```bash
./main.sh 4
```

**Update final** skips its menu when run this way: `./main.sh 6` updates the airing works, and `--all` updates every work
on your list:

```bash
./main.sh 6 --all
```

| # | Option | What it does |
|---|--------|--------------|
| 1 | **Sync your csv** | Matches your list with `anime.csv` and creates `final.csv` with the full information of every match. Exact titles are matched first (with their punctuation, so `K-ON!` and `K-ON!!` stay apart), then the closest one (85% similarity or more) among the formats your type allows, leaving out the works already matched. The titles left unmatched are printed at the end. |
| 2 | **Add work** | Adds works to `final.csv` one by one, with autocomplete over every title in `anime.csv`. Works already on your list are skipped. |
| 3 | **Remove work** | Removes works from `final.csv`, with autocomplete and a confirmation for each one. |
| 4 | **Dashboard** | Launches the dashboard at `http://localhost:8501`, stop it with `ctrl + c`. You can also run `streamlit run streamlit_app.py`. |
| 5 | **Update airing** | Fetches from AniList every work releasing now, plus the ones yet to release from this and next season (Japanese, Chinese and Korean), cleans them and merges them into `anime.csv`. Works from next season only reach `anime.csv` once their season starts, and works that stopped airing are fetched one last time so their final episodes and scores are kept. |
| 6 | **Update final** | Brings the latest information into `final.csv`, choose how (or go back to the menu): **Airing works** takes the episodes, scores and community numbers of the airing works on your list from `airing_anime_M.csv`, and the works still releasing or yet to release on your list that are no longer airing (finished, cancelled or postponed) from `anime.csv`. **Every work** takes every work on your list from `anime.csv`. |
| 7 | **Fetch from AniList** | Looks up a work on AniList by title and format and adds it to `anime.csv`, or replaces it if it is already there. Use it for works missing from the database. |
| 8 | **Exit** | Closes the program. |

> [!NOTE]
> `anime.csv` in this repository is updated every day by a GitHub Action (option 5) and every Monday with the whole
> current season, so a `git pull` is usually enough to have the latest works.

## Dashboard

Every page except the score predictor reads `final.csv`. The sidebar filters (release year and season, format, genres,
tags, source, studios, episodes, score...) apply to every page, and you can prefer English titles over romaji. Tables let
you select a row to see the whole work: dates, studios, staff, streaming sites, synopsis and a link to AniList.
Scores are the ones from AniList.

| Page | What you get |
|------|--------------|
| **Overview** | Headline numbers (works, episodes, hours, average score), your most common traits, works by release year, formats, top genres, score distribution and the standouts of your list. |
| **Timeline** | Works and hours per period, average score through time, a season calendar, your oldest and newest works and the ones still airing. |
| **Scores** | Score distribution and bands, what scores higher by format, source, season, decade, length or studio, average score by genre, score against popularity and your top and bottom 10. |
| **Genres & Studios** | Genres (frequency, mix by decade, pairs that go together), tags, sources, studios (most watched, hours, quality against quantity) and the people behind your works by role. |
| **Watch time** | Biggest time sinks, episodes by format and whether the long works were worth it. |
| **Community** | Your list against AniList users: popularity against favorites, the most dropped and most loved works, completion rate by format and the hidden gems of your list. |
| **Explorer** | Every work on your list in a table, choose the columns, sort them and download it as CSV. |
| **Airing** | What is airing now, and what this and next season bring, sorted by popularity with links to AniList. |
| **Score predictor** | Estimates the AniList mean score of a work. Search it on AniList, or enter it step by step (format, source, episodes, season, studios, staff, genres, tags...) for a work that isn't there yet. |

### Score predictor

The predictor uses a machine learning model trained on the AniList data, its typical error is about 7 points (on a 0-100
scale) on works it never saw. To see how it was trained head over to
[predict-anime-score](https://github.com/Andres-pixel35/predict-anime-score).

> [!WARNING]
> The model lives in `model/pipe.pkl` and needs `anime_transformers.py` to load, so keep that file at the root of the
> repository.

## Configuration

Every setting lives in `config.json`.

| Key | What it does |
|-----|--------------|
| `user_name` | Your name, shown in the dashboard's title. |
| `path_user_csv` | Your list, the input of **Sync your csv**. |
| `path_original_airing` | The airing works as they come from AniList. |
| `path_modified_airing` | The airing works once cleaned, used by **Update final** and the **Airing** page. |
| `path_historical_csv` | The anime database, `anime.csv`, also used by **Update final**. |
| `path_final_csv` | Your dataset, the one the dashboard reads. |
| `path_last_season` | The last season fetched, so the first fetch of a new season also refetches the previous one. |
| `sort_final` | How `final.csv` is sorted: `"date"`, `"title"`, or `null` to keep the order the works were added. |
| `show_unmatched` | `false` hides the titles **Sync your csv** couldn't match. |
| `valid_type` | Every format AniList uses, the choices of **Fetch from AniList**. |
| `type_mappings` | The types your CSV can use, and the formats each one may match. `"movie": ["movie", "ona", "ova"]` means a work tagged `movie` is looked for among movies, then ONAs, then OVAs. If your CSV says `serie` instead of `tv`, rename the `tv` key to `serie` (or add it). |
| `blue_style` | The colors of the prompts of **Add work**, **Remove work** and **Fetch from AniList**, as a [questionary style](https://questionary.readthedocs.io/en/stable/pages/advanced.html#themes-styling): `qmark` is the icon before the question, `question` the question, `answer` your answer once you press enter, `pointer` the arrow in lists, `highlighted` the hovered choice, `selected` the chosen one, `text` what you type, and `completion-menu.*` the autocomplete dropdown. |

## Data

`anime.csv` started as the dataset of [LeoRigasaki](https://github.com/LeoRigasaki). Since then it is maintained here: it
is cleaned, kept up to date from AniList and has some works added by hand.

- Placeholder values (such as `0` episodes) are turned into nulls and nothing is imputed, see
  [notes/fillin.md](notes/fillin.md) for every rule.
- The works added by hand are listed in [notes/added_manually.txt](notes/added_manually.txt).

### Project structure

```text
.
├── .github/workflows/    # daily airing update and weekly season fetch
├── .streamlit/           # dashboard theme
├── api/                  # AniList API client and Fetch from AniList
├── dashboard/            # data loading, filters, charts, the predictor and one file per page (pages/)
├── data/
│   ├── user/             # your list
│   ├── original/         # raw airing works from AniList
│   ├── modified/         # anime.csv and the cleaned airing works
│   └── final/            # your dataset, final.csv
├── model/                # the score prediction model
├── notes/                # how the data is cleaned and the works added by hand
├── src/
│   ├── manual/           # Add work and Remove work
│   └── pipeline/         # fetching, cleaning, matching and merging
├── anime_transformers.py # custom transformers the model needs to load
├── config.json           # settings
├── environment.yml       # conda environment
├── main.sh               # the CLI
├── requirements.txt      # pip / uv dependencies
└── streamlit_app.py      # the dashboard
```

## Acknowledgements

- **[AniList](https://anilist.co)**: for the API every work comes from.
- **[LeoRigasaki](https://github.com/LeoRigasaki)**: the original `anime.csv` comes from him.

## Contact

If you find an error, a work missing from `anime.csv` that you added, or you have suggestions or questions, reach me at
**anidash@proton.me**.
