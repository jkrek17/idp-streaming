import { Page, Section, Table, Segmented, Select, Toggle, Callout, Metrics, Properties, BulletList, Text, Grid, useState } from "grok/canvas";

type Val = string | number | boolean | null;
type Tone = "success" | "warning" | "danger";
type Cell = string | { text: string; tone: Tone };
type Slot = { slot: string; player: string; team: string; pos: string; matchup: string; mean: number; floor: number; p90: number; p_boom: number; grade: string; note: string };
type Waiver = { pos: string; player: string; team: string; status: string; pct: number | null; ros: number; wk: number; gain: number; verdict: string; faab: string; opp: string };
type Data = {
  week: number; season: number; generated: string; league: string; faab: number; waivers_clear: string;
  players: Val[][];
  lineup: { safe: Slot[]; boom: Slot[] }; bench: Slot[]; moves: string[]; waivers: Waiver[];
  boom_thr: Record<string, number>; scoring: string; backtest: string;
};
type TradeRow = { mine: boolean; a: string; aid: number; b: string; bid: number; kind: string; get: string; give: string; ga: number; gb: number; bal: number; minG: number; accept: string; note: string; ratio: number; moves: string; reason: string; preset?: string };
type TradeTest = { test: string; trade: string; gain_me: number; gain_them: number; passed: boolean };
type TradeData = { week: number; weeks: string; me: string; sources: string[]; minRatio: number; minGain: number; nWinWin: number; nKept: number; odds: { team: string; p: number }[]; tests: TradeTest[]; rows: TradeRow[] };
const DATA: Data = {
"week":9,
"season":2026,
"generated":"2026-11-03 09:30 ET",
"league":"Irene's Bush League (Yahoo 54162) - Breeces Pieces",
"faab":76,
"waivers_clear":"Nov 4",
"players":[
["Joe Burrow","CIN","QB","@ ATL",24.0,11.3,21.6,39.2,0.39,"C-",0.98,"7/7",0.37,23.7,"",27.8,"",null,false],
["Dak Prescott","DAL","QB","@ IND",21.4,9.9,19.5,35.2,0.3,"A",1.0,"8/8",0.23,19.3,"",28.8,"mine",null,false],
["Brock Purdy","SF","QB","vs LV",21.3,9.8,19.2,35.6,0.3,"B",0.99,"7/7",0.25,19.0,"",30.8,"",null,false],
["Kirk Cousins","LV","QB","@ SF",21.1,9.9,19.0,35.1,0.29,"C",0.99,"8/8",0.19,20.3,"",20.8,"",null,false],
["Jared Goff","DET","QB","@ MIA",20.8,9.0,18.8,35.2,0.29,"A+",0.99,"6/7",0.3,18.3,"",28.8,"",null,false],
["Jordan Love","GB","QB","@ NE",20.4,9.4,18.5,33.7,0.27,"B",1.0,"8/8",0.22,19.5,"",21.8,"",null,false],
["Patrick Mahomes","KC","QB","vs NYJ",20.3,9.1,18.4,33.8,0.27,"B",1.0,"5/7",0.41,18.7,"",28.0,"",null,false],
["Josh Allen","BUF","QB","@ MIN",19.9,9.1,18.0,33.0,0.25,"D",0.98,"7/7",0.28,21.6,"",24.5,"",null,false],
["Drake Maye","NE","QB","vs GB",19.4,8.7,17.7,32.8,0.24,"D",0.99,"5/8",0.47,20.2,"",24.8,"",null,false],
["Deshaun Watson","CLE","QB","@ NO",19.2,9.3,17.6,31.1,0.22,"B",0.98,"5/8",0.23,18.8,"",20.5,"W",12,false],
["Jayden Daniels","WAS","QB","vs LA",19.1,9.5,17.6,30.6,0.21,"C",0.98,"5/5",0.3,19.2,"",21.0,"",null,false],
["Trevor Lawrence","JAX","QB","@ BAL",18.5,8.0,16.6,31.2,0.21,"B",0.93,"6/7",0.33,19.0,"",26.0,"",null,false],
["Sam Darnold","SEA","QB","vs ARI",18.4,7.7,16.6,31.5,0.21,"B",0.98,"5/7",0.6,17.7,"",28.0,"",null,false],
["Geno Smith","NYJ","QB","@ KC",18.3,8.6,16.4,30.2,0.2,"C",1.0,"5/8",0.38,18.1,"",18.5,"W",23,false],
["C.J. Stroud","HOU","QB","@ LAC",18.3,8.4,16.8,30.0,0.19,"C-",1.0,"6/7",0.21,18.8,"",22.5,"W",76,false],
["Tyler Shough","NO","QB","vs CLE",17.7,7.8,16.0,29.6,0.18,"C-",0.99,"6/7",0.43,18.3,"",23.0,"",null,false],
["Malik Willis","MIA","QB","vs DET",17.7,7.9,16.3,29.4,0.18,"B",1.0,"4/7",0.43,16.9,"",21.8,"W",20,false],
["Michael Penix Jr.","ATL","QB","vs CIN",17.1,7.5,15.7,28.4,0.16,"C",1.0,"4/6",0.41,15.4,"",24.8,"W",20,false],
["Justin Herbert","LAC","QB","vs HOU",16.7,8.0,15.3,27.3,0.14,"C-",1.0,"2/7",0.13,17.5,"",18.0,"W",44,false],
["Jahmyr Gibbs","DET","RB","@ MIA",23.3,8.8,20.7,40.7,0.52,"C",0.79,"7/7",0.34,20.8,"",28.8,"",null,false],
["Kenneth Walker III","KC","RB","vs NYJ",19.5,6.3,16.7,36.1,0.39,"C-",0.76,"6/7",0.41,17.5,"",28.0,"",null,false],
["Chuba Hubbard","CAR","RB","vs DEN",17.2,6.0,15.2,31.0,0.32,"B",0.82,"6/7",0.33,17.0,"",20.2,"",null,false],
["Christian McCaffrey","SF","RB","vs LV",17.2,5.3,15.0,31.4,0.32,"C",0.71,"7/7",0.25,15.5,"",30.8,"",null,false],
["James Cook","BUF","RB","@ MIN",16.3,4.9,14.0,31.0,0.29,"B",0.61,"6/7",0.26,15.1,"",24.5,"",null,false],
["D'Andre Swift","CHI","RB","vs TB",15.6,4.4,13.4,29.7,0.27,"D",0.7,"6/8",0.48,15.4,"",26.2,"",null,false],
["Chase Brown","CIN","RB","@ ATL",14.5,4.8,13.0,26.5,0.22,"A+",0.69,"3/7",0.34,13.2,"",27.8,"",null,false],
["Javonte Williams","DAL","RB","@ IND",14.4,3.7,12.1,27.6,0.23,"C-",0.72,"6/8",0.47,13.1,"",28.8,"",null,false],
["Kyren Williams","LA","RB","@ WAS",14.4,4.2,12.6,26.8,0.23,"B",0.65,"7/8",0.39,13.1,"",26.5,"mine",null,false],
["Bijan Robinson","ATL","RB","vs CIN",14.3,4.6,12.5,26.7,0.22,"B",0.78,"5/8",0.6,13.3,"",24.8,"",null,false],
["Jonathan Taylor","IND","RB","vs DAL",14.3,4.1,12.4,27.0,0.22,"A",0.71,"5/8",0.46,13.7,"",22.8,"",null,false],
["Bucky Irving","TB","RB","@ CHI",13.3,3.7,11.7,25.2,0.19,"D",0.63,"5/8",0.57,15.5,"",20.2,"mine",null,false],
["Braelon Allen","NYJ","RB","@ KC",13.2,4.4,11.8,24.0,0.17,"C",0.79,"4/8",0.57,14.2,"",18.5,"",null,false],
["Bhayshul Tuten","JAX","RB","@ BAL",13.2,3.8,11.5,24.6,0.18,"C-",0.57,"6/7",0.43,13.1,"",26.0,"",null,false],
["Josh Jacobs","GB","RB","@ NE",13.2,3.4,11.3,24.9,0.19,"D",0.62,"2/2",0.07,14.5,"",21.8,"",null,false],
["Quinshon Judkins","CLE","RB","@ NO",12.6,3.0,10.7,24.5,0.17,"A",0.5,"2/7",0.59,12.5,"",20.5,"",null,false],
["Ashton Jeanty","LV","RB","@ SF",12.2,3.1,10.7,23.0,0.16,"A",0.59,"5/8",0.47,11.8,"",20.8,"",null,false],
["Jonah Coleman","DEN","RB","@ CAR",11.4,2.9,9.6,22.2,0.14,"B",0.52,"2/4",0.69,11.2,"",23.2,"",null,false],
["Woody Marks","HOU","RB","@ LAC",11.3,2.9,9.7,21.8,0.13,"B",0.76,"1/7",0.24,10.5,"",22.5,"",null,false],
["Rhamondre Stevenson","NE","RB","vs GB",10.7,2.9,9.2,20.4,0.1,"C",0.68,"5/8",0.55,10.4,"",24.8,"",null,false],
["Cam Skattebo","NYG","RB","@ PHI",10.4,2.9,8.8,19.9,0.1,"B",0.62,"3/6",0.41,9.7,"",22.0,"",null,false],
["Ollie Gordon II","MIA","RB","vs DET",10.1,2.4,8.5,19.6,0.1,"D",0.74,"4/6",0.51,11.3,"",21.8,"",null,false],
["Derrick Henry","BAL","RB","vs JAX",9.8,2.3,8.3,19.7,0.09,"D",0.53,"6/8",0.56,11.9,"",16.5,"",null,false],
["Blake Corum","LA","RB","@ WAS",9.7,2.3,8.1,19.0,0.09,"C",0.33,"4/8",0.54,8.9,"",26.5,"",null,false],
["Emanuel Wilson","SEA","RB","vs ARI",6.5,0.0,3.8,17.7,0.07,"C-",0.45,"3/7",0.82,9.3,"",28.0,"mine",null,false],
["Kendre Miller","NO","RB","vs CLE",8.8,1.7,7.2,18.1,0.07,"A",0.36,"0/6",0.56,8.3,"",23.0,"W",24,false],
["Dylan Sampson","CLE","RB","@ NO",7.6,1.6,6.4,15.0,0.04,"A",0.51,"0/2",0.04,7.1,"",20.5,"W",17,false],
["Kimani Vidal","LAC","RB","vs HOU",5.2,0.9,4.1,10.7,0.01,"C-",0.39,"2/6",0.74,5.4,"",18.0,"W",13,false],
["Justice Hill","BAL","RB","vs JAX",5.0,0.0,4.1,11.2,0.01,"C",0.45,"0/8",0.45,5.7,"Q",16.5,"W",5,false],
["Chris Rodriguez Jr.","JAX","RB","@ BAL",4.7,0.0,3.1,11.9,0.01,"C-",0.22,"1/7",0.69,5.4,"Q",26.0,"W",26,false],
["Bam Knight","ARI","RB","@ SEA",4.7,0.0,3.6,11.1,0.01,"C",0.35,"1/5",0.94,6.4,"Q",16.5,"W",19,false],
["Malik Nabers","NYG","WR","@ PHI",16.5,3.7,14.0,33.5,0.31,"A+",0.8,"4/7",0.6,15.1,"",22.0,"",null,false],
["CeeDee Lamb","DAL","WR","@ IND",15.4,3.1,12.7,31.2,0.27,"C",0.8,"6/8",0.58,15.2,"",28.8,"mine",null,false],
["Puka Nacua","LA","WR","@ WAS",14.5,3.3,12.2,28.5,0.24,"D",0.9,"5/6",0.36,14.9,"",26.5,"",null,false],
["Jaxon Smith-Njigba","SEA","WR","vs ARI",14.4,2.9,11.9,29.2,0.24,"B",0.88,"8/8",0.33,14.8,"",28.0,"",null,false],
["Amon-Ra St. Brown","DET","WR","@ MIA",14.3,2.5,11.9,28.8,0.25,"B",0.8,"4/7",0.48,14.7,"",28.8,"",null,false],
["Ja'Marr Chase","CIN","WR","@ ATL",13.5,2.5,11.2,27.0,0.21,"D",0.87,"5/7",0.55,14.5,"",27.8,"",null,false],
["Matthew Golden","GB","WR","@ NE",13.0,2.1,10.9,26.3,0.2,"A",0.85,"6/8",0.34,12.1,"",21.8,"",null,false],
["Zay Flowers","BAL","WR","vs JAX",12.9,2.5,10.8,25.5,0.18,"A",0.8,"5/7",0.56,11.1,"",16.5,"",null,false],
["Tee Higgins","CIN","WR","@ ATL",12.5,1.9,10.5,25.1,0.18,"D",0.82,"5/7",0.55,13.3,"",27.8,"",null,false],
["Drake London","ATL","WR","vs CIN",11.1,1.8,9.0,22.4,0.14,"C",0.92,"5/8",0.6,10.0,"",24.8,"",null,false],
["Jameson Williams","DET","WR","@ MIA",10.7,0.7,8.5,23.2,0.14,"B",0.86,"4/7",0.52,10.5,"",28.8,"",null,false],
["Chris Olave","NO","WR","vs CLE",10.4,1.8,8.5,21.5,0.12,"D",0.77,"5/7",0.37,11.3,"",23.0,"",null,false],
["Christian Watson","GB","WR","@ NE",10.3,1.5,8.6,20.5,0.11,"A",0.73,"5/8",0.56,9.3,"",21.8,"",null,false],
["Michael Wilson","ARI","WR","@ SEA",9.9,2.0,8.2,19.9,0.1,"F",0.87,"3/8",0.64,11.0,"",16.5,"",null,false],
["Luther Burden III","CHI","WR","vs TB",9.6,1.6,8.0,19.7,0.1,"C-",0.55,"4/8",0.46,10.1,"",26.2,"",null,false],
["Tetairoa McMillan","CAR","WR","vs DEN",9.6,1.6,8.0,19.3,0.09,"F",0.8,"3/7",0.87,10.2,"",20.2,"",null,false],
["Adonai Mitchell","NYJ","WR","@ KC",9.3,1.2,7.6,19.7,0.09,"D",0.6,"1/4",0.85,9.2,"",18.5,"",null,false],
["Parker Washington","JAX","WR","@ BAL",9.2,0.8,7.2,19.9,0.1,"A",0.74,"4/7",0.69,9.4,"",26.0,"",null,false],
["Justin Jefferson","MIN","WR","vs BUF",9.2,1.3,7.4,19.2,0.09,"D",0.89,"3/6",0.64,9.6,"",21.0,"",null,false],
["Garrett Wilson","NYJ","WR","@ KC",9.1,1.2,7.3,19.2,0.09,"D",0.88,"5/8",0.55,9.1,"",18.5,"",null,false],
["George Pickens","DAL","WR","@ IND",8.8,0.9,6.9,18.5,0.08,"C",0.71,"4/8",0.54,9.0,"",28.8,"",null,false],
["Tre Tucker","LV","WR","@ SF",8.4,0.8,6.6,18.7,0.08,"C-",0.68,"3/8",0.79,8.3,"",20.8,"",null,false],
["Malik Washington","MIA","WR","vs DET",8.1,1.4,6.7,16.6,0.05,"B",0.79,"1/7",0.32,7.6,"",21.8,"W",48,false],
["DJ Moore","BUF","WR","@ MIN",8.1,0.9,6.5,17.4,0.07,"D",0.57,"2/5",0.79,8.9,"",24.5,"",null,false],
["Rashee Rice","KC","WR","vs NYJ",7.9,0.7,6.1,17.3,0.07,"D",0.69,"3/4",0.19,8.4,"",28.0,"",null,false],
["Nico Collins","HOU","WR","@ LAC",7.8,0.8,6.3,16.6,0.05,"C",0.7,"2/5",0.69,8.1,"",22.5,"",null,false],
["Keenan Allen","IND","WR","vs DAL",7.7,1.3,6.4,15.7,0.04,"B",0.57,"3/7",0.56,7.3,"",22.8,"W",52,false],
["Denzel Boston","CLE","WR","@ NO",7.7,0.7,6.1,16.8,0.06,"C",0.88,"4/8",0.53,8.0,"",20.5,"",null,false],
["Ryan Flournoy","DAL","WR","@ IND",7.7,0.8,5.8,17.0,0.06,"C",0.76,"3/8",0.48,7.6,"",28.8,"W",34,false],
["KC Concepcion","CLE","WR","@ NO",7.6,1.3,6.5,15.4,0.04,"C",0.77,"1/8",0.8,7.6,"",20.5,"",null,false],
["Jaylen Waddle","DEN","WR","@ CAR",6.6,0.8,5.3,14.5,0.03,"C-",0.57,"3/8",0.67,7.2,"",23.2,"mine",null,false],
["Khalil Shakir","BUF","WR","@ MIN",6.2,0.0,4.6,14.0,0.03,"D",0.65,"1/7",0.42,7.0,"",24.5,"mine",null,false],
["Deebo Samuel Sr.","SF","WR","vs LV",5.5,0.0,3.8,13.2,0.03,"A",0.6,"3/5",0.57,5.7,"Q",30.8,"mine",null,false],
["Jahan Dotson","ATL","WR","vs CIN",6.4,0.0,4.6,15.0,0.04,"C",0.7,"3/8",0.82,5.8,"",24.8,"W",2,false],
["Treylon Burks","WAS","WR","vs LA",6.4,0.0,4.8,14.5,0.03,"D",0.62,"1/6",0.56,6.6,"",21.0,"W",2,false],
["Jordan Addison","MIN","WR","vs BUF",6.0,0.5,4.6,13.1,0.02,"D",0.92,"2/6",0.84,6.3,"",21.0,"W",71,false],
["Brock Bowers","LV","TE","@ SF",13.5,2.7,11.2,26.6,0.35,"C",0.87,"6/6",0.34,12.8,"",20.8,"mine",null,false],
["George Kittle","SF","TE","vs LV",11.3,1.7,9.1,23.5,0.27,"A",0.87,"5/7",0.53,10.3,"",30.8,"",null,false],
["Trey McBride","ARI","TE","@ SEA",10.6,2.5,9.2,20.8,0.23,"C-",0.94,"7/8",0.34,11.6,"",16.5,"",null,false],
["Harold Fannin Jr.","CLE","TE","@ NO",10.0,1.6,8.3,20.0,0.21,"A",0.86,"4/8",0.76,9.1,"",20.5,"",null,false],
["Colston Loveland","CHI","TE","vs TB",9.6,1.7,8.0,19.7,0.2,"B",0.88,"4/8",0.81,10.1,"",26.2,"",null,false],
["Greg Dulcich","MIA","TE","vs DET",9.0,1.4,7.2,18.8,0.18,"A+",0.69,"2/6",0.46,7.5,"",21.8,"W",6,false],
["Sam LaPorta","DET","TE","@ MIA",8.2,0.7,6.3,17.7,0.15,"A+",0.92,"3/7",0.59,7.3,"",28.8,"",null,false],
["Isaiah Likely","NYG","TE","@ PHI",8.1,0.9,6.4,17.3,0.14,"F",0.83,"4/7",0.74,9.3,"",22.0,"",null,false],
["Tucker Kraft","GB","TE","@ NE",8.1,1.1,6.5,16.8,0.14,"A",0.84,"5/8",0.46,7.6,"",21.8,"",null,false],
["Tyler Warren","IND","TE","vs DAL",8.1,1.4,6.6,16.5,0.13,"C-",0.84,"4/6",0.45,7.8,"",22.8,"",null,false],
["Travis Kelce","KC","TE","vs NYJ",8.0,0.9,6.4,17.2,0.14,"A+",0.77,"4/7",0.55,7.5,"",28.0,"",null,false],
["Kyle Pitts","ATL","TE","vs CIN",7.8,0.8,6.2,17.0,0.14,"A+",0.61,"3/8",0.99,6.8,"",24.8,"",null,false],
["Michael Mayer","LV","TE","@ SF",7.6,1.2,6.3,15.8,0.12,"C-",0.8,"3/8",0.55,7.2,"",20.8,"",null,false],
["Mason Taylor","NYJ","TE","@ KC",7.6,1.0,6.0,16.1,0.12,"A",0.6,"1/5",1.09,7.3,"",18.5,"W",4,false],
["Hunter Henry","NE","TE","vs GB",5.1,0.0,3.4,12.7,0.06,"F",0.57,"4/8",0.54,7.5,"Q",24.8,"mine",null,false],
["Dalton Schultz","HOU","TE","@ LAC",6.3,0.5,4.8,14.2,0.09,"D",0.52,"1/7",0.79,6.7,"",22.5,"W",37,false],
["Dallas Goedert","PHI","TE","vs NYG",6.1,0.7,4.8,13.4,0.07,"C",0.76,"2/6",0.76,6.0,"",18.5,"W",88,false],
["AJ Barner","SEA","TE","vs ARI",5.7,0.0,3.6,13.9,0.08,"C",0.9,"1/8",0.56,5.7,"",28.0,"W",12,false],
["Mike Gesicki","CIN","TE","@ ATL",4.8,0.0,3.2,11.9,0.06,"D",0.51,"4/6",0.32,5.2,"",27.8,"W",19,false],
["Brandon Aubrey","DAL","K","@ IND",10.9,2.8,9.9,20.6,0.4,"C",null,"5/8",0.61,10.1,"",28.8,"",null,false],
["Tyler Bass","BUF","K","@ MIN",10.9,2.8,10.0,20.5,0.39,"C",null,"5/7",0.44,11.5,"",24.5,"",null,false],
["Jake Bates","DET","K","@ MIA",10.7,3.0,9.7,20.0,0.38,"C",null,"6/7",0.43,9.7,"",28.8,"W",65,false],
["Jason Myers","SEA","K","vs ARI",10.6,2.6,9.7,19.8,0.37,"C",null,"5/8",0.71,9.9,"",28.0,"W",91,false],
["Harrison Butker","KC","K","vs NYJ",10.2,2.0,9.2,19.2,0.35,"C",null,"3/7",0.48,9.2,"",28.0,"",null,false],
["Cairo Santos","CHI","K","vs TB",9.9,2.0,8.9,18.5,0.34,"C",null,"6/8",0.46,9.5,"",26.2,"W",43,false],
["Spencer Shrader","IND","K","vs DAL",9.8,2.0,8.7,18.7,0.32,"C",null,"5/8",0.58,9.6,"",22.8,"",null,false],
["Will Reichard","MIN","K","vs BUF",9.7,2.0,8.8,18.6,0.33,"C",null,"6/7",0.47,10.2,"",21.0,"",null,false],
["Ka'imi Fairbairn","HOU","K","@ LAC",9.7,2.0,8.8,18.8,0.33,"C",null,"6/7",0.39,10.0,"",22.5,"mine",null,false],
["Matt Gay","LV","K","@ SF",9.6,2.0,8.7,18.5,0.31,"C",null,"7/8",0.29,10.7,"",20.8,"",null,false],
["Chase McLaughlin","TB","K","@ CHI",9.5,2.0,8.7,18.3,0.31,"C",null,"7/8",0.42,10.6,"",20.2,"mine",null,false],
["Drew Stevens","WAS","K","vs LA",9.5,2.0,8.5,18.4,0.31,"C",null,"5/7",0.39,9.9,"",21.0,"W",11,false],
["Dominic Zvada","NYG","K","@ PHI",9.3,2.0,8.3,17.9,0.3,"C",null,"5/7",0.48,9.6,"",22.0,"W",2,false],
["Wil Lutz","DEN","K","@ CAR",9.3,2.0,8.3,18.0,0.29,"C",null,"6/8",0.45,9.6,"",23.2,"W",15,false],
["Aidan Hutchinson","DET","DL","@ MIA",5.2,0.8,3.5,11.5,0.14,"F",0.9,"3/7",0.73,5.2,"",null,"",null,false],
["George Karlaftis","KC","DL","vs NYJ",5.1,0.8,3.5,11.2,0.13,"A",0.81,"3/7",0.68,5.1,"",null,"W",null,false],
["Maxx Crosby","LV","DL","@ SF",5.0,0.8,3.5,11.0,0.13,"F",0.92,"3/8",0.71,5.0,"",null,"W",null,false],
["Quinnen Williams","DAL","DL","@ IND",4.9,0.8,3.2,11.3,0.14,"D",0.59,"5/8",0.58,4.9,"",null,"W",null,false],
["Jalen Carter","PHI","DL","vs NYG",4.9,0.8,3.5,11.0,0.13,"C-",0.87,"3/8",1.14,4.9,"",null,"W",null,false],
["Chase Young","NO","DL","vs CLE",4.7,0.5,3.0,12.0,0.16,"A+",0.71,"4/7",0.69,4.7,"",null,"",null,false],
["Carl Granderson","NO","DL","vs CLE",4.6,0.5,3.0,11.2,0.14,"A+",0.68,"4/6",0.4,4.6,"",null,"W",null,false],
["Leonard Williams","SEA","DL","vs ARI",4.6,0.5,3.0,10.8,0.13,"C",0.73,"3/8",0.75,4.6,"",null,"W",null,false],
["Josh Hines-Allen","JAX","DL","@ BAL",4.6,0.5,3.0,10.5,0.12,"C",0.75,"3/7",1.03,4.6,"",null,"W",null,false],
["Jaylahn Tuimoloau","IND","DL","vs DAL",4.5,0.8,3.2,10.0,0.1,"C",0.78,"1/8",1.19,4.5,"",null,"",null,false],
["Boye Mafe","CIN","DL","@ ATL",4.5,0.8,3.2,10.0,0.1,"A",0.77,"5/7",0.64,4.5,"",null,"W",null,false],
["Laiatu Latu","IND","DL","vs DAL",4.5,0.5,3.0,10.2,0.11,"C",0.8,"0/8",0.71,4.5,"",null,"W",null,false],
["Jalen Redmond","MIN","DL","vs BUF",4.5,0.8,3.2,10.0,0.1,"C-",0.84,"1/7",0.62,4.5,"",null,"",null,false],
["Travon Walker","JAX","DL","@ BAL",4.4,0.2,2.8,10.5,0.12,"C",0.74,"2/7",0.84,4.4,"",null,"W",null,false],
["Blake Cashman","MIN","LB","vs BUF",8.0,3.2,7.2,13.8,0.28,"A",0.98,"6/7",0.51,8.0,"",null,"",null,true],
["Ernest Jones","SEA","LB","vs ARI",7.4,3.0,6.8,13.0,0.23,"A+",1.0,"5/8",0.49,7.4,"",null,"",null,true],
["Alex Singleton","DEN","LB","@ CAR",7.3,2.8,6.2,13.2,0.23,"F",1.0,"5/8",0.43,7.3,"",null,"",null,true],
["Eric Wilson","MIN","LB","vs BUF",7.2,2.8,6.5,12.8,0.22,"A",0.95,"2/7",0.93,7.2,"",null,"W",null,true],
["Jordyn Brooks","MIA","LB","vs DET",7.0,2.8,6.2,12.2,0.2,"B",0.9,"2/7",0.42,7.0,"",null,"W",null,true],
["Devin Bush","CHI","LB","vs TB",6.7,2.5,6.0,12.0,0.18,"A+",0.93,"3/8",0.29,6.7,"",null,"W",null,true],
["Fred Warner","SF","LB","vs LV",6.4,2.2,5.5,11.2,0.16,"B",0.99,"5/7",0.27,6.4,"",null,"",null,true],
["Jamien Sherwood","NYJ","LB","@ KC",6.3,2.5,5.5,11.5,0.16,"B",0.97,"4/8",0.56,6.3,"",null,"mine",null,true],
["Nakobe Dean","LV","LB","@ SF",6.3,2.2,5.5,11.5,0.16,"A",1.0,"5/8",0.51,6.3,"",null,"",null,true],
["Josiah Trotter","TB","LB","@ CHI",6.2,2.2,5.5,11.0,0.15,"A+",0.93,"3/7",0.81,6.2,"",null,"W",null,true],
["Jacob Rodriguez","MIA","LB","vs DET",6.2,2.5,5.5,11.5,0.16,"B",1.0,"4/7",0.56,6.2,"",null,"W",null,true],
["Nate Landman","LA","LB","@ WAS",6.2,2.2,5.5,11.2,0.15,"A+",0.86,"2/7",0.77,6.2,"",null,"W",null,true],
["Kendal Daniels","ATL","LB","vs CIN",6.1,1.5,5.2,11.5,0.16,"B",0.82,"4/8",0.76,6.1,"",null,"",null,true],
["Quay Walker","LV","LB","@ SF",6.1,2.2,5.2,11.2,0.15,"A",0.99,"3/8",0.39,6.1,"",null,"W",null,true],
["Sonny Styles","WAS","LB","vs LA",6.1,2.2,5.2,11.0,0.14,"A",0.94,"4/7",0.61,6.1,"",null,"",null,true],
["Roquan Smith","BAL","LB","vs JAX",6.0,2.2,5.2,11.2,0.15,"F",0.85,"3/8",0.6,6.0,"",null,"",null,true],
["Christian Elliss","NE","LB","vs GB",6.0,2.0,5.0,11.2,0.14,"F",0.99,"3/8",0.75,6.0,"",null,"",null,true],
["Carson Schwesinger","CLE","LB","@ NO",6.0,2.2,5.2,11.0,0.14,"A",1.0,"3/8",0.64,6.0,"",null,"",null,true],
["Zack Baun","PHI","LB","vs NYG",6.0,2.2,5.2,10.8,0.13,"B",1.0,"3/7",0.4,6.0,"",null,"W",null,true],
["Alex Anzalone","TB","LB","@ CHI",6.0,2.0,5.2,10.8,0.13,"A+",0.97,"3/8",0.86,6.0,"",null,"W",null,true],
["Quincy Williams","CLE","LB","@ NO",5.8,2.0,5.0,11.0,0.14,"A",0.99,"4/8",0.8,5.8,"",null,"W",null,true],
["Akeem Davis-Gaither","IND","LB","vs DAL",5.8,2.0,5.0,10.8,0.13,"C",0.88,"1/8",0.34,5.8,"",null,"W",null,true],
["Josh Metellus","MIN","DB","vs BUF",5.6,2.0,4.8,10.2,0.11,"A+",0.99,"2/7",0.38,5.6,"",null,"",null,false],
["Dane Belton","NYJ","DB","@ KC",5.4,2.0,4.8,10.0,0.1,"D",1.0,"3/8",0.47,5.4,"",null,"",null,false],
["Carlton Davis III","NE","DB","vs GB",5.3,1.8,4.5,10.0,0.11,"A+",0.95,"1/4",0.51,5.3,"",null,"",null,false],
["Devon Witherspoon","SEA","DB","vs ARI",5.3,1.8,4.5,10.0,0.1,"A+",0.99,"2/8",0.44,5.3,"",null,"",null,false],
["Jessie Bates","ATL","DB","vs CIN",5.2,1.5,4.2,10.2,0.11,"C-",0.98,"3/8",0.72,5.2,"",null,"W",null,false],
["Andrew Mukuba","PHI","DB","vs NYG",5.2,1.8,4.2,9.8,0.1,"D",0.99,"2/8",0.73,5.2,"",null,"",null,false],
["Jordan Battle","CIN","DB","@ ATL",5.2,1.8,4.2,10.0,0.1,"C",0.96,"3/7",0.58,5.2,"",null,"W",null,false],
["Antoine Winfield Jr.","TB","DB","@ CHI",5.2,1.8,4.5,9.8,0.09,"A+",0.96,"1/5",0.59,5.2,"",null,"W",null,false],
["Julian Love","SEA","DB","vs ARI",5.0,1.5,4.0,9.8,0.09,"A",0.98,"2/7",0.71,5.0,"",null,"W",null,false],
["Kevin Byard","NE","DB","vs GB",5.0,1.5,4.0,9.8,0.1,"C-",0.98,"1/8",0.74,5.0,"",null,"W",null,false],
["Jacob Parrish","TB","DB","@ CHI",5.0,1.8,4.2,9.2,0.08,"A",0.96,"4/7",0.54,5.0,"",null,"",null,false],
["Jeremy Chinn","LV","DB","@ SF",5.0,1.5,4.0,9.8,0.1,"C",1.0,"4/8",0.5,5.0,"",null,"W",null,false],
["Xavier Watts","ATL","DB","vs CIN",4.9,1.5,4.0,9.5,0.09,"C-",0.98,"5/8",0.45,4.9,"",null,"W",null,false],
["Nick Emmanwori","SEA","DB","vs ARI",4.9,1.2,4.0,10.0,0.11,"A",0.92,"2/7",0.98,4.9,"",null,"W",null,false],
["Evan Williams","GB","DB","@ NE",4.9,1.5,4.0,9.8,0.09,"F",1.0,"5/8",0.41,4.9,"",null,"",null,false],
["Marcus Jones","NE","DB","vs GB",4.8,1.2,4.0,9.5,0.09,"A+",0.84,"2/8",0.68,4.8,"",null,"W",null,false],
["Kamari Lassiter","HOU","DB","@ LAC",4.8,1.2,3.8,9.5,0.09,"A",1.0,"4/7",0.32,4.8,"",null,"W",null,false],
["Craig Woodson","NE","DB","vs GB",4.8,1.5,4.0,9.5,0.09,"C-",0.98,"1/7",0.36,4.8,"",null,"",null,false],
["Kyle Hamilton","BAL","DB","vs JAX",4.2,1.0,3.5,8.2,0.06,"F",0.96,"5/8",0.4,4.2,"",null,"mine",null,false]
],
"lineup":{"safe":[
{"slot":"QB","player":"Dak Prescott","team":"DAL","pos":"QB","matchup":"@ IND","mean":21.4,"floor":9.9,"p90":35.2,"p_boom":0.3,"grade":"A","note":""},
{"slot":"RB","player":"Kyren Williams","team":"LA","pos":"RB","matchup":"@ WAS","mean":14.4,"floor":4.2,"p90":26.8,"p_boom":0.23,"grade":"B","note":""},
{"slot":"RB","player":"Bucky Irving","team":"TB","pos":"RB","matchup":"@ CHI","mean":13.3,"floor":3.7,"p90":25.2,"p_boom":0.19,"grade":"D","note":""},
{"slot":"WR","player":"CeeDee Lamb","team":"DAL","pos":"WR","matchup":"@ IND","mean":15.4,"floor":3.1,"p90":31.2,"p_boom":0.27,"grade":"C","note":""},
{"slot":"WR","player":"Jaylen Waddle","team":"DEN","pos":"WR","matchup":"@ CAR","mean":6.6,"floor":0.8,"p90":14.5,"p_boom":0.03,"grade":"C-","note":""},
{"slot":"TE","player":"Brock Bowers","team":"LV","pos":"TE","matchup":"@ SF","mean":13.5,"floor":2.7,"p90":26.6,"p_boom":0.35,"grade":"C","note":""},
{"slot":"W/R/T","player":"Emanuel Wilson","team":"SEA","pos":"RB","matchup":"vs ARI","mean":6.5,"floor":0.0,"p90":17.7,"p_boom":0.07,"grade":"C-","note":""},
{"slot":"K","player":"Ka'imi Fairbairn","team":"HOU","pos":"K","matchup":"@ LAC","mean":9.7,"floor":2.0,"p90":18.8,"p_boom":0.33,"grade":"C","note":""},
{"slot":"D","player":"Kyle Hamilton","team":"BAL","pos":"DB","matchup":"vs JAX","mean":4.2,"floor":1.0,"p90":8.2,"p_boom":0.06,"grade":"F","note":"6.3 wtd-L4 (7.4 ssn), 96% snaps; 1 INT/4 PD, 0.113 tkl/snap; big dog: run script"},
{"slot":"LB","player":"Jamien Sherwood","team":"NYJ","pos":"LB","matchup":"@ KC","mean":6.3,"floor":2.5,"p90":11.5,"p_boom":0.16,"grade":"B","note":"8.2 wtd-L4 (7.0 ssn), 97% snaps; 0.133 tkl/snap; neutral volume; big dog: run script"}
],
"boom":[
{"slot":"QB","player":"Dak Prescott","team":"DAL","pos":"QB","matchup":"@ IND","mean":21.4,"floor":9.9,"p90":35.2,"p_boom":0.3,"grade":"A","note":""},
{"slot":"RB","player":"Bucky Irving","team":"TB","pos":"RB","matchup":"@ CHI","mean":13.3,"floor":3.7,"p90":25.2,"p_boom":0.19,"grade":"D","note":""},
{"slot":"RB","player":"Emanuel Wilson","team":"SEA","pos":"RB","matchup":"vs ARI","mean":6.5,"floor":0.0,"p90":17.7,"p_boom":0.07,"grade":"C-","note":""},
{"slot":"WR","player":"CeeDee Lamb","team":"DAL","pos":"WR","matchup":"@ IND","mean":15.4,"floor":3.1,"p90":31.2,"p_boom":0.27,"grade":"C","note":""},
{"slot":"WR","player":"Jaylen Waddle","team":"DEN","pos":"WR","matchup":"@ CAR","mean":6.6,"floor":0.8,"p90":14.5,"p_boom":0.03,"grade":"C-","note":""},
{"slot":"TE","player":"Brock Bowers","team":"LV","pos":"TE","matchup":"@ SF","mean":13.5,"floor":2.7,"p90":26.6,"p_boom":0.35,"grade":"C","note":""},
{"slot":"W/R/T","player":"Kyren Williams","team":"LA","pos":"RB","matchup":"@ WAS","mean":14.4,"floor":4.2,"p90":26.8,"p_boom":0.23,"grade":"B","note":""},
{"slot":"K","player":"Ka'imi Fairbairn","team":"HOU","pos":"K","matchup":"@ LAC","mean":9.7,"floor":2.0,"p90":18.8,"p_boom":0.33,"grade":"C","note":""},
{"slot":"D","player":"Kyle Hamilton","team":"BAL","pos":"DB","matchup":"vs JAX","mean":4.2,"floor":1.0,"p90":8.2,"p_boom":0.06,"grade":"F","note":"6.3 wtd-L4 (7.4 ssn), 96% snaps; 1 INT/4 PD, 0.113 tkl/snap; big dog: run script"},
{"slot":"LB","player":"Jamien Sherwood","team":"NYJ","pos":"LB","matchup":"@ KC","mean":6.3,"floor":2.5,"p90":11.5,"p_boom":0.16,"grade":"B","note":"8.2 wtd-L4 (7.0 ssn), 97% snaps; 0.133 tkl/snap; neutral volume; big dog: run script"}
]},
"bench":[
{"slot":"BN","player":"Khalil Shakir","team":"BUF","pos":"WR","matchup":"@ MIN","mean":6.2,"floor":0.0,"p90":14.0,"p_boom":0.03,"grade":"D","note":""},
{"slot":"BN","player":"TreVeyon Henderson","team":"NE","pos":"RB","matchup":"-","mean":0.0,"floor":0.0,"p90":0.0,"p_boom":0.0,"grade":"","note":""},
{"slot":"BN","player":"Deebo Samuel","team":"SF","pos":"WR","matchup":"vs LV","mean":5.5,"floor":0.0,"p90":13.2,"p_boom":0.03,"grade":"A","note":""},
{"slot":"IR","player":"Jordyn Tyson","team":"NO","pos":"WR","matchup":"-","mean":0.0,"floor":0.0,"p90":0.0,"p_boom":0.0,"grade":"","note":""},
{"slot":"BN","player":"Hunter Henry","team":"NE","pos":"TE","matchup":"vs GB","mean":5.1,"floor":0.0,"p90":12.7,"p_boom":0.06,"grade":"F","note":""},
{"slot":"BN","player":"Chase McLaughlin","team":"TB","pos":"K","matchup":"@ CHI","mean":9.5,"floor":2.0,"p90":18.3,"p_boom":0.31,"grade":"C","note":""}
],
"moves":["Move Jordyn Tyson to an IR slot (Yahoo IR; frees a bench spot, no drop needed).","Drop candidate: Chase McLaughlin (2nd K, @ CHI wk9, ROS 10.6/g); one K is enough outside bye weeks.","Low-value bench: TreVeyon Henderson ROS 4.4/g (-).","Low-value bench: Deebo Samuel ROS 5.7/g (vs LV).","Low-value bench: Khalil Shakir ROS 7.0/g (@ MIN).","QB: Dak Prescott bye wk 14 - stream that week","Week 9 roster"],
"waivers":[
{"pos":"LB","player":"Eric Wilson","team":"MIN","status":"W","pct":null,"ros":7.2,"wk":7.2,"gain":3.1,"verdict":"upgrade over starter","faab":"$15-23 (20%-30% of $76)","opp":"vs BUF"},
{"pos":"LB","player":"Jordyn Brooks","team":"MIA","status":"W","pct":null,"ros":7.0,"wk":7.0,"gain":2.9,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"vs DET"},
{"pos":"LB","player":"Devin Bush","team":"CHI","status":"W","pct":null,"ros":6.7,"wk":6.7,"gain":2.5,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"vs TB"},
{"pos":"LB","player":"Josiah Trotter","team":"TB","status":"W","pct":null,"ros":6.2,"wk":6.2,"gain":2.1,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"@ CHI"},
{"pos":"LB","player":"Jacob Rodriguez","team":"MIA","status":"W","pct":null,"ros":6.2,"wk":6.2,"gain":2.1,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"vs DET"},
{"pos":"LB","player":"Nate Landman","team":"LA","status":"W","pct":null,"ros":6.2,"wk":6.2,"gain":2.1,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"@ WAS"},
{"pos":"DL","player":"Andrew Van Ginkel","team":"MIN","status":"W","pct":null,"ros":5.8,"wk":5.8,"gain":1.6,"verdict":"upgrade over starter","faab":"$8-15 (10%-20% of $76)","opp":"vs BUF"},
{"pos":"DB","player":"Jessie Bates III","team":"ATL","status":"W","pct":null,"ros":5.2,"wk":5.2,"gain":1.0,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs CIN"},
{"pos":"DB","player":"Antoine Winfield Jr.","team":"TB","status":"W","pct":null,"ros":5.2,"wk":5.2,"gain":1.0,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"@ CHI"},
{"pos":"DB","player":"Jordan Battle","team":"CIN","status":"W","pct":null,"ros":5.2,"wk":5.2,"gain":1.0,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"@ ATL"},
{"pos":"DL","player":"George Karlaftis","team":"KC","status":"W","pct":null,"ros":5.1,"wk":5.1,"gain":1.0,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs NYJ"},
{"pos":"RB","player":"Dameon Pierce","team":"PHI","status":"W","pct":21,"ros":10.2,"wk":0.0,"gain":0.9,"verdict":"clear ROS upgrade","faab":"$3-8 (4%-10% of $76)","opp":"BYE/-"},
{"pos":"DB","player":"Julian Love","team":"SEA","status":"W","pct":null,"ros":5.0,"wk":5.0,"gain":0.9,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs ARI"},
{"pos":"DB","player":"Kevin Byard III","team":"NE","status":"W","pct":null,"ros":5.0,"wk":5.0,"gain":0.8,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs GB"},
{"pos":"DB","player":"Jeremy Chinn","team":"LV","status":"W","pct":null,"ros":5.0,"wk":5.0,"gain":0.8,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"@ SF"},
{"pos":"DL","player":"Maxx Crosby","team":"LV","status":"W","pct":null,"ros":5.0,"wk":5.0,"gain":0.8,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"@ SF"},
{"pos":"DL","player":"Quinnen Williams","team":"DAL","status":"W","pct":null,"ros":4.9,"wk":4.9,"gain":0.8,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"@ IND"},
{"pos":"DL","player":"Jalen Carter","team":"PHI","status":"W","pct":null,"ros":4.9,"wk":4.9,"gain":0.7,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs NYG"},
{"pos":"DL","player":"Dallas Turner","team":"MIN","status":"W","pct":null,"ros":4.7,"wk":4.7,"gain":0.6,"verdict":"upgrade over starter","faab":"$3-8 (4%-10% of $76)","opp":"vs BUF"},
{"pos":"WR","player":"Ryan Flournoy","team":"DAL","status":"W","pct":34,"ros":7.6,"wk":7.7,"gain":0.4,"verdict":"toss-up (within model error)","faab":"$0-1 (depth only)","opp":"@ IND"},
{"pos":"WR","player":"Malik Washington","team":"MIA","status":"W","pct":48,"ros":7.6,"wk":8.1,"gain":0.4,"verdict":"toss-up (within model error)","faab":"$0-1 (depth only)","opp":"vs DET"},
{"pos":"WR","player":"Keenan Allen","team":"IND","status":"W","pct":52,"ros":7.3,"wk":7.7,"gain":0.1,"verdict":"toss-up (within model error)","faab":"$0-1 (depth only)","opp":"vs DAL"},
{"pos":"QB","player":"C.J. Stroud","team":"HOU","status":"W","pct":76,"ros":18.8,"wk":18.3,"gain":-0.4,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"@ LAC"},
{"pos":"WR","player":"Mack Hollins","team":"NE","status":"W","pct":2,"ros":6.7,"wk":0.0,"gain":-0.5,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"BYE/-"},
{"pos":"QB","player":"Deshaun Watson","team":"CLE","status":"W","pct":12,"ros":18.8,"wk":19.2,"gain":-0.5,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"@ NO"},
{"pos":"WR","player":"Treylon Burks","team":"WAS","status":"W","pct":2,"ros":6.6,"wk":6.4,"gain":-0.6,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"vs LA"},
{"pos":"K","player":"Drew Stevens","team":"WAS","status":"W","pct":11,"ros":9.9,"wk":9.5,"gain":-0.7,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"vs LA"},
{"pos":"K","player":"Jason Myers","team":"SEA","status":"W","pct":91,"ros":9.9,"wk":10.6,"gain":-0.8,"verdict":"week-9 streamer","faab":"$0-1 (depth only)","opp":"vs ARI"},
{"pos":"WR","player":"Jordan Addison","team":"MIN","status":"W","pct":71,"ros":6.3,"wk":6.0,"gain":-0.9,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"vs BUF"},
{"pos":"RB","player":"Kendre Miller","team":"NO","status":"W","pct":24,"ros":8.3,"wk":8.8,"gain":-0.9,"verdict":"week-9 streamer","faab":"$0-1 (depth only)","opp":"vs CLE"},
{"pos":"K","player":"Jake Bates","team":"DET","status":"W","pct":65,"ros":9.7,"wk":10.7,"gain":-0.9,"verdict":"week-9 streamer","faab":"$0-1 (depth only)","opp":"@ MIA"},
{"pos":"K","player":"Wil Lutz","team":"DEN","status":"W","pct":15,"ros":9.6,"wk":9.3,"gain":-1.0,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"@ CAR"}
],
"boom_thr":{"QB":25,"RB":20,"WR":20,"TE":15,"K":12},
"scoring":"Pass 20 yd/pt (+5 at 375), TD 4, INT -1; Rush 10 yd/pt (+5 at 180), TD 6; Rec 0.5 PPR, 10 yd/pt (+5 at 200), TD 6; FL -2; 2pt 2. K: PAT +1/-1, FG 0.1 pt per made-FG yard, missed FG 0-29 yds -1. IDP: solo .75, ast .25, sack 3, INT 5, FF 5, FR 2, TD 6, PD 1, TFL 1.5, safety 3.",
"backtest":"Offense backtest (mean over weeks, by position):\n               spearman    hit  top_avg    mae   bias\npos model                                           \nK   base         0.157  0.438    8.794  4.296  0.400\n    base_inj     0.157  0.438    8.794  4.296  0.400\n    model        0.107  0.458    8.596  4.245  0.282\nQB  base         0.378  0.521   19.315  8.795  3.616\n    base_inj     0.585  0.583   21.407  7.212  1.937\n    model        0.652  0.625   21.697  6.829  0.603\nRB  base         0.424  0.719   12.033  6.739  1.721\n    base_inj     0.605  0.812   13.354  5.678  0.542\n    model        0.643  0.823   13.312  5.463 -0.209\nTE  base         0.431  0.354    8.394  4.193  0.528\n    base_inj     0.489  0.375    8.506  3.944  0.227\n    model        0.576  0.354    8.546  3.525 -0.619\nWR  base         0.417  0.556    9.425  5.052  1.527\n    base_inj     0.602  0.625   10.561  4.353  0.635\n    model        0.654  0.639   10.621  4.116 -0.278 \n\nAll positions:\n           spearman    hit  top_avg    mae\nmodel                                    \nbase         0.362  0.517   11.592  5.815\nbase_inj     0.488  0.567   12.524  5.097\nmodel        0.527  0.580   12.554  4.836\n\nCalibration (n=1083): below P10 0.049, above P90 0.104\n  p_ge15: predicted 0.161 observed 0.187\n  p_ge20: predicted 0.084 observed 0.101\n  p_boom: predicted 0.098 observed 0.118\n  P(>=20) reliability:\n                 n   pred    obs\n_b                              \n(-0.01, 0.03]  502  0.008  0.016\n(0.03, 0.08]   255  0.052  0.039\n(0.08, 0.15]   110  0.109  0.127\n(0.15, 0.25]   103  0.202  0.272\n(0.25, 0.4]     78  0.320  0.321\n(0.4, 1.0]      35  0.467  0.686\n"
};
const TRADES: TradeData = {"week":9,"weeks":"9-17","me":"Breeces Pieces","sources":["FantasyCalc redraft trade values (12-team, 1QB, half PPR; 195 players, fetched 2026-11-03)","FantasyPros ROS half-PPR overall ECR (396 players, 4 experts, updated 11/03)","FantasyPros ROS IDP ECR (181 players, 2 experts, updated 11/01)"],"minRatio":0.4,"minGain":3.0,"nWinWin":440,"nKept":70,"odds":[{"team":"High Speed Ja’Marr Chase","p":0.87},{"team":"Teach me how2 Griddy","p":0.87},{"team":"Nico(demus) Brown","p":0.86},{"team":"Daejon Love","p":0.78},{"team":"Breeces Pieces","p":0.73},{"team":"Run it back with Runningbacks?","p":0.72},{"team":"Eggsbuka Tyrone","p":0.4},{"team":"Psoas-spended","p":0.4},{"team":"We Are Christian Kirk","p":0.14},{"team":"Learn How2 Griddy Already","p":0.12},{"team":"LONDON Bridge is Falling Down","p":0.11},{"team":"4 + 9 IRs and counting","p":0.0}],"tests":[{"test":"star-for-scrub rejected","trade":"T4 gives Dak Prescott for T.J. Watt (T1)","gain_me":-6.6,"gain_them":7.5,"passed":true},{"test":"surplus-for-need swap is mutual","trade":"RB-rich team gives Bucky Irving for Jaxon Smith-Njigba","gain_me":50.1,"gain_them":50.3,"passed":true}],
"rows":[
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Garrett Wilson (WR, NYJ)","give":"Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":8.9,"gb":9.5,"bal":0.93,"minG":8.9,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":7.71,"moves":"T8 drops Caleb Douglas; T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich; T4 adds FA Kendre Miller","reason":"You: WR +1.1, IDP -0.5 = net +1.0/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, IDP +0.4, WR -1.4 = net +1.2/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Garrett Wilson (WR, NYJ) + Ernest Jones IV (LB, SEA)","give":"Hunter Henry (TE, NE)","ga":11.7,"gb":8.5,"bal":0.73,"minG":8.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":8.54,"moves":"T4 adds FA C.J. Stroud; T8 adds FA Greg Dulcich","reason":"You: WR +1.1, IDP +0.8, TE -0.4 = net +1.3/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +3.3, IDP -0.8, WR -1.4 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Drake London (WR, ATL)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":8.3,"gb":9.4,"bal":0.88,"minG":8.3,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.25,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud","reason":"You: WR +2.0, FLEX +1.8, RB +1.6, TE -4.1 = net +1.2/wk. LONDON Bridge is Falling Down: TE +7.0, FLEX -1.3, RB -2.1, WR -2.2 = net +1.3/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Garrett Wilson (WR, NYJ) + Jacoby Brissett (QB, ARI)","give":"Dak Prescott (QB, DAL) + Hunter Henry (TE, NE)","ga":7.8,"gb":10.3,"bal":0.76,"minG":7.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.08,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich","reason":"You: WR +1.1, QB -0.4 = net +0.7/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, QB +0.5, WR -1.4 = net +1.3/wk; Brissett was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Garrett Wilson (WR, NYJ)","give":"Hunter Henry (TE, NE) + Jaylen Waddle (WR, DEN)","ga":13.0,"gb":7.6,"bal":0.58,"minG":7.6,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.16,"moves":"T8 drops Caleb Douglas; T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich; T4 adds FA Jordyn Brooks","reason":"You: WR +1.1, IDP +0.5 = net +1.5/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, WR -1.3 = net +1.0/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Garrett Wilson (WR, NYJ) + Patrick Mahomes (QB, KC)","give":"Hunter Henry (TE, NE)","ga":7.4,"gb":9.7,"bal":0.77,"minG":7.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":10.85,"moves":"T4 adds FA Greg Dulcich; T8 adds FA C.J. Stroud","reason":"You: WR +1.1 = net +0.9/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, QB +0.3, WR -1.4 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Garrett Wilson (WR, NYJ) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE)","ga":7.2,"gb":10.0,"bal":0.72,"minG":7.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":9.15,"moves":"T4 adds FA C.J. Stroud; T8 adds FA Greg Dulcich","reason":"You: WR +1.2, TE -0.4 = net +0.7/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +3.3, WR -1.9 = net +1.4/wk; Vele was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Drake London (WR, ATL) + Jacoby Brissett (QB, ARI)","give":"Hunter Henry (TE, NE)","ga":12.9,"gb":7.1,"bal":0.55,"minG":7.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":11.17,"moves":"T4 adds FA C.J. Stroud; T8 adds FA Greg Dulcich","reason":"You: WR +2.0, TE -0.4 = net +1.4/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +3.3, WR -2.2 = net +0.8/wk; Brissett was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Braelon Allen (RB, NYJ) + Matthew Golden (WR, GB)","give":"Brock Bowers (TE, LV) + Kyren Williams (RB, LA)","ga":6.8,"gb":7.2,"bal":0.95,"minG":6.8,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.48,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T6 adds FA C.J. Stroud; T6 adds FA Jordyn Brooks","reason":"You: WR +3.7, RB +1.4, FLEX -0.4, TE -4.1 = net +0.6/wk. High Speed Ja’Marr Chase: TE +4.6, IDP +0.5, FLEX -1.0, RB -1.4, WR -1.6 = net +0.7/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Garrett Wilson (WR, NYJ) + Jacoby Brissett (QB, ARI)","give":"Hunter Henry (TE, NE)","ga":6.7,"gb":12.3,"bal":0.55,"minG":6.7,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":8.52,"moves":"T4 adds FA C.J. Stroud; T8 adds FA Greg Dulcich","reason":"You: WR +1.1, TE -0.4 = net +0.7/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +3.3, WR -1.4 = net +1.6/wk; Brissett was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-1","get":"Garrett Wilson (WR, NYJ)","give":"Hunter Henry (TE, NE)","ga":9.9,"gb":6.5,"bal":0.66,"minG":6.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":8.24,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich","reason":"You: WR +1.1 = net +1.1/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, WR -1.4 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Woody Marks (RB, HOU)","give":"Emanuel Wilson (RB, SEA) + Hunter Henry (TE, NE)","ga":10.7,"gb":6.1,"bal":0.57,"minG":6.1,"accept":"Fair on paper","note":"consensus values are close","ratio":0.8,"moves":"T8 drops Caleb Douglas; T4 adds FA C.J. Stroud; T4 adds FA Malik Washington; T4 adds FA Greg Dulcich","reason":"You: FLEX +0.8, RB +0.7 = net +1.4/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, FLEX -1.3 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Dak Prescott (QB, DAL) + Hunter Henry (TE, NE)","ga":13.4,"gb":5.9,"bal":0.44,"minG":5.9,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.66,"moves":"T8 drops Caleb Douglas; T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich; T4 adds FA Jordyn Brooks","reason":"You: WR +2.0, IDP +0.5, QB -0.8 = net +1.5/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, QB +0.5, WR -2.2 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"James Cook III (RB, BUF)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":14.4,"gb":5.8,"bal":0.4,"minG":5.8,"accept":"Fair on paper","note":"consensus values are close","ratio":1.08,"moves":"T8 drops Caleb Douglas; T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T4 adds FA Malik Washington","reason":"You: RB +3.3, FLEX +2.7, TE -4.1 = net +1.8/wk. LONDON Bridge is Falling Down: TE +7.0, FLEX -1.4, RB -4.6 = net +1.0/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Emanuel Wilson (RB, SEA) + Hunter Henry (TE, NE)","ga":10.3,"gb":5.8,"bal":0.56,"minG":5.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":4.96,"moves":"T8 drops Caleb Douglas; T4 adds FA Kendre Miller; T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich","reason":"You: WR +2.0, FLEX -0.6 = net +1.3/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, FLEX +0.3, WR -2.2 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Sam Darnold (QB, SEA) + Christian Watson (WR, GB)","give":"Dak Prescott (QB, DAL)","ga":5.7,"gb":6.8,"bal":0.84,"minG":5.7,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.34,"moves":"T4 adds FA C.J. Stroud; T12 adds FA C.J. Stroud; T12 adds FA Drew Stevens","reason":"You: WR +1.1, QB -0.6 = net +0.4/wk. Run it back with Runningbacks?: K +0.8, QB +0.6 = net +0.9/wk; Darnold/Watson were mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Matthew Golden (WR, GB) + Aaron Jones Sr. (RB, MIN)","give":"Brock Bowers (TE, LV) + Jaylen Waddle (WR, DEN)","ga":5.7,"gb":6.4,"bal":0.89,"minG":5.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.64,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T6 adds FA Kendre Miller; T6 adds FA C.J. Stroud","reason":"You: WR +3.7, FLEX +0.6, RB +0.3, TE -4.1 = net +0.7/wk. High Speed Ja’Marr Chase: TE +4.6, RB -0.4, WR -1.6, FLEX -1.8 = net +0.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Ashton Jeanty (RB, LV) + Justin Jefferson (WR, MIN)","give":"Kyren Williams (RB, LA)","ga":8.0,"gb":5.2,"bal":0.65,"minG":5.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.56,"moves":"T4 adds FA C.J. Stroud; T12 adds FA C.J. Stroud; T12 adds FA Drew Stevens","reason":"You: WR +1.8, RB -0.7 = net +0.8/wk. Run it back with Runningbacks?: FLEX +1.1, K +0.8, WR -0.9 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-2","get":"Ashton Jeanty (RB, LV) + Christian Watson (WR, GB)","give":"Kyren Williams (RB, LA) + Jaylen Waddle (WR, DEN)","ga":5.3,"gb":5.0,"bal":0.96,"minG":5.0,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.29,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Jordyn Brooks; T12 adds FA C.J. Stroud","reason":"You: WR +1.0, IDP +0.5, FLEX -0.3, RB -0.7 = net +0.4/wk. Run it back with Runningbacks?: FLEX +1.2 = net +0.6/wk; Watson was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Ernest Jones IV (LB, SEA) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE) + Jaylen Waddle (WR, DEN)","ga":5.0,"gb":9.8,"bal":0.51,"minG":5.0,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.42,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich","reason":"You: IDP +0.8 = net +0.6/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, IDP -0.8 = net +1.4/wk; Vele was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Garrett Wilson (WR, NYJ)","give":"Brock Bowers (TE, LV) + Jaylen Waddle (WR, DEN)","ga":7.5,"gb":4.9,"bal":0.66,"minG":4.9,"accept":"Fair on paper","note":"consensus values are close","ratio":1.05,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud","reason":"You: FLEX +2.3, RB +1.6, WR +1.1, TE -4.1 = net +1.0/wk. LONDON Bridge is Falling Down: TE +7.0, WR -1.3, RB -2.3, FLEX -2.6 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Javonte Williams (RB, DAL) + Drake London (WR, ATL)","give":"Brock Bowers (TE, LV)","ga":7.4,"gb":4.7,"bal":0.64,"minG":4.7,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.34,"moves":"T4 adds FA Greg Dulcich; T8 adds FA Kendre Miller","reason":"You: FLEX +2.3, WR +2.0, RB +1.6, QB -0.7, TE -4.1 = net +1.1/wk. LONDON Bridge is Falling Down: TE +7.0, FLEX -1.8, WR -2.2, RB -2.3 = net +0.7/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-2","get":"Chris Olave (WR, NO) + Ashton Jeanty (RB, LV)","give":"Bucky Irving (RB, TB) + Jaylen Waddle (WR, DEN)","ga":4.5,"gb":4.5,"bal":0.98,"minG":4.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.49,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Jordyn Brooks; T12 adds FA C.J. Stroud","reason":"You: WR +3.5, IDP +0.5, RB -3.1 = net +0.6/wk. Run it back with Runningbacks?: RB +2.1, FLEX +1.0, WR -2.6 = net +0.3/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Daejon Love","bid":1,"kind":"1-for-2","get":"DK Metcalf (WR, PIT) + Kyler Murray (QB, MIN)","give":"Dak Prescott (QB, DAL)","ga":10.3,"gb":4.4,"bal":0.43,"minG":4.4,"accept":"Fair on paper","note":"consensus values are close","ratio":0.83,"moves":"T4 adds FA C.J. Stroud; T1 adds FA Drew Stevens; T1 adds FA C.J. Stroud","reason":"You: WR +1.3, QB -0.5 = net +0.8/wk. Daejon Love: K +1.0, QB +0.5, FLEX -0.3 = net +0.7/wk; Murray was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Ernest Jones IV (LB, SEA)","give":"Hunter Henry (TE, NE) + Jaylen Waddle (WR, DEN)","ga":4.4,"gb":11.0,"bal":0.4,"minG":4.4,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.11,"moves":"T8 drops Caleb Douglas; T4 adds FA C.J. Stroud; T4 adds FA Malik Washington; T4 adds FA Greg Dulcich","reason":"You: IDP +0.8 = net +0.6/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, IDP -0.8 = net +1.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Puka Nacua (WR, LA) + Chase Brown (RB, CIN)","give":"Bucky Irving (RB, TB) + Brock Bowers (TE, LV)","ga":4.1,"gb":5.7,"bal":0.72,"minG":4.1,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.2,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T9 adds FA Drew Stevens; T9 adds FA Jordyn Brooks","reason":"You: WR +6.2, RB -1.6, TE -4.1 = net +0.7/wk. Psoas-spended: TE +4.5, RB +1.6, WR -5.4 = net +0.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Ja'Marr Chase (WR, CIN) + Kyle Pitts Sr. (TE, ATL)","give":"Bucky Irving (RB, TB) + Hunter Henry (TE, NE)","ga":4.0,"gb":6.0,"bal":0.67,"minG":4.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.69,"moves":"T4 adds FA Kendre Miller; T4 adds FA C.J. Stroud; T6 adds FA Greg Dulcich; T6 adds FA C.J. Stroud","reason":"You: WR +6.7, FLEX -0.5, RB -5.6 = net +0.5/wk; Henry was mostly bench. High Speed Ja’Marr Chase: RB +4.6, TE +0.5, WR -4.6 = net +0.4/wk; Pitts was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Matthew Golden (WR, GB) + Rhamondre Stevenson (RB, NE)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":3.9,"gb":9.7,"bal":0.41,"minG":3.9,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.78,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T6 adds FA C.J. Stroud; T6 adds FA Jordyn Brooks","reason":"You: WR +3.7, FLEX +1.0, TE -4.1 = net +0.5/wk. High Speed Ja’Marr Chase: TE +4.6, IDP +0.5, RB -0.5, WR -1.6, FLEX -1.9 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Matthew Golden (WR, GB) + Michael Wilson (WR, ARI)","give":"CeeDee Lamb (WR, DAL) + Jaylen Waddle (WR, DEN)","ga":3.7,"gb":6.5,"bal":0.58,"minG":3.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.61,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Jordyn Brooks; T6 adds FA Greg Dulcich; T6 adds FA C.J. Stroud","reason":"You: IDP +0.5 = net +0.2/wk. High Speed Ja’Marr Chase: WR +2.4, FLEX -1.2 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Matthew Golden (WR, GB) + Aaron Jones Sr. (RB, MIN)","give":"Kyren Williams (RB, LA) + Hunter Henry (TE, NE)","ga":7.0,"gb":3.7,"bal":0.53,"minG":3.7,"accept":"Fair on paper","note":"consensus values are close","ratio":0.83,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich; T6 adds FA C.J. Stroud; T6 adds FA Greg Dulcich","reason":"You: WR +3.7, RB -2.6 = net +0.7/wk; Henry was mostly bench. High Speed Ja’Marr Chase: RB +2.2, TE +0.5, FLEX -0.5, WR -1.6 = net +0.3/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"1-for-2","get":"Michael Wilson (WR, ARI) + Rhamondre Stevenson (RB, NE)","give":"Kyren Williams (RB, LA)","ga":3.7,"gb":5.9,"bal":0.62,"minG":3.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.69,"moves":"T4 adds FA C.J. Stroud; T6 adds FA Greg Dulcich; T6 adds FA C.J. Stroud; T6 adds FA Jordyn Brooks","reason":"You: WR +2.5, RB -2.4 = net +0.1/wk. High Speed Ja’Marr Chase: RB +2.4, IDP +0.5, WR -0.4, FLEX -1.3 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Daejon Love","bid":1,"kind":"1-for-2","get":"DK Metcalf (WR, PIT) + Tyler Warren (TE, IND)","give":"Emanuel Wilson (RB, SEA)","ga":3.4,"gb":5.8,"bal":0.59,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":4.07,"moves":"T4 adds FA Kendre Miller; T1 adds FA C.J. Stroud; T1 adds FA Drew Stevens","reason":"You: WR +1.3, FLEX -0.3, QB -0.7 = net +0.4/wk. Daejon Love: K +1.0 = net +0.6/wk; Warren was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Teach me how2 Griddy","bid":11,"kind":"2-for-2","get":"Jaxon Smith-Njigba (WR, SEA) + Cam Skattebo (RB, NYG)","give":"Bucky Irving (RB, TB) + Emanuel Wilson (RB, SEA)","ga":3.4,"gb":4.3,"bal":0.79,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.16,"moves":"T4 adds FA Kendre Miller; T4 adds FA C.J. Stroud; T11 adds FA Greg Dulcich","reason":"You: WR +6.1, FLEX -0.4, RB -5.2 = net +0.5/wk. Teach me how2 Griddy: RB +5.3, FLEX +0.6, WR -5.7 = net +0.2/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Garrett Wilson (WR, NYJ)","give":"Brock Bowers (TE, LV) + Jamien Sherwood (LB, NYJ)","ga":3.3,"gb":6.3,"bal":0.53,"minG":3.3,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.21,"moves":"T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud","reason":"You: FLEX +2.3, RB +1.6, WR +1.1, IDP -0.5, TE -4.1 = net +0.6/wk. LONDON Bridge is Falling Down: TE +7.0, IDP +0.4, WR -1.4, RB -2.3, FLEX -2.7 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"James Cook III (RB, BUF) + Ernest Jones IV (LB, SEA)","give":"Bucky Irving (RB, TB) + Hunter Henry (TE, NE)","ga":3.2,"gb":6.8,"bal":0.48,"minG":3.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.49,"moves":"T4 adds FA C.J. Stroud; T4 adds FA Greg Dulcich","reason":"You: IDP +0.8, WR -0.5 = net +0.7/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.4, FLEX -0.4, IDP -0.8 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Nico(demus) Brown","bid":7,"kind":"2-for-1","get":"Kenneth Walker III (RB, KC)","give":"Brock Bowers (TE, LV) + Kyren Williams (RB, LA)","ga":6.0,"gb":3.2,"bal":0.53,"minG":3.2,"accept":"Fair on paper","note":"consensus values are close","ratio":0.92,"moves":"T7 drops Josh Downs; T4 adds FA Greg Dulcich; T4 adds FA C.J. Stroud; T4 adds FA Malik Washington","reason":"You: RB +5.0, TE -4.1 = net +0.8/wk. Nico(demus) Brown: TE +5.0, RB -4.7 = net +0.2/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Learn How2 Griddy Already","bid":2,"kind":"2-for-1","get":"DJ Moore (WR, BUF)","give":"Emanuel Wilson (RB, SEA) + Jamien Sherwood (LB, NYJ)","ga":4.2,"gb":3.1,"bal":0.74,"minG":3.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.0,"moves":"T2 drops Seth McGowan; T4 adds FA Kendre Miller; T4 adds FA C.J. Stroud; T4 adds FA Jordyn Brooks","reason":"You: WR +0.9, FLEX -0.4 = net +0.5/wk. Learn How2 Griddy Already: FLEX +0.6, IDP +0.5, WR -0.9 = net +0.4/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Javonte Williams (RB, DAL)","give":"Isaiah Likely (TE, NYG) + DK Metcalf (WR, PIT)","ga":12.5,"gb":10.2,"bal":0.81,"minG":10.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.79,"moves":"T8 drops Caleb Douglas; T1 adds FA C.J. Stroud; T1 adds FA Drew Stevens","reason":"Daejon Love: FLEX +2.4, K +1.0, RB +0.7, TE -1.9 = net +1.7/wk. LONDON Bridge is Falling Down: TE +4.5, WR +0.8, FLEX -1.8, RB -2.3 = net +1.2/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Patrick Mahomes (QB, KC)","give":"Colston Loveland (TE, CHI) + Kirk Cousins (QB, LV)","ga":8.1,"gb":7.1,"bal":0.87,"minG":7.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.68,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +4.1, FLEX +0.5, IDP -0.5, QB -1.0, TE -2.1 = net +1.0/wk. LONDON Bridge is Falling Down: TE +4.8, QB +1.2, RB -2.3, FLEX -2.5 = net +1.1/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"1-for-2","get":"George Kittle (TE, SF) + Ollie Gordon II (RB, MIA)","give":"James Cook III (RB, BUF)","ga":12.0,"gb":7.0,"bal":0.58,"minG":7.0,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.6,"moves":"T8 drops Caleb Douglas; T10 adds FA Greg Dulcich; T10 adds FA Kendre Miller","reason":"LONDON Bridge is Falling Down: TE +5.5, RB -3.7 = net +1.6/wk. We Are Christian Kirk: RB +3.8, TE -2.8 = net +0.9/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-2","get":"Colston Loveland (TE, CHI) + Kirk Cousins (QB, LV)","give":"Isaiah Likely (TE, NYG) + Tetairoa McMillan (WR, CAR)","ga":7.1,"gb":6.7,"bal":0.94,"minG":6.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.48,"moves":"T1 adds FA Drew Stevens; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens; T3 adds FA Jordyn Brooks","reason":"Daejon Love: K +1.0, QB +0.9, TE +0.8, FLEX -0.3, WR -1.3 = net +0.7/wk. 4 + 9 IRs and counting: WR +2.2, TE -0.4, QB -1.4 = net +0.5/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Javonte Williams (RB, DAL)","give":"Isaiah Likely (TE, NYG) + Mike Evans (WR, SF)","ga":6.5,"gb":14.2,"bal":0.46,"minG":6.5,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.21,"moves":"T8 drops Caleb Douglas; T1 adds FA C.J. Stroud; T1 adds FA Drew Stevens","reason":"Daejon Love: FLEX +2.4, K +1.0, RB +0.7, WR -0.9, TE -1.9 = net +1.0/wk. LONDON Bridge is Falling Down: TE +4.5, WR +1.1, FLEX -1.4, RB -2.3 = net +1.9/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"1-for-2","get":"George Kittle (TE, SF) + Jameson Williams (WR, DET)","give":"James Cook III (RB, BUF)","ga":6.5,"gb":9.0,"bal":0.72,"minG":6.5,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.62,"moves":"T8 drops Caleb Douglas; T10 adds FA Greg Dulcich; T10 adds FA Malik Washington","reason":"LONDON Bridge is Falling Down: TE +5.5, WR +1.7, FLEX -1.4, RB -4.9 = net +0.8/wk. We Are Christian Kirk: RB +4.3, FLEX +2.3, WR -2.5, TE -2.8 = net +1.2/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Woody Marks (RB, HOU)","give":"Rachaad White (RB, WAS) + Brenton Strange (TE, JAX)","ga":14.4,"gb":6.4,"bal":0.45,"minG":6.4,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.64,"moves":"T8 drops Caleb Douglas; T7 adds FA Drew Stevens","reason":"Nico(demus) Brown: FLEX +1.3, K +1.0, TE -0.5 = net +1.6/wk. LONDON Bridge is Falling Down: TE +2.2, FLEX -1.2 = net +0.8/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"1-for-2","get":"George Kittle (TE, SF) + Derrick Henry (RB, BAL)","give":"James Cook III (RB, BUF)","ga":12.2,"gb":6.2,"bal":0.51,"minG":6.2,"accept":"Fair on paper","note":"consensus values are close","ratio":1.02,"moves":"T8 drops Caleb Douglas; T10 adds FA Greg Dulcich; T10 adds FA Kendre Miller","reason":"LONDON Bridge is Falling Down: TE +5.5, FLEX -0.4, RB -3.3 = net +1.7/wk. We Are Christian Kirk: RB +3.6, TE -2.8 = net +0.8/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Garrett Wilson (WR, NYJ)","give":"Colston Loveland (TE, CHI) + Tre Tucker (WR, LV)","ga":6.0,"gb":7.2,"bal":0.84,"minG":6.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.61,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +2.0, WR +0.7, FLEX +0.6, IDP -0.5, TE -2.1 = net +0.8/wk. LONDON Bridge is Falling Down: TE +4.8, RB -0.4, WR -0.7, FLEX -2.5 = net +1.1/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Javonte Williams (RB, DAL)","give":"Colston Loveland (TE, CHI) + Rashee Rice (WR, KC)","ga":8.8,"gb":6.0,"bal":0.68,"minG":6.0,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.24,"moves":"T8 drops Caleb Douglas; T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller; T3 adds FA Jordyn Brooks","reason":"4 + 9 IRs and counting: RB +4.1, FLEX +0.5, WR -1.0, TE -2.1 = net +1.3/wk. LONDON Bridge is Falling Down: TE +4.8, FLEX -1.9, RB -2.3 = net +0.8/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Garrett Wilson (WR, NYJ)","give":"Colston Loveland (TE, CHI) + Zach Charbonnet (RB, SEA)","ga":5.8,"gb":7.5,"bal":0.77,"minG":5.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.38,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +2.0, WR +1.0, FLEX +0.3, IDP -0.5, TE -2.1 = net +0.8/wk. LONDON Bridge is Falling Down: TE +4.8, RB -0.3, WR -1.4, FLEX -1.9 = net +1.0/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Garrett Wilson (WR, NYJ) + Ernest Jones IV (LB, SEA)","give":"Brenton Strange (TE, JAX)","ga":5.8,"gb":5.8,"bal":1.0,"minG":5.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":6.22,"moves":"T7 drops Josh Downs; T8 adds FA Greg Dulcich","reason":"Nico(demus) Brown: IDP +0.8, TE -0.5 = net +0.6/wk. LONDON Bridge is Falling Down: TE +2.8, IDP -0.8, WR -1.4 = net +0.7/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-2","get":"George Kittle (TE, SF) + Anthony Hill Jr. (LB, TEN)","give":"Javonte Williams (RB, DAL) + Ernest Jones IV (LB, SEA)","ga":7.6,"gb":5.7,"bal":0.75,"minG":5.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.61,"moves":"T10 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: TE +5.5, IDP +0.3, RB -2.3, FLEX -2.5 = net +0.9/wk. We Are Christian Kirk: FLEX +2.0, RB +2.0, IDP -0.3, TE -2.8 = net +0.9/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-2","get":"Josh Allen (QB, BUF) + George Kittle (TE, SF)","give":"James Cook III (RB, BUF) + Patrick Mahomes (QB, KC)","ga":6.1,"gb":5.5,"bal":0.9,"minG":5.5,"accept":"Fair on paper","note":"consensus values are close","ratio":1.01,"moves":"T10 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: TE +5.5, QB +2.7, FLEX -2.5, RB -4.9 = net +0.7/wk. We Are Christian Kirk: RB +4.3, FLEX +2.3, TE -2.8, QB -2.9 = net +0.8/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Woody Marks (RB, HOU) + Garrett Wilson (WR, NYJ)","give":"Colston Loveland (TE, CHI)","ga":5.2,"gb":8.5,"bal":0.62,"minG":5.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.98,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T8 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +2.0, WR +1.0, IDP -0.5, TE -2.1 = net +0.7/wk. LONDON Bridge is Falling Down: TE +4.8, WR -1.4, FLEX -1.9 = net +1.1/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-2","get":"George Kittle (TE, SF) + George Pickens (WR, DAL)","give":"Javonte Williams (RB, DAL) + Garrett Wilson (WR, NYJ)","ga":5.1,"gb":8.2,"bal":0.62,"minG":5.1,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.69,"moves":"T10 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: TE +5.5, RB -2.3, FLEX -2.5 = net +0.6/wk. We Are Christian Kirk: FLEX +2.0, RB +2.0, TE -2.8 = net +1.2/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Rachaad White (RB, WAS) + Brenton Strange (TE, JAX)","ga":8.4,"gb":5.0,"bal":0.59,"minG":5.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.97,"moves":"T8 drops Caleb Douglas; T7 adds FA Drew Stevens","reason":"Nico(demus) Brown: K +1.0, WR +0.5, TE -0.5 = net +0.9/wk. LONDON Bridge is Falling Down: TE +2.2, WR -2.2 = net +0.5/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-2","get":"Kirk Cousins (QB, LV) + Tre Tucker (WR, LV)","give":"Mike Evans (WR, SF) + Kyler Murray (QB, MIN)","ga":5.0,"gb":4.9,"bal":0.98,"minG":4.9,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.32,"moves":"T1 adds FA Drew Stevens; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens; T3 adds FA Jordyn Brooks","reason":"Daejon Love: K +1.0, QB +0.7, WR -0.7 = net +0.5/wk; Murray was mostly bench. 4 + 9 IRs and counting: WR +1.6, QB -1.2 = net +0.4/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-1","get":"Justin Jefferson (WR, MIN)","give":"Kirk Cousins (QB, LV)","ga":4.9,"gb":6.0,"bal":0.81,"minG":4.9,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":14.44,"moves":"T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens; T3 adds FA Jordyn Brooks; T12 adds FA Drew Stevens","reason":"4 + 9 IRs and counting: WR +1.6, QB -1.4 = net +0.3/wk. Run it back with Runningbacks?: QB +1.1, K +0.8, WR -0.9 = net +0.5/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"We Are Christian Kirk","bid":10,"kind":"1-for-1","get":"George Kittle (TE, SF)","give":"Javonte Williams (RB, DAL)","ga":4.8,"gb":8.5,"bal":0.57,"minG":4.8,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.61,"moves":"T10 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: TE +5.5, RB -2.3, FLEX -2.5 = net +0.6/wk. We Are Christian Kirk: FLEX +2.0, RB +2.0, TE -2.8 = net +1.1/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-1","get":"Kirk Cousins (QB, LV)","give":"Mike Evans (WR, SF) + Kyler Murray (QB, MIN)","ga":6.0,"gb":4.7,"bal":0.78,"minG":4.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.12,"moves":"T1 adds FA Drew Stevens; T1 adds FA C.J. Stroud; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens","reason":"Daejon Love: QB +1.2, K +1.0, FLEX -0.3, WR -0.9 = net +0.6/wk; Murray was mostly bench. 4 + 9 IRs and counting: WR +1.9, IDP -0.5, QB -1.2 = net +0.4/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Drake London (WR, ATL)","give":"Colston Loveland (TE, CHI) + Rashee Rice (WR, KC)","ga":8.8,"gb":4.5,"bal":0.52,"minG":4.5,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.28,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +2.0, WR +1.3, FLEX +0.6, IDP -0.5, TE -2.1 = net +1.3/wk. LONDON Bridge is Falling Down: TE +4.8, RB -0.4, WR -1.4, FLEX -2.4 = net +0.6/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Drake London (WR, ATL)","give":"Colston Loveland (TE, CHI) + Kyle Monangai (RB, CHI)","ga":8.4,"gb":4.5,"bal":0.53,"minG":4.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.99,"moves":"T3 adds FA Greg Dulcich; T3 adds FA Kendre Miller; T3 adds FA C.J. Stroud; T8 adds FA C.J. Stroud","reason":"4 + 9 IRs and counting: RB +2.6, WR +1.7, FLEX +0.4, IDP -0.5, K -0.5, TE -2.1 = net +1.5/wk. LONDON Bridge is Falling Down: TE +4.8, QB +0.6, FLEX -0.8, RB -2.1, WR -2.2 = net +0.3/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-1","get":"Colston Loveland (TE, CHI)","give":"Isaiah Likely (TE, NYG) + DK Metcalf (WR, PIT)","ga":6.8,"gb":4.3,"bal":0.64,"minG":4.3,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.73,"moves":"T1 adds FA C.J. Stroud; T1 adds FA Drew Stevens; T3 adds FA Kendre Miller; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens","reason":"Daejon Love: K +1.0, TE +0.8, FLEX -0.3 = net +0.9/wk. 4 + 9 IRs and counting: WR +1.2, TE -0.4, IDP -0.5 = net +0.6/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Ernest Jones IV (LB, SEA)","give":"Colston Loveland (TE, CHI) + KC Concepcion Jr. (WR, CLE)","ga":4.2,"gb":8.4,"bal":0.49,"minG":4.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.34,"moves":"T3 adds FA Greg Dulcich; T3 adds FA C.J. Stroud; T3 adds FA Drew Stevens; T3 adds FA Kendre Miller","reason":"4 + 9 IRs and counting: RB +2.0, FLEX +0.6, TE -2.1 = net +0.6/wk; Concepcion was mostly bench. LONDON Bridge is Falling Down: TE +4.8, RB -0.4, IDP -0.8, FLEX -2.4 = net +1.2/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-1","get":"Kirk Cousins (QB, LV)","give":"Tetairoa McMillan (WR, CAR) + Kyler Murray (QB, MIN)","ga":4.0,"gb":8.1,"bal":0.49,"minG":4.0,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.1,"moves":"T1 adds FA Drew Stevens; T1 adds FA C.J. Stroud; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens","reason":"Daejon Love: QB +1.2, K +1.0, FLEX -0.3, WR -1.3 = net +0.3/wk; Murray was mostly bench. 4 + 9 IRs and counting: WR +2.2, IDP -0.5, QB -1.2 = net +0.7/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Garrett Wilson (WR, NYJ)","give":"Colston Loveland (TE, CHI) + Kyle Monangai (RB, CHI)","ga":4.0,"gb":9.7,"bal":0.41,"minG":4.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.71,"moves":"T3 adds FA Greg Dulcich; T3 adds FA Kendre Miller; T3 adds FA C.J. Stroud; T8 adds FA C.J. Stroud","reason":"4 + 9 IRs and counting: RB +2.6, WR +1.0, FLEX +0.3, IDP -0.5, K -0.5, TE -2.1 = net +0.8/wk. LONDON Bridge is Falling Down: TE +4.8, QB +0.6, FLEX -0.8, WR -1.4, RB -2.1 = net +1.1/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Chris Olave (WR, NO) + Ashton Jeanty (RB, LV)","give":"Jaylen Warren (RB, PIT)","ga":3.9,"gb":4.5,"bal":0.86,"minG":3.9,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.01,"moves":"T2 drops Chris Godwin Jr.; T12 adds FA C.J. Stroud; T12 adds FA Drew Stevens","reason":"Learn How2 Griddy Already: WR +2.7, FLEX +0.4, RB -2.4 = net +0.8/wk. Run it back with Runningbacks?: RB +1.3, FLEX +0.8, K +0.8, WR -2.6 = net +0.1/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"2-for-2","get":"Kirk Cousins (QB, LV) + KC Concepcion Jr. (WR, CLE)","give":"DK Metcalf (WR, PIT) + Kyler Murray (QB, MIN)","ga":8.0,"gb":3.5,"bal":0.44,"minG":3.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.86,"moves":"T1 adds FA Drew Stevens; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens; T3 adds FA Jordyn Brooks","reason":"Daejon Love: K +1.0, QB +0.7, FLEX -0.3 = net +0.9/wk; Murray was mostly bench. 4 + 9 IRs and counting: WR +1.2, QB -1.2 = net +0.2/wk; Concepcion was mostly bench."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"2-for-2","get":"Matthew Golden (WR, GB) + Kyle Pitts Sr. (TE, ATL)","give":"Isaiah Likely (TE, NYG) + DK Metcalf (WR, PIT)","ga":3.4,"gb":3.5,"bal":0.99,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.53,"moves":"T1 adds FA C.J. Stroud; T6 adds FA C.J. Stroud; T6 adds FA Jordyn Brooks","reason":"Daejon Love: WR +2.0, TE -1.6 = net +0.6/wk. High Speed Ja’Marr Chase: TE +1.7, IDP +0.5, FLEX -0.6, WR -1.3 = net +0.1/wk; Pitts was mostly bench."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"4 + 9 IRs and counting","bid":3,"kind":"1-for-1","get":"Kirk Cousins (QB, LV)","give":"Mike Evans (WR, SF)","ga":3.4,"gb":6.2,"bal":0.55,"minG":3.4,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.13,"moves":"T1 adds FA Drew Stevens; T3 adds FA C.J. Stroud; T3 adds FA Kendre Miller; T3 adds FA Drew Stevens; T3 adds FA Jordyn Brooks","reason":"Daejon Love: K +1.0, QB +0.9, FLEX -0.3, WR -0.9 = net +0.3/wk. 4 + 9 IRs and counting: WR +1.9, QB -1.4 = net +0.6/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Drake London (WR, ATL)","give":"Isaiah Likely (TE, NYG) + Tetairoa McMillan (WR, CAR)","ga":5.8,"gb":3.4,"bal":0.58,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.72,"moves":"T1 adds FA C.J. Stroud","reason":"Daejon Love: FLEX +2.6, RB +0.7, WR -0.4, TE -1.9 = net +1.0/wk. LONDON Bridge is Falling Down: TE +4.5, WR +0.4, RB -2.3, FLEX -2.4 = net +0.2/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Breece Hall (RB, NYJ) + Jared Goff (QB, DET)","give":"Tetairoa McMillan (WR, CAR) + Kyler Murray (QB, MIN)","ga":3.1,"gb":5.4,"bal":0.58,"minG":3.1,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.15,"moves":"T1 adds FA Drew Stevens; T1 adds FA C.J. Stroud; T5 adds FA C.J. Stroud; T5 adds FA Greg Dulcich","reason":"Daejon Love: K +1.0, FLEX +0.3, QB +0.3, WR -1.3 = net +0.3/wk; Murray was mostly bench. Eggsbuka Tyrone: FLEX +0.8, WR +0.4, QB -0.3, RB -0.4 = net +0.5/wk."}
]};

type P = {
  player: string; team: string; pos: string; opp: string; mean: number; floor: number; median: number; p90: number;
  p_boom: number; grade: string; snap: number | null; useful: string; cv: number | null; ros: number | null;
  inj: string; implied: number | null; status: string; pct: number | null; lb: boolean;
};

const num = (v: Val): number | null => (typeof v === "number" ? v : null);
const str = (v: Val): string => (typeof v === "string" ? v : "");
const PLAYERS: P[] = DATA.players.map((r) => ({
  player: str(r[0]), team: str(r[1]), pos: str(r[2]), opp: str(r[3]),
  mean: num(r[4]) ?? 0, floor: num(r[5]) ?? 0, median: num(r[6]) ?? 0, p90: num(r[7]) ?? 0, p_boom: num(r[8]) ?? 0,
  grade: str(r[9]), snap: num(r[10]), useful: str(r[11]), cv: num(r[12]), ros: num(r[13]), inj: str(r[14]),
  implied: num(r[15]), status: str(r[16]), pct: num(r[17]), lb: r[18] === true,
}));

const OFF = ["QB", "RB", "WR", "TE", "K"];
const IDP = ["DL", "LB", "DB"];
const VIEWS = [...OFF, ...IDP, "LB slot", "D slot", "My roster"];
const GRADE_RANK: Record<string, number> = { "A+": 7, A: 6, B: 5, C: 4, "C-": 3, D: 2, F: 1 };

const f1 = (x: number | null): string => (x === null ? "–" : x.toFixed(1));
const pc = (x: number | null): string => (x === null ? "–" : `${Math.round(x * 100)}%`);
const gradeCell = (g: string): Cell => {
  if (g === "A+" || g === "A") return { text: g, tone: "success" };
  if (g === "D") return { text: g, tone: "warning" };
  if (g === "F") return { text: g, tone: "danger" };
  return g || "–";
};
const statusText = (p: P): string => {
  const s = p.status === "mine" ? "Mine" : p.status === "W" ? "Waivers" : p.status === "FA" ? "FA" : "Rostered";
  const pct = p.pct === null ? "" : ` ${p.pct}%`;
  const inj = p.inj ? ` · ${p.inj}` : "";
  return s + pct + inj;
};

type SortKey = "auto" | "mean" | "floor" | "median" | "p90" | "p_boom" | "grade" | "snap" | "useful" | "cv" | "ros" | "opp";
const SORTS: { value: SortKey; label: string }[] = [
  { value: "auto", label: "Mode default" }, { value: "mean", label: "Mean" }, { value: "floor", label: "Floor (P10)" },
  { value: "median", label: "Median" }, { value: "p90", label: "P90" }, { value: "p_boom", label: "P(boom)" },
  { value: "grade", label: "Matchup grade" }, { value: "snap", label: "Snap share" }, { value: "useful", label: "Useful games" },
  { value: "cv", label: "Consistency (low CV)" }, { value: "ros", label: "ROS ppg" }, { value: "opp", label: "Opponent" },
];
const usefulFrac = (u: string): number => {
  const [a, b] = u.split("/").map(Number);
  return b ? a / b : -1;
};
const sortVal = (p: P, k: SortKey): number | string => {
  switch (k) {
    case "grade": return GRADE_RANK[p.grade] ?? 0;
    case "snap": return p.snap ?? -1;
    case "useful": return usefulFrac(p.useful);
    case "cv": return p.cv === null ? -99 : -p.cv;
    case "ros": return p.ros ?? -1;
    case "opp": return p.opp.replace(/^(vs|@) /, "");
    case "auto": return p.mean;
    default: return p[k];
  }
};

const slotTable = (rows: Slot[]) => (
  <Table
    columns={["Slot", "Player", "Matchup", "Grade", "Mean", "Floor", "P90", "P(boom)"]}
    rows={rows.map((s) => [s.slot, `${s.player} · ${s.team} ${s.pos}`, s.matchup, gradeCell(s.grade), f1(s.mean), f1(s.floor), f1(s.p90), pc(s.p_boom)])}
  />
);

const BT_RE = /^\s*(QB|RB|WR|TE|K)?\s*(base_inj|base|model)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)/;
const btRows = (): Cell[][] => {
  const out: Cell[][] = [];
  let pos = "";
  let inAll = false;
  for (const line of DATA.backtest.split("\n")) {
    if (line.startsWith("All positions")) { inAll = true; pos = "All"; continue; }
    if (line.startsWith("Calibration")) break;
    const m = BT_RE.exec(line);
    if (!m) continue;
    if (m[1]) pos = m[1];
    if (inAll && !m[1]) pos = "All";
    const label = m[2] === "model" ? "Model" : m[2] === "base_inj" ? "Season avg, injury-adj." : "Season avg";
    out.push([pos, m[2] === "model" ? { text: label, tone: "success" } : label, m[3], m[4], m[5], m[6]]);
  }
  return out;
};
const calLines = (): string[] => {
  const i = DATA.backtest.indexOf("Calibration");
  if (i < 0) return [];
  return DATA.backtest.slice(i).split("\n").map((l) => l.trim()).filter((l) => l.length > 0).slice(0, 4);
};

type TSort = "minG" | "ga" | "gb" | "bal" | "accept" | "kind";
const ACCEPT_ORDER: Record<string, number> = { "Easy yes": 0, "Fair on paper": 1, "Hard sell": 2, "Unlikely": 3 };
const acceptCell = (a: string): Cell =>
  a === "Unlikely" ? { text: a, tone: "danger" } : a === "Hard sell" ? { text: a, tone: "warning" } : { text: a, tone: "success" };
const plus = (v: number): string => `${v >= 0 ? "+" : ""}${v.toFixed(1)}`;
const tradeSortVal = (r: TradeRow, k: TSort): number | string =>
  k === "accept" ? ACCEPT_ORDER[r.accept] ?? 9 : k === "kind" ? r.kind : r[k];

function TradeFinder() {
  const [scope, setScope] = useState<"mine" | "all" | "wr2">("mine");
  const [partner, setPartner] = useState<string>("All");
  const [tsort, setTsort] = useState<TSort>("minG");
  const [tdir, setTdir] = useState<"desc" | "asc">("desc");
  const [hideUnlikely, setHideUnlikely] = useState<boolean>(false);

  const base = TRADES.rows.filter((r) => (scope === "wr2" ? r.preset === "wr2" : !r.preset && (scope === "mine" ? r.mine : true)));
  const teams = Array.from(new Set(scope !== "all" ? base.map((r) => r.b) : base.flatMap((r) => [r.a, r.b]))).sort();
  let rows = base.filter((r) => partner === "All" || r.b === partner || (scope === "all" && r.a === partner));
  if (hideUnlikely) rows = rows.filter((r) => r.accept !== "Unlikely");
  const dir = tdir === "desc" ? -1 : 1;
  rows = [...rows].sort((x, y) => {
    const vx = tradeSortVal(x, tsort);
    const vy = tradeSortVal(y, tsort);
    if (vx < vy) return -dir;
    if (vx > vy) return dir;
    return y.minG - x.minG;
  });
  const why = (r: TradeRow): string => `${r.reason}${r.moves ? ` Moves: ${r.moves}.` : ""} Paper value: ${r.note}.`;
  const mineRows: Cell[][] = rows.map((r) => [r.b, r.get, r.give, plus(r.ga), plus(r.gb), r.bal.toFixed(2), acceptCell(r.accept), why(r)]);
  const allRows: Cell[][] = rows.map((r) => [r.a, r.get, r.give, r.b, plus(r.ga), plus(r.gb), r.bal.toFixed(2), acceptCell(r.accept), why(r)]);
  const mineAll = TRADES.rows.filter((r) => r.mine && !r.preset);
  const wr2All = TRADES.rows.filter((r) => r.preset === "wr2");
  const best = mineAll.length ? mineAll[0] : null;
  const sorts: { value: TSort; label: string }[] = [
    { value: "minG", label: "Smaller gain (default)" }, { value: "ga", label: scope !== "all" ? "Your gain" : "Team A gain" },
    { value: "gb", label: scope !== "all" ? "Their gain" : "Team B gain" }, { value: "bal", label: "Balance" },
    { value: "accept", label: "Acceptance" }, { value: "kind", label: "Trade size" },
  ];

  return (
    <Section heading="Trade Finder" id="trades" caption={`Gains are rest-of-season starting-lineup points (weeks ${TRADES.weeks}, playoff weeks weighted by each team's playoff odds), not player value. Only trades where both teams gain and the smaller gain is at least ${Math.round(TRADES.minRatio * 100)}% of the larger (and at least ${TRADES.minGain} points) are listed. Ranked by the smaller gain.`}>
      <Metrics metrics={[
        { value: String(mineAll.length), label: `Mutual trades for ${TRADES.me}` },
        { value: best ? plus(best.minG) : "–", label: "Best smaller-side gain", detail: best ? `${best.get} for ${best.give}` : "" },
        { value: String(TRADES.nKept), label: "Mutual trades league-wide", detail: `out of ${TRADES.nWinWin} where both sides gain at all` },
      ]} />
      <Segmented value={scope} onChange={(v: string) => { setScope(v === "all" ? "all" : v === "wr2" ? "wr2" : "mine"); setPartner("All"); }} options={[{ value: "mine", label: "My trades", count: mineAll.length }, { value: "wr2", label: "WR2 without Bowers", count: wr2All.length }, { value: "all", label: "All league", count: TRADES.rows.filter((r) => !r.preset).length }]} />
      {scope === "wr2" ? <Callout tone="info" lead="WR2 without Bowers:">{`Bowers and Lamb never leave. Every trade here brings back a WR projecting 9.5+ pts/wk rest of season (Shakir projects 7.4), and the WR slots are the biggest part of your gain. Same 40% balance rule and market check as above. Trades that include Hunter Henry are flagged in the Why column (he is Bowers' bye-week cover). One row per package received; the full list is in trades_week8_wr2.csv. Waivers: no free-agent WR clears the bar. The best by projection is Malik Washington at 7.6/wk; Flournoy and Douglas have had 11-13 ppg over the last 3 games on 5.7 targets a game, which is touchdown-driven.`}</Callout> : null}
      <Grid columns={4}>
        <Select label={scope !== "all" ? "Partner" : "Team"} value={partner} onChange={(v: string) => setPartner(v)} options={["All", ...teams].map((t) => ({ value: t, label: t }))} />
        <Select label="Sort by" value={tsort} onChange={(v: string) => setTsort(v as TSort)} options={sorts} />
        <Segmented value={tdir} onChange={(v: string) => setTdir(v === "asc" ? "asc" : "desc")} options={[{ value: "desc", label: "High → low" }, { value: "asc", label: "Low → high" }]} />
        <Toggle label="Hide unlikely" value={hideUnlikely} onChange={(v: boolean) => setHideUnlikely(v)} />
      </Grid>
      {scope !== "all"
        ? <Table columns={["Partner", "You get", "You give", "Your gain", "Their gain", "Balance", "Acceptance", "Why"]} rows={mineRows} />
        : <Table columns={["Team A", "A gets", "A gives", "Team B", "A gain", "B gain", "Balance", "Acceptance", "Why"]} rows={allRows} />}
      <Section heading="How the trade finder works" collapsible defaultOpen={false}>
        <BulletList items={[
          "Each team's value = sum over remaining weeks of its best legal lineup (QB, 2 RB, 2 WR, TE, W/R/T, K, D, LB). Empty or weak slots are filled by streaming the best free agent at 85% of his projection, 60% for tight ends (in 2026 weeks 2-7 the top-projected free-agent TEs scored only 45-63% of projection; QB, RB and WR streamers scored 84-90%).",
          "Depth counts a little: each starter has a 6% weekly chance of an unexpected miss, so a backup is worth 6% of his edge over the streamer.",
          "Injuries by Yahoo tag: Q 85% this week, then 95%, then full. D 25% then 85%. O out this week, 70% next. IR/IR-R/NA out 4 weeks, then 60% (IR) or 90% (IR-R).",
          "Week weights: this week 0.5 (trade processing lag), weeks 9-14 1.0, weeks 15-17 0.5 + playoff odds. Playoff odds come from a simulation of the rest of the regular season using each team's current lineup strength and record (6 teams assumed to make it; real schedule not exported).",
          "A team receiving 2-for-1 drops its least valuable player; a team left short adds the best free agent. Both are shown under Moves.",
          `Balance = smaller gain ÷ larger gain. Cut-off ${TRADES.minRatio}: below that one side is mostly a donor. About half of all win-win trades are under 0.4.`,
          "Acceptance compares consensus trade values from the partner's side (best player + 70% of the second). Unlikely = they give up 30%+ more paper value. Hard sell = 12-30% more. Easy yes = they get 25%+ more on paper.",
          ...TRADES.sources.map((s) => `Source: ${s}`),
          ...TRADES.tests.map((t) => `Sanity test ${t.passed ? "passed" : "FAILED"}: ${t.test} (${t.trade}: ${plus(t.gain_me)} / ${plus(t.gain_them)})`),
          `Playoff odds used: ${TRADES.odds.map((o) => `${o.team} ${Math.round(o.p * 100)}%`).join(", ")}.`,
        ]} />
      </Section>
    </Section>
  );
}

export default function FantasyRankings() {
  const [mode, setMode] = useState<"safe" | "boom">("safe");
  const [view, setView] = useState<string>("RB");
  const [avail, setAvail] = useState<boolean>(false);
  const [sortKey, setSortKey] = useState<SortKey>("auto");
  const [desc, setDesc] = useState<"desc" | "asc">("desc");
  const [group, setGroup] = useState<"proj" | "profile">("proj");
  const [wpos, setWpos] = useState<string>("All");
  const [limit, setLimit] = useState<string>("40");

  const lineup = DATA.lineup[mode];
  const total = lineup.reduce((a, s) => a + s.mean, 0);
  const totalP90 = lineup.reduce((a, s) => a + s.p90, 0);

  let rows = PLAYERS.filter((p) => {
    if (view === "LB slot") return p.lb;
    if (view === "D slot") return IDP.includes(p.pos);
    if (view === "My roster") return p.status === "mine";
    return p.pos === view;
  });
  if (avail) rows = rows.filter((p) => p.status === "FA" || p.status === "W" || p.status === "mine");
  const key: SortKey = sortKey === "auto" ? (mode === "safe" ? "mean" : "p90") : sortKey;
  const dir = desc === "desc" ? -1 : 1;
  rows = [...rows].sort((a, b) => {
    const va = sortVal(a, key);
    const vb = sortVal(b, key);
    if (va < vb) return -dir;
    if (va > vb) return dir;
    return mode === "safe" ? b.floor - a.floor : b.p_boom - a.p_boom;
  });
  const shown = limit === "all" ? rows : rows.slice(0, Number(limit));

  const name = (p: P): string => `${p.player}${p.status === "mine" ? " ★" : ""}`;
  const projRows: Cell[][] = shown.map((p) => [name(p), `${p.team} ${p.pos}`, p.opp, gradeCell(p.grade), f1(p.mean), f1(p.floor), f1(p.median), f1(p.p90), pc(p.p_boom)]);
  const profRows: Cell[][] = shown.map((p) => [name(p), `${p.team} ${p.pos}`, statusText(p), pc(p.snap), p.useful || "–", p.cv === null ? "–" : p.cv.toFixed(2), f1(p.ros), f1(p.implied)]);

  const waivers = DATA.waivers.filter((w) => wpos === "All" || w.pos === wpos);
  const wRows: Cell[][] = waivers.map((w) => [
    w.player, `${w.team} ${w.pos} · ${w.opp}`, `${w.status}${w.pct === null ? "" : ` ${w.pct}%`}`, f1(w.ros), f1(w.wk),
    w.gain >= 0.5 ? { text: `+${w.gain.toFixed(1)}`, tone: "success" } : w.gain > 0 ? `+${w.gain.toFixed(1)}` : w.gain.toFixed(1),
    w.verdict === "clear ROS upgrade" ? { text: "Upgrade", tone: "success" } : w.verdict, w.faab,
  ]);
  const notes = [...lineup, ...DATA.bench].filter((s) => s.note).map((s) => `${s.player}: ${s.note}`);

  return (
    <Page title={`Fantasy Week ${DATA.week} Rankings`} width="full">
      <Text>{`${DATA.league} · ${DATA.season} week ${DATA.week} · data generated ${DATA.generated} · FAAB $${DATA.faab}, waivers clear ${DATA.waivers_clear}`}</Text>

      <Section heading="Recommended lineup" id="lineup" caption="Brute-force best lineup from your roster. Safe maximizes mean (floor breaks ties); Boom maximizes P90 (P(boom) breaks ties). Sherwood at LB and Hamilton at D are fixed.">
        <Segmented value={mode} onChange={(v: string) => setMode(v === "boom" ? "boom" : "safe")} options={[{ value: "safe", label: "Safe" }, { value: "boom", label: "Boom" }]} />
        <Metrics metrics={[
          { value: f1(total), label: "Projected lineup points (mean)" },
          { value: f1(totalP90), label: "Sum of P90s" },
          { value: `$${DATA.faab}`, label: "FAAB left", detail: `Waivers clear ${DATA.waivers_clear}` },
        ]} />
        {slotTable(lineup)}
        <Text>Bench and IR</Text>
        {slotTable(DATA.bench)}
        <BulletList items={notes} />
      </Section>

      <Section heading="Roster moves" id="moves">
        <Callout tone="warning" lead="Suggested this week">{DATA.moves.join(" ")}</Callout>
      </Section>

      <Section heading="Rankings" id="rankings" caption={`Mode ${mode === "safe" ? "Safe (sorted by mean)" : "Boom (sorted by P90)"} unless you pick a sort. Boom = QB ${DATA.boom_thr.QB}+, RB/WR ${DATA.boom_thr.RB}+, TE ${DATA.boom_thr.TE}+, K ${DATA.boom_thr.K}+, IDP 10+. Grade = projection vs a neutral opponent. ★ = your player.`}>
        <Segmented value={view} onChange={(v: string) => setView(v)} options={VIEWS.map((v) => ({ value: v, label: v }))} />
        <Grid columns={4}>
          <Select label="Sort by" value={sortKey} onChange={(v: string) => setSortKey(v as SortKey)} options={SORTS} />
          <Segmented value={desc} onChange={(v: string) => setDesc(v === "asc" ? "asc" : "desc")} options={[{ value: "desc", label: "High → low" }, { value: "asc", label: "Low → high" }]} />
          <Segmented value={group} onChange={(v: string) => setGroup(v === "profile" ? "profile" : "proj")} options={[{ value: "proj", label: "Projection" }, { value: "profile", label: "Usage & status" }]} />
          <Select label="Show" value={limit} onChange={(v: string) => setLimit(v)} options={[{ value: "25", label: "Top 25" }, { value: "40", label: "Top 40" }, { value: "all", label: "All" }]} />
        </Grid>
        <Toggle label="Available only (FA/waivers, plus your players)" value={avail} onChange={(v: boolean) => setAvail(v)} />
        {group === "proj"
          ? <Table columns={["Player", "Team", "Opp", "Grade", "Mean", "Floor", "Median", "P90", "P(boom)"]} rows={projRows} />
          : <Table columns={["Player", "Team", "Status", "Snap share", "Useful games", "CV (lower = steadier)", "ROS ppg", "Team implied"]} rows={profRows} />}
      </Section>

      <Section heading="Waiver suggestions" id="waivers" caption={`ROS = projected points per game, weeks ${DATA.week}-17, with byes and schedule. Gain = ROS ppg over your weakest starter at that position (or flex). FAAB as % of $${DATA.faab}.`}>
        <Select label="Position" value={wpos} onChange={(v: string) => setWpos(v)} options={["All", ...OFF, ...IDP].map((v) => ({ value: v, label: v }))} />
        <Callout tone="info" lead="Usage audit (Oct 28):">Malik Washington is not a real upgrade over Khalil Shakir. Washington's target share was inflated by 3 games without Caleb Douglas (wks 3-5) and he got 3 targets when Douglas returned in wk 7. The model now discounts targets earned while current teammates were out, scores WR carries at the league WR rate, and ties receiver yards per target to the team's passing efficiency (Willis/MIA vs Allen/BUF). Gains under +0.5/g are toss-ups within model error.</Callout>
        <Table columns={["Player", "Team · matchup", "Status", "ROS ppg", `Wk ${DATA.week}`, "Gain", "Verdict", "FAAB"]} rows={wRows} />
      </Section>

      <TradeFinder />

      <Section heading="Scoring and model check" id="model">
        <Properties items={[{ label: "League scoring", value: DATA.scoring }]} />
        <Text>{`Backtest, weeks 4-${DATA.week - 1}: each week projected using only earlier games, compared with season-average points. Spearman = rank correlation with actual points; hit = overlap between the projected top group and the actual top group.`}</Text>
        <Table columns={["Pos", "Method", "Spearman", "Hit", "Top avg", "MAE"]} rows={btRows()} />
        <BulletList items={calLines()} />
      </Section>
    </Page>
  );
}
