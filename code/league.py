# # API data for premier league table - current season

# ## Set environment
import os
from pathlib import Path
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 500)
from datetime import datetime

from dotenv import load_dotenv

import xlsxwriter

import requests
import json

# current date
date = datetime.now().strftime("%Y%m%d")

load_dotenv("../.env")

# ## API call
# keep columns
keep_cols = [
    "id",
    "utcDate",
    "status",
    "matchday",
    "homeTeam.shortName",
    "awayTeam.shortName",
    "score.fullTime.home",
    "score.fullTime.away",
]

# Rename club names to simplify
club_names = {
    "Brighton Hove": "Brighton",
    "Leeds United": "Leeds",
    "Leicester City": "Leicester",
    "Wolverhampton": "Wolves",
}


# ### API data call
# Add scoreline to dataframe

api_key = os.environ["API_AUTH_KEY"]
uri = "http://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
headers = {"X-Auth-Token": api_key}

response = requests.get(uri, headers=headers)
data = response.json()


df = pd.json_normalize(data, record_path=["matches"])
df.head()

df = df[keep_cols]
df["utcDate"] = pd.to_datetime(df["utcDate"])
# remove timezone
df["utcDate"] = df["utcDate"].dt.tz_localize(None)
# create full time score column
df["score.fullTime"] = (
    df["score.fullTime.home"].astype(str) + "-" + df["score.fullTime.away"].astype(str)
)
# rename club names using dictionary
df["homeTeam.shortName"] = df["homeTeam.shortName"].replace(club_names)
df["awayTeam.shortName"] = df["awayTeam.shortName"].replace(club_names)


### Create Matches DataFrame with a row for each team
points_map = {"W": 3, "D": 1, "L": 0}


def get_result(score, score_opp):
    if score == score_opp:
        return "D"
    elif score > score_opp:
        return "W"
    else:
        return "L"


drop_cols = ["homeTeam.shortName", "awayTeam.shortName"]

# convert each match into two rows (one for each team)

df["H"] = df["homeTeam.shortName"]
df["A"] = df["awayTeam.shortName"]

df_matches = pd.melt(
    df,
    id_vars=keep_cols,
    value_vars=["H", "A"],
    var_name="homeAway",
    value_name="team",
)


df_matches["opponent"] = np.where(
    df_matches["homeAway"] == "H",
    df_matches["awayTeam.shortName"],
    df_matches["homeTeam.shortName"],
)
# add column for full time score
df_matches["score.fullTime"] = (
    df_matches["score.fullTime.home"].astype(str)
    + "-"
    + df_matches["score.fullTime.away"].astype(str)
)

# full time goals
df_matches["goalsScored"] = np.where(
    df_matches["team"] == df_matches["homeTeam.shortName"],
    df_matches["score.fullTime.home"],
    df_matches["score.fullTime.away"],
)
df_matches["goalsAgainst"] = np.where(
    df_matches["team"] != df_matches["homeTeam.shortName"],
    df_matches["score.fullTime.home"],
    df_matches["score.fullTime.away"],
)
df_matches["result"] = np.vectorize(get_result)(
    df_matches["goalsScored"], df_matches["goalsAgainst"]
)
df_matches["points"] = df_matches["result"].map(points_map)


# sort df_matches by id
df_matches = (
    df_matches.drop(drop_cols, axis=1)
    .sort_values(by=["utcDate", "id"], ascending=True)
    .reset_index(drop=True)
)

