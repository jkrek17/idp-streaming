import pickle, numpy as np, pandas as pd
from idp_ratings import norm_name
G=pd.read_pickle('/tmp/uG.pkl'); X=pd.read_pickle('/tmp/uX.pkl')
P,L=pickle.load(open('/tmp/tfP.pkl','rb'))
ros=lambda v: v.sum()/ (len(v)-1 if (v==0).sum()>=1 else len(v))
P['ros']=P.pts.map(ros)
G=G[G.position=='WR']
def tab(names):
    out=[]
    for nm in names:
        g=G[G.player.map(norm_name)==norm_name(nm)]
        if not len(g):
            g=G[G.player.str.split().str[-1]==nm.split()[-1]]; g=g[g.player.str[0]==nm[0]]
        if not len(g): out.append(dict(name=nm)); continue
        g=g.sort_values('week'); l3=g.tail(3)
        pr=P[P.name.map(norm_name)==norm_name(nm)]
        out.append(dict(name=nm, tm=g.team.iloc[-1], own=int(pr.owner.iloc[0]) if len(pr) else -1, gp=len(g),
            snap=round(g.offense_pct.mean()*100), snapL3=round(l3.offense_pct.mean()*100),
            tpg=round(g.tgt.mean(),1), tpgL3=round(l3.tgt.mean(),1), tsh=round(100*g.tgt.sum()/g.t_att.sum()), tshL3=round(100*l3.tgt.sum()/l3.t_att.sum()),
            airpg=round(g.air.mean()), rz=int(g.rz_tgt.sum()), ppg=round(g.fpts.mean(),1), ppgL3=round(l3.fpts.mean(),1),
            ros=round(pr.ros.iloc[0],1) if len(pr) else None, wks=",".join(map(str,g.week))))
    return pd.DataFrame(out)
pd.set_option('display.width',250)
trade=["Tee Higgins","Germie Bernard","Drake London","Zay Flowers","Tetairoa McMillan","Luther Burden III","Khalil Shakir","Jaylen Waddle","Deebo Samuel","CeeDee Lamb"]
A=tab(trade); A["set"]="trade target / yours"; print(A.to_string())
fa=P[(P.owner==0)&(P.grp=='WR')].sort_values('ros',ascending=False).head(14)
F=tab(list(fa.name)); F["set"]="free agent"; print(F.to_string()); pd.concat([A,F]).to_csv("wr_usage_week8.csv", index=False)
