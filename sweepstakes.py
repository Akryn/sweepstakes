import os
import requests
import pandas as pd
import pulp
import matplotlib.pyplot as plt


API_KEY = os.environ.get('THE_ODDS_API_KEY')
# You must have an API key from https://the-odds-api.com/ set as an environment
# variable called 'THE_ODDS_API_KEY'. Restart computer after setting.

NUMBER_OF_PLAYERS = 7
# Total number of players in the sweepstakes.

ACCEPTABLE_BOOMKAKERS_ORDERED_LIST = [
    'bet365', 'skybet', 'paddypower', 'williamhill']
# Acceptable bookmakers in decreasing order of preference.
# See: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html#uk-bookmakers

BOOKMAKERS = ','.join(ACCEPTABLE_BOOMKAKERS_ORDERED_LIST)

REGIONS = 'uk'
# Region for bookmakers. Will be ignored in favour of BOOKMAKERS.

BASE_URL = 'https://api.the-odds-api.com/v4/sports'
SPORT = 'soccer_fifa_world_cup_winner'
MARKETS = 'outrights'

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

# Flatten with pandas.
df = pd.json_normalize(
    response_json,
    record_path=['bookmakers', 'markets', 'outcomes'],
)

df.columns = ['country', 'decimal_odds']

# Calculate probability from decimal odds.
df['unscaled_prob'] = df['decimal_odds'].apply(lambda x: 1/x)

# Bookies' odds don't sum to one.
prob_normalisation_factor = sum(df['unscaled_prob'])
df['prob'] = df['unscaled_prob'] / prob_normalisation_factor

prob_dict = df.set_index('country').to_dict()['prob']


# Optimisation
def partition(samples, num_groups):
    """
    Splits samples into groups to minimise the difference between the largest 
    and smallest group totals.

    Parameters
    ----------
    samples : dict
        Dictionary of {sample_name: utility_value}.
    num_groups : int
        Number of groups to split into (e.g., 12).
    """
    names = list(samples.keys())
    utilities = list(samples.values())
    num_items = len(names)

    # Initialise the optimisation problem.
    prob = pulp.LpProblem("Partitioning", pulp.LpMinimize)

    # Define decision variables:
    # x[i, j] = 1 if item i is assigned to group j, else 0.
    x = pulp.LpVariable.dicts("assign",
                              ((i, j) for i in range(num_items)
                               for j in range(num_groups)),
                              cat='Binary')

    # Variables to track the boundary weights of the groups.
    max_utility = pulp.LpVariable("max_utility", lowBound=0)
    min_utility = pulp.LpVariable("min_utility", lowBound=0)

    # Objective Function: Minimise the difference between min and max utlility.
    prob += max_utility - min_utility

    # Constraints:
    # Every sample must belong to exactly one group.
    for i in range(num_items):
        prob += pulp.lpSum(x[i, j] for j in range(num_groups)) == 1

    # Total utility for any group must be within the min and max group utilities.
    for j in range(num_groups):
        group_total = pulp.lpSum(x[i, j] * utilities[i]
                                 for i in range(num_items))
        prob += group_total <= max_utility
        prob += group_total >= min_utility

    # print(prob)

    # Solve:
    prob.solve(pulp.PULP_CBC_CMD(
        timeLimit=30,  # Exact solution in general will not exist.
        # gapRel=0.05,
        msg=False
        # If True, won't display in an IPython console. Run from terminal instead.
    ))
    # prob_status = pulp.LpStatus[prob.status]
    sol_status = pulp.LpSolution[prob.sol_status]
    sol_time = prob.solutionTime

    # Reconstruct the groups
    groups = [[] for _ in range(num_groups)]
    group_totals = [0] * num_groups

    for i in range(num_items):
        for j in range(num_groups):
            if pulp.value(x[i, j]) == 1:
                groups[j].append((names[i], utilities[i]))
                group_totals[j] += utilities[i]
                break

    return sol_status, sol_time, groups, group_totals


sol_status, sol_time, groups, group_totals = partition(
    prob_dict, NUMBER_OF_PLAYERS)

# https://github.com/coin-or/pulp/blob/master/pulp/constants.py
if sol_status == pulp.LpSolution[pulp.LpSolutionOptimal]:
    print('Optimal solution found. If gapRel is set, the solution is within the gap.')
elif sol_status == pulp.LpSolution[pulp.LpSolutionIntegerFeasible]:
    print('Timeout: Sub-optimal solution found.')
else:
    print('Error: Solver stopped or failed without finding any valid solution.')

# Plotting
plt.figure()
plt.bar(list(range(len(group_totals))), group_totals)
plt.xlabel('Grouping')
plt.ylabel('Combined Prboability of Winning')

# For World Cup 2026 at the time of writing, as soon as num_groups > 7, we cannot find a good solution.
# For 8 teams, Spain and France individually already have more probability than what would be the maximum to enable "fairness".

group_names = [", ".join(item[0] for item in group) for group in groups]

for name, total in zip(group_names, group_totals):
    print(f"{name} ({total})")