# Nov 3 IDP audit: walk-forward (week W uses weeks < W only), weeks 4-8.
import pickle, numpy as np, pandas as pd, idp_ratings as M, warnings; warnings.filterwarnings("ignore")
D=pickle.load(open("idp_cache_w9.pkl","rb"))
ps=M.score(D["ps"]); pbp=D["pbp"]; pbp=pbp[pbp.posteam.notna()]
R9=pd.read_csv("ratings_week9.csv")
pm={"DE":"DL","DT":"DL","DL":"DL","NT":"DL","OLB":"LB","ILB":"LB","MLB":"LB","LB":"LB","CB":"DB","S":"DB","FS":"DB","SS":"DB","DB":"DB","SAF":"DB"}
role=R9.set_index("gsis_id").role
d=ps[ps.position.isin(pm)].copy()
d["role"]=d.player_id.map(role)
d["grp"]=np.where(d.role.isin(["EDGE","IDL"]),"DL",np.where(d.role=="LB","LB",np.where(d.role.isin(["CB","S"]),"DB",d.position.map(pm))))
d["edge_lb"]=(d.role=="EDGE")&d.position.isin(["LB","OLB"])
sn=D["snaps"][["gsis_id","week","defense_pct","defense_snaps"]].dropna(subset=["gsis_id"])
d=d.merge(sn,left_on=["player_id","week"],right_on=["gsis_id","week"],how="left")
d["big"]=d.p_sack+d.p_tfl+d.p_int+d.p_ff+d.p_other; d["tkl"]=d.p_tackle
d["big_cap"]=np.minimum(d.sacks,2)*3+d.p_tfl+np.minimum(d.ints,1)*5+np.minimum(d.ff,1)*5+np.minimum(d.p_other,2)
d["b12"]=(d.fpts>=12).astype(int)
GRPS=["DL","LB","DB"]

def offense(W, k_db=150, k_g=3):
    p=pbp[pbp.week<W]; g=p.groupby("posteam").game_id.nunique()
    db=p[p.qb_dropback==1]; L=lambda s,n,k: (s+k*(s.sum()/n.sum()))/(n+k)
    n_db=db.groupby("posteam").size()
    f=pd.DataFrame(index=g.index)
    f["sack_rate"]=L(db.groupby("posteam").sack.sum(),n_db,k_db)
    f["hit_rate"]=L((db.qb_hit.fillna(0)+db.sack.fillna(0)>0).groupby(db.posteam).sum(),n_db,k_db)
    f["int_rate"]=L(db.groupby("posteam").interception.sum(),n_db,k_db*2)
    gv=(p.interception.fillna(0)+p.fumble_lost.fillna(0)).groupby(p.posteam).sum()
    f["give_pg"]=(gv+k_g*gv.sum()/g.sum())/(g+k_g)
    runs=p[p.rush_attempt==1]; f["stuff_rate"]=L(runs.groupby("posteam").tackled_for_loss.sum(),runs.groupby("posteam").size(),k_db)
    f["plays_pg"]=p[p.play_type.isin(["run","pass"])].groupby("posteam").size()/g
    f["rush_pg"]=runs.groupby("posteam").size()/g
    f["pass_pg"]=n_db/g
    q=d[(d.week<W)&(d.defense_pct>=0.5)]
    for gr in GRPS:
        x=q[q.grp==gr]; tw=x.groupby(["opponent_team","week"]).agg(big=("big","mean"),tkl=("tkl","mean"),b12=("b12","mean"))
        a=tw.groupby(level=0).agg(["sum","count"])
        for c in ["big","tkl","b12"]:
            mu=tw[c].mean(); f[f"{c}_{gr}"]=(a[(c,"sum")]+k_g*mu)/(a[(c,"count")]+k_g)
    return f

FEAT={"DL":["sack_rate","hit_rate","give_pg","stuff_rate","big_DL","b12_DL","tkl_DL","plays_pg","pass_pg"],
      "LB":["sack_rate","hit_rate","give_pg","stuff_rate","big_LB","b12_LB","tkl_LB","plays_pg","rush_pg"],
      "DB":["int_rate","give_pg","sack_rate","big_DB","b12_DB","tkl_DB","plays_pg","pass_pg"]}

