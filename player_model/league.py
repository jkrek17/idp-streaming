"""Irene's Bush League settings (Yahoo screenshots 2026-11-17; they override the 2024 constitution)."""
TEAMS = 12
# starting slots per pool; FLEX = W/R/T, D = any IDP
SLOTS = {
    "offense": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1},
    "idp": {"LB": 1, "D": 1},
}
FLEX_ELIG = {"FLEX": ["RB", "WR", "TE"], "D": ["DL", "LB", "DB"]}
POOL_POS = {"offense": ["QB", "RB", "WR", "TE", "K"], "idp": ["DL", "LB", "DB"]}
REG_WEEKS = 18          # 2021+ (17 games); fantasy season runs through week 17
FANTASY_LAST_WEEK = 17
PLAYOFF_WEEKS = (15, 16, 17)

OFF = dict(pass_yd=1 / 20, pass_td=4, int=-1, rush_yd=1 / 10, rush_td=6, rec=0.5, rec_yd=1 / 10, rec_td=6,
           ret_td=6, two_pt=2, fum_lost=-2, bonus_pass=(375, 5), bonus_rush=(180, 5), bonus_rec=(200, 5),
           pat_made=1, pat_miss=-1, fg_yd=1 / 10, fg_miss_0_29=-1)
IDP = dict(solo=0.75, ast=0.25, tfl=1.5, sack=3, pd=1, int=5, ff=5, fr=2, td=6, safety=3, blk=2)

POS_MAP = {"QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB", "WR": "WR", "TE": "TE", "K": "K", "PK": "K",
           "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "EDGE": "DL",
           "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
           "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB", "SAF": "DB"}
