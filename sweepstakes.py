import os
import requests
import pandas as pd


API_KEY = os.environ.get('THE_ODDS_API_KEY')
# Remeber to restart computer after setting as environment variable.

BASE_URL = 'https://api.the-odds-api.com/v4/sports'
SPORT = 'soccer_fifa_world_cup_winner'
REGIONS = 'uk'
MARKETS = 'outrights'

ACCEPTABLE_BOOMKAKERS_ORDERED_LIST = ['bet365', 'skybet', 'paddypower', 'williamhill']
# Acceptable bookmakers in decreasing order of preference.

BOOKMAKERS = ','.join(ACCEPTABLE_BOOMKAKERS_ORDERED_LIST)

if 'response' not in locals():
    response = requests.get(f'{BASE_URL}/{SPORT}/odds', params={
        'api_key': API_KEY,
        'markets': MARKETS,
        'regions': REGIONS,
        'bookmakers': BOOKMAKERS
    })

if response.status_code != 200:
    print(
        f'Failed to get odds: status_code {response.status_code}, response body {response.text}')
else:
    response_json = response.json()

available_bookmakers = []
for dic in response_json[0]['bookmakers']:
    available_bookmakers.append(dic['key'])

for bookmaker in ACCEPTABLE_BOOMKAKERS_ORDERED_LIST:
    if bookmaker in available_bookmakers:
        chosen_bookmaker = bookmaker
        print(chosen_bookmaker, 'chosen as bookmaker.')
        break

if 'chosen_bookmaker' not in locals():
    print('No acceptable bookmakers found.')

df = pd.json_normalize(
    response_json, 
    record_path=['bookmakers', 'markets', 'outcomes'],
)

df.columns = ['country', 'decimal_odds']

# Calculate probability from decimal odds.
df['unscaled_prob'] = df['decimal_odds'].apply(lambda x: 1/x)
prob_normalisation_factor = sum(df['unscaled_prob'])
df['prob'] = df['unscaled_prob'] / prob_normalisation_factor
