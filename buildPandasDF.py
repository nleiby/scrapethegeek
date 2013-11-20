from scipy.stats.stats import pearsonr
import operator
import pandas as pd
import numpy as np
import os
import pickle


# takes a dataframe ldf, makes a copy of it, and returns the copy
# with all averages and review counts recomputed
# this is used when a frame is subsetted.
def recompute_frame(ldf):
    ldfu=ldf.groupby('user')
    ldfb=ldf.groupby('gameName')
    user_avg=ldfu.rating.mean()
    user_review_count=ldfu.rating.count()
    game_avg=ldfb.rating.mean()
    game_review_count=ldfb.rating.count()
    nldf=ldf.copy()
    nldf.set_index(['gameName'], inplace=True)
    nldf['game_avg']=game_avg
    nldf['game_review_count']=game_review_count
    nldf.reset_index(inplace=True)
    nldf.set_index(['user'], inplace=True)
    nldf['user_avg']=user_avg
    nldf['user_review_count']=user_review_count
    nldf.reset_index(inplace=True)
    return nldf


#  Given a subframe of game1 reviews and a subframe of game2 reviews,
#  where the reviewers are those who have reviewed both games, return 
#  the pearson correlation coefficient between the user average subtracted ratings.
def pearson_sim(game1_reviews, game2_reviews, n_common):
    if n_common==0:
        rho=0.
    else:
        diff1=game1_reviews['rating']-game1_reviews['user_avg']
        diff2=game2_reviews['rating']-game2_reviews['user_avg']
        rho=pearsonr(diff1, diff2)[0]
    return rho

#alternative similarity metric for 2 games
#compute cosine similarity of v1 to v2: (v1 dot v1)/{||v1||*||v2||)
def cosine_similarity(game1_reviews, game2_reviews, n_common):
    v1=game1_reviews['rating'].values
    v2=game2_reviews['rating'].values
    sumxx, sumxy, sumyy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    return sumxy/math.sqrt(sumxx*sumyy)



#Calculates the similarity between 2 games using a provided similarity metric
#takes as arguments the 2 gameNames, the dataframe to use, and a function to calculate similarity
def calculate_similarity(game1,game2,df,similarity_func):
    game1_reviewers = df[df.gameName==game1].user.unique()
    game2_reviewers = df[df.gameName==game2].user.unique()
    common_reviewers = set(game1_reviewers).intersection(game2_reviewers)
    n_common=len(common_reviewers)
    
    game1_reviews=get_game_reviews(game1, df, common_reviewers)
    game2_reviews=get_game_reviews(game2, df, common_reviewers)

    sim=similarity_func(game1_reviews, game2_reviews, n_common)
    if np.isnan(sim):
        sim=0
    comparison=(sim, n_common)
    return comparison

#given a gameName and a set of reviewers (e.g., the reviewers in common)
#return the sub-dataframe of their reviews.
def get_game_reviews(game, df, set_of_users):  
    mask = (df.user.isin(set_of_users)) & (df.gameName==game)
    reviews = df[mask]
    reviews = reviews[reviews.user.duplicated()==False]
    return reviews

#takes a similarity and shrinks it down by using the regularizer
#this down-weights comparisons with low common support
def shrunk_sim(sim, n_common, reg=1000.):
    ssim=(n_common*sim)/(n_common+reg)
    return ssim

class Database:
    # A class representing a database of similaries and common supports
    
    def __init__(self, df):
        # "the constructor, takes a reviews dataframe like smalldf as its argument"
        database={}
        self.df=df
        self.gameNames={v:k for (k,v) in enumerate(df.gameName.unique())}
        keys=self.gameNames.keys()
        l_keys=len(keys)
        self.database_sim=np.zeros([l_keys,l_keys])
        self.database_sup=np.zeros([l_keys, l_keys], dtype=np.int)
        
    def populate_by_calculating(self, similarity_func):
        # a populator for every pair of games in df. takes similarity_func like
        # pearson_sim as argument
      
        items=self.gameNames.items()
        for g1, i1 in items:
            for g2, i2 in items:
                if i1 < i2:
                    sim, nsup=calculate_similarity(g1, g2, self.df, similarity_func)
                    self.database_sim[i1][i2]=sim
                    self.database_sim[i2][i1]=sim
                    self.database_sup[i1][i2]=nsup
                    self.database_sup[i2][i1]=nsup
                elif i1==i2:
                    nsup=self.df[self.df.gameName==g1].user.count()
                    self.database_sim[i1][i1]=1.
                    self.database_sup[i1][i1]=nsup
                    

    def get(self, g1, g2):
       # "returns a tuple of similarity,common_support given two business ids"
        sim=self.database_sim[self.gameNames[g1]][self.gameNames[g2]]
        nsup=self.database_sup[self.gameNames[g1]][self.gameNames[g2]]
        return (sim, nsup)


