## Takes a CSV file containing user reviews and returns a tuple (rho, cosSim, n_common) for pairs of games

import numpy as np
from mrjob.job import MRJob
from itertools import combinations, permutations
from scipy.stats.stats import pearsonr
import math

class GameSimilarities(MRJob):
	def line_mapper(self,_,line):
		#Takes passed df and yields a tuple of data keyed to the user id
		user,gameID,rating,game_avg,user_avg=line.split(',')
		yield user, (gameID,rating,game_avg,user_avg)
		
	def users_items_collector(self, user, values):
		#iterate over the list of tuples yielded in the previous mapper, each corresponding to a user
		#and appends them to an array of rating information for that user
		arr=[val for val in values]
		yield user, arr
		#pass
		
	def pair_items_mapper(self, user, values):
		# ignoring the user key, take all combinations of game pairs
		# and yield as key the pair id, and as value the pair rating information
		inputs=[val for val in values]
		#by sorting the inputs, when we do use the combinations function we ensure that (a,b) and (b,a) are combined
		#inputs.sort()
		#sort by game ID
		inputs=sorted(inputs, key=lambda game: game[0])
		pair_keys=[key for key in combinations([val[0] for val in inputs],2)]
		pair_values=[info for info in combinations([val[1:] for val in inputs],2)]
		for i,key in enumerate(pair_keys):
			yield key, pair_values[i]

		
	def calc_sim_collector(self, key, values):
      # Pick up the information from the previous yield, now keyed to pairs of games- so this collects
      #	all of the ratings for game 1 and game 2 for all people who have rated those games
      #  Calculates from this the pearson correlation and yields that and the common support for the game pair
		(game1, game2), common_ratings = key, values
		diffs1=[]
		diffs2=[]

		######
		#Calculate pearsons r
		######
		#iterate over all generated values
		for val in values:
			#break the generated value into to lists for game1 and game2
			#subtract the difference between the user rating and user average for each value
			diffs1.append(float(val[0][0])-float(val[0][2]))
			diffs2.append(float(val[1][0])-float(val[1][2]))

		#common support is the length of the difference vectors, rho is the correlation between distance vector (0 if only 1 rating in common)
		n_common=len(diffs1)
		if n_common>1:
			rho=pearsonr(diffs1, diffs2)[0]
		else:
			rho=0
		#In test I get a very small number of cases (2) where the correlation is undefined despite n_common being equal to two (all ratings are the same)	
		#This is a kludgy way of dealing with that without re-writing pearsonr
		if np.isnan(rho):
			rho=0

		# ######
		# #Calculate cosine similarity
		# ######
		# v1=diffs1
		# v2=diffs2
		# sumxx, sumxy, sumyy = 0, 0, 0
		# for i in range(len(v1)):
		# 	x = v1[i]; y = v2[i]
		# 	sumxx += x*x
		# 	sumyy += y*y
		# 	sumxy += x*y
		# cosSim=sumxy/math.sqrt(sumxx*sumyy)
		# yield (game1, game2), (rho,cosSim,n_common)
		yield (game1, game2), (rho,n_common)

	def steps(self):
		# The steps in the map-reduce process- MrJob runs through these in order
		thesteps = [self.mr(mapper=self.line_mapper, reducer=self.users_items_collector),
				self.mr(mapper=self.pair_items_mapper, reducer=self.calc_sim_collector)

		]
		return thesteps
#Calls the Mrjob class initialization
if __name__ == '__main__':
	GameSimilarities.run()