# create a dictionary of logos
logosDict = {
    "Arsenal": "https://upload.wikimedia.org/wikipedia/en/5/53/Arsenal_FC.svg",
    "Aston Villa": "https://upload.wikimedia.org/wikipedia/en/f/f9/Aston_Villa_FC_crest_%282016%29.svg",
    "Brighton": "https://upload.wikimedia.org/wikipedia/en/f/fd/Brighton_%26_Hove_Albion_logo.svg",
    "Brentford": "https://upload.wikimedia.org/wikipedia/en/2/2a/Brentford_FC_crest.svg",
    "Burnley": "https://upload.wikimedia.org/wikipedia/en/0/02/Burnley_FC_badge.svg",
    "Bournemouth": "https://upload.wikimedia.org/wikipedia/en/e/e5/AFC_Bournemouth_%282013%29.svg",
    "Chelsea": "https://upload.wikimedia.org/wikipedia/en/c/cc/Chelsea_FC.svg",
    "Crystal Palace": "https://upload.wikimedia.org/wikipedia/en/a/a2/Crystal_Palace_FC_logo_%282022%29.svg",
    "Everton": "https://upload.wikimedia.org/wikipedia/en/7/7c/Everton_FC_logo.svg",
    "Fulham": "https://upload.wikimedia.org/wikipedia/sco/e/eb/Fulham_FC_%28shield%29.svg",
    "Leeds": "https://upload.wikimedia.org/wikipedia/en/5/54/Leeds_United_F.C._logo.svg",
    "Leicester": "https://upload.wikimedia.org/wikipedia/en/2/2d/Leicester_City_crest.svg",
    "Liverpool": "https://upload.wikimedia.org/wikipedia/en/0/0c/Liverpool_FC.svg",
    "Man City": "https://upload.wikimedia.org/wikipedia/en/e/eb/Manchester_City_FC_badge.svg",
    "Man United": "https://upload.wikimedia.org/wikipedia/sco/7/7a/Manchester_United_FC_crest.svg",
    "Newcastle": "https://upload.wikimedia.org/wikipedia/en/5/56/Newcastle_United_Logo.svg",
    "Nottingham": "https://upload.wikimedia.org/wikipedia/en/e/e5/Nottingham_Forest_F.C._logo.svg",
    "Southampton": "https://upload.wikimedia.org/wikipedia/en/c/c9/FC_Southampton.svg",
    "Tottenham": "https://upload.wikimedia.org/wikipedia/en/b/b4/Tottenham_Hotspur.svg",
    "West Ham": "https://upload.wikimedia.org/wikipedia/en/c/c2/West_Ham_United_FC_logo.svg",
    "Wolves": "https://upload.wikimedia.org/wikipedia/en/f/fc/Wolverhampton_Wanderers.svg",
}


def league(x):
    results = {
        "played": x["result"].count(),
        "won": (x["result"] == "W").sum(),
        "drawn": (x["result"] == "D").sum(),
        "lost": (x["result"] == "L").sum(),
        "goalsFor": x["goalsScored"].sum(),
        "goalsAgainst": x["goalsAgainst"].sum(),
        "goalDiff": x["goalsScored"].sum() - x["goalsAgainst"].sum(),
        "points": x["points"].sum(),
        "form": "".join(x["result"].tail(5).tolist()),
        # previous 5 games
        "f5": x["result"].tail(5).tolist()[0],
        "f4": x["result"].tail(4).tolist()[0],
        "f3": x["result"].tail(3).tolist()[0],
        "f2": x["result"].tail(2).tolist()[0],
        "f1": x["result"].tail(1).tolist()[0],
        # ANALYSIS  COLUMNS
        # win %
        "win%": "{:.0%}".format((x["result"] == "W").sum() / x["result"].count()),
        # percentage of points from last 5 games
        "form%": "{:.0%}".format(x["points"].tail(5).sum() / 15),
        # goals per game
        "goalsScoredPg": "{:.2f}".format(x["goalsScored"].sum() / x["result"].count()),
        # goals against per game
        "goalsAgainstPg": "{:.2f}".format(
            x["goalsAgainst"].sum() / x["result"].count()
        ),
        # goal difference per game
        "goalDifferencePg": "{:.2f}".format(
            (x["goalsScored"].sum() - x["goalsAgainst"].sum()) / x["result"].count()
        ),
        # clean sheets
        "cleanSheets": (x["goalsAgainst"] == 0).sum(),
        # points per game
        "pointsPg": "{:.2f}".format(x["points"].sum() / x["result"].count()),
        # Home points per game
        "homePointsPg": "{:.2f}".format(
            x[x["homeAway"] == "H"]["points"].sum()
            / x[x["homeAway"] == "H"]["result"].count()
        ),
        # Away points per game
        "awayPointsPg": "{:.2f}".format(
            x[x["homeAway"] == "A"]["points"].sum()
            / x[x["homeAway"] == "A"]["result"].count()
        ),
        # Score away against Newcastle
        "NewcastleHome": x[(x["opponent"] == "Newcastle") & (x["homeAway"] == "A")][
            "score.fullTime"
        ].tolist(),
        # Score at home against Newcastle
        "NewcastleAway": x[(x["opponent"] == "Newcastle") & (x["homeAway"] == "H")][
            "score.fullTime"
        ].tolist(),
        # maximum possible points remainig game for the seaon * 3
        "maxPoints": ((38 - x["result"].count()) * 3) + x["points"].sum(),
        # Expected points, based on points per game
        "expectedPoints": "{:.0f}".format(
            (x["points"].sum() / x["result"].count()) * (38 - x["result"].count())
            + x["points"].sum()
        ),
    }
    return pd.Series(results)


