import requests
import pandas as pd
import time
from datetime import datetime, timezone

URL = 'https://graphql.anilist.co'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Referer': 'https://anilist.co/',
    'Origin': 'https://anilist.co',
}

# AniList seasons in the order of the year, three months each
SEASON_NAMES = ['WINTER', 'SPRING', 'SUMMER', 'FALL']

# japanese, chinese and korean works, the rest are left out
COUNTRIES = ['JP', 'CN', 'KR']

# relation types kept, each one becomes a column with the ids of the anime this one is that relation of, e.g. sequel
# holds the anime this one is a sequel of
RELATIONS = ['PREQUEL', 'SEQUEL', 'PARENT', 'SIDE_STORY', 'SPIN_OFF', 'SUMMARY', 'ALTERNATIVE']

# what this anime is to a related one, deduced from what the related one is to this anime. PARENT is missing since this
# anime could be its SIDE_STORY, SPIN_OFF or SUMMARY
INVERSE = {'PREQUEL': 'SEQUEL', 'SEQUEL': 'PREQUEL', 'SIDE_STORY': 'PARENT', 'SPIN_OFF': 'PARENT', 'SUMMARY': 'PARENT',
           'ALTERNATIVE': 'ALTERNATIVE'}

# external link types kept, each one becomes a column with the names of the linked sites
LINK_TYPES = ['STREAMING', 'INFO', 'SOCIAL']

# every field build_row needs, shared by all the queries
MEDIA_FIELDS = '''
            id
            title {
                romaji
                english
                native
            }
            format
            episodes
            duration
            status
            source
            season
            seasonYear
            studios {
                edges {
                    isMain
                    node {
                        name
                    }
                }
            }
            genres
            tags {
                name
            }
            averageScore
            meanScore
            popularity
            favourites
            stats {
                statusDistribution {
                    status
                    amount
                }
            }
            startDate {
                year
                month
                day
            }
            endDate {
                year
                month
                day
            }
            description
            countryOfOrigin
            isLicensed
            hashtag
            relations {
                edges {
                    relationType(version: 2)
                    node {
                        id
                        type
                        relations {
                            edges {
                                relationType(version: 2)
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
            characters(role: MAIN, perPage: 10) {
                nodes {
                    name {
                        full
                    }
                }
            }
            staff(perPage: 10, sort: [RELEVANCE, ID]) {
                edges {
                    role
                    node {
                        name {
                            full
                        }
                    }
                }
            }
            externalLinks {
                site
                type
            }
            isAdult
            synonyms
            siteUrl
            updatedAt
            nextAiringEpisode {
                episode
            }
'''

def post(query, variables):
    """
    send the query and return its "Page", raising if AniList answers with an error
    """

    # a hung connection raises instead of stalling the CI run until GitHub's 6 hour limit
    response = requests.post(URL, json={'query': query, 'variables': variables}, headers=HEADERS, timeout=60)
    data = response.json()

    errors = data.get('errors') or []
    error_msg = '; '.join(e.get('message', '') for e in errors) or response.text

    if not response.ok:
        raise RuntimeError(f"AniList API returned {response.status_code}: {error_msg}")

    if errors:
        raise RuntimeError(f"AniList API error: {error_msg}")

    return (data.get('data') or {}).get('Page') or {}

def fmt_date(d):
    if d and d.get('year') and d.get('month') and d.get('day'):
        return f"{d['year']}-{d['month']}-{d['day']}"
    return None

