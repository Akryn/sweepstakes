# sweepstakes
Fairer sweepstakes balanced around bookies' odds.

[`sweepstakes.py`](https://github.com/Akryn/sweepstakes/blob/main/sweepstakes.py) obtains odds for the 2026 FIFA World Cup outright winner via [The Odds API](https://the-odds-api.com/) and then uses [PuLP](https://pypi.org/project/PuLP/) to attempt to find partitions of teams such that each partition has roughly the same total chance of winning.

The optimisation cannot find an exact solution in general and is set to timeout after 30 s.

### Requirements
- You must have an API key from [The Odds API](https://the-odds-api.com/) set as an environment variable called `THE_ODDS_API_KEY`. Restart your computer after setting.