def knearest(gameName,set_of_games,dbase,k=7,reg=1000):
    sims=[dbase.get(gameName, iterGame) for iterGame in set_of_games]
    shrunkSims=[(shrunk_sim(sim[0], sim[1], reg), sim[1]) for sim in sims]
    getFirstItem=operator.itemgetter(0)
    sortedInds=np.argsort(map(getFirstItem,shrunkSims))[::-1]
    #if we ask for more returned nearest than are in the set of games, return them all
    if k>len(set_of_games):
        k=len(set_of_games)
    kNearestInds=sortedInds[0:k]
    kNearest=[(set_of_games[i],shrunkSims[i][0],shrunkSims[i][1]) for i in kNearestInds]
    
    #Don't include the game itself in its own k-nearest neighbors
    #this would be easier if we can assume that the game's best match is always unqiue and 
    #with itself and just skip the first term in the sorted list
    if gameName in map(getFirstItem,kNearest):
        #remove the self-comparison entry
        selfId=map(getFirstItem,kNearest).index(gameName)
        kNearest.pop(selfId)
        #if there are more restaurants available in the set to use
        if k!=len(sortedInds):
            ind=sortedInds[k]
            additionalItem=(set_of_games[ind],shrunkSims[ind][0],shrunkSims[ind][1])
            kNearest.append(additionalItem)
        
    return kNearest

#"get the sorted top 5 games for a user by the rating the user gave them"
def get_user_top_choices(user, df, numchoices=5):
    udf=df[df.user==user][['gameName','rating']].sort(['rating'], ascending=False).head(numchoices)
    return udf


def get_top_recos_for_user(user, df, dbase, n=5, k=8, reg=200):
    #a set just containing the gameNames strings
    neighborGames=set()
    #lists the games already rated by the user
    userAlreadyRatedGames=set(df[df.user==user].gameName.values)
    games=get_user_top_choices(user, df,numchoices=n)['gameName'].values
    #for each of the user top choices, get the k nearest neighbor games
    for userTopGame in games:
        kNearestGames=knearest(userTopGame,df.gameName.unique(),dbase, k, reg)
        for nearGame in kNearestGames:
            #checks if the games we might recommend has already been reviewed by user
            if nearGame[0] not in userAlreadyRatedGames:
            #add the game name to the set
                neighborGames.add(nearGame[0])
           
    #find the average rating for all games in the passed df        
    gameRatings=df.groupby('gameName')['rating'].aggregate(np.mean)
    #recs is a list of tuples pairing each of the neighbor games with their average rating
    recs=[(neighborGameName,gameRatings[neighborGameName]) for neighborGameName in neighborGames]
    #sort the recommendations b rating
    getSecondItem=operator.itemgetter(1)
    sortedInds=np.argsort(map(getSecondItem,recs))[::-1]
    topRecs=[recs[ind] for ind in sortedInds]
    return topRecs



def knearest_amongst_userrated(gameName,user,df,dbase,k=7,reg=200.):
    userRatedGames=df[df.user==user].gameName.unique()
    nearestAmongstRated=knearest(gameName,userRatedGames,dbase,k,reg)
    return nearestAmongstRated

def calcBase(df,user,gameName):
    ybar=np.mean(df.rating)
    yubar=np.mean(df[df.user==user].rating)
    ymbar=np.mean(df[df.gameName==gameName].rating)
    base=ybar+(yubar-ybar)+(ymbar-ybar)
    return base

