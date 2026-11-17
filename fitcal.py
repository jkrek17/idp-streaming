import idp_ratings as m, pandas as pd, numpy as np
m.P.update(decay=0.5,snap_recent_w=0.8)
D=m.load_data(2026); sc=m.score(D["ps"]); out=[]
for wk in [4,5,6,7,8]:
    T=m.project(D,wk); act=sc[sc.week==wk].set_index("player_id").fpts
    T=T[T.proj_snap_pct>=0.5].copy(); T["act"]=T.gsis_id.map(act); T=T[T.act.notna()]; out.append(T[["pos","proj_raw","act"]])
R=pd.concat(out)
for p,g in R.groupby("pos"):
    b,a=np.polyfit(g.proj_raw,g.act,1); print(p,round(a,3),round(b,3))
