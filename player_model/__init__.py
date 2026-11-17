"""Season-long player ranking and value model (offense and IDP pools).

Pipeline: data (nflverse 2018+) -> features (usage, empirical-Bayes shares, consistency, context)
-> LightGBM mean + quantile models with calibrated threshold probabilities -> value layer
(position ranks, flex ranks, value over free agents in consistency / balanced / ceiling modes) -> web page.
Run: python -m player_model.run --week 11
"""