def prior(W, decay=0.8):
    q=d[d.week<W].copy(); q["w"]=decay**(W-1-q.week)
    def agg(x):
        w=x.w; s=x.defense_pct.fillna(0)
        return pd.Series({"n":len(x),"avg":np.average(x.fpts,weights=w),"avg_flat":x.fpts.mean(),
          "snap_l3":x.sort_values("week").defense_pct.tail(3).mean(),"snap_s":s.mean(),
          "tkl_ps":(x.tkl*w).sum()/max((x.defense_snaps.fillna(0)*w).sum(),1),
          "big_ps":(x.big*w).sum()/max((x.defense_snaps.fillna(0)*w).sum(),1),
          "bigc_ps":(x.big_cap*w).sum()/max((x.defense_snaps.fillna(0)*w).sum(),1),
          "hits_ps":((x.qb_hits+x.sacks)*w).sum()/max((x.defense_snaps.fillna(0)*w).sum(),1),
          "r12":x.b12.mean(),"grp":x.grp.iloc[-1],"edge_lb":x.edge_lb.iloc[-1]})
    return q.groupby("player_id").apply(agg)

rows=[]
for W in range(4,10):
    f=offense(W); z=(f-f.mean())/f.std()
    pr=prior(W)
    if W==9: F9,Z9,P9=f,z,pr; break
    a=d[(d.week==W)].join(pr,on="player_id",rsuffix="_p")
    a=a[(a.n>=2)&(a.snap_l3>=0.5)]
    for c in z.columns: a["z_"+c]=a.opponent_team.map(z[c])
    a["W"]=W; rows.append(a)
A=pd.concat(rows); A["resid"]=A.fpts-A.avg
# shrink player prior toward group mean (k=3 games) for residual baseline
gm=A.groupby("grp").fpts.transform("mean"); A["base"]=(A.avg*A.n+3*gm)/(A.n+3); A["resid"]=A.fpts-A.base
out=[]
P=lambda *s: (print(*s), out.append(" ".join(map(str,s))))
P("rows",len(A),A.groupby("grp").size().to_dict())
P("\n(c) single-factor walk-forward signal, weeks 4-8: corr(z, resid) | top-third minus bottom-third: pts, 12+ rate")
SING={}
for gr in GRPS:
    x=A[A.grp==gr]
    for c in FEAT[gr]:
        zc=x["z_"+c]; t=zc>zc.quantile(2/3); b=zc<zc.quantile(1/3)
        r=np.corrcoef(zc.fillna(0),x.resid)[0,1]; SING[(gr,c)]=r
        P(f"  {gr} {c:11s} r={r:+.3f}  dPts={x.resid[t].mean()-x.resid[b].mean():+.2f}  d12={x.b12[t].mean()-x.b12[b].mean():+.3f}")
# walk-forward ridge fit on resid
def fit(x,cols,lam):
    X=x[["z_"+c for c in cols]].fillna(0).values; y=x.resid.values
    return np.linalg.solve(X.T@X+lam*len(x)*np.eye(len(cols)),X.T@y)
P("\n(c) walk-forward weights: train weeks 4..W-1, test W (5-8). MSE gain vs no matchup (pts^2), corr pred-vs-resid")
best={}
for gr in GRPS:
    cols=FEAT[gr]
    for lam in [0.05,0.2,1.0]:
        pr_,ys=[],[]
        for W in range(5,9):
            tr=A[(A.grp==gr)&(A.W<W)]; te=A[(A.grp==gr)&(A.W==W)]
            b=fit(tr,cols,lam); pr_+=list(te[["z_"+c for c in cols]].fillna(0).values@b); ys+=list(te.resid)
        pr_,ys=np.array(pr_),np.array(ys); g=np.mean(ys**2)-np.mean((ys-pr_)**2); r=np.corrcoef(pr_,ys)[0,1]
        P(f"  {gr} lam={lam}: MSEgain={g:+.3f} r={r:+.3f}")
        if gr not in best or g>best[gr][1]: best[gr]=(lam,g,r)
# old weights test (percentile scheme from matchup_view.py, using fpa total proxies)
OLD={"DL":{"sack_rate":.35,"hit_rate":.25,"big_DL":.2,"tkl_DL":.2},"LB":{"plays_pg":.25,"rush_pg":.25,"tkl_LB":.25,"big_LB":.25},"DB":{"pass_pg":.25,"int_rate":.3,"tkl_DB":.225,"big_DB":.225}}
P("\nold-style (volume/FPA percentile) score corr with resid:")
for gr in GRPS:
    x=A[A.grp==gr]; s=sum(w*x["z_"+c].fillna(0) for c,w in OLD[gr].items()); P(f"  {gr} r={np.corrcoef(s,x.resid)[0,1]:+.3f}")