def month_season(d):
    # a start date with a month but no day has no start_date (fmt_date) for fill_season to use, so the season of its month is used
    if d and d.get('month') and not d.get('day'):
        return SEASON_NAMES[(d['month'] - 1) // 3]
    return None

def join(values):
    # AniList may return a null name (characters, staff, synonyms)
    values = [v for v in values if v]
    return ';'.join(values) if values else None

def get_in(obj, *keys):
    # obj[k1][k2]... that gives None instead of raising when any level is null
    for k in keys:
        obj = (obj or {}).get(k)
    return obj

def relations_of(media):
    """
    {column: ids of the anime media is that relation of}. The relation a related anime has back to media says it
    directly, without one the INVERSE of its relation to media is used. Manga and novels are left out since they are
    not in anime.csv
    """

    found = {r: [] for r in RELATIONS}
    for e in (media.get('relations') or {}).get('edges') or []:
        node = (e or {}).get('node') or {}
        if node.get('type') != 'ANIME':
            continue
        back_edges = (node.get('relations') or {}).get('edges') or []
        back = [b['relationType'] for b in back_edges if get_in(b, 'node', 'id') == media['id']]
        for r in back or [INVERSE.get(e['relationType'])]:
            # the same anime can come in more than one edge
            if r in found and str(node['id']) not in found[r]:
                found[r].append(str(node['id']))

    return {r.lower(): join(ids) for r, ids in found.items()}

def build_row(media):
    title = media.get('title') or {}
    studios = (media.get('studios') or {}).get('edges') or []
    characters = (media.get('characters') or {}).get('nodes') or []
    staff = (media.get('staff') or {}).get('edges') or []
    # unreleased works can come back with null stats
    status = {s['status']: s['amount'] for s in (media.get('stats') or {}).get('statusDistribution') or []}
    next_episode = (media.get('nextAiringEpisode') or {}).get('episode')

    return {
        'anime_id': media['id'],
        'title': title.get('romaji'),
        'english_title': title.get('english'),
        'japanese_title': title.get('native'),
        'type': media['format'],
        'episodes': media['episodes'],
        'duration': media['duration'],
        'status': media['status'],
        'source': media['source'],
        'season': media['season'] or month_season(media['startDate']),
        # AniList has no seasonYear for most works with only a year or year and month as start date, which fmt_date
        # drops, so the year of startDate keeps them from ending up without any year
        'season_year': media['seasonYear'] or (media['startDate'] or {}).get('year'),
        'studios': join([get_in(e, 'node', 'name') for e in studios]),
        'main_studios': join([get_in(e, 'node', 'name') for e in studios if e and e['isMain']]),
        'genres': join(media['genres'] or []),
        'tags': join([get_in(tag, 'name') for tag in media['tags'] or []]),
        'score': media['averageScore'],
        'mean_score': media['meanScore'],
        'popularity': media['popularity'],
        'favorites': media['favourites'],
        'watching': status.get('CURRENT', 0),
        'completed': status.get('COMPLETED', 0),
        'on_hold': status.get('PAUSED', 0),
        'dropped': status.get('DROPPED', 0),
        'plan_to_watch': status.get('PLANNING', 0),
        'start_date': fmt_date(media['startDate']),
        'end_date': fmt_date(media['endDate']),
        'synopsis': media['description'],
        'country_of_origin': media['countryOfOrigin'],
        'is_licensed': media['isLicensed'],
        'hashtag': media['hashtag'],
        **relations_of(media),
        'main_characters': join([get_in(c, 'name', 'full') for c in characters]),
        'main_staff': join([f"{name} ({e['role']})" for e in staff if e and (name := get_in(e, 'node', 'name', 'full'))]),
        **{f'{t.lower()}_sites': join([get_in(l, 'site') for l in media['externalLinks'] or [] if l and l['type'] == t]) for t in LINK_TYPES},
        'is_adult': media['isAdult'],
        'synonyms': join(media['synonyms'] or []),
        'site_url': media['siteUrl'],
        'updated_at': media['updatedAt'],
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'data_source': 'anilist',
        'next_episode_number': next_episode
    }

# up to 10 works whose title matches $search
SEARCH_QUERY = '''
query ($search: String, $format: MediaFormat) {
    Page (perPage: 10) {
    media (search: $search, type: ANIME, format: $format) {''' + MEDIA_FIELDS + '''
    }
    }
}
'''

def fetch_anime_info(name, work_type):
    """
    the matches of name as a DataFrame, empty when nothing matched or AniList failed
    """

    variables = {'search': name, 'format': work_type.upper()}

    try:
        medias = [m for m in post(SEARCH_QUERY, variables).get('media') or [] if m]
        if not medias:
            raise RuntimeError(f"No match found for '{name}' with type '{work_type}'")

        df = pd.DataFrame([build_row(m) for m in medias])
        time.sleep(2)
        return df

    except Exception as e:
        print(f"Error: {str(e)}")
        time.sleep(1)
        return pd.DataFrame()

def fetch_media(filters):
    """
    every anime matching filters, GraphQL media arguments such as "season: FALL, seasonYear: 2026", 50 per request.
    Only works from COUNTRIES are kept. Unlike fetch_anime_info it raises on any error, so a half fetched list is never saved
    """

    query = '''
    query ($page: Int) {
        Page (page: $page, perPage: 50) {
        pageInfo {
            hasNextPage
        }
        media (type: ANIME, ''' + filters + ''') {''' + MEDIA_FIELDS + '''
        }
        }
    }
    '''

    rows, page, has_next = [], 1, True
    while has_next:
        result = post(query, {'page': page})
        rows += [build_row(m) for m in result.get('media') or [] if m and m['countryOfOrigin'] in COUNTRIES]
        has_next = (result.get('pageInfo') or {}).get('hasNextPage')
        page += 1
        # AniList allows a few dozen requests per minute
        time.sleep(10)

    return pd.DataFrame(rows)
