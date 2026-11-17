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
"week":8,
"season":2026,
"generated":"2026-10-28 14:39 ET",
"league":"Irene's Bush League (Yahoo 54162) - Breeces Pieces",
"faab":76,
"waivers_clear":"Oct 31",
"players":[
["Drake Maye","NE","QB","@ MIA",22.8,10.7,20.6,37.7,0.35,"A",0.99,"4/7",0.51,20.9,"",25.2,"",null,false],
["Josh Allen","BUF","QB","vs BAL",22.1,10.4,20.1,36.4,0.33,"B",1.0,"6/6",0.3,21.0,"",28.8,"",null,false],
["Dak Prescott","DAL","QB","vs ARI",22.0,9.9,19.7,37.2,0.33,"A",1.0,"7/7",0.25,19.1,"",30.8,"mine",null,false],
["Jacoby Brissett","ARI","QB","@ DAL",21.8,10.4,19.7,35.7,0.31,"B",1.0,"5/7",0.4,20.1,"",23.8,"",null,false],
["Joe Burrow","CIN","QB","vs TEN",21.6,9.8,19.6,35.7,0.32,"C-",0.98,"6/6",0.25,21.2,"",28.5,"",null,false],
["Trevor Lawrence","JAX","QB","vs IND",21.3,9.3,19.2,35.8,0.3,"B",0.99,"5/6",0.35,20.0,"",28.2,"",null,false],
["Jayden Daniels","WAS","QB","vs PHI",19.8,9.6,18.5,31.7,0.24,"B",0.89,"4/4",0.3,18.9,"",23.0,"",null,false],
["Kirk Cousins","LV","QB","@ NYJ",19.8,9.1,17.9,32.8,0.24,"C",0.96,"7/7",0.17,18.9,"",22.0,"",null,false],
["Jordan Love","GB","QB","vs CAR",19.2,8.7,17.3,32.1,0.22,"D",0.99,"7/7",0.23,19.7,"",25.5,"",null,false],
["Tyler Huntley","BAL","QB","@ BUF",19.1,8.7,17.5,31.6,0.22,"C",0.95,"3/4",0.47,17.3,"",25.8,"",null,false],
["Geno Smith","NYJ","QB","vs LV",19.1,8.5,17.2,32.1,0.23,"B",1.0,"4/7",0.41,17.9,"",23.5,"FA",19,false],
["Sam Darnold","SEA","QB","vs CHI",18.6,8.6,16.9,31.0,0.21,"A",0.97,"4/6",0.67,17.4,"",24.8,"",null,false],
["Matthew Stafford","LA","QB","vs LAC",18.2,8.4,16.3,30.5,0.2,"C-",0.99,"5/7",0.43,18.0,"",26.0,"",null,false],
["Jared Goff","DET","QB","vs MIN",18.1,8.2,16.3,30.5,0.2,"D",0.99,"6/6",0.22,19.8,"",24.8,"",null,false],
["Kyler Murray","MIN","QB","@ DET",17.4,8.1,15.8,28.6,0.16,"B",0.96,"2/5",0.51,17.1,"",21.8,"",null,false],
["Aaron Rodgers","PIT","QB","vs CLE",17.3,7.4,15.6,29.2,0.17,"C-",0.99,"5/7",0.36,18.4,"",21.5,"W",49,false],
["Justin Herbert","LAC","QB","@ LA",17.2,7.8,15.9,28.2,0.16,"C",1.0,"2/6",0.14,17.4,"",19.5,"FA",47,false],
["Deshaun Watson","CLE","QB","@ PIT",17.1,8.0,15.6,28.2,0.15,"C-",1.0,"5/7",0.23,18.5,"",18.0,"FA",13,false],
["Malik Willis","MIA","QB","vs NE",16.4,7.5,15.0,26.8,0.14,"C",1.0,"3/6",0.46,16.7,"",18.2,"FA",19,false],
["Michael Penix Jr.","ATL","QB","@ TB",16.4,7.3,14.9,27.2,0.14,"C",0.99,"4/5",0.2,16.5,"",21.0,"FA",19,false],
["Jahmyr Gibbs","DET","RB","vs MIN",20.7,7.2,18.5,37.0,0.44,"C-",0.81,"6/6",0.36,20.6,"",24.8,"",null,false],
["Kenneth Walker III","KC","RB","@ DEN",19.0,6.1,16.4,35.7,0.38,"B",0.74,"5/6",0.36,18.4,"",21.0,"",null,false],
["James Cook","BUF","RB","vs BAL",16.7,4.5,14.2,31.9,0.3,"D",0.64,"5/6",0.28,16.1,"",28.8,"",null,false],
["Kyren Williams","LA","RB","vs LAC",16.4,5.4,14.3,30.5,0.29,"A",0.66,"6/7",0.39,14.8,"",26.0,"mine",null,false],
["Bucky Irving","TB","RB","vs ATL",15.8,4.5,13.4,29.9,0.27,"A",0.65,"4/7",0.62,14.9,"",23.5,"mine",null,false],
["Javonte Williams","DAL","RB","vs ARI",15.7,4.3,13.1,30.1,0.28,"C",0.74,"6/7",0.4,13.7,"",30.8,"",null,false],
["Bijan Robinson","ATL","RB","@ TB",14.5,5.0,12.9,25.6,0.22,"D",0.77,"5/7",0.56,15.5,"",21.0,"",null,false],
["Braelon Allen","NYJ","RB","vs LV",14.3,4.7,12.7,26.1,0.21,"A",0.79,"3/7",0.54,13.0,"",23.5,"",null,false],
["Chuba Hubbard","CAR","RB","@ GB",14.0,3.9,12.1,26.4,0.22,"C",0.78,"5/6",0.35,13.9,"",22.0,"",null,false],
["Jaylen Warren","PIT","RB","vs CLE",14.0,4.7,12.3,25.5,0.19,"C",0.75,"4/7",0.55,13.6,"",21.5,"",null,false],
["D'Andre Swift","CHI","RB","@ SEA",13.5,3.8,11.8,25.0,0.19,"C-",0.66,"5/7",0.5,14.3,"",21.8,"",null,false],
["Chase Brown","CIN","RB","vs TEN",13.4,3.8,11.6,24.9,0.19,"A",0.71,"2/6",0.36,12.1,"",28.5,"",null,false],
["Jonathan Taylor","IND","RB","@ JAX",13.0,3.5,11.2,24.8,0.18,"C-",0.74,"5/7",0.36,15.0,"",18.2,"",null,false],
["Josh Jacobs","GB","RB","vs CAR",12.8,3.4,11.1,24.0,0.18,"B",0.52,"1/1",0.0,12.3,"",25.5,"",null,false],
["Ashton Jeanty","LV","RB","@ NYJ",12.7,3.7,11.1,23.9,0.17,"C-",0.64,"5/7",0.45,13.6,"",22.0,"",null,false],
["Tony Pollard","TEN","RB","@ CIN",12.6,3.3,10.7,24.4,0.17,"C",0.64,"3/7",0.84,14.1,"",18.0,"",null,false],
["Bhayshul Tuten","JAX","RB","vs IND",12.6,3.8,11.1,23.7,0.16,"C-",0.6,"5/6",0.34,11.9,"",28.2,"",null,false],
["Derrick Henry","BAL","RB","@ BUF",12.5,2.8,10.7,24.4,0.17,"C",0.56,"5/7",0.57,12.3,"",25.8,"",null,false],
["Quinshon Judkins","CLE","RB","@ PIT",12.3,3.2,10.5,23.3,0.15,"C-",0.57,"2/6",0.56,13.9,"",18.0,"",null,false],
["Aaron Jones","MIN","RB","@ DET",11.4,3.1,9.8,22.0,0.13,"C-",0.61,"5/6",0.39,12.1,"",21.8,"",null,false],
["Ollie Gordon II","MIA","RB","vs NE",10.5,2.5,8.9,20.5,0.11,"C-",0.68,"4/5",0.49,11.8,"",18.2,"",null,false],
["Emanuel Wilson","SEA","RB","vs CHI",10.0,2.1,8.3,19.6,0.09,"F",0.45,"3/7",0.82,10.9,"",24.8,"mine",null,false],
["Blake Corum","LA","RB","vs LAC",9.7,2.3,8.2,18.9,0.08,"A",0.32,"3/7",0.58,8.6,"",26.0,"",null,false],
["Rhamondre Stevenson","NE","RB","@ MIA",9.6,2.5,8.4,18.3,0.07,"B",0.65,"4/7",0.59,9.2,"",25.2,"",null,false],
["TreVeyon Henderson","NE","RB","@ MIA",4.8,0.6,3.7,10.3,0.01,"A",0.25,"1/6",0.73,4.2,"",25.2,"mine",null,false],
["Roschon Johnson","CHI","RB","@ SEA",6.0,1.1,4.8,12.4,0.01,"C-",0.28,"1/4",0.78,6.2,"",21.8,"FA",14,false],
["MarShawn Lloyd","GB","RB","vs CAR",6.0,0.7,4.5,13.1,0.02,"A",0.4,"1/7",0.75,5.3,"",25.5,"FA",46,false],
["Kimani Vidal","LAC","RB","@ LA",5.3,0.8,4.2,10.9,0.01,"A",0.35,"2/5",0.75,5.1,"",19.5,"FA",11,false],
["George Holani","SEA","RB","vs CHI",5.2,0.3,3.7,12.0,0.02,"C",0.43,"0/7",0.59,5.3,"",24.8,"FA",6,false],
["Chris Rodriguez Jr.","JAX","RB","vs IND",5.2,0.5,3.7,11.6,0.01,"D",0.23,"0/6",0.71,4.9,"",28.2,"FA",24,false],
["Justice Hill","BAL","RB","@ BUF",5.0,0.8,4.0,10.4,0.01,"A",0.44,"0/7",0.49,4.4,"",25.8,"FA",5,false],
["Jaxon Smith-Njigba","SEA","WR","vs CHI",19.6,4.5,16.2,40.5,0.39,"A+",0.84,"7/7",0.35,17.1,"",24.8,"",null,false],
["Puka Nacua","LA","WR","vs LAC",15.0,3.6,12.8,29.1,0.25,"C-",0.86,"4/5",0.4,15.5,"",26.0,"",null,false],
["CeeDee Lamb","DAL","WR","vs ARI",14.8,2.7,12.0,30.4,0.26,"B",0.77,"6/7",0.56,14.0,"",30.8,"mine",null,false],
["Zay Flowers","BAL","WR","@ BUF",14.1,2.8,11.8,27.7,0.23,"C-",0.79,"5/6",0.36,13.7,"",25.8,"",null,false],
["Amon-Ra St. Brown","DET","WR","vs MIN",13.4,2.9,11.5,26.5,0.2,"D",0.86,"4/6",0.45,14.7,"",24.8,"",null,false],
["Drake London","ATL","WR","@ TB",12.8,2.5,10.8,25.0,0.19,"C-",0.91,"5/7",0.47,12.4,"",21.0,"",null,false],
["Tetairoa McMillan","CAR","WR","@ GB",12.2,2.3,10.2,23.7,0.17,"B",0.78,"3/6",0.89,11.3,"",22.0,"",null,false],
["George Pickens","DAL","WR","vs ARI",11.4,1.6,9.2,23.8,0.16,"B",0.79,"4/7",0.51,11.1,"",30.8,"",null,false],
["Tee Higgins","CIN","WR","vs TEN",11.3,1.4,9.2,23.5,0.15,"B",0.79,"4/6",0.52,11.0,"",28.5,"",null,false],
["Parker Washington","JAX","WR","vs IND",10.9,1.3,8.4,23.3,0.15,"C",0.78,"4/6",0.6,11.2,"",28.2,"",null,false],
["Matthew Golden","GB","WR","vs CAR",10.6,1.4,8.7,22.2,0.13,"D",0.83,"5/7",0.36,11.4,"",25.5,"",null,false],
["Tre Tucker","LV","WR","@ NYJ",10.4,1.3,8.6,21.9,0.12,"C",0.73,"3/7",0.65,10.2,"",22.0,"",null,false],
["Michael Wilson","ARI","WR","@ DAL",9.5,1.4,7.8,19.2,0.09,"B",0.89,"2/7",0.61,8.6,"",23.8,"",null,false],
["Germie Bernard","PIT","WR","vs CLE",9.3,1.6,7.5,19.5,0.1,"C-",0.84,"2/6",0.86,10.0,"",21.5,"",null,false],
["DK Metcalf","PIT","WR","vs CLE",9.3,1.3,7.6,19.4,0.09,"C-",0.94,"3/7",0.48,10.1,"",21.5,"",null,false],
["Carnell Tate","TEN","WR","@ CIN",9.1,1.5,7.6,18.5,0.07,"B",0.81,"2/7",0.64,8.6,"",18.0,"",null,false],
["Jameson Williams","DET","WR","vs MIN",8.8,0.7,7.0,19.1,0.09,"D",0.9,"3/6",0.57,9.6,"",24.8,"",null,false],
["A.J. Brown","NE","WR","@ MIA",8.5,0.2,6.5,19.1,0.09,"C",0.75,"0/3",0.21,8.6,"",25.2,"",null,false],
["Luther Burden III","CHI","WR","@ SEA",8.4,1.4,7.0,17.3,0.06,"F",0.59,"3/7",0.5,9.8,"",21.8,"",null,false],
["Khalil Shakir","BUF","WR","vs BAL",8.4,0.9,6.6,17.9,0.07,"A+",0.67,"1/6",0.47,7.4,"",28.8,"mine",null,false],
["Ja'Marr Chase","CIN","WR","vs TEN",8.4,0.8,6.6,18.5,0.08,"B",0.72,"4/6",0.57,8.5,"",28.5,"",null,false],
["Jalen Coker","CAR","WR","@ GB",8.4,1.1,6.9,17.6,0.06,"B",0.63,"3/5",0.89,7.9,"",22.0,"",null,false],
["Justin Jefferson","MIN","WR","@ DET",8.3,0.9,6.8,17.6,0.07,"C",0.72,"2/5",0.7,8.0,"",21.8,"",null,false],
["Keon Coleman","BUF","WR","vs BAL",8.3,0.2,6.4,18.1,0.07,"A+",0.74,"2/6",0.7,7.1,"",28.8,"",null,false],
["Keenan Allen","IND","WR","@ JAX",8.1,1.4,6.8,16.4,0.05,"A+",0.56,"2/6",0.61,7.0,"",18.2,"FA",53,false],
["Malik Washington","MIA","WR","vs NE",8.1,1.3,6.7,16.3,0.05,"C",0.83,"0/6",0.26,7.6,"",18.2,"FA",49,false],
["Jakobi Meyers","JAX","WR","vs IND",8.0,0.5,6.2,17.3,0.07,"C",0.8,"3/6",0.54,8.4,"",28.2,"",null,false],
["Kendrick Bourne","ARI","WR","@ DAL",7.7,0.9,6.1,16.8,0.05,"B",0.55,"1/6",0.61,7.0,"",23.8,"FA",17,false],
["KC Concepcion","CLE","WR","@ PIT",7.7,1.3,6.4,15.7,0.04,"C",0.64,"1/7",0.82,8.0,"",18.0,"",null,false],
["Christian Watson","GB","WR","vs CAR",7.6,0.7,6.2,16.3,0.05,"D",0.82,"4/7",0.58,8.4,"",25.5,"",null,false],
["Jaylen Waddle","DEN","WR","vs KC",5.5,0.0,4.0,13.0,0.02,"D",0.63,"2/7",0.74,6.7,"Q",19.5,"mine",null,false],
["Ryan Flournoy","DAL","WR","vs ARI",7.2,0.6,5.5,15.9,0.05,"B",0.77,"2/7",0.51,7.0,"",30.8,"FA",24,false],
["DeMario Douglas","NE","WR","@ MIA",6.4,0.0,4.8,14.6,0.04,"C-",0.57,"2/7",0.92,6.5,"",25.2,"W",33,false],
["Jordan Addison","MIN","WR","@ DET",6.0,0.5,4.6,13.3,0.02,"C",0.91,"1/5",0.98,5.9,"",21.8,"FA",72,false],
["Trey McBride","ARI","TE","@ DAL",12.2,2.5,10.2,24.4,0.31,"D",0.93,"6/7",0.37,12.5,"",23.8,"",null,false],
["Brock Bowers","LV","TE","@ NYJ",11.3,2.0,9.0,23.1,0.27,"C",0.84,"5/5",0.33,11.1,"",22.0,"mine",null,false],
["Brenton Strange","JAX","TE","vs IND",8.4,1.2,6.7,17.9,0.15,"C-",0.8,"3/6",0.44,8.6,"",28.2,"",null,false],
["Hunter Henry","NE","TE","@ MIA",8.3,0.9,6.6,18.3,0.16,"A+",0.73,"4/7",0.52,7.5,"",25.2,"mine",null,false],
["T.J. Hockenson","MIN","TE","@ DET",8.3,1.0,6.6,17.6,0.15,"A+",0.58,"3/6",0.75,7.4,"",21.8,"",null,false],
["Greg Dulcich","MIA","TE","vs NE",8.2,1.2,6.7,16.8,0.14,"A+",0.69,"2/5",0.5,7.3,"",18.2,"FA",5,false],
["Colston Loveland","CHI","TE","@ SEA",8.1,1.3,6.6,16.7,0.13,"D",0.85,"3/7",0.88,8.9,"",21.8,"",null,false],
["Sam LaPorta","DET","TE","vs MIN",7.5,0.8,6.0,16.1,0.12,"D",0.89,"3/6",0.56,8.7,"",24.8,"",null,false],
["Mason Taylor","NYJ","TE","vs LV",7.3,0.6,5.6,16.2,0.12,"A+",0.59,"1/4",1.04,6.9,"",23.5,"FA",1,false],
["AJ Barner","SEA","TE","vs CHI",7.2,0.5,5.6,16.2,0.12,"A+",0.89,"1/7",0.56,6.6,"",24.8,"FA",10,false],
["Kyle Pitts","ATL","TE","@ TB",7.2,0.8,5.5,15.7,0.12,"B",0.64,"3/7",0.91,7.4,"",21.0,"",null,false],
["Travis Kelce","KC","TE","@ DEN",7.1,0.9,5.8,15.2,0.1,"C",0.77,"3/6",0.59,7.5,"",21.0,"",null,false],
["Dallas Goedert","PHI","TE","@ WAS",7.0,0.9,5.6,14.8,0.1,"A",0.73,"2/5",0.75,6.2,"",17.5,"W",88,false],
["Tucker Kraft","GB","TE","vs CAR",6.8,0.6,5.1,15.0,0.1,"D",0.82,"4/7",0.47,7.5,"",25.5,"",null,false],
["Mark Andrews","BAL","TE","@ BUF",5.9,0.0,4.4,13.6,0.08,"A",0.66,"1/7",0.61,4.9,"",25.8,"FA",68,false],
["Eli Raridon","NE","TE","@ MIA",5.9,0.0,4.1,13.9,0.09,"A+",0.54,"2/6",0.7,5.3,"",25.2,"FA",1,false],
["Tyler Bass","BUF","K","vs BAL",11.5,3.0,10.5,21.6,0.42,"C",null,"4/6",0.48,11.0,"",28.8,"",null,false],
["Will Reichard","MIN","K","@ DET",11.4,3.0,10.6,21.3,0.43,"C",null,"6/6",0.27,12.0,"",21.8,"",null,false],
["Chad Ryland","ARI","K","@ DAL",11.0,2.7,9.9,20.8,0.4,"C",null,"5/7",0.6,10.8,"",23.8,"",null,false],
["Matt Gay","LV","K","@ NYJ",10.8,2.6,9.8,20.3,0.39,"C",null,"6/7",0.31,11.1,"",22.0,"",null,false],
["Brandon Aubrey","DAL","K","vs ARI",10.6,2.8,9.5,20.0,0.37,"C",null,"4/7",0.68,9.4,"",30.8,"",null,false],
["Jason Myers","SEA","K","vs CHI",10.4,2.0,9.5,19.6,0.36,"C",null,"5/7",0.61,10.5,"",24.8,"W",90,false],
["Chris Boswell","PIT","K","vs CLE",10.1,2.0,9.3,19.1,0.35,"C",null,"5/7",0.43,10.6,"",21.5,"",null,false],
["Spencer Shrader","IND","K","@ JAX",9.9,2.0,9.0,19.0,0.34,"C",null,"5/7",0.44,11.1,"",18.2,"",null,false],
["Chase McLaughlin","TB","K","vs ATL",9.9,2.0,9.0,19.3,0.33,"C",null,"6/7",0.46,10.5,"",23.5,"mine",null,false],
["Cam Little","JAX","K","vs IND",9.8,2.0,8.9,18.4,0.33,"C",null,"5/6",0.32,9.0,"",28.2,"",null,false],
["Jake Bates","DET","K","vs MIN",9.5,2.0,8.6,18.2,0.3,"C",null,"5/6",0.43,9.6,"",24.8,"FA",68,false],
["Trey Smack","GB","K","vs CAR",9.4,2.0,8.5,18.1,0.31,"C",null,"4/7",0.48,8.9,"",25.5,"FA",38,false],
["Jason Sanders","NYJ","K","vs LV",9.4,2.0,8.4,18.0,0.3,"C",null,"3/7",0.54,9.0,"",23.5,"FA",1,false],
["Cairo Santos","CHI","K","@ SEA",9.1,2.0,8.0,17.9,0.28,"C",null,"5/7",0.5,9.6,"",21.8,"FA",44,false],
["Andre Szmyt","CLE","K","@ PIT",8.6,1.0,7.6,17.1,0.26,"C",null,"5/7",0.37,9.7,"",18.0,"W",1,false],
["Leonard Williams","SEA","DL","vs CHI",5.4,1.2,4.5,11.0,0.13,"A+",0.76,"3/7",0.71,5.4,"",null,"FA",null,false],
["Aidan Hutchinson","DET","DL","vs MIN",5.2,0.8,4.2,11.8,0.16,"A+",0.9,"3/6",0.74,5.2,"",null,"",null,false],
["Austin Booker","CHI","DL","@ SEA",5.2,1.0,4.2,10.5,0.12,"A+",0.69,"2/7",0.92,5.2,"",null,"FA",null,false],
["Quinnen Williams","DAL","DL","vs ARI",5.0,1.0,3.8,10.5,0.12,"C-",0.63,"4/7",0.58,5.0,"",null,"FA",null,false],
["Jalen Redmond","MIN","DL","@ DET",4.9,1.0,4.0,9.5,0.09,"A+",0.82,"1/6",0.6,4.9,"",null,"FA",null,false],
["Josh Hines-Allen","JAX","DL","vs IND",4.7,0.8,3.5,10.2,0.11,"D",0.83,"2/6",1.17,4.7,"",null,"FA",null,false],
["George Karlaftis","KC","DL","@ DEN",4.5,0.8,3.5,9.8,0.1,"F",0.84,"2/6",0.67,4.5,"",null,"FA",null,false],
["Maxx Crosby","LV","DL","@ NYJ",4.5,0.8,3.2,10.0,0.11,"A+",0.88,"2/7",0.78,4.5,"",null,"FA",null,false],
["Jeffery Simmons","TEN","DL","@ CIN",4.5,1.0,3.5,9.2,0.08,"F",0.87,"3/7",0.78,4.5,"",null,"",null,false],
["Byron Murphy II","SEA","DL","vs CHI",4.4,1.0,3.5,8.8,0.07,"A+",0.7,"1/7",1.08,4.4,"",null,"",null,false],
["Deone Walker","BUF","DL","vs BAL",4.2,1.0,3.5,8.5,0.06,"A+",0.73,"1/6",0.55,4.2,"",null,"FA",null,false],
["DeForest Buckner","IND","DL","@ JAX",4.2,1.0,3.2,8.5,0.06,"A",0.84,"3/7",0.48,4.2,"",null,"",null,false],
["Zach Sieler","MIA","DL","vs NE",4.2,1.0,3.2,8.2,0.06,"A+",0.78,"1/6",0.9,4.2,"",null,"FA",null,false],
["Travon Walker","JAX","DL","vs IND",4.1,0.5,2.8,9.8,0.09,"D",0.83,"1/6",0.96,4.1,"",null,"FA",null,false],
["Blake Cashman","MIN","LB","@ DET",9.2,3.8,8.5,15.8,0.38,"C-",0.96,"5/6",0.51,9.2,"",null,"",null,true],
["Ernest Jones","SEA","LB","vs CHI",8.5,3.5,7.8,14.2,0.32,"A+",1.0,"4/7",0.51,8.5,"",null,"",null,true],
["Alex Singleton","DEN","LB","vs KC",7.4,3.0,6.8,12.8,0.23,"C",1.0,"4/7",0.45,7.4,"",null,"",null,true],
["Jamien Sherwood","NYJ","LB","vs LV",6.5,2.5,6.0,11.5,0.17,"B",0.96,"3/7",0.59,6.5,"",null,"FA",null,true],
["Devin Bush","CHI","LB","@ SEA",6.5,2.5,5.8,11.5,0.16,"A+",0.93,"2/7",0.23,6.5,"",null,"FA",null,true],
["Payton Wilson","PIT","LB","vs CLE",6.4,2.2,5.8,11.5,0.17,"D",0.88,"6/7",0.32,6.4,"",null,"",null,true],
["Josiah Trotter","TB","LB","vs ATL",6.4,2.5,5.8,11.0,0.15,"B",0.95,"3/6",0.74,6.4,"",null,"FA",null,true],
["Jacob Rodriguez","MIA","LB","vs NE",6.4,2.5,5.8,11.5,0.16,"C",0.99,"3/6",0.62,6.4,"",null,"FA",null,true],
["Roquan Smith","BAL","LB","@ BUF",6.3,2.0,5.2,11.2,0.15,"B",0.97,"2/7",0.62,6.3,"",null,"",null,true],
["Zack Baun","PHI","LB","@ WAS",6.2,2.5,5.5,11.0,0.14,"A+",0.99,"3/6",0.43,6.2,"",null,"W",null,true],
["Bobby Okereke","CAR","LB","@ GB",6.2,2.2,5.5,11.2,0.15,"F",0.87,"4/6",0.51,6.2,"",null,"FA",null,true],
["Nakobe Dean","LV","LB","@ NYJ",6.2,2.2,5.5,11.5,0.16,"F",1.0,"5/7",0.48,6.2,"",null,"",null,true],
["Foyesade Oluokun","JAX","LB","vs IND",6.2,2.0,5.5,11.2,0.16,"D",0.94,"3/6",0.64,6.2,"",null,"",null,true],
["Jack Campbell","DET","LB","vs MIN",6.2,2.2,5.5,11.0,0.14,"F",1.0,"2/6",0.26,6.2,"",null,"",null,true],
["Jordyn Brooks","MIA","LB","vs NE",6.2,2.2,5.5,10.8,0.14,"C",0.91,"2/6",0.46,6.2,"",null,"FA",null,true],
["Kendal Daniels","ATL","LB","@ TB",6.1,1.8,5.5,11.0,0.15,"A+",0.68,"3/7",0.81,6.1,"",null,"",null,true],
["Quincy Williams","CLE","LB","@ PIT",5.9,2.0,5.2,10.8,0.14,"F",0.97,"3/7",0.88,5.9,"",null,"FA",null,true],
["Nick Bolton","KC","LB","@ DEN",5.9,2.2,5.2,10.5,0.13,"D",1.0,"3/6",0.38,5.9,"",null,"",null,true],
["Akeem Davis-Gaither","IND","LB","@ JAX",5.9,2.2,5.2,10.2,0.12,"D",0.95,"1/7",0.28,5.9,"",null,"FA",null,true],
["Christian Elliss","NE","LB","@ MIA",5.9,2.0,5.0,10.8,0.13,"F",0.95,"2/7",0.83,5.9,"",null,"",null,true],
["DeMarvion Overshown","DAL","LB","vs ARI",5.8,2.0,5.0,10.5,0.13,"A+",0.69,"1/2",0.68,5.8,"",null,"",null,true],
["Carson Schwesinger","CLE","LB","@ PIT",5.8,2.0,5.0,10.8,0.13,"F",1.0,"3/7",0.65,5.8,"",null,"",null,true],
["David Bailey","NYJ","LB","vs LV",5.7,1.2,4.8,12.0,0.16,"C-",0.86,"4/7",0.53,5.7,"",null,"mine",null,true],
["Evan Williams","GB","DB","vs CAR",7.1,2.8,6.2,12.8,0.23,"B",1.0,"4/7",0.41,7.1,"",null,"",null,false],
["Kyle Hamilton","BAL","DB","@ BUF",6.5,2.5,5.8,11.5,0.17,"A+",0.96,"5/7",0.41,6.5,"",null,"mine",null,false],
["Budda Baker","ARI","DB","@ DAL",6.4,2.2,5.5,11.5,0.17,"B",0.99,"4/7",0.6,6.4,"",null,"FA",null,false],
["Keisean Nixon","GB","DB","vs CAR",6.2,2.5,5.5,11.0,0.15,"C",0.97,"4/7",0.39,6.2,"",null,"FA",null,false],
["Dillon Thieneman","CHI","DB","@ SEA",6.1,2.0,5.2,11.2,0.15,"A+",0.96,"4/7",0.39,6.1,"",null,"FA",null,false],
["Dane Belton","NYJ","DB","vs LV",6.0,2.2,5.2,10.5,0.13,"C-",1.0,"2/7",0.44,6.0,"",null,"",null,false],
["Quentin Lake","LA","DB","vs LAC",5.9,2.0,5.0,11.0,0.15,"C",1.0,"3/7",0.6,5.9,"",null,"",null,false],
["Caleb Downs","DAL","DB","vs ARI",5.9,2.0,5.2,10.8,0.13,"A",0.96,"3/7",0.68,5.9,"",null,"FA",null,false],
["Jalen Ramsey","PIT","DB","vs CLE",5.9,2.0,5.0,10.8,0.14,"F",1.0,"2/7",0.89,5.9,"",null,"",null,false],
["Nick Emmanwori","SEA","DB","vs CHI",5.9,1.0,5.0,11.5,0.16,"A+",0.85,"2/6",0.96,5.9,"",null,"FA",null,false],
["Kevin Winston Jr.","TEN","DB","@ CIN",5.6,2.0,5.0,10.0,0.11,"D",1.0,"2/5",0.29,5.6,"",null,"",null,false],
["Brandon Cisse","GB","DB","vs CAR",5.6,1.8,4.8,10.2,0.12,"C",0.9,"3/7",0.46,5.6,"",null,"",null,false],
["Amik Robertson","WAS","DB","vs PHI",5.4,2.0,4.8,10.0,0.1,"D",0.99,"2/6",0.51,5.4,"",null,"",null,false],
["Devon Witherspoon","SEA","DB","vs CHI",5.4,2.0,4.8,9.5,0.09,"A",0.99,"1/7",0.47,5.4,"",null,"",null,false],
["Josh Metellus","MIN","DB","@ DET",5.4,2.0,4.8,9.5,0.09,"A+",0.99,"1/6",0.34,5.4,"",null,"",null,false],
["Cole Bishop","BUF","DB","vs BAL",5.3,2.0,4.8,9.5,0.09,"A+",0.99,"0/6",0.26,5.3,"",null,"FA",null,false],
["Ty Okada","SEA","DB","vs CHI",5.3,1.8,4.5,9.8,0.1,"A+",0.97,"1/3",0.5,5.3,"",null,"",null,false],
["Will Lee III","CAR","DB","@ GB",5.2,1.5,4.8,10.0,0.11,"A+",0.9,"3/6",0.4,5.2,"",null,"",null,false]
],
"lineup":{"safe":[
{"slot":"QB","player":"Dak Prescott","team":"DAL","pos":"QB","matchup":"vs ARI","mean":22.0,"floor":9.9,"p90":37.2,"p_boom":0.33,"grade":"A","note":""},
{"slot":"RB","player":"Kyren Williams","team":"LA","pos":"RB","matchup":"vs LAC","mean":16.4,"floor":5.4,"p90":30.5,"p_boom":0.29,"grade":"A","note":""},
{"slot":"RB","player":"Bucky Irving","team":"TB","pos":"RB","matchup":"vs ATL","mean":15.8,"floor":4.5,"p90":29.9,"p_boom":0.27,"grade":"A","note":""},
{"slot":"WR","player":"CeeDee Lamb","team":"DAL","pos":"WR","matchup":"vs ARI","mean":14.8,"floor":2.7,"p90":30.4,"p_boom":0.26,"grade":"B","note":""},
{"slot":"WR","player":"Khalil Shakir","team":"BUF","pos":"WR","matchup":"vs BAL","mean":8.4,"floor":0.9,"p90":17.9,"p_boom":0.07,"grade":"A+","note":""},
{"slot":"TE","player":"Brock Bowers","team":"LV","pos":"TE","matchup":"@ NYJ","mean":11.3,"floor":2.0,"p90":23.1,"p_boom":0.27,"grade":"C","note":""},
{"slot":"W/R/T","player":"Emanuel Wilson","team":"SEA","pos":"RB","matchup":"vs CHI","mean":10.0,"floor":2.1,"p90":19.6,"p_boom":0.09,"grade":"F","note":""},
{"slot":"K","player":"Chase McLaughlin","team":"TB","pos":"K","matchup":"vs ATL","mean":9.9,"floor":2.0,"p90":19.3,"p_boom":0.33,"grade":"C","note":""},
{"slot":"D","player":"Kyle Hamilton","team":"BAL","pos":"DB","matchup":"@ BUF","mean":6.5,"floor":2.5,"p90":11.5,"p_boom":0.17,"grade":"A+","note":"7.5 wtd-L4 (7.6 ssn), 96% snaps; 1 INT/4 PD, 0.118 tkl/snap"},
{"slot":"LB","player":"Jamien Sherwood","team":"NYJ","pos":"LB","matchup":"vs LV","mean":6.5,"floor":2.5,"p90":11.5,"p_boom":0.17,"grade":"B","note":"9.6 wtd-L4 (7.1 ssn), 97% snaps; 0.121 tkl/snap; low-volume opp"}
],
"boom":[
{"slot":"QB","player":"Dak Prescott","team":"DAL","pos":"QB","matchup":"vs ARI","mean":22.0,"floor":9.9,"p90":37.2,"p_boom":0.33,"grade":"A","note":""},
{"slot":"RB","player":"Kyren Williams","team":"LA","pos":"RB","matchup":"vs LAC","mean":16.4,"floor":5.4,"p90":30.5,"p_boom":0.29,"grade":"A","note":""},
{"slot":"RB","player":"Bucky Irving","team":"TB","pos":"RB","matchup":"vs ATL","mean":15.8,"floor":4.5,"p90":29.9,"p_boom":0.27,"grade":"A","note":""},
{"slot":"WR","player":"CeeDee Lamb","team":"DAL","pos":"WR","matchup":"vs ARI","mean":14.8,"floor":2.7,"p90":30.4,"p_boom":0.26,"grade":"B","note":""},
{"slot":"WR","player":"Khalil Shakir","team":"BUF","pos":"WR","matchup":"vs BAL","mean":8.4,"floor":0.9,"p90":17.9,"p_boom":0.07,"grade":"A+","note":""},
{"slot":"TE","player":"Brock Bowers","team":"LV","pos":"TE","matchup":"@ NYJ","mean":11.3,"floor":2.0,"p90":23.1,"p_boom":0.27,"grade":"C","note":""},
{"slot":"W/R/T","player":"Emanuel Wilson","team":"SEA","pos":"RB","matchup":"vs CHI","mean":10.0,"floor":2.1,"p90":19.6,"p_boom":0.09,"grade":"F","note":""},
{"slot":"K","player":"Chase McLaughlin","team":"TB","pos":"K","matchup":"vs ATL","mean":9.9,"floor":2.0,"p90":19.3,"p_boom":0.33,"grade":"C","note":""},
{"slot":"D","player":"Kyle Hamilton","team":"BAL","pos":"DB","matchup":"@ BUF","mean":6.5,"floor":2.5,"p90":11.5,"p_boom":0.17,"grade":"A+","note":"7.5 wtd-L4 (7.6 ssn), 96% snaps; 1 INT/4 PD, 0.118 tkl/snap"},
{"slot":"LB","player":"Jamien Sherwood","team":"NYJ","pos":"LB","matchup":"vs LV","mean":6.5,"floor":2.5,"p90":11.5,"p_boom":0.17,"grade":"B","note":"9.6 wtd-L4 (7.1 ssn), 97% snaps; 0.121 tkl/snap; low-volume opp"}
]},
"bench":[
{"slot":"BN","player":"Jaylen Waddle","team":"DEN","pos":"WR","matchup":"vs KC","mean":5.5,"floor":0.0,"p90":13.0,"p_boom":0.02,"grade":"D","note":""},
{"slot":"BN","player":"TreVeyon Henderson","team":"NE","pos":"RB","matchup":"@ MIA","mean":4.8,"floor":0.6,"p90":10.3,"p_boom":0.01,"grade":"A","note":""},
{"slot":"IR","player":"Deebo Samuel","team":"SF","pos":"WR","matchup":"BYE","mean":0.0,"floor":0.0,"p90":0.0,"p_boom":0.0,"grade":"","note":"Yahoo INA; SF bye; 5 games in 2026 (10.5 ppg), none since wk5 - check IR eligibility"},
{"slot":"IR","player":"Jordyn Tyson","team":"NO","pos":"WR","matchup":"BYE","mean":0.0,"floor":0.0,"p90":0.0,"p_boom":0.0,"grade":"","note":"Yahoo IR on bench; NO bye; no 2026 snaps in nflverse"},
{"slot":"BN","player":"Hunter Henry","team":"NE","pos":"TE","matchup":"@ MIA","mean":8.3,"floor":0.9,"p90":18.3,"p_boom":0.16,"grade":"A+","note":""},
{"slot":"BN","player":"Ka'imi Fairbairn","team":"HOU","pos":"K","matchup":"BYE","mean":0.0,"floor":0.0,"p90":0.0,"p_boom":0.0,"grade":"","note":"2nd K, HOU bye"}
],
"moves":["Move Jordyn Tyson to an IR slot (Yahoo IR; frees a bench spot, no drop needed).","Drop candidate: Ka'imi Fairbairn (2nd K, BYE wk8, ROS 10.2/g); one K is enough outside bye weeks.","Low-value bench: TreVeyon Henderson ROS 4.2/g (@ MIA).","Low-value bench: Deebo Samuel ROS 5.6/g (Yahoo INA; SF bye; 5 games in 2026 (10.5 ppg), none since wk5 - check IR eligibility).","Low-value bench: Jaylen Waddle ROS 6.7/g (vs KC).","QB: Dak Prescott bye wk 14 - stream that week","Sherwood at LB per user decision (FA add; Bailey is Q)"],
"waivers":[
{"pos":"WR","player":"Malik Washington","team":"MIA","status":"FA","pct":49,"ros":7.6,"wk":8.1,"gain":0.2,"verdict":"toss-up (within model error)","faab":"FA - free add, no bid","opp":"vs NE"},
{"pos":"LB","player":"Jamien Sherwood","team":"NYJ","status":"FA","pct":null,"ros":6.5,"wk":6.5,"gain":0.0,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs LV"},
{"pos":"K","player":"Jason Myers","team":"SEA","status":"W","pct":90,"ros":10.5,"wk":10.4,"gain":0.0,"verdict":"toss-up (within model error)","faab":"$0-1 (depth only)","opp":"vs CHI"},
{"pos":"LB","player":"Devin Bush","team":"CHI","status":"FA","pct":null,"ros":6.5,"wk":6.5,"gain":-0.0,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ SEA"},
{"pos":"LB","player":"Jacob Rodriguez","team":"MIA","status":"FA","pct":null,"ros":6.4,"wk":6.4,"gain":-0.1,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs NE"},
{"pos":"LB","player":"Josiah Trotter","team":"TB","status":"FA","pct":null,"ros":6.4,"wk":6.4,"gain":-0.1,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs ATL"},
{"pos":"DB","player":"Budda Baker","team":"ARI","status":"FA","pct":null,"ros":6.4,"wk":6.4,"gain":-0.1,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ DAL"},
{"pos":"DB","player":"Keisean Nixon","team":"GB","status":"FA","pct":null,"ros":6.2,"wk":6.2,"gain":-0.2,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs CAR"},
{"pos":"LB","player":"Zack Baun","team":"PHI","status":"W (until Oct 31)","pct":null,"ros":6.2,"wk":6.2,"gain":-0.2,"verdict":"depth","faab":"$0-1 (depth only)","opp":"@ WAS"},
{"pos":"LB","player":"Bobby Okereke","team":"CAR","status":"FA","pct":null,"ros":6.2,"wk":6.2,"gain":-0.2,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ GB"},
{"pos":"WR","player":"Ryan Flournoy","team":"DAL","status":"FA","pct":24,"ros":7.0,"wk":7.2,"gain":-0.4,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"vs ARI"},
{"pos":"DB","player":"Dillon Thieneman","team":"CHI","status":"FA","pct":null,"ros":6.1,"wk":6.1,"gain":-0.4,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ SEA"},
{"pos":"WR","player":"Kendrick Bourne","team":"ARI","status":"FA","pct":17,"ros":7.0,"wk":7.7,"gain":-0.4,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"@ DAL"},
{"pos":"WR","player":"Keenan Allen","team":"IND","status":"FA","pct":53,"ros":7.0,"wk":8.1,"gain":-0.4,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"@ JAX"},
{"pos":"DB","player":"Caleb Downs","team":"DAL","status":"FA","pct":null,"ros":5.9,"wk":5.9,"gain":-0.6,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs ARI"},
{"pos":"QB","player":"Deshaun Watson","team":"CLE","status":"FA","pct":13,"ros":18.5,"wk":17.1,"gain":-0.6,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"@ PIT"},
{"pos":"DB","player":"Nick Emmanwori","team":"SEA","status":"FA","pct":null,"ros":5.9,"wk":5.9,"gain":-0.6,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs CHI"},
{"pos":"QB","player":"Aaron Rodgers","team":"PIT","status":"W","pct":49,"ros":18.4,"wk":17.3,"gain":-0.8,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"vs CLE"},
{"pos":"K","player":"Andre Szmyt","team":"CLE","status":"W","pct":1,"ros":9.7,"wk":8.6,"gain":-0.8,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"@ PIT"},
{"pos":"WR","player":"DeMario Douglas","team":"NE","status":"W","pct":33,"ros":6.5,"wk":6.4,"gain":-0.8,"verdict":"depth/bye cover","faab":"$0-1 (depth only)","opp":"@ MIA"},
{"pos":"DL","player":"Dallas Turner","team":"MIN","status":"FA","pct":null,"ros":5.6,"wk":5.6,"gain":-0.9,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ DET"},
{"pos":"K","player":"Cairo Santos","team":"CHI","status":"FA","pct":44,"ros":9.6,"wk":9.1,"gain":-0.9,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"@ SEA"},
{"pos":"K","player":"Wil Lutz","team":"DEN","status":"FA","pct":15,"ros":9.6,"wk":8.5,"gain":-0.9,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"vs KC"},
{"pos":"K","player":"Jake Bates","team":"DET","status":"FA","pct":68,"ros":9.6,"wk":9.5,"gain":-0.9,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"vs MIN"},
{"pos":"DL","player":"Andrew Van Ginkel","team":"MIN","status":"W (until Oct 31)","pct":null,"ros":5.4,"wk":5.4,"gain":-1.1,"verdict":"depth","faab":"$0-1 (depth only)","opp":"@ DET"},
{"pos":"DL","player":"Leonard Williams","team":"SEA","status":"FA","pct":null,"ros":5.4,"wk":5.4,"gain":-1.1,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs CHI"},
{"pos":"DB","player":"Cole Bishop","team":"BUF","status":"FA","pct":null,"ros":5.3,"wk":5.3,"gain":-1.2,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs BAL"},
{"pos":"QB","player":"Geno Smith","team":"NYJ","status":"FA","pct":19,"ros":17.9,"wk":19.1,"gain":-1.2,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"vs LV"},
{"pos":"DL","player":"Austin Booker","team":"CHI","status":"FA","pct":null,"ros":5.2,"wk":5.2,"gain":-1.3,"verdict":"depth","faab":"FA - free add, no bid","opp":"@ SEA"},
{"pos":"WR","player":"Jordan Addison","team":"MIN","status":"FA","pct":72,"ros":5.9,"wk":6.0,"gain":-1.5,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"@ DET"},
{"pos":"DL","player":"Quinnen Williams","team":"DAL","status":"FA","pct":null,"ros":5.0,"wk":5.0,"gain":-1.5,"verdict":"depth","faab":"FA - free add, no bid","opp":"vs ARI"},
{"pos":"K","player":"Jason Sanders","team":"NYJ","status":"FA","pct":1,"ros":9.0,"wk":9.4,"gain":-1.5,"verdict":"depth/bye cover","faab":"FA - free add, no bid","opp":"vs LV"}
],
"boom_thr":{"QB":25,"RB":20,"WR":20,"TE":15,"K":12},
"scoring":"Pass 20 yd/pt (+5 at 375), TD 4, INT -1; Rush 10 yd/pt (+5 at 180), TD 6; Rec 0.5 PPR, 10 yd/pt (+5 at 200), TD 6; FL -2; 2pt 2. K: PAT +1/-1, FG 0.1 pt per made-FG yard, missed FG 0-29 yds -1. IDP: solo .75, ast .25, sack 3, INT 5, FF 5, FR 2, TD 6, PD 1, TFL 1.5, safety 3.",
"backtest":"Offense backtest (mean over weeks, by position):\n               spearman    hit  top_avg    mae   bias\npos model                                           \nK   base         0.201  0.458    9.652  4.295  0.012\n    base_inj     0.201  0.458    9.652  4.295  0.012\n    model        0.151  0.458    9.400  4.248 -0.139\nQB  base         0.351  0.521   18.386  8.718  3.550\n    base_inj     0.558  0.583   20.594  6.914  1.648\n    model        0.656  0.583   21.340  6.173  0.054\nRB  base         0.451  0.688   12.301  6.271  1.287\n    base_inj     0.634  0.781   13.558  5.230  0.129\n    model        0.669  0.802   13.701  5.066 -0.589\nTE  base         0.419  0.292    7.600  4.239  0.650\n    base_inj     0.497  0.312    7.927  3.943  0.313\n    model        0.585  0.354    8.735  3.474 -0.559\nWR  base         0.369  0.535    9.291  5.364  1.292\n    base_inj     0.558  0.597   10.538  4.696  0.417\n    model        0.632  0.618   10.660  4.270 -0.470 \n\nAll positions:\n           spearman    hit  top_avg    mae\nmodel                                    \nbase         0.358  0.499   11.446  5.777\nbase_inj     0.490  0.547   12.454  5.015\nmodel        0.539  0.563   12.767  4.646\n\nCalibration (n=1092): below P10 0.038, above P90 0.109\n  p_ge15: predicted 0.160 observed 0.195\n  p_ge20: predicted 0.084 observed 0.099\n  p_boom: predicted 0.098 observed 0.119\n  P(>=20) reliability:\n                 n   pred    obs\n_b                              \n(-0.01, 0.03]  504  0.008  0.016\n(0.03, 0.08]   254  0.051  0.039\n(0.08, 0.15]   123  0.109  0.154\n(0.15, 0.25]    98  0.200  0.224\n(0.25, 0.4]     79  0.326  0.354\n(0.4, 1.0]      34  0.465  0.618\n"
};
const TRADES: TradeData = {"week":8,"weeks":"8-17","me":"Breeces Pieces","sources":["FantasyCalc redraft trade values (12-team, 1QB, half PPR; 197 players, fetched 2026-10-28)","FantasyPros ROS half-PPR overall ECR (398 players, 5 experts, updated 10/28)","FantasyPros ROS IDP ECR (169 players, 2 experts, updated 10/25)"],"minRatio":0.4,"minGain":3.0,"nWinWin":447,"nKept":91,"odds":[{"team":"Nico(demus) Brown","p":0.89},{"team":"Daejon Love","p":0.86},{"team":"Teach me how2 Griddy","p":0.86},{"team":"Breeces Pieces","p":0.67},{"team":"High Speed Ja’Marr Chase","p":0.61},{"team":"Run it back with Runningbacks?","p":0.58},{"team":"Eggsbuka Tyrone","p":0.57},{"team":"Psoas-spended","p":0.31},{"team":"LONDON Bridge is Falling Down","p":0.3},{"team":"Learn How2 Griddy Already","p":0.24},{"team":"We Are Christian Kirk","p":0.12},{"team":"4 + 9 IRs and counting","p":0.0}],"tests":[{"test":"star-for-scrub rejected","trade":"T4 gives Dak Prescott for Jihaad Campbell (T1)","gain_me":-16.1,"gain_them":14.1,"passed":true},{"test":"surplus-for-need swap is mutual","trade":"RB-rich team gives Jonathan Taylor for Tetairoa McMillan","gain_me":35.9,"gain_them":67.0,"passed":true}],
"rows":[
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Tee Higgins (WR, CIN) + Trevor Lawrence (QB, JAX)","give":"Brock Bowers (TE, LV) + Dak Prescott (QB, DAL)","ga":15.2,"gb":9.8,"bal":0.64,"minG":9.8,"accept":"Fair on paper","note":"consensus values are close","ratio":0.83,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +3.2, QB +1.2, TE -2.8 = net +1.4/wk. Psoas-spended: TE +3.5, WR -1.5 = net +1.2/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Tee Higgins (WR, CIN) + Trevor Lawrence (QB, JAX)","give":"Brock Bowers (TE, LV)","ga":8.8,"gb":8.3,"bal":0.94,"minG":8.3,"accept":"Fair on paper","note":"consensus values are close","ratio":0.96,"moves":"T9 adds FA Bobby Okereke","reason":"You: WR +3.2, QB +1.3, TE -3.6 = net +0.8/wk. Psoas-spended: TE +3.5, IDP +0.6, QB -1.0, WR -1.5 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Chris Olave (WR, NO)","give":"Brock Bowers (TE, LV) + Khalil Shakir (WR, BUF)","ga":8.0,"gb":8.9,"bal":0.91,"minG":8.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.83,"moves":"T12 drops Mike Washington Jr.; T4 adds FA Greg Dulcich; T4 adds FA Bobby Okereke","reason":"You: WR +3.2, IDP +0.4, TE -2.8 = net +0.6/wk. Run it back with Runningbacks?: TE +4.0, WR -2.9 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Blake Cashman (LB, MIN) + Germie Bernard (WR, PIT)","give":"Brock Bowers (TE, LV) + Jamien Sherwood (LB, NYJ)","ga":7.8,"gb":7.6,"bal":0.98,"minG":7.6,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.13,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +1.9, IDP +1.8, TE -2.8 = net +0.8/wk. Psoas-spended: TE +3.5, WR -0.4, IDP -1.8 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Kyren Williams (RB, LA)","ga":11.3,"gb":7.4,"bal":0.66,"minG":7.4,"accept":"Fair on paper","note":"consensus values are close","ratio":1.11,"moves":"T9 adds FA Greg Dulcich","reason":"You: WR +3.2, RB -2.2 = net +1.0/wk. Psoas-spended: RB +2.0, TE +0.7, WR -1.5 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Jacoby Brissett (QB, ARI)","give":"Dak Prescott (QB, DAL) + Hunter Henry (TE, NE)","ga":7.3,"gb":9.5,"bal":0.77,"minG":7.3,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.1,"moves":"T8 drops Garrett Wilson; T4 adds FA Malik Washington; T4 adds FA Bobby Okereke","reason":"You: QB +0.9, IDP +0.4, TE -0.4 = net +0.6/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, QB -0.9 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Bucky Irving (RB, TB)","ga":7.3,"gb":7.7,"bal":0.95,"minG":7.3,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.62,"moves":"T9 adds FA Greg Dulcich","reason":"You: WR +3.2, RB -2.8 = net +0.7/wk. Psoas-spended: RB +1.7, TE +0.7, WR -1.5 = net +1.0/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-2","get":"Chuba Hubbard (RB, CAR) + Chris Olave (WR, NO)","give":"Kyren Williams (RB, LA) + Brock Bowers (TE, LV)","ga":7.0,"gb":9.0,"bal":0.78,"minG":7.0,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.79,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +3.4, TE -2.8 = net +0.5/wk. Run it back with Runningbacks?: TE +4.0, WR -2.9 = net +1.2/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Brock Bowers (TE, LV) + Khalil Shakir (WR, BUF)","ga":12.7,"gb":6.7,"bal":0.53,"minG":6.7,"accept":"Fair on paper","note":"consensus values are close","ratio":0.9,"moves":"T8 drops Garrett Wilson; T4 adds FA Greg Dulcich; T4 adds FA Bobby Okereke","reason":"You: WR +4.0, IDP +0.4, TE -2.8 = net +1.3/wk. LONDON Bridge is Falling Down: TE +5.2, WR -4.3 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Chris Olave (WR, NO)","give":"Brock Bowers (TE, LV) + Jamien Sherwood (LB, NYJ)","ga":6.5,"gb":11.7,"bal":0.55,"minG":6.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.85,"moves":"T12 drops Mike Washington Jr.; T4 adds FA Greg Dulcich; T4 adds FA Bobby Okereke","reason":"You: WR +3.4, TE -2.8 = net +0.5/wk. Run it back with Runningbacks?: TE +4.0, IDP +0.3, WR -2.9 = net +1.4/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-1","get":"Tee Higgins (WR, CIN)","give":"Brock Bowers (TE, LV) + Khalil Shakir (WR, BUF)","ga":6.1,"gb":13.4,"bal":0.45,"minG":6.1,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.66,"moves":"T9 drops DJ Moore; T4 adds FA Greg Dulcich; T4 adds FA Bobby Okereke","reason":"You: WR +3.2, IDP +0.4, TE -2.8 = net +0.6/wk. Psoas-spended: TE +3.5, WR -1.5 = net +1.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-1","get":"Chris Olave (WR, NO)","give":"Brock Bowers (TE, LV)","ga":6.0,"gb":8.5,"bal":0.7,"minG":6.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.86,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +3.4, TE -2.8 = net +0.4/wk. Run it back with Runningbacks?: TE +4.0, WR -2.9 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","give":"Bucky Irving (RB, TB)","ga":10.3,"gb":5.8,"bal":0.56,"minG":5.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.57,"moves":"T9 adds FA Greg Dulcich","reason":"You: WR +3.2, RB -2.4 = net +1.0/wk. Psoas-spended: RB +1.6, TE +0.7, WR -1.5 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Chase Brown (RB, CIN) + Germie Bernard (WR, PIT)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":5.7,"gb":9.2,"bal":0.63,"minG":5.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.71,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +1.9, FLEX +0.9, RB +0.7, TE -2.8 = net +0.7/wk. Psoas-spended: TE +3.5, WR -0.4, RB -0.6, FLEX -1.3 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Chase Brown (RB, CIN) + Germie Bernard (WR, PIT)","give":"Kyren Williams (RB, LA) + Khalil Shakir (WR, BUF)","ga":5.3,"gb":8.6,"bal":0.62,"minG":5.3,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.68,"moves":"T4 adds FA Bobby Okereke","reason":"You: WR +1.9, IDP +0.4, RB -1.7 = net +0.4/wk. Psoas-spended: RB +1.5, WR -0.4 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Brock Bowers (TE, LV) + Jamien Sherwood (LB, NYJ)","ga":11.2,"gb":4.9,"bal":0.44,"minG":4.9,"accept":"Fair on paper","note":"consensus values are close","ratio":0.92,"moves":"T8 drops Malachi Fields; T4 adds FA Greg Dulcich; T4 adds FA Bobby Okereke","reason":"You: WR +4.1, TE -2.8 = net +1.1/wk. LONDON Bridge is Falling Down: TE +5.2, WR -4.9 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Drake London (WR, ATL) + Woody Marks (RB, HOU)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":8.6,"gb":4.6,"bal":0.53,"minG":4.6,"accept":"Fair on paper","note":"consensus values are close","ratio":0.96,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +4.1, RB +0.3, FLEX -0.7, TE -2.8 = net +0.8/wk. LONDON Bridge is Falling Down: TE +5.2, FLEX +0.5, WR -4.9 = net +0.7/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Ernest Jones IV (LB, SEA) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE) + Khalil Shakir (WR, BUF)","ga":5.3,"gb":4.5,"bal":0.85,"minG":4.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.9,"moves":"T4 adds FA Greg Dulcich","reason":"You: IDP +1.0 = net +0.5/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, IDP -1.2 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Ernest Jones IV (LB, SEA) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":4.4,"gb":4.5,"bal":0.98,"minG":4.4,"accept":"Fair on paper","note":"consensus values are close","ratio":1.11,"moves":"T4 adds FA Bobby Okereke","reason":"You: IDP +1.1, TE -0.4 = net +0.5/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, IDP -0.6, WR -0.8 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Quinshon Judkins (RB, CLE) + Emeka Egbuka (WR, TB)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":4.2,"gb":5.4,"bal":0.78,"minG":4.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.56,"moves":"T4 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"You: FLEX +1.9, WR +0.7, RB +0.7, TE -2.8 = net +0.4/wk. Eggsbuka Tyrone: TE +3.3, IDP +0.7, FLEX -0.4, RB -2.7 = net +0.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Ernest Jones IV (LB, SEA)","give":"Hunter Henry (TE, NE) + Khalil Shakir (WR, BUF)","ga":4.2,"gb":9.6,"bal":0.44,"minG":4.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.14,"moves":"T8 drops Garrett Wilson; T4 adds FA Malik Washington; T4 adds FA Greg Dulcich","reason":"You: IDP +1.0 = net +0.5/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, IDP -1.2 = net +1.1/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Ernest Jones IV (LB, SEA) + Nakobe Dean (LB, LV)","give":"Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":5.9,"gb":4.2,"bal":0.7,"minG":4.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.34,"moves":"T4 adds FA Malik Washington","reason":"You: IDP +1.3, TE -0.4 = net +0.6/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, IDP -1.5 = net +0.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Teach me how2 Griddy","bid":11,"kind":"2-for-1","get":"Jalen Coker (WR, CAR)","give":"Jamien Sherwood (LB, NYJ) + Khalil Shakir (WR, BUF)","ga":4.3,"gb":4.1,"bal":0.94,"minG":4.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":6.2,"moves":"T11 drops Will Anderson Jr.; T4 adds FA Bobby Okereke; T4 adds FA Justin Herbert","reason":"You: QB +0.3 = net +0.4/wk. Teach me how2 Griddy: IDP +0.6 = net +0.4/wk; Coker was mostly bench."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Zay Flowers (WR, BAL) + Breece Hall (RB, NYJ)","give":"Brock Bowers (TE, LV) + Emanuel Wilson (RB, SEA)","ga":7.0,"gb":4.0,"bal":0.56,"minG":4.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.34,"moves":"T4 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"You: WR +5.3, FLEX -1.9, TE -2.8 = net +0.8/wk. Eggsbuka Tyrone: TE +3.3, RB +1.0, IDP +0.7, FLEX +0.3, WR -4.7 = net +0.3/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Zay Flowers (WR, BAL) + Breece Hall (RB, NYJ)","give":"Kyren Williams (RB, LA) + Jamien Sherwood (LB, NYJ)","ga":4.0,"gb":3.9,"bal":0.98,"minG":3.9,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.32,"moves":"T4 adds FA Bobby Okereke; T5 adds FA Greg Dulcich","reason":"You: WR +5.3, FLEX -1.8, RB -3.3 = net +0.3/wk. Eggsbuka Tyrone: RB +4.5, IDP +0.6, FLEX +0.3, WR -4.7 = net +0.5/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Ernest Jones IV (LB, SEA) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE)","ga":3.7,"gb":7.5,"bal":0.49,"minG":3.7,"accept":"Fair on paper","note":"consensus values are close","ratio":1.18,"moves":"T8 adds FA Greg Dulcich","reason":"You: IDP +1.0, TE -0.4 = net +0.4/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.7, WR -0.8, IDP -1.2 = net +0.9/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"1-for-2","get":"Zay Flowers (WR, BAL) + Breece Hall (RB, NYJ)","give":"Kyren Williams (RB, LA)","ga":3.5,"gb":4.5,"bal":0.78,"minG":3.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.33,"moves":"T5 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"You: WR +5.3, FLEX -1.8, RB -3.3 = net +0.2/wk. Eggsbuka Tyrone: RB +4.5, IDP +0.7, FLEX +0.3, WR -4.7 = net +0.6/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Drake London (WR, ATL) + Woody Marks (RB, HOU)","give":"Kyren Williams (RB, LA) + Hunter Henry (TE, NE)","ga":3.5,"gb":6.2,"bal":0.56,"minG":3.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.89,"moves":"T4 adds FA Greg Dulcich","reason":"You: WR +4.1, FLEX -0.7, RB -3.1 = net +0.1/wk; Henry was mostly bench. LONDON Bridge is Falling Down: FLEX +2.5, TE +2.0, RB +1.5, WR -4.9 = net +1.0/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Nakobe Dean (LB, LV) + Devaughn Vele (WR, NO)","give":"Hunter Henry (TE, NE) + Khalil Shakir (WR, BUF)","ga":3.4,"gb":5.7,"bal":0.6,"minG":3.4,"accept":"Fair on paper","note":"consensus values are close","ratio":0.93,"moves":"T4 adds FA Greg Dulcich","reason":"You: IDP +0.7 = net +0.2/wk; Henry was mostly bench. LONDON Bridge is Falling Down: TE +2.0, IDP -0.9 = net +0.8/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Harold Fannin Jr. (TE, CLE) + Emeka Egbuka (WR, TB)","give":"Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":3.2,"gb":6.4,"bal":0.5,"minG":3.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.22,"moves":"T4 adds FA Bobby Okereke; T5 adds FA Greg Dulcich","reason":"You: WR +0.7 = net +0.3/wk; Henry was mostly bench. Eggsbuka Tyrone: TE +0.7, IDP +0.6, FLEX -0.4 = net +0.7/wk; Fannin was mostly bench."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","give":"Jonathan Taylor (RB, IND)","ga":11.0,"gb":10.0,"bal":0.91,"minG":10.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.86,"moves":"T2 drops Seth McGowan; T9 adds FA Greg Dulcich","reason":"Learn How2 Griddy Already: WR +3.5, RB -2.3 = net +1.3/wk. Psoas-spended: RB +2.2, TE +0.7, WR -1.5 = net +1.1/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Drake London (WR, ATL)","give":"Luther Burden III (WR, CHI) + Brenton Strange (TE, JAX)","ga":13.4,"gb":10.0,"bal":0.75,"minG":10.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.7,"moves":"T8 drops Garrett Wilson; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: WR +2.3, IDP +0.7, TE -1.3 = net +1.3/wk. LONDON Bridge is Falling Down: TE +3.3, WR -2.3 = net +1.0/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"D'Andre Swift (RB, CHI) + Tee Higgins (WR, CIN)","give":"James Cook III (RB, BUF)","ga":9.7,"gb":10.0,"bal":0.97,"minG":9.7,"accept":"Fair on paper","note":"consensus values are close","ratio":0.94,"moves":"T8 drops Garrett Wilson; T9 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: WR +3.5, RB -2.1 = net +1.2/wk. Psoas-spended: RB +2.1, TE +0.7, WR -1.5 = net +1.1/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"James Cook III (RB, BUF)","give":"Tony Pollard (RB, TEN) + Isaiah Likely (TE, NYG)","ga":9.7,"gb":8.3,"bal":0.85,"minG":8.3,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.1,"moves":"T8 drops Garrett Wilson; T1 adds FA Greg Dulcich","reason":"Daejon Love: RB +2.8, TE -1.3 = net +1.4/wk. LONDON Bridge is Falling Down: TE +3.5, FLEX -0.5, RB -2.2 = net +0.8/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Woody Marks (RB, HOU)","give":"Brenton Strange (TE, JAX) + Nico Collins (WR, HOU)","ga":8.3,"gb":12.7,"bal":0.65,"minG":8.3,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.18,"moves":"T8 drops Garrett Wilson; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: FLEX +1.6, IDP +0.7, TE -1.3 = net +0.7/wk. LONDON Bridge is Falling Down: TE +3.3, WR +0.8, RB -0.4, FLEX -2.1 = net +1.5/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"2-for-1","get":"Tee Higgins (WR, CIN)","give":"Sam LaPorta (TE, DET) + Alex Singleton (LB, DEN)","ga":11.9,"gb":8.2,"bal":0.69,"minG":8.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.88,"moves":"T9 drops DJ Moore; T2 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +3.5, IDP -0.7, TE -1.3 = net +1.4/wk. Psoas-spended: TE +1.6, IDP +1.2, WR -1.5 = net +0.9/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Chris Olave (WR, NO) + Sam Darnold (QB, SEA)","give":"Drake Maye (QB, NE)","ga":8.2,"gb":8.1,"bal":0.98,"minG":8.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.85,"moves":"T2 drops Seth McGowan; T12 adds FA Greg Dulcich","reason":"Learn How2 Griddy Already: WR +3.5, QB -3.0 = net +0.7/wk. Run it back with Runningbacks?: QB +3.1, TE +0.9, WR -2.9 = net +1.1/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Ashton Jeanty (RB, LV)","give":"Joe Burrow (QB, CIN) + Brenton Strange (TE, JAX)","ga":7.8,"gb":10.0,"bal":0.78,"minG":7.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.51,"moves":"T12 drops Mike Washington Jr.; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: FLEX +3.3, RB +1.5, IDP +0.7, TE -1.3, QB -3.3 = net +0.8/wk. Run it back with Runningbacks?: QB +3.8, TE +1.9, RB -0.8, FLEX -3.8 = net +1.0/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Jonathan Taylor (RB, IND)","ga":7.2,"gb":11.9,"bal":0.6,"minG":7.2,"accept":"Fair on paper","note":"consensus values are close","ratio":0.89,"moves":"T2 drops Seth McGowan; T9 adds FA Greg Dulcich","reason":"Learn How2 Griddy Already: WR +3.5, RB -2.7 = net +1.0/wk. Psoas-spended: RB +2.2, TE +0.7, WR -1.5 = net +1.2/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Jaylen Warren (RB, PIT) + Sam LaPorta (TE, DET)","ga":6.8,"gb":7.2,"bal":0.95,"minG":6.8,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.29,"moves":"","reason":"Learn How2 Griddy Already: WR +3.5, TE -1.3, RB -1.4 = net +0.9/wk. Psoas-spended: TE +1.6, RB +1.0, WR -1.5 = net +0.7/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Chris Olave (WR, NO) + Fred Warner (LB, SF)","give":"Joe Burrow (QB, CIN)","ga":8.0,"gb":6.7,"bal":0.84,"minG":6.7,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.69,"moves":"T7 drops Josh Downs; T12 adds FA Greg Dulcich","reason":"Nico(demus) Brown: WR +1.6, FLEX +1.3, IDP +0.9, QB -3.3 = net +0.6/wk. Run it back with Runningbacks?: QB +3.8, TE +0.9, IDP -0.9, WR -2.9 = net +0.9/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-1","get":"George Kittle (TE, SF)","give":"Tucker Kraft (TE, GB) + Tee Higgins (WR, CIN)","ga":11.1,"gb":6.4,"bal":0.57,"minG":6.4,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.58,"moves":"T10 drops Marvin Harrison Jr.; T9 adds FA Bobby Okereke","reason":"Psoas-spended: TE +2.5, IDP +0.6, WR -1.5 = net +1.0/wk. We Are Christian Kirk: WR +1.7, FLEX +1.5, TE -2.3 = net +1.0/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"Teach me how2 Griddy","bid":11,"kind":"2-for-1","get":"Jaxon Smith-Njigba (WR, SEA)","give":"D'Andre Swift (RB, CHI) + Tee Higgins (WR, CIN)","ga":7.5,"gb":6.4,"bal":0.85,"minG":6.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.47,"moves":"T11 drops Kaelon Black; T9 adds FA Greg Dulcich","reason":"Psoas-spended: WR +5.0, TE +0.7, FLEX -1.9, RB -2.6 = net +1.0/wk. Teach me how2 Griddy: RB +4.8, FLEX +0.8, WR -5.2 = net +0.6/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"James Cook III (RB, BUF) + Nakobe Dean (LB, LV)","give":"Jonathan Taylor (RB, IND) + Sam LaPorta (TE, DET)","ga":7.9,"gb":6.3,"bal":0.8,"minG":6.3,"accept":"Fair on paper","note":"consensus values are close","ratio":0.82,"moves":"","reason":"Learn How2 Griddy Already: RB +1.7, IDP +0.7, TE -1.3 = net +0.9/wk. LONDON Bridge is Falling Down: TE +3.4, IDP -0.9, RB -1.6 = net +0.6/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"James Cook III (RB, BUF)","give":"Jonathan Taylor (RB, IND) + Sam LaPorta (TE, DET)","ga":6.2,"gb":14.3,"bal":0.44,"minG":6.2,"accept":"Fair on paper","note":"consensus values are close","ratio":0.81,"moves":"T8 drops Garrett Wilson; T2 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: RB +1.7, IDP +0.5, TE -1.3 = net +0.7/wk. LONDON Bridge is Falling Down: TE +3.4, RB -1.6 = net +1.5/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"Teach me how2 Griddy","bid":11,"kind":"2-for-1","get":"Christian McCaffrey (RB, SF)","give":"Chase Brown (RB, CIN) + Josh Jacobs (RB, GB)","ga":6.2,"gb":8.4,"bal":0.74,"minG":6.2,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.15,"moves":"T11 drops Kenny Gainwell; T9 adds FA Greg Dulcich","reason":"Psoas-spended: RB +1.6, TE +0.7, FLEX -1.8 = net +0.3/wk. Teach me how2 Griddy: FLEX +0.8, RB +0.5 = net +1.4/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Nakobe Dean (LB, LV)","give":"Sam LaPorta (TE, DET) + Blake Corum (RB, LA)","ga":7.6,"gb":6.1,"bal":0.8,"minG":6.1,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.31,"moves":"","reason":"Learn How2 Griddy Already: FLEX +1.1, IDP +0.7, RB +0.4, TE -1.3 = net +0.7/wk. LONDON Bridge is Falling Down: TE +3.4, IDP -0.9, FLEX -1.3 = net +0.8/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Ashton Jeanty (RB, LV) + Chris Olave (WR, NO)","give":"James Cook III (RB, BUF)","ga":6.3,"gb":6.0,"bal":0.95,"minG":6.0,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.16,"moves":"T8 drops Garrett Wilson; T12 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: WR +3.5, RB -2.9 = net +0.6/wk. Run it back with Runningbacks?: RB +2.0, TE +0.9, FLEX +0.9, WR -2.9 = net +0.9/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"Woody Marks (RB, HOU)","give":"Sam LaPorta (TE, DET) + Blake Corum (RB, LA)","ga":5.9,"gb":14.0,"bal":0.42,"minG":5.9,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.28,"moves":"T8 drops Garrett Wilson; T2 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: FLEX +1.1, IDP +0.5, RB +0.4, TE -1.3 = net +0.5/wk. LONDON Bridge is Falling Down: TE +3.4, FLEX -1.3 = net +1.7/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Ernest Jones IV (LB, SEA)","give":"Bhayshul Tuten (RB, JAX) + Brenton Strange (TE, JAX)","ga":5.7,"gb":9.5,"bal":0.6,"minG":5.7,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.27,"moves":"","reason":"Nico(demus) Brown: RB +1.2, IDP +1.2, TE -1.3 = net +0.7/wk. LONDON Bridge is Falling Down: TE +3.3, FLEX +0.3, IDP -1.2, RB -1.5 = net +0.9/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Puka Nacua (WR, LA) + D'Andre Swift (RB, CHI)","give":"Kenneth Walker III (RB, KC) + Brenton Strange (TE, JAX)","ga":5.6,"gb":6.4,"bal":0.87,"minG":5.6,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.2,"moves":"","reason":"Nico(demus) Brown: WR +5.5, FLEX +1.0, TE -1.3, RB -4.8 = net +0.4/wk. Psoas-spended: RB +4.4, TE +1.5, WR -5.3 = net +0.6/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Chuba Hubbard (RB, CAR) + Ashton Jeanty (RB, LV)","give":"Kenneth Walker III (RB, KC)","ga":6.4,"gb":5.5,"bal":0.86,"minG":5.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.87,"moves":"T7 drops Josh Downs; T12 adds FA Greg Dulcich","reason":"Nico(demus) Brown: FLEX +3.3, RB -3.0 = net +0.5/wk. Run it back with Runningbacks?: RB +3.7, TE +0.9, FLEX -3.8 = net +0.6/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"James Cook III (RB, BUF) + Ernest Jones IV (LB, SEA)","give":"Malik Nabers (WR, NYG) + Brenton Strange (TE, JAX)","ga":5.4,"gb":8.2,"bal":0.66,"minG":5.4,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.16,"moves":"","reason":"Nico(demus) Brown: RB +4.2, FLEX +3.6, IDP +1.2, TE -1.3, WR -6.4 = net +1.0/wk. LONDON Bridge is Falling Down: WR +7.0, TE +3.3, IDP -1.2, FLEX -2.1, RB -6.6 = net +0.4/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-2","get":"George Kittle (TE, SF) + Arvell Reese (LB,DE, NYG)","give":"Josh Jacobs (RB, GB) + Tucker Kraft (TE, GB)","ga":5.6,"gb":5.4,"bal":0.95,"minG":5.4,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.62,"moves":"","reason":"Psoas-spended: TE +2.5, IDP +0.7, RB -0.8, FLEX -1.8 = net +0.3/wk. We Are Christian Kirk: FLEX +2.6, RB +1.4, IDP -0.8, TE -2.3 = net +1.0/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","give":"Jaylen Warren (RB, PIT) + Sam LaPorta (TE, DET)","ga":10.7,"gb":5.3,"bal":0.5,"minG":5.3,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.25,"moves":"","reason":"Learn How2 Griddy Already: WR +3.5, RB -1.0, TE -1.3 = net +1.2/wk. Psoas-spended: TE +1.6, RB +0.8, WR -1.5 = net +0.6/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Psoas-spended","bid":9,"kind":"2-for-2","get":"D'Andre Swift (RB, CHI) + Tee Higgins (WR, CIN)","give":"Jonathan Taylor (RB, IND) + Sam LaPorta (TE, DET)","ga":10.6,"gb":5.3,"bal":0.5,"minG":5.3,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.77,"moves":"","reason":"Learn How2 Griddy Already: WR +3.5, RB -0.6, TE -1.3 = net +1.4/wk. Psoas-spended: TE +1.6, RB +0.7, WR -1.5 = net +0.5/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Jacoby Brissett (QB, ARI) + Ernest Jones IV (LB, SEA)","give":"Isaiah Likely (TE, NYG)","ga":5.2,"gb":6.8,"bal":0.77,"minG":5.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.11,"moves":"T1 drops David Montgomery; T8 adds FA Justin Herbert","reason":"Daejon Love: QB +2.4, IDP +1.2, TE -2.7 = net +0.7/wk. LONDON Bridge is Falling Down: TE +3.5, IDP -1.2, QB -2.0 = net +0.3/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Eggsbuka Tyrone","bid":5,"kind":"1-for-2","get":"Zay Flowers (WR, BAL) + J.K. Dobbins (RB, DEN)","give":"Jonathan Taylor (RB, IND)","ga":5.1,"gb":5.1,"bal":1.0,"minG":5.1,"accept":"Fair on paper","note":"consensus values are close","ratio":0.84,"moves":"T2 drops Seth McGowan; T5 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +5.6, RB -4.9 = net +0.7/wk. Eggsbuka Tyrone: RB +4.7, IDP +0.7, WR -4.7 = net +0.4/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"1-for-2","get":"Chuba Hubbard (RB, CAR) + Fred Warner (LB, SF)","give":"Jonathan Taylor (RB, IND)","ga":4.7,"gb":4.8,"bal":0.98,"minG":4.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.6,"moves":"T2 drops Seth McGowan; T12 adds FA Greg Dulcich","reason":"Learn How2 Griddy Already: IDP +0.8, RB -0.4 = net +0.4/wk. Run it back with Runningbacks?: TE +0.9, RB +0.3, IDP -0.9 = net +0.5/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Chuba Hubbard (RB, CAR)","give":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","ga":5.7,"gb":4.7,"bal":0.82,"minG":4.7,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.68,"moves":"T12 drops Mike Washington Jr.; T9 adds FA Greg Dulcich","reason":"Psoas-spended: RB +1.3, TE +0.7, WR -1.5 = net +0.6/wk. Run it back with Runningbacks?: WR +2.3, RB -0.8, FLEX -1.0 = net +0.6/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Drake London (WR, ATL) + Nakobe Dean (LB, LV)","give":"Colston Loveland (TE, CHI) + Tre Tucker (WR, LV)","ga":7.9,"gb":4.2,"bal":0.54,"minG":4.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.97,"moves":"T3 adds FA Greg Dulcich; T3 adds FA Bobby Okereke","reason":"4 + 9 IRs and counting: WR +1.9, IDP +0.9, TE -1.4 = net +1.0/wk. LONDON Bridge is Falling Down: TE +3.4, IDP -0.9, WR -2.0 = net +0.5/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Ashton Jeanty (RB, LV)","give":"Joe Burrow (QB, CIN) + Luther Burden III (WR, CHI)","ga":6.8,"gb":4.2,"bal":0.62,"minG":4.2,"accept":"Fair on paper","note":"consensus values are close","ratio":1.07,"moves":"T12 drops Mike Washington Jr.; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: FLEX +3.2, RB +1.5, IDP +0.7, WR -1.3, QB -3.3 = net +0.6/wk. Run it back with Runningbacks?: QB +3.8, WR +1.0, RB -0.8, FLEX -3.6 = net +0.3/wk."},
{"mine":false,"a":"High Speed Ja’Marr Chase","aid":6,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Ashton Jeanty (RB, LV)","give":"Aaron Jones Sr. (RB, MIN) + Brock Purdy (QB, SF)","ga":4.1,"gb":4.2,"bal":0.99,"minG":4.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.45,"moves":"T12 drops Mike Washington Jr.; T6 adds FA Greg Dulcich; T6 adds FA Bobby Okereke; T6 adds FA Justin Herbert","reason":"High Speed Ja’Marr Chase: RB +1.1, QB -0.5 = net +0.5/wk. Run it back with Runningbacks?: QB +1.6, RB -0.4, FLEX -1.0 = net +0.3/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"1-for-2","get":"Brock Purdy (QB, SF) + Ja'Marr Chase (WR, CIN)","give":"Mike Evans (WR, SF)","ga":4.1,"gb":5.6,"bal":0.73,"minG":4.1,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.68,"moves":"T1 drops David Montgomery; T6 adds FA Greg Dulcich; T6 adds FA Bobby Okereke; T6 adds FA Justin Herbert","reason":"Daejon Love: QB +1.5, WR -0.4, FLEX -0.6 = net +0.5/wk. High Speed Ja’Marr Chase: WR +1.0, QB -0.5 = net +0.5/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Ashton Jeanty (RB, LV)","give":"Drake Maye (QB, NE) + Sam LaPorta (TE, DET)","ga":4.0,"gb":4.4,"bal":0.92,"minG":4.0,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.24,"moves":"T12 drops Mike Washington Jr.; T2 adds FA Justin Herbert","reason":"Learn How2 Griddy Already: FLEX +4.0, RB +0.7, TE -1.3, QB -3.1 = net +0.4/wk. Run it back with Runningbacks?: QB +3.1, TE +2.0, RB -0.8, FLEX -3.8 = net +0.5/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Nakobe Dean (LB, LV)","give":"Sam LaPorta (TE, DET) + Alex Singleton (LB, DEN)","ga":4.0,"gb":5.2,"bal":0.77,"minG":4.0,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.44,"moves":"","reason":"Learn How2 Griddy Already: FLEX +1.7, RB +0.4, IDP -0.5, TE -1.3 = net +0.3/wk. LONDON Bridge is Falling Down: TE +3.4, IDP +0.5, RB -0.4, FLEX -2.7 = net +0.8/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Teach me how2 Griddy","bid":11,"kind":"1-for-2","get":"Parker Washington (WR, JAX) + Cam Skattebo (RB, NYG)","give":"Jaylen Warren (RB, PIT)","ga":4.0,"gb":6.1,"bal":0.65,"minG":4.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.38,"moves":"T2 drops Seth McGowan; T11 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +3.6, RB -3.5 = net +0.3/wk. Teach me how2 Griddy: RB +3.9, IDP +0.7, FLEX -0.7, WR -2.8 = net +0.8/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Bijan Robinson (RB, ATL)","give":"Jaylen Warren (RB, PIT) + Sam LaPorta (TE, DET)","ga":4.5,"gb":4.0,"bal":0.87,"minG":4.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.85,"moves":"T12 drops Mike Washington Jr.; T2 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: RB +1.4, IDP +0.5, TE -1.3 = net +0.6/wk. Run it back with Runningbacks?: TE +2.0, RB -1.5 = net +0.4/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Amon-Ra St. Brown (WR, DET) + J.K. Dobbins (RB, DEN)","give":"Jonathan Taylor (RB, IND) + Sam LaPorta (TE, DET)","ga":4.3,"gb":4.0,"bal":0.93,"minG":4.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.96,"moves":"T5 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +6.9, TE -1.3, RB -4.9 = net +0.4/wk. Eggsbuka Tyrone: RB +4.7, TE +1.3, IDP +0.7, WR -6.1 = net +0.4/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"James Cook III (RB, BUF) + Nakobe Dean (LB, LV)","give":"Malik Nabers (WR, NYG) + Brenton Strange (TE, JAX)","ga":3.9,"gb":9.5,"bal":0.42,"minG":3.9,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.16,"moves":"","reason":"Nico(demus) Brown: RB +4.2, FLEX +3.6, IDP +0.9, TE -1.3, WR -6.4 = net +0.8/wk. LONDON Bridge is Falling Down: WR +7.0, TE +3.3, IDP -0.9, FLEX -2.1, RB -6.6 = net +0.6/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Woody Marks (RB, HOU) + Ernest Jones IV (LB, SEA)","give":"Sam LaPorta (TE, DET) + Alex Singleton (LB, DEN)","ga":5.3,"gb":3.9,"bal":0.73,"minG":3.9,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.43,"moves":"","reason":"Learn How2 Griddy Already: FLEX +1.7, RB +0.4, TE -1.3 = net +0.5/wk. LONDON Bridge is Falling Down: TE +3.4, RB -0.4, FLEX -2.7 = net +0.5/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Eggsbuka Tyrone","bid":5,"kind":"2-for-2","get":"Zay Flowers (WR, BAL) + J.K. Dobbins (RB, DEN)","give":"Jaylen Warren (RB, PIT) + Sam LaPorta (TE, DET)","ga":3.8,"gb":4.9,"bal":0.77,"minG":3.8,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.22,"moves":"T5 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +5.6, TE -1.3, RB -3.6 = net +0.5/wk. Eggsbuka Tyrone: RB +3.4, TE +1.3, IDP +0.7, WR -4.7 = net +0.4/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-2","get":"Javonte Williams (RB, DAL) + Drake London (WR, ATL)","give":"Malik Nabers (WR, NYG) + Brenton Strange (TE, JAX)","ga":4.8,"gb":3.8,"bal":0.79,"minG":3.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.4,"moves":"","reason":"Nico(demus) Brown: FLEX +3.2, RB +1.7, TE -1.3, WR -2.6 = net +1.0/wk. LONDON Bridge is Falling Down: TE +3.3, WR +2.7, FLEX -2.6, RB -3.6 = net -0.2/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-2","get":"George Kittle (TE, SF) + Arvell Reese (LB,DE, NYG)","give":"Chase Brown (RB, CIN) + Tucker Kraft (TE, GB)","ga":3.8,"gb":7.5,"bal":0.5,"minG":3.8,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.65,"moves":"","reason":"Psoas-spended: TE +2.5, IDP +0.7, RB -1.0, FLEX -1.8 = net +0.1/wk. We Are Christian Kirk: FLEX +3.0, RB +1.1, IDP -0.8, TE -2.3 = net +1.1/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Jacoby Brissett (QB, ARI) + Nakobe Dean (LB, LV)","give":"Isaiah Likely (TE, NYG)","ga":3.8,"gb":8.0,"bal":0.47,"minG":3.8,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.12,"moves":"T1 drops David Montgomery; T8 adds FA Justin Herbert","reason":"Daejon Love: QB +2.4, IDP +0.9, TE -2.7 = net +0.5/wk. LONDON Bridge is Falling Down: TE +3.5, IDP -0.9, QB -2.0 = net +0.6/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Tony Pollard (RB, TEN)","ga":6.9,"gb":3.6,"bal":0.52,"minG":3.6,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":4.14,"moves":"T1 drops David Montgomery; T9 adds FA Greg Dulcich","reason":"Daejon Love: WR +1.0, FLEX +1.0, RB -1.5 = net +0.9/wk. Psoas-spended: RB +1.5, TE +0.7, WR -1.5 = net +0.4/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"We Are Christian Kirk","bid":10,"kind":"1-for-2","get":"George Pickens (WR, DAL) + Arvell Reese (LB,DE, NYG)","give":"Tetairoa McMillan (WR, CAR)","ga":3.6,"gb":3.7,"bal":0.98,"minG":3.6,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.13,"moves":"T1 drops David Montgomery; T10 adds FA Bobby Okereke","reason":"Daejon Love: IDP +0.8, WR -0.3 = net +0.2/wk. We Are Christian Kirk: WR +0.5 = net +0.4/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"1-for-2","get":"Brock Purdy (QB, SF) + Ja'Marr Chase (WR, CIN)","give":"DK Metcalf (WR, PIT)","ga":3.5,"gb":6.2,"bal":0.57,"minG":3.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":6.97,"moves":"T1 drops David Montgomery; T6 adds FA Greg Dulcich; T6 adds FA Bobby Okereke; T6 adds FA Justin Herbert","reason":"Daejon Love: QB +1.5, WR -0.6, FLEX -0.6 = net +0.3/wk. High Speed Ja’Marr Chase: WR +1.1, QB -0.5 = net +0.6/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"1-for-2","get":"Braelon Allen (RB, NYJ) + Brock Purdy (QB, SF)","give":"Tony Pollard (RB, TEN)","ga":3.5,"gb":6.6,"bal":0.53,"minG":3.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.76,"moves":"T1 drops David Montgomery; T6 adds FA Greg Dulcich; T6 adds FA Bobby Okereke; T6 adds FA Justin Herbert","reason":"Daejon Love: QB +1.5, RB -1.1 = net +0.3/wk. High Speed Ja’Marr Chase: RB +1.2, QB -0.5 = net +0.7/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-2","get":"Ashton Jeanty (RB, LV) + Chris Olave (WR, NO)","give":"Jonathan Taylor (RB, IND) + Sam LaPorta (TE, DET)","ga":7.7,"gb":3.5,"bal":0.45,"minG":3.5,"accept":"Fair on paper","note":"consensus values are close","ratio":0.94,"moves":"","reason":"Learn How2 Griddy Already: WR +3.5, TE -1.3, RB -1.3 = net +0.8/wk. Run it back with Runningbacks?: TE +2.0, RB +0.8, FLEX +0.5, WR -2.9 = net +0.4/wk."},
{"mine":false,"a":"Daejon Love","aid":1,"b":"High Speed Ja’Marr Chase","bid":6,"kind":"1-for-2","get":"Rhamondre Stevenson (RB, NE) + Brock Purdy (QB, SF)","give":"DK Metcalf (WR, PIT)","ga":7.1,"gb":3.4,"bal":0.48,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":2.67,"moves":"T1 drops David Montgomery; T6 adds FA Greg Dulcich; T6 adds FA Bobby Okereke; T6 adds FA Justin Herbert","reason":"Daejon Love: QB +1.5, RB +0.4, FLEX -0.3, WR -0.8 = net +0.7/wk. High Speed Ja’Marr Chase: WR +1.2, QB -0.5 = net +0.3/wk."},
{"mine":false,"a":"LONDON Bridge is Falling Down","aid":8,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"D'Andre Swift (RB, CHI) + Josh Jacobs (RB, GB)","give":"James Cook III (RB, BUF)","ga":5.2,"gb":3.4,"bal":0.65,"minG":3.4,"accept":"Fair on paper","note":"consensus values are close","ratio":0.96,"moves":"T8 drops Garrett Wilson; T9 adds FA Greg Dulcich","reason":"LONDON Bridge is Falling Down: FLEX +2.2, RB -1.8 = net +0.7/wk. Psoas-spended: RB +1.6, TE +0.7, FLEX -1.8 = net +0.3/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Chris Olave (WR, NO)","give":"Luther Burden III (WR, CHI) + Brenton Strange (TE, JAX)","ga":7.8,"gb":3.4,"bal":0.43,"minG":3.4,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.57,"moves":"T12 drops Mike Washington Jr.; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: WR +1.4, IDP +0.7, TE -1.3 = net +0.6/wk. Run it back with Runningbacks?: TE +1.9, WR -1.5 = net +0.5/wk."},
{"mine":false,"a":"Psoas-spended","aid":9,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-1","get":"Chuba Hubbard (RB, CAR)","give":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","ga":7.5,"gb":3.2,"bal":0.43,"minG":3.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.66,"moves":"T12 drops Mike Washington Jr.; T9 adds FA Greg Dulcich","reason":"Psoas-spended: RB +1.4, TE +0.7, FLEX +0.3, WR -1.5 = net +0.8/wk. Run it back with Runningbacks?: WR +2.3, FLEX -0.9, RB -1.1 = net +0.4/wk."},
{"mine":false,"a":"We Are Christian Kirk","aid":10,"b":"Teach me how2 Griddy","bid":11,"kind":"2-for-1","get":"Parker Washington (WR, JAX)","give":"George Pickens (WR, DAL) + Arvell Reese (LB,DE, NYG)","ga":3.2,"gb":4.6,"bal":0.69,"minG":3.2,"accept":"Fair on paper","note":"consensus values are close","ratio":1.01,"moves":"T11 drops Will Anderson Jr.; T10 adds FA Bobby Okereke","reason":"We Are Christian Kirk: WR +0.5 = net +0.3/wk. Teach me how2 Griddy: IDP +0.8, WR -0.4 = net +0.4/wk."},
{"mine":false,"a":"Nico(demus) Brown","aid":7,"b":"Psoas-spended","bid":9,"kind":"2-for-1","get":"Tee Higgins (WR, CIN)","give":"Luther Burden III (WR, CHI) + Brenton Strange (TE, JAX)","ga":5.8,"gb":3.2,"bal":0.55,"minG":3.2,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.25,"moves":"T9 drops DJ Moore; T7 adds FA Bobby Okereke","reason":"Nico(demus) Brown: WR +1.4, IDP +0.7, TE -1.3 = net +0.6/wk. Psoas-spended: TE +1.5, WR -1.0 = net +0.3/wk."},
{"mine":false,"a":"4 + 9 IRs and counting","aid":3,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"1-for-2","get":"Jacoby Brissett (QB, ARI) + Ernest Jones IV (LB, SEA)","give":"Colston Loveland (TE, CHI)","ga":3.2,"gb":4.4,"bal":0.72,"minG":3.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.12,"moves":"T3 adds FA Greg Dulcich; T8 adds FA Justin Herbert","reason":"4 + 9 IRs and counting: QB +1.7, IDP +0.5, TE -1.4 = net +0.5/wk. LONDON Bridge is Falling Down: TE +3.4, IDP -1.2, QB -2.0 = net +0.2/wk."},
{"mine":false,"a":"Eggsbuka Tyrone","aid":5,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"2-for-1","get":"James Cook III (RB, BUF)","give":"Amon-Ra St. Brown (WR, DET) + J.K. Dobbins (RB, DEN)","ga":6.5,"gb":3.1,"bal":0.48,"minG":3.1,"accept":"Fair on paper","note":"consensus values are close","ratio":0.85,"moves":"T8 drops Garrett Wilson; T5 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"Eggsbuka Tyrone: RB +6.5, IDP +0.7, WR -6.1 = net +0.9/wk. LONDON Bridge is Falling Down: WR +6.9, FLEX -0.8, RB -6.0 = net +0.2/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Nico(demus) Brown","bid":7,"kind":"2-for-1","get":"Luther Burden III (WR, CHI)","give":"A.J. Brown (WR, NE) + Alex Singleton (LB, DEN)","ga":3.0,"gb":3.1,"bal":0.99,"minG":3.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.9,"moves":"T7 drops Josh Downs; T2 adds FA Bobby Okereke","reason":"Learn How2 Griddy Already: WR +1.0, IDP -0.7 = net +0.3/wk. Nico(demus) Brown: IDP +1.4, WR -0.8 = net +0.4/wk."},
{"mine":false,"a":"Eggsbuka Tyrone","aid":5,"b":"We Are Christian Kirk","bid":10,"kind":"2-for-1","get":"Josh Allen (QB, BUF)","give":"Jared Goff (QB, DET) + J.K. Dobbins (RB, DEN)","ga":3.0,"gb":4.5,"bal":0.67,"minG":3.0,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":3.03,"moves":"T10 drops Marvin Harrison Jr.; T5 adds FA Greg Dulcich; T5 adds FA Bobby Okereke","reason":"Eggsbuka Tyrone: QB +1.3, IDP +0.7, RB -1.0 = net +0.5/wk. We Are Christian Kirk: FLEX +1.2, QB -1.3 = net +0.3/wk."},
{"mine":false,"a":"Learn How2 Griddy Already","aid":2,"b":"Run it back with Runningbacks?","bid":12,"kind":"2-for-2","get":"Chuba Hubbard (RB, CAR) + Fred Warner (LB, SF)","give":"Jaylen Warren (RB, PIT) + Sam LaPorta (TE, DET)","ga":3.5,"gb":3.0,"bal":0.86,"minG":3.0,"accept":"Fair on paper","note":"consensus values are close","ratio":0.87,"moves":"","reason":"Learn How2 Griddy Already: RB +0.8, IDP +0.8, TE -1.3 = net +0.2/wk. Run it back with Runningbacks?: TE +2.0, RB -0.3, FLEX -0.5, IDP -0.9 = net +0.3/wk."},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"3-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Kyren Williams (RB, LA) + Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":9.9,"gb":9.8,"bal":0.99,"minG":9.8,"accept":"Fair on paper","note":"consensus values are close","ratio":1.04,"moves":"Psoas-spended drops DJ Moore; You add FA Bobby Okereke; You add FA Greg Dulcich","reason":"You: WR +3.2, RB -2.2/wk (Tee Higgins 11.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +2.0, TE +0.5, IDP +0.4, WR -1.5/wk. FLAG: includes Hunter Henry (soft-locked).","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"3-for-2","get":"Chase Brown (RB, CIN) + Germie Bernard (WR, PIT)","give":"Kyren Williams (RB, LA) + Jaylen Waddle (WR, DEN) + Kyle Hamilton (S, BAL)","ga":9.8,"gb":9.6,"bal":0.99,"minG":9.6,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.6,"moves":"Psoas-spended drops DJ Moore; You add FA Bobby Okereke; You add FA Justin Herbert","reason":"You: WR +1.9, IDP +0.4, QB +0.3, RB -1.7/wk (Germie Bernard 10.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +1.5, WR -0.4/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"3-for-2","get":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","give":"Bucky Irving (RB, TB) + Hunter Henry (TE, NE) + Jamien Sherwood (LB, NYJ)","ga":9.7,"gb":8.2,"bal":0.84,"minG":8.2,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.37,"moves":"Psoas-spended drops DJ Moore; You add FA Bobby Okereke; You add FA Greg Dulcich","reason":"You: WR +3.2, RB -2.4/wk (Tee Higgins 11.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +1.6, TE +0.5, IDP +0.4, WR -1.5/wk. FLAG: includes Hunter Henry (soft-locked).","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"LONDON Bridge is Falling Down","bid":8,"kind":"3-for-2","get":"Drake London (WR, ATL) + Woody Marks (RB, HOU)","give":"Kyren Williams (RB, LA) + Jaylen Waddle (WR, DEN) + Hunter Henry (TE, NE)","ga":7.8,"gb":7.9,"bal":0.99,"minG":7.8,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.78,"moves":"LONDON Bridge is Falling Down drops Garrett Wilson; You add FA Greg Dulcich; You add FA Bobby Okereke","reason":"You: WR +4.1, IDP +0.4, FLEX -0.7, RB -3.1/wk (Drake London 12.3/wk vs Khalil Shakir 7.4). LONDON Bridge is Falling Down: FLEX +2.5, TE +2.0, RB +1.5, WR -4.8/wk. FLAG: includes Hunter Henry (soft-locked).","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Josh Jacobs (RB, GB) + Tee Higgins (WR, CIN)","give":"Kyren Williams (RB, LA)","ga":11.3,"gb":7.4,"bal":0.66,"minG":7.4,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.13,"moves":"Psoas-spended adds FA Greg Dulcich","reason":"You: WR +3.2, RB -2.2/wk (Tee Higgins 11.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +2.0, TE +0.7, WR -1.5/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"3-for-2","get":"Josh Jacobs (RB, GB) + Germie Bernard (WR, PIT)","give":"Kyren Williams (RB, LA) + TreVeyon Henderson (RB, NE) + Deebo Samuel Sr. (WR, SF)","ga":7.2,"gb":10.5,"bal":0.69,"minG":7.2,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.64,"moves":"Psoas-spended drops DJ Moore; You add FA Bobby Okereke; You add FA Justin Herbert","reason":"You: WR +1.9, IDP +0.4, QB +0.3, RB -2.2/wk (Germie Bernard 10.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +2.0, WR -0.4/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Psoas-spended","bid":9,"kind":"1-for-2","get":"Chase Brown (RB, CIN) + Tee Higgins (WR, CIN)","give":"Bucky Irving (RB, TB)","ga":10.3,"gb":5.8,"bal":0.56,"minG":5.8,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.54,"moves":"Psoas-spended adds FA Greg Dulcich","reason":"You: WR +3.2, RB -2.4/wk (Tee Higgins 11.0/wk vs Khalil Shakir 7.4). Psoas-spended: RB +1.6, TE +0.7, WR -1.5/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Eggsbuka Tyrone","bid":5,"kind":"1-for-2","get":"Breece Hall (RB, NYJ) + Zay Flowers (WR, BAL)","give":"Kyren Williams (RB, LA)","ga":3.5,"gb":4.5,"bal":0.78,"minG":3.5,"accept":"Unlikely","note":"they give the bigger name on paper","ratio":1.37,"moves":"Eggsbuka Tyrone adds FA Greg Dulcich; Eggsbuka Tyrone adds FA Bobby Okereke","reason":"You: WR +5.3, FLEX -1.8, RB -3.3/wk (Zay Flowers 13.7/wk vs Khalil Shakir 7.4). Eggsbuka Tyrone: RB +4.5, IDP +0.7, FLEX +0.3, WR -4.7/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Nico(demus) Brown","bid":7,"kind":"3-for-2","get":"Kenneth Walker III (RB, KC) + Luther Burden III (WR, CHI)","give":"Bucky Irving (RB, TB) + Kyren Williams (RB, LA) + Kyle Hamilton (S, BAL)","ga":3.4,"gb":3.7,"bal":0.92,"minG":3.4,"accept":"Hard sell","note":"a bit more name value going their way out","ratio":1.25,"moves":"Nico(demus) Brown drops Josh Downs; You add FA Bobby Okereke; You add FA Pierre Strong Jr.","reason":"You: WR +1.8, IDP +0.4, FLEX -2.3/wk (Luther Burden III 9.8/wk vs Khalil Shakir 7.4). Nico(demus) Brown: FLEX +2.5, RB -1.1, WR -1.3/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Nico(demus) Brown","bid":7,"kind":"3-for-2","get":"Bhayshul Tuten (RB, JAX) + Luther Burden III (WR, CHI)","give":"Kyren Williams (RB, LA) + Jaylen Waddle (WR, DEN) + Jamien Sherwood (LB, NYJ)","ga":3.2,"gb":3.6,"bal":0.89,"minG":3.2,"accept":"Fair on paper","note":"consensus values are close","ratio":0.81,"moves":"Nico(demus) Brown drops Josh Downs; You add FA Bobby Okereke; You add FA Justin Herbert","reason":"You: WR +1.8, QB +0.3, RB -1.9/wk (Luther Burden III 9.8/wk vs Khalil Shakir 7.4). Nico(demus) Brown: RB +2.1, IDP +0.6, FLEX -0.8, WR -1.3/wk.","preset":"wr2"},
{"mine":true,"a":"Breeces Pieces","aid":4,"b":"Daejon Love","bid":1,"kind":"3-for-2","get":"Tony Pollard (RB, TEN) + Tetairoa McMillan (WR, CAR)","give":"Kyren Williams (RB, LA) + Emanuel Wilson (RB, SEA) + Jamien Sherwood (LB, NYJ)","ga":3.1,"gb":3.8,"bal":0.82,"minG":3.1,"accept":"Easy yes","note":"they get the bigger name; you pay on paper","ratio":0.71,"moves":"Daejon Love drops David Montgomery; You add FA Bobby Okereke; You add FA Pierre Strong Jr.","reason":"You: WR +3.5, RB -1.0, FLEX -2.3/wk (Tetairoa McMillan 11.3/wk vs Khalil Shakir 7.4). Daejon Love: FLEX +1.4, RB +0.7, IDP +0.6, WR -2.3/wk.","preset":"wr2"}
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