# final constrained weights: use best lam trained on 4-8; keep sign-sensible (drop negatives -> refit)
FINAL={}
for gr in GRPS:
    cols=list(FEAT[gr]); lam=max(best[gr][0],0.2)
    x=A[A.grp==gr]
    while True:
        b=fit(x,cols,lam)
        if (b>=0).all() or len(cols)==1: break
        cols=[c for c,v in zip(cols,b) if v>0]
    FINAL[gr]=dict(zip(cols,b))
    P(f"final {gr} (pts per +1 SD, lam={lam}):", {k:round(v,3) for k,v in FINAL[gr].items()})
# 12+ by predicted matchup tercile, walk-forward
P("\n12+ rate by walk-forward matchup tercile (weeks 5-8):")
for gr in GRPS:
    cols=list(FINAL[gr]); pp=[]
    for W in range(5,9):
        tr=A[(A.grp==gr)&(A.W<W)]; te=A[(A.grp==gr)&(A.W==W)].copy(); te["pm"]=te[["z_"+c for c in cols]].fillna(0).values@fit(tr,cols,0.2); pp.append(te)
    te=pd.concat(pp); q=pd.qcut(te.pm,3,labels=["bad","mid","good"])
    P(f"  {gr}", te.groupby(q).agg(n=("b12","size"),r12=("b12","mean"),resid=("resid","mean")).round(3).to_dict("index"))

# (a) tackle opportunity
P("\n(a) tackle pts: corr(pred, actual tkl pts) by snap estimate")
for nm,s in [("season",A.snap_s),("last3",A.snap_l3),("50/50",(A.snap_s+A.snap_l3)/2)]:
    pr_=s*A.tkl_ps*65; P(f"  {nm:7s} r={np.corrcoef(pr_.fillna(0),A.tkl)[0,1]:.3f} MAE={np.mean(abs(pr_.fillna(0)-A.tkl)):.2f}")
# (b)/(d) big-play rate
P("\n(b,d) big-play pts per game: corr with actual big pts, by group")
for gr in GRPS:
    x=A[A.grp==gr]; sn=(x.snap_s+x.snap_l3)/2*65
    mu=x.big_ps.mean(); n=x.n*sn; shr=lambda r,k:(r*n+k*mu)/(n+k)
    xs=x.hits_ps*0.55*3+x.big_ps*0  # hits->sacks proxy
    res={"raw":x.big_ps*sn,"capped":x.bigc_ps*sn,"shrunk300":shr(x.big_ps,300)*sn,"capped+shrunk":((x.bigc_ps*n+300*x.bigc_ps.mean())/(n+300))*sn,"qb-hits":x.hits_ps*sn}
    P(f"  {gr} "+"  ".join(f"{k}={np.corrcoef(v.fillna(0),x.big)[0,1]:+.3f}" for k,v in res.items()))
# (e) recency
P("\n(e) recency: corr(prior ppg, actual) by decay")
for dec in [1.0,0.8,0.6]:
    rr=[]
    for W in range(4,9):
        pr=prior(W,dec); a=A[A.W==W].join(pr[["avg"]],on="player_id",rsuffix="_d"); rr.append(a)
    a=pd.concat(rr); P(f"  decay {dec}: r={np.corrcoef(a.avg_d,a.fpts)[0,1]:.3f} MAE={np.mean(abs(a.avg_d-a.fpts)):.3f}")
# (f) 12+ calibration from prior history
P("\n(f) 12+ games: prior 12+ rate vs next-week 12+ (weeks 4-8)")
q=pd.cut(A.r12,[-.01,0,.2,1]); P("  ",A.groupby(q).agg(n=("b12","size"),obs=("b12","mean")).round(3).to_dict("index"))
b=pd.read_csv("backtest_boom_weeks4-7.csv"); b["bin12"]=pd.to_numeric(b.bin12.astype(str).map({"True":1,"False":0,"1":1,"0":0}),errors="coerce"); bb=pd.cut(b.p_ge12,[0,.02,.05,.1,1])
P("   model p_ge12 bins (wks4-7):",b.groupby(bb).agg(n=("bin12","size"),pred=("p_ge12","mean"),obs=("bin12","mean")).round(3).to_dict("index"))
# (g) role mapping
P("\n(g) EDGE-flagged LBs vs true LBs vs DL: 12+ rate, big share; which feature set predicts them")
x=A[A.edge_lb]; y=A[(A.grp=="LB")]; z_=A[(A.grp=="DL")&~A.edge_lb]
for nm,g in [("EDGE_LB",x),("LB",y),("DL other",z_)]:
    P(f"  {nm}: n={len(g)} ppg={g.fpts.mean():.2f} 12+={g.b12.mean():.3f} big share={g.big.sum()/g.fpts.sum():.2f}")