# apply league function
df_league = df_matches.groupby("team").apply(league)
# Sort by points and then goal difference
df_league = df_league.sort_values(by=["points", "goalDiff"], ascending=False)

##### ADD IN POSITION COLUMN

# add column for position
df_league["position"] = df_league["points"].rank(ascending=False, method="first")
# reformat position to int
df_league["position"] = df_league["position"].astype(int)

####### ADD IN PREVIOUS WEEKS DATA
# To calculate position change


# Function for Previous weeks league table for points and goal difference only
def leaguePrev(x):
    results = {
        "pointsPrev": x["points"].sum(),
        "goalDiffPrev": x["goalsScored"].sum() - x["goalsAgainst"].sum(),
    }
    return pd.Series(results)


# df_matchesPrev where matchday does not equal max
df_matchesPrev = df_matches[df_matches["matchday"] != df_matches["matchday"].max()]

# apply league_prev function
df_leaguePrev = df_matchesPrev.groupby("team").apply(leaguePrev)
# sort by points and then goal difference
df_leaguePrev = df_leaguePrev.sort_values(
    by=["pointsPrev", "goalDiffPrev"], ascending=False
)
# add column for position
df_leaguePrev["positionPrev"] = df_leaguePrev["pointsPrev"].rank(
    ascending=False, method="first"
)
# reformat position to int
df_leaguePrev["positionPrev"] = df_leaguePrev["positionPrev"].astype(int)

# join df_league with df_leaguePrev on index
df_league = df_league.join(df_leaguePrev, how="left")

# add in position change symbol
df_league["positionChange"] = np.where(
    df_league["position"] > df_league["positionPrev"],
    "▼",
    np.where(
        df_league["position"] < df_league["positionPrev"],
        "▲",
        "=",
    ),
)
# drop previous position
df_league = df_league.drop(["pointsPrev", "goalDiffPrev", "positionPrev"], axis=1)

# move team from index to column
df_league = df_league.reset_index()

##### ADD IN RESULTS VS NEWCASTLE

# df to show points taken by Newcastle against each opponent
df_ncl = df_matches[df_matches["team"] == "Newcastle"]
# group by opponent and sum points and games
df_ncl = df_ncl.groupby("opponent").agg({"points": "sum", "matchday": "count"})
# calculate % of points taken and format as a percentage
df_ncl["%Taken"] = df_ncl["points"] / (df_ncl["matchday"] * 3)
df_ncl["%Taken"] = df_ncl["%Taken"].apply(lambda x: "{:.0%}".format(x))
# Remaining points to be taken from each opponent
df_ncl["pointsRemaining"] = (2 - df_ncl["matchday"]) * 3
# drop matchday column
df_ncl = df_ncl.drop(["matchday"], axis=1)
# rename points column to pointsTaken
df_ncl = df_ncl.rename(columns={"points": "pointsTaken"})
# remove index
df_ncl = df_ncl.reset_index()

# Join with df_league
# Add df_ncl to df_league on left on team, right on opponent
df_league = df_league.merge(df_ncl, left_on="team", right_on="opponent", how="left")
# drop opponent column
df_league = df_league.drop(["opponent"], axis=1)

##### add in longest unbeaten run


# function to calculate longest unbeaten consecutive results
def longestUnbeaten(x):
    # calculate length of longest unbeaten run
    results = {
        "longestUnbeaten": len(max("".join(x["result"]).split("L"), key=len)),
    }
    return pd.Series(results)


# apply longestUnbeaten function
df_streaks = df_matches.groupby("team").apply(longestUnbeaten).reset_index()
# join df_streaks with df_league on team name
df_league = df_league.merge(df_streaks, how="left", on="team")

##### add in current unbeaten run


