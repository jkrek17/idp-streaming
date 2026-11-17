import numpy as np, pandas as pd, warnings, sys; warnings.filterwarnings("ignore")
import idp_ratings as M, boom, comp_audit as A
D=A.D; ps=M.score(D["ps"]); M.CAL_MODE=sys.argv[1] if len(sys.argv)>1 else "split"
Ts={}
for wk in range(4,9):
    T=M.project(D,wk); Ts[wk]=T[T.proj_snap_pct>=0.5].copy()
def ev(sims):
    G=[]
    for wk,T in Ts.items():
        B=boom.simulate(T,D,wk,{**sims,"n":4000}); g=T[["gsis_id","pos","proj_pts"]].merge(B,on="gsis_id")
        g["actual"]=g.gsis_id.map(ps[ps.week==wk].set_index("player_id").fpts).fillna(0); g["week"]=wk; G.append(g)
    G=pd.concat(G); y=(G.actual>=12).astype(float); p=G.p_ge12.clip(1e-4,1-1e-4)
    ll=-(y*np.log(p)+(1-y)*np.log(1-p)).mean()
    bl=G.groupby("week").apply(lambda z:z.nlargest(24,"p_ge12")).reset_index(drop=True)
    pos={k:f"{x.p_ge12.mean():.3f}/{(x.actual>=12).mean():.3f}" for k,x in G.groupby("pos")}
    q=pd.qcut(G.p_ge12.rank(method="first"),5,labels=False)
    return dict(p12=round(G.p_ge12.mean(),4),o12=round(y.mean(),4),p10=round(G.p_ge10.mean(),4),o10=round((G.actual>=10).mean(),4),
        ll12=round(ll,4),below_p10=round((G.actual<G.floor_p10).mean(),3),above_p90=round((G.actual>G.p90).mean(),3),
        list_pred=round(bl.p_ge12.mean(),3),list_obs=round((bl.actual>=12).mean(),3),list_avg=round(bl.actual.mean(),2),
        quint=[(round(x.p_ge12.mean(),3),round((x.actual>=12).mean(),3)) for _,x in G.groupby(q)],**pos), G
if __name__=="__main__":
    for cv in [0.0,0.4,0.6,0.8,1.0]:
        for rt in [12.0,6.0]:
            r,_=ev(dict(SPLASH_CV=cv,R_TKL=rt)); print(cv,rt,r,flush=True)
