# Nov 3: matchup-first IDP view (sort: matchup score, then 12+ rate, then 10+ rate). No floor/safety terms.
import pickle, numpy as np, pandas as pd, idp_ratings as M, streamers as S, json
WK=9
D=pickle.load(open("idp_cache_w9.pkl","rb"))
ps=M.score(D["ps"]); ps=ps[ps.week<WK]
R=pd.read_csv(f"ratings_week{WK}.csv")
R["grp"]=np.where(R.role.isin(["EDGE","IDL"]),"DL",np.where(R.role=="LB","LB","DB"))
role=R.set_index("gsis_id").grp
# defender group for every ps row (fallback by roster position)
pm={"DE":"DL","DT":"DL","DL":"DL","NT":"DL","OLB":"LB","ILB":"LB","MLB":"LB","LB":"LB","CB":"DB","S":"DB","FS":"DB","SS":"DB","DB":"DB","SAF":"DB"}
dfn=ps[ps.position.isin(pm)].copy()
dfn["grp"]=dfn.player_id.map(role).fillna(dfn.position.map(pm))
# FPA by offense team per game, per group
g=dfn.groupby(["opponent_team","week","grp"]).fpts.sum().unstack("grp").fillna(0)
fpa=g.groupby(level=0).mean()
# offense profile from pbp
pbp=D["pbp"]; pbp=pbp[(pbp.week<WK)&pbp.posteam.notna()]
gp=pbp.groupby("posteam").game_id.nunique()
db=pbp[pbp.qb_dropback==1].groupby("posteam")
off=pd.DataFrame({"sack_rate":db.sack.mean(),"hit_rate":db.qb_hit.mean(),
  "plays_pg":pbp[pbp.play_type.isin(["run","pass"])].groupby("posteam").size()/gp,
  "rush_pg":pbp[pbp.rush_attempt==1].groupby("posteam").size()/gp,
  "pass_pg":pbp[pbp.pass_attempt==1].groupby("posteam").size()/gp,
  "int_rate":db.interception.mean()})
# pressure-to-sack proxy: sacks / (sacks + non-sack hits)
off["p2s"]=pbp[pbp.qb_dropback==1].groupby("posteam").apply(lambda x: x.sack.sum()/max(((x.sack.fillna(0)+x.qb_hit.fillna(0))>0).sum(),1))
off=off.join(fpa.add_prefix("fpa_"))
# Nov 3 audit: big-play-first index on shrunk walk-forward offense features (idp_audit.py), scaled to pts vs average.
AU=pickle.load(open("audit_final.pkl","rb")); Z9,IDX,SCALE=AU["Z9"],AU["IDX"],AU["SCALE"]
def mexp(grp,opp):
    if opp not in Z9.index: return np.nan
    return SCALE[grp]*sum(w*Z9.loc[opp,k] for k,w in IDX[grp].items())
R["opp"]=R.matchup.str.replace("vs ","").str.replace("@ ","")
R["mexp"]=[mexp(gq,o) for gq,o in zip(R.grp,R.opp)]
R["mscore"]=R.mexp
grade=lambda s:"A" if s>=0.15 else "B" if s>=0.05 else "C" if s>-0.05 else "D" if s>-0.15 else "F"
R["mgrade"]=R.mexp.map(lambda s: grade(s) if pd.notna(s) else "")
# player game log
pl=ps.groupby("player_id")
st=pd.DataFrame({"gp":pl.size(),"g12":pl.fpts.apply(lambda x:(x>=12).sum()),"g10":pl.fpts.apply(lambda x:(x>=10).sum()),
 "g6":pl.fpts.apply(lambda x:(x>=6).sum()),"avg":pl.fpts.mean(),
 "l3":ps.sort_values("week").groupby("player_id").fpts.apply(lambda x:x.tail(3).mean()),
 "sk":pl.sacks.sum(),"tfl_s":pl.tfl.sum(),"to":pl.ints.sum()+pl.ff.sum()+pl.fr.sum(),
 "int_s":pl.ints.sum(),"ff_s":pl.ff.sum(),"fr_s":pl.fr.sum(),"best":pl.fpts.max()})
R=R.join(st,on="gsis_id")
# availability
L=S.parse_league(f"yahoo_league_week{WK}.md")
L["k"]=L.player_y.map(M.norm_name)+"|"+L.team
R["k"]=R.player.map(M.norm_name)+"|"+R.team
def lk(n):
    w=M.norm_name(n).split(); return f"{w[-1]}|{w[0][0]}" if w else ""
k2=R.player.map(lk)+"|"+R.team; uniq=dict(zip(k2[~k2.duplicated(keep=False)],R.k[~k2.duplicated(keep=False)]))
L["k"]=[k if k in set(R.k) else uniq.get(lk(n)+"|"+t,k) for k,n,t in zip(L.k,L.player_y,L.team)]
av=L.drop_duplicates("k").set_index("k")
R["status"]=np.where(R.player.isin(["Jamien Sherwood","Kyle Hamilton"]),"Mine",np.where(R.k.isin(av.index),"Available","Not listed"))
R["ypos"]=R.k.map(av.yahoo_pos).fillna(R.position)
R=R[(R.gp>=3)&R.mscore.notna()&((R.proj_snap_pct>=0.5)|(R.status=="Mine"))].copy()
R["r12"]=R.g12/R.gp; R["r10"]=R.g10/R.gp
R["mscore"]=R.mexp.round(2)
R=R.sort_values(["mscore","r12","r10"],ascending=False)
R.to_csv(f"matchup_view_week{WK}.csv",index=False)
off.round(3).to_csv(f"opp_profile_week{WK}.csv")
cols=["player","team","grp","ypos","matchup","opp_qb","mgrade","mscore","g12","g10","g6","gp","sk","tfl_s","to","avg","l3","status"]
pd.set_option("display.width",250); pd.set_option("display.max_rows",200)
print(R[R.status!="Not listed"][cols].head(40).round(1).to_string())
print(R[R.status=="Mine"][cols].round(1).to_string())
print(len(R), R.status.value_counts().to_dict())
R["inj"]=R.k.map(av.yahoo_tag).fillna("")
R.to_csv(f"matchup_view_week{WK}.csv",index=False)
X=R[R.status!="Not listed"]
rows=[[r.player,r.team,r.grp,r.ypos,r.matchup,r.opp_qb if isinstance(r.opp_qb,str) else "",r.mgrade,round(float(r.mexp),2),int(r.g12),int(r.g10),int(r.g6),int(r.gp),
  float(r.sk),float(r.tfl_s),int(r.to),round(r.avg,1),round(r.l3,1),r.status,r.inj,round(float(r.p_ge12)*100,1)] for r in X.itertuples()]
open(f"mv_rows_week{WK}.txt","w").write(",\n".join(json.dumps(x,ensure_ascii=False) for x in rows))
op=Z9.round(2); op.to_csv(f'opp_z_week{WK}.csv')
print(len(rows))