for gr in ["DL","LB"]:
    s=sum(v*x["z_"+c].fillna(0) for c,v in FINAL[gr].items()); P(f"  EDGE_LB resid vs {gr} matchup model r={np.corrcoef(s,x.resid)[0,1]:+.3f}")
IDX={"DL":{"sack_rate":.30,"hit_rate":.20,"give_pg":.10,"big_DL":.20,"b12_DL":.15,"plays_pg":.05},
 "LB":{"give_pg":.25,"sack_rate":.15,"hit_rate":.10,"big_LB":.20,"b12_LB":.15,"rush_pg":.10,"tkl_LB":.05},
 "DB":{"int_rate":.30,"give_pg":.25,"big_DB":.20,"b12_DB":.15,"pass_pg":.10}}
P("\n(c) fixed big-play-first index, ONE scale parameter fit walk-forward (train 4..W-1, test W=5-8)")
SCALE={}
for gr in GRPS:
    def ix(x): return sum(w*x["z_"+c].fillna(0) for c,w in IDX[gr].items())
    pr_,ys=[],[]
    for W in range(5,9):
        tr=A[(A.grp==gr)&(A.W<W)]; te=A[(A.grp==gr)&(A.W==W)]; i=ix(tr)
        k=max((i*tr.resid).sum()/((i*i).sum()+0.5*len(tr)),0); pr_+=list(k*ix(te)); ys+=list(te.resid)
    pr_,ys=np.array(pr_),np.array(ys); x=A[A.grp==gr]; i=ix(x)
    SCALE[gr]=max((i*x.resid).sum()/((i*i).sum()+0.5*len(x)),0)
    P(f"  {gr}: MSEgain={np.mean(ys**2)-np.mean((ys-pr_)**2):+.4f} r={np.corrcoef(pr_,ys)[0,1]:+.3f}  in-sample corr={np.corrcoef(i,x.resid)[0,1]:+.3f}  final scale={SCALE[gr]:.3f} pts per index-SD (index sd={i.std():.2f})")
pickle.dump(dict(IDX=IDX,SCALE=SCALE,FINAL=FINAL,F9=F9,Z9=Z9),open("audit_final.pkl","wb"))
open("idp_audit_weeks4-8.txt","w").write("\n".join(out))
b=pd.read_csv("backtest_boom_weeks4-7.csv"); b["y12"]=(b.actual>=12).astype(int); bb=pd.cut(b.p_ge12,[0,.02,.05,.1,1])
P("\n(f) model P(12+) calibration wks 4-7:",b.groupby(bb).agg(n=("y12","size"),pred=("p_ge12","mean"),obs=("y12","mean")).round(3).to_dict("index"))
from scipy.stats import rankdata
def auc(y,s):
    y=np.asarray(y);r=rankdata(s);n1=y.sum();n0=len(y)-n1
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0)
A["bigx"]=A.big_ps*(A.snap_s+A.snap_l3)/2; A["hitx"]=A.hits_ps*(A.snap_s+A.snap_l3)/2; A["tklx"]=A.tkl_ps*(A.snap_s+A.snap_l3)/2
P("(f) what predicts a 12+ game? AUC, weeks 4-8 walk-forward priors:")
for c in ["avg","r12","bigx","hitx","tklx"]: P(f"  {c}: AUC={auc(A.b12,A[c].fillna(0)):.3f}")
A["edge"]=A.edge_lb.astype(int); P(f"  edge_lb flag: AUC={auc(A.b12,A.edge):.3f}")
for gr in GRPS:
    x=A[A.grp==gr]; P(f"  {gr}: n12={x.b12.sum()} avg AUC={auc(x.b12,x.avg):.3f} big AUC={auc(x.b12,x.bigx.fillna(0)):.3f} hits AUC={auc(x.b12,x.hitx.fillna(0)):.3f} r12 AUC={auc(x.b12,x.r12):.3f}")
open("idp_audit_weeks4-8.txt","w").write("\n".join(out))
