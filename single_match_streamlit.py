import random
import pandas as pd
import streamlit as st

# random.seed(5900)

def skill_based_weights(skill: float) -> list[float]:
	#// This function is the key and controls the runs and wickets it needs to be tuned in a goodway
	#// but i dont know how to tune the parameters
	"""
	Weights for [0, 1, 2, 3, 4, 6, 'w'] tuned for IPL-style scores.

	• skill ≈ 1.30  → superstar
	• skill ≈ 1.15  → top-order regular
	• skill ≈ 1.00  → solid middle order
	• skill ≈ 0.85  → lower order
	• skill ≈ 0.65  → tail
	• skill ≈ 0.45  → genuine rabbit
	"""
	# Baseline for a skill-1.00 batter (we need to change this base ratios)
	base = [0.30, 0.34, 0.11, 0.01, 0.15, 0.05, 0.04]		  # dot,1,2,3,4,6,w

	# Boost (or shrink) the scoring shots linearly with skill
	boost = 1 + 0.70 * (skill - 1)							 # 0.70 = gentler slope
	scoring = [p * boost for p in base[1:6]]				   # 1-run through six-run

	# Re-allocate residual probability to dots & wickets
	residual = 1.0 - sum(scoring)
	dot_share = base[0] / (base[0] + base[6])				  # keep original dot:wicket ratio
	dot, wicket = residual * dot_share, residual * (1 - dot_share)

	weights = [round(dot, 3)] + [round(x, 3) for x in scoring] + [round(wicket, 3)]

	# tiny fix for rounding drift
	weights[0] += round(1.0 - sum(weights), 3)
	return weights

