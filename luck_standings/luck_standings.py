"""Luck-reduced standings. Input: weekly_scores.csv with columns
week,team,points,opponent  (one row per team per week, weeks 1-8, real Yahoo data only).
Output: luck_standings.csv.
Power = 1/3 all-play win% + 1/3 (H2H+median) win% + 1/3 PF percentile (min-max 0-1)."""
import csv,sys,statistics as st
from collections import defaultdict
inp=sys.argv[1] if len(sys.argv)>1 else 'weekly_scores.csv'
rows=list(csv.DictReader(open(inp)))
pts=defaultdict(dict); opp=defaultdict(dict)
for r in rows:
    w=int(r['week']); pts[w][r['team']]=float(r['points']); opp[w][r['team']]=r['opponent']
teams=sorted({t for w in pts for t in pts[w]})
S={t:defaultdict(float) for t in teams}
for w,sc in pts.items():
    med=st.median(sc.values())
    for t,p in sc.items():
        o=sc[opp[w][t]]; s=S[t]
        s['W']+=p>o; s['L']+=p<o; s['T']+=p==o; s['PF']+=p; s['G']+=1
        for u,q in sc.items():
            if u!=t: s['aW']+=p>q; s['aL']+=p<q; s['aT']+=p==q
        s['mW']+=p>med; s['mL']+=p<med; s['mT']+=p==med
pfs=[S[t]['PF'] for t in teams]; lo,hi=min(pfs),max(pfs)
out=[]
for t in teams:
    s=S[t]; ap=(s['aW']+.5*s['aT'])/(s['aW']+s['aL']+s['aT'])
    hm=(s['W']+s['mW']+.5*(s['T']+s['mT']))/(2*s['G'])
    pfn=(s['PF']-lo)/(hi-lo) if hi>lo else .5
    out.append(dict(team=t,record=f"{int(s['W'])}-{int(s['L'])}-{int(s['T'])}",
      allplay=f"{int(s['aW'])}-{int(s['aL'])}-{int(s['aT'])}",allplay_pct=round(ap,3),
      h2h_median=f"{int(s['W']+s['mW'])}-{int(s['L']+s['mL'])}-{int(s['T']+s['mT'])}",h2h_median_pct=round(hm,3),
      PF=round(s['PF'],2),PF_norm=round(pfn,3),luck=round(s['W']+.5*s['T']-ap*s['G'],2),
      power=round((ap+hm+pfn)/3,4),_w=s['W']+.5*s['T']))
for k,key in [('actual_rank',lambda r:(-r['_w'],-r['PF'])),('PF_rank',lambda r:-r['PF']),('power_rank',lambda r:-r['power'])]:
    for i,r in enumerate(sorted(out,key=key),1): r[k]=i
for r in out: r['rank_change']=r['actual_rank']-r['power_rank']; del r['_w']
out.sort(key=lambda r:r['power_rank'])
def spear(a,b):
    n=len(a); return 1-6*sum((x-y)**2 for x,y in zip(a,b))/(n*(n*n-1))
print('Spearman PF vs actual rank:',round(spear([r['PF_rank'] for r in out],[r['actual_rank'] for r in out]),3))
print('Spearman PF vs power rank:',round(spear([r['PF_rank'] for r in out],[r['power_rank'] for r in out]),3))
w=csv.DictWriter(open('luck_standings.csv','w',newline=''),fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for r in out: print(r)