def getRating(df,gameName):
    try:
        ratings=df[df.gameName==gameName].rating.values[0]
        return ratings
    except:
        print 'no rating found'
        return None
    
def ratingPredictor(df,dbase,gameName,user,k=7, reg=200.):
    userReviews=df[df.user==user]
    yum_base=calcBase(df,user,gameName)
    
    kNearestUserRated=knearest_amongst_userrated(gameName,user,df,dbase,k,reg)
    s=np.array([dbase.get(gameName, neighbor[0])[0] for neighbor in kNearestUserRated])  
    yu=np.array([getRating(userReviews,neighbor[0]) for neighbor in kNearestUserRated])
    yuj_base=[calcBase(df, user,neighbor[0]) for neighbor in kNearestUserRated]
 
    if sum(s)==0 or np.isnan(sum(s)):
        print 'no similarities'
        return yum_base
    
    else:
        prediction=yum_base+sum((yu-yuj_base)*s)/sum(s)

        return prediction

def get_other_ratings(gameName, user, df):
    "get a user's rating for a game and the game's average rating"
    choice=df[(df.gameName==gameName) & (df.user==user)]
    users_score=choice.rating.values[0]
    average_score=choice.game_avg.values[0]
    return users_score, average_score

#"get the sorted top 5 games for a user by the rating the user gave them"
def get_user_top_choices(user, df, numchoices=5):
    udf=df[df.user==user][['gameName','rating']].sort(['rating'], ascending=False)
    return udf.head(numchoices)



#Build a pandas database fullDf from all of the individual game ratings csvs saved
def buildDfFromScrapedCsvs():
    dataDir='gameRatings/'
    gameRatingsFiles=os.listdir(dataDir)
    if '.DS_Store' in gameRatingsFiles:
            gameRatingsFiles.remove('.DS_Store')
    fullDf=pd.DataFrame()

    for file in gameRatingsFiles:
        filePath=dataDir+file
        df=pd.read_csv(filePath)
        fullDf=pd.concat([fullDf,df],ignore_index=True)
    print 'Built fullDf:\n',fullDf.head(),'\n', fullDf

    fullDf=recompute_frame(fullDf)
    return fullDf
#fullDf=buildDfFromScrapedCsvs()
##Save the dataframe or load from csv
#fullDf.to_csv('google_drive/fullGamesDf.csv')
fullDf=pd.read_csv('google_drive/fullGamesDf.csv')

#create a smaller dataframe containing only the ratings by users with 13 or more ratings 
#(number chosen arbitrarily)
smallDf=fullDf[fullDf.user_review_count>=13]
smallDf=recompute_frame(smallDf)



# db=Database(smallDf)
# db.populate_by_calculating(pearson_sim)
# fout=open('google_drive/gameDbPickle','w')
# pickle.dump(db,fout)
# fout.close()

fin=open('google_drive/gameDbPickle','r')
db=pickle.load(fin)
fin.close()

#define some variables for function testing
testGame1='Mage Wars'
testGame2='Terra Mystica'
testuser="m4c14s"
print 'the database and this function should return the same values'
print calculate_similarity(testGame1,testGame2,smallDf,pearson_sim)
print 'database load test: ', db.get(testGame1,testGame2)
print "For user", testuser, "top rated games are:" 
gameRecs=get_user_top_choices(testuser, smallDf)['gameName'].values
print gameRecs


print "\nFor user", testuser, "the top recommendations are:"
toprecos=get_top_recos_for_user(testuser, smallDf, db, n=5, k=7)
for gameName, gameRating in toprecos:
    print gameName, '| aveRating:',gameRating

print "\nfor user",testuser, 'avg', smallDf[smallDf.user==testuser].rating.mean() 
for game in gameRecs:
    print "----------------------------------"
    print game
    print "Predicted Rating:",ratingPredictor(smallDf, db, game, testuser, k=7, reg=1000.) 
    u,a=get_other_ratings(game, testuser, smallDf)
    print "Actual User Rating:",u,"Avg Rating",a