class Player:
	def __init__(self,name, skill):
		self.name = name 
		self.skill = skill
		self.is_bowler = False
		self.is_keeper = False
		self.each_ball_batted = []
		self.each_ball_bowled = []
		self.overs_bowled = 0
		self.catches = 0
		self.bowled = 0
		self.run_outs = 0
		self.stumpings = 0
		# self.fours = 0
		# self.sixes = 0
		self.wickets = 0
	@property
	def fours(self):
		return self.each_ball_batted.count(4)

	@property
	def sixes(self):
		return self.each_ball_batted.count(6)
	
	
	@property
	def skill_weights(self):
		return skill_based_weights(self.skill)

	@property
	def balls_faced(self):
		return len(self.each_ball_batted)
	
	@property
	def balls_bowled(self):
		return len(self.each_ball_bowled)
	

	@property
	def runs_scored(self):
		return sum(i for i in self.each_ball_batted if i != "w")

	@property
	def runs_conceded(self):
		return sum(i for i in self.each_ball_bowled if i != "w")
	
	@property
	def strike_rate(self):
		if self.balls_faced:
			return round(self.runs_scored*100/self.balls_faced,2)
		else:
			return 0
	@property
	def economy(self):
		balls_bowled = len(self.each_ball_bowled)
		if balls_bowled:
			return round(self.runs_conceded*6/balls_bowled, 2)

		else: return 0

	# Helper function to the fantasy points main function
	def calculate_batting_points(self):
		fantasy_points = 0
		for ball_outcome in self.each_ball_batted:
			if ball_outcome in [1,2,3]:
				fantasy_points+=ball_outcome
			elif ball_outcome == 4:
				fantasy_points+=8
			elif ball_outcome == 6:
				fantasy_points+=12

		fantasy_points += (self.runs_scored//25)*4

		return fantasy_points

	# Helper function to the fantasy points main function
	def calculate_bowling_points(self):
		fantasy_points = 0
		for ball_outcome in self.each_ball_bowled:
			if ball_outcome == 0:
				fantasy_points += 1
		fantasy_points+=self.wickets*30
		return fantasy_points

	# Helper function to the fantasy points main function
	def calculate_other_points(self):
		fantasy_points = 0
		fantasy_points += self.catches*8
		fantasy_points += self.run_outs*8
		fantasy_points += self.stumpings *12
		fantasy_points += self.bowled * 8
		return fantasy_points

	@property
	def total_fantasy_points(self):
		return (
				4 +	  # four is the base point
				self.calculate_batting_points() +
				self.calculate_bowling_points() +
				self.calculate_other_points()
				)

	def __repr__(self):
		return f'Player(name = {self.name}, skill = {self.skill})'
	
def prepare_playing_eleven(total_team, bowlers, keeper):
	team = [Player(p, s) for p, s in total_team]
	for p in team:
		if p.name in bowlers: p.is_bowler = True
		if p.name == keeper:  p.is_keeper = True
	return team

def wicket_type_manager(bowler, fielders):
	wicket_type = random.choices(["caught", "bowled", "caught_and_bowled", "run_out"], weights=[0.5,0.4,0.05,0.05], k=1)[0]
	if wicket_type == "caught_and_bowled":
		bowler.wickets+=1
		bowler.catches+=1
	elif wicket_type  == "bowled":
		bowler.wickets+=1
		bowler.bowled +=1
	elif wicket_type == "caught":
		bowler.wickets+=1
		fielder = random.choice(fielders)
		fielder.catches+=1
	else:
		fielder = random.choice(fielders)
		fielder.run_outs+=1

def simulate_innings(inning_number, batting_team, fielding_team, target = None):
	possibilities = [0,1,2,3,4,6,"w"]
	score = wickets = balls = 0
	striker_i, non_striker_i, next_i = 0, 1, 2
	

	bowlers = [p for p in fielding_team if p.is_bowler]
	balls_in_over = 0
	bowler = random.choice(bowlers)
	
	over_no, ball_no_in_over = 0, 0
	while wickets <10 and balls<120 :
		if balls_in_over == 0:
			available = [b for b in bowlers if b.overs_bowled < 4]
			bowler = random.choice(available)
		

		striker = batting_team[striker_i]
		
		ball_outcome = random.choices(possibilities, weights = striker.skill_weights, k=1)[0]
		

		striker.each_ball_batted.append(ball_outcome)
		bowler.each_ball_bowled.append(ball_outcome)

		balls+=1
		balls_in_over += 1

		if ball_outcome == "w":
			wickets+=1
			wicket_type_manager(bowler, fielding_team)
			if next_i >= 11: break
			striker_i = next_i
			next_i+=1
			
		else:
			score += ball_outcome
			if ball_outcome %2:
				striker_i, non_striker_i = non_striker_i, striker_i
			
		#over count and strike change
		if balls_in_over ==6:
			bowler.overs_bowled += 1
			striker_i, non_striker_i = non_striker_i, striker_i
			balls_in_over = 0
			over_no += 1

		# if a team wins break the loop
		if target and score > target:
			break

	return score, wickets, balls

def simulate_match(team1, team2):
	
	runsA, wicketsA, ballsA = simulate_innings(1,team1, team2)
	runsB, wicketsB, ballsB = simulate_innings(2,team2, team1, target = runsA)
	
	return (runsA, wicketsA, ballsA, runsB, wicketsB, ballsB )
	
def give_match_results_for_streamlit(simulated_match, team1_name, team2_name):
	runsA, wicketsA, ballsA , runsB, wicketsB, ballsB = simulated_match
	winner = ""


	if runsA > runsB:
		winner = f'{team1_name} won by {runsA-runsB} runs'
	elif runsA<runsB:
		winner = f'{team2_name} won by {10-wicketsB} wickets'
	else:
		winner = "match is a tie"
	
	result = {
		team1_name: {"Runs": runsA, "Wickets": wicketsA, "Overs": str(ballsA//6) +"."+ str(ballsA%6)},
		team2_name: {"Runs": runsB, "Wickets": wicketsB, "Overs": str(ballsA//6) +"."+ str(ballsA%6)},
		"Winner": winner
	}
	return result


def batting_stats_for_streamlit(players_list):
	
	players_data = [
		{
			"Batter": p.name,   
			"Runs": p.runs_scored,
			"Balls": p.balls_faced,
			"Fours": p.fours,
			"Sixes": p.sixes,
			"Strike Rate": p.strike_rate,
		}
		for p in players_list
	]

	return pd.DataFrame(players_data)

def bowling_stats_for_streamlit(players_list):
	
	players_data = [
		{
			"Bowler": p.name,   
			"Overs": p.overs_bowled,
			"Runs ": p.runs_conceded,
			"Wickers": p.wickets,
			"Economy": p.economy
		}
		for p in players_list if p.is_bowler
	]

	return pd.DataFrame(players_data)

def give_innings_stats_for_streamlit(team1, team2):
	batting_stats = batting_stats_for_streamlit(team1)
	bowling_stats = bowling_stats_for_streamlit(team2)
	return batting_stats, bowling_stats

def get_fantasy_points_df(team1, team2):
	"""Creates a DataFrame of players' fantasy points from two teams."""
	player_data = [
		{
			"Name": p.name,
			"Fantasy Points": p.total_fantasy_points,
			"Runs Scored": p.runs_scored,
			"Wickets": p.wickets,
			"Catches": p.catches,
			"Run Outs": p.run_outs
		}
		for p in team1 + team2
	]

	# Convert to pandas DataFrame
	df = pd.DataFrame(player_data)

	# Sort by Fantasy Points (highest first)
	df.sort_values(by="Fantasy Points", ascending=False, inplace=True)

	return df



team1_name = "MI"
team1_player_names= [("Rohit", 1), ("Jacks", 1), ("Surya",1.2), ("Tilak", 0.95), 
		("Pandya", 0.9), ("Naman", 0.8), ("Santner", 0.76), ("Gleeson",0.72), 
		("Ashwani", 0.55), ("Bumrah", 0.5), ("Boult", 0.6)]
team1_bowlers = ["Pandya", "Santner", "Gleeson", "Ashwani", "Bumrah", "Boult"]
team1_keeper = "Jacks"


team2_name = "RCB"
team2_player_names = [("Salt", 1),("Kohli",1.2),("Agarwal", 0.95),("Rajat",1),
					("Livingstone", 0.9),("Jitesh", 0.95),("Romario", 0.82),("Krunal",  0.7),
					("Bhuvi", 0.59),("Yash_dayal", 0.5),("Hazlewood", 0.5)]
team2_bowlers = ["Krunal", "Bhuvi", "Yash_dayal", "Romario", "Hazlewood"]
team2_keeper = "Jitesh"





def main():

	team1 = prepare_playing_eleven( team1_player_names, team1_bowlers, team1_keeper)
	team2 = prepare_playing_eleven( team2_player_names, team2_bowlers, team2_keeper)


	simulated_match_results = simulate_match(team1, team2)
	runsA, wicketsA, ballsA , runsB, wicketsB, ballsB = simulated_match_results


	match_results = give_match_results_for_streamlit(simulated_match_results, team1_name, team2_name)
	
		
	first_innings_batting_stats = batting_stats_for_streamlit(team1)
	
	first_innings_bowling_stats = bowling_stats_for_streamlit(team2)
	
	second_innings_batting_stats = batting_stats_for_streamlit(team2)
	
	second_innings_bowling_stats = bowling_stats_for_streamlit(team1)
	fantasy_stats = get_fantasy_points_df(team1, team2)

	st.title("Match Results")
	st.subheader("Match Summary")
	# Display results dynamically
	st.subheader(f" {team1_name}  {runsA}/{wicketsA} in {ballsA//6}.{ballsA%6}   ")
	st.subheader(f" {team2_name}  {runsB}/{wicketsB} in {ballsB//6}.{ballsB%6}   ")

	winner = ""


	if runsA > runsB:
		winner = f'{team1_name} won by {runsA-runsB} runs'
	elif runsA<runsB:
		winner = f'{team2_name} won by {10-wicketsB} wickets'
	else:
		winner = "match is a tie"

	st.subheader(winner)


	
	st.write(f" {team1_name} {runsA}/{wicketsA} - ({ballsA//6}.{ballsA%6} Ov)")
	st.table(first_innings_batting_stats.set_index("Batter"))
	st.table(first_innings_bowling_stats.set_index("Bowler"))

	st.write(f" {team2_name} {runsB}/{wicketsB} - ({ballsB//6}.{ballsB%6} Ov)")
	st.table(second_innings_batting_stats.set_index("Batter"))
	st.table(second_innings_bowling_stats.set_index("Bowler"))

	st.table(fantasy_stats.set_index("Name"))
	

main()