# calculate number of games since last loss
def gamesSinceLoss(x):
    # calculate length of longest unbeaten run
    results = {
        "gamesSinceLoss": len("".join(x["result"]).split("L")[-1]),
    }
    return pd.Series(results)


# apply gamesSinceLoss function
df_loss = df_matches.groupby("team").apply(gamesSinceLoss).reset_index()
# join df_loss with df_league on team name
df_league = df_league.merge(df_loss, how="left", on="team")

####### add logos for each team

# add logo column from logoDict to df_league and limit to 30px
df_league["logo"] = df_league["team"].map(logosDict)
# render logo in html format with 30px height
df_league["logo"] = df_league["logo"].apply(
    lambda x: '<img src="{}" height="30" alt="logo">'.format(x)
)

##### FORMAT THE DATA

# remove [] from newcastleHome and NewcastleAway
df_league["NewcastleHome"] = df_league["NewcastleHome"].str[0]
df_league["NewcastleAway"] = df_league["NewcastleAway"].str[0]
# replace nan with -
df_league = df_league.fillna("-")

# Reorder columns
df_league = df_league[
    [
        "position",
        "positionChange",
        "logo",
        "team",
        "played",
        "won",
        "drawn",
        "lost",
        "goalsFor",
        "goalsAgainst",
        "goalDiff",
        "points",
        "f5",
        "f4",
        "f3",
        "f2",
        "f1",
        "longestUnbeaten",
        "gamesSinceLoss",
        "win%",
        "form%",
        "pointsPg",
        "homePointsPg",
        "awayPointsPg",
        "goalDifferencePg",
        "cleanSheets",
        "NewcastleHome",
        "NewcastleAway",
        "pointsTaken",
        "pointsRemaining",
        "%Taken",
        "maxPoints",
        "expectedPoints",
    ]
]


# ### Upcoming fixtures

uri_sched = "http://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"

# from the API get the next fixtures
headers = {"X-Auth-Token": api_key}

response_sched = requests.get(uri_sched, headers=headers)
data_sched = response_sched.json()
df_scheduled = pd.json_normalize(data_sched, record_path=["matches"])

# convert date to datetime and remove timezone
df_scheduled["utcDate"] = pd.to_datetime(df_scheduled["utcDate"]).dt.tz_localize(None)

# keep only the columns we need

schedule_keep_cols = [
    "id",
    "utcDate",
    "matchday",
    "homeTeam.shortName",
    "awayTeam.shortName",
]
df_scheduled = df_scheduled[schedule_keep_cols]

# rename team names from dict
df_scheduled["homeTeam.shortName"] = df_scheduled["homeTeam.shortName"].replace(
    club_names
)
df_scheduled["awayTeam.shortName"] = df_scheduled["awayTeam.shortName"].replace(
    club_names
)

# convert each match into two rows (one for each team)
df_scheduled["H"] = df_scheduled["homeTeam.shortName"]
df_scheduled["A"] = df_scheduled["awayTeam.shortName"]

df_scheduled = pd.melt(
    df_scheduled,
    id_vars=schedule_keep_cols,
    value_vars=["H", "A"],
    var_name="homeAway",
    value_name="team",
)

df_scheduled["opponent"] = np.where(
    df_scheduled["homeAway"] == "H",
    df_scheduled["awayTeam.shortName"],
    df_scheduled["homeTeam.shortName"],
)

# rename opponent column to nextOpponent
df_scheduled = df_scheduled.rename(columns={"opponent": "nextOpponent"})

# drop columns we don't need - drop_cols
df_scheduled = df_scheduled.drop(drop_cols, axis=1)

# sort by date
df_scheduled = df_scheduled.sort_values(by=["utcDate"])

# reduce to only the next game for each team
df_next = df_scheduled.groupby("team").head(1).reset_index(drop=True)

# concat opponent and homeAway columns
df_next["nextOpponent"] = df_next["nextOpponent"] + " (" + df_next["homeAway"] + ")"
# drop homeAway column
df_next = df_next.drop(["id", "utcDate", "matchday", "homeAway"], axis=1)

# add in next opponent to df_league from df_next
df_league = df_league.merge(df_next, how="left", on="team")


# using df create a bootstrap table with date in filename
df_league.to_html(f"../output/{date}-table.html", index=False, escape=False)
