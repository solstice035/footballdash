
from copyreg import pickle
import os
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

dateNow = datetime.now().strftime("%Y%m%d")

p = Path().absolute()
data_folder = Path(p, "data")

# Keep columns: 
keepcols = [
    "Div",
    "Date",
    "Time",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "Referee",
    "HS",
    "AS",
    "HST",
    "AST",
    "HF",
    "AF",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
]

# Load input csv 
results_csv = data_folder / "E0.csv"
results = pd.read_csv(
    results_csv, usecols=keepcols, parse_dates=["Date"], dayfirst=True
)

# Melt the data 
## converting each matchup into 2 rows
## one where each team is 'current_team' and opponent is identfied
results["H"] = results["HomeTeam"]
results["A"] = results["AwayTeam"]
cols_to_keep = [
    "Div",
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "Referee",
]

team_results = pd.melt(
    results,
    id_vars=cols_to_keep,
    value_vars=["H", "A"],
    var_name="Home/Away",
    value_name="Team",
)

team_results["Opponent"] = np.where(
    team_results["Team"] == team_results["HomeTeam"],
    team_results["AwayTeam"],
    team_results["HomeTeam"],
)

# Get points from results
points_map = {
    'W': 3,
    'D': 1,
    'L': 0
}

def get_result(score, score_opp):
    if score == score_opp:
        return 'D'
    elif score > score_opp:
        return 'W'
    else:
        return 'L'

# Full time goals
team_results["Goals"] = np.where(
    team_results["Team"] == team_results["HomeTeam"],
    team_results["FTHG"],
    team_results["FTAG"],
)
team_results["Goals_Opp"] = np.where(
    team_results["Team"] != team_results["HomeTeam"],
    team_results["FTHG"],
    team_results["FTAG"],
)
team_results["Result"] = np.vectorize(get_result)(
    team_results["Goals"], team_results["Goals_Opp"]
)
team_results["Points"] = team_results["Result"].map(points_map)

team_results["Score"] = team_results["Goals"].astype(str) + '-' + team_results["Goals_Opp"].astype(str) 


# Drop unnecessary columns and sort by date
cols_to_drop = ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 'HTR']
team_results = (team_results
                    .drop(cols_to_drop, axis=1)
                    .sort_values(by=['Date', 'Referee']))

# Export the data to pickle and csv
pickle_folder = Path(p, "data", "pickle", f"{dateNow}-team_results.pkl")
team_results.to_pickle(pickle_folder)
# log export results
print(f"Exported {team_results.shape[0]} rows to {pickle_folder}")
csv_folder = Path(p, "output",  f"{dateNow}-team_results.csv")
team_results.to_csv(csv_folder)
print("data exported as csv")