"""Simple independent-Poisson BTTS baseline. Not calibrated."""
from math import exp
def btts(home_for, home_against, away_for, away_against):
    lh=max(.05,(home_for+away_against)/2)
    la=max(.05,(away_for+home_against)/2)
    return round((1-exp(-lh))*(1-exp(-la)),5)
def score(rows,home,away,league,min_games=5):
    hs=[r for r in rows if r["league"]==league and r["home"]==home][-20:]
    aa=[r for r in rows if r["league"]==league and r["away"]==away][-20:]
    if min(len(hs),len(aa))<min_games:return None
    return btts(sum(r["hg"] for r in hs)/len(hs),sum(r["ag"] for r in hs)/len(hs),sum(r["ag"] for r in aa)/len(aa),sum(r["hg"] for r in aa)/len(aa))
