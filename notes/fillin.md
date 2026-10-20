# How the data is cleaned
Nothing is imputed (no medians, no random samples, no "OTHER"/"UNKNOWN"): a missing value stays missing (NaN).
The only exceptions are `episodes`, `season_year` and `season`, filled only when it is possible. All of this lives in `src/pipeline/helpers.py`
and runs for the airing dataset and the works fetched from Anilist (the historical dataset got the same cleaning once, when it was built).

## Order of the steps
The airing file (`cleanup_airing`), the seasons (`fetch_season`) and works fetched from Anilist (`get_anime`) all go through `helpers.clean`:
1. The columns are the ones `build_row` (`api/anilist.py`) creates. Every type is kept (`tv`, `tv_short`, `movie`, `ova`, `ona`, `special`, `music`).
2. `clean_invalid` (below).
3. `fill_episodes`, `fill_season_year`, `fill_season`.
4. Rows are **not** dropped for missing values, including a missing `start_date`.
5. `helpers.merge` joins them with the historical file and drops duplicates by `anime_id` (the unique key of every work), keeping the new row (it has newer information).
   `start_date` is saved as `YYYY-MM-DD` and the file is sorted by date.

## Values that only pretend to be data (`clean_invalid`)
Turned into NaN before anything is filled (the wrong `season_year` and `season` are then refilled below):
- blank strings, and "None"/"null"/"N/A" in `season`, `source`, `status` and `country_of_origin`
- `0` in `episodes`, `duration`, `score`, `mean_score` and `season_year`
- `end_date` earlier than `start_date`
- `season_year` more than one year away from the `start_date` year
- a `season` on the opposite side of the year from `start_date`

## episodes
Only for airing works: `next_episode_number - 1`. If the next episode is 0 or 1 nothing can be inferred and it stays NaN.

## season_year
Only if it is null (originally or after `clean_invalid`): the year of `start_date`. Without `start_date` it stays NaN.

## season
Only if it is null (originally or after `clean_invalid`) and `start_date` exists, otherwise it stays NaN.
- Movies: the season of the month of `start_date`.
- Any other type: the season that `start_date + 30 days` falls in, so a work released on June 28th (or on December 7th) is `SUMMER` (`WINTER`), not `SPRING` (`FALL`).

## Sorting by date
Rows are sorted by `start_date`; rows without it are placed using the first day of their `season` in `season_year`.

## Dropped columns
`scored_by`, `rank` and `popularity_rank` are not created by `build_row` since they were (almost) always empty or 0 in the source.
