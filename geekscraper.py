
from pattern import web
import requests
import pandas as pd
import numpy as np
import os
import re
import pickle





#Requests the pageNum page of reviews for the gameID game, returns the source as an xml
#uses the BGG XML API2 http://boardgamegeek.com/wiki/page/BGG_XML_API2#
def requestReviewPage(gameID,pageNum):
    url = 'http://www.boardgamegeek.com/xmlapi2/thing'  
    options = {'type':'boardgame','id':gameID,'ratingcomments':1,'pagesize':100,'page':pageNum }
    xml = requests.get(url, params=options).text
    return xml

#given a pattern.web object for a review page, returns the name of the game being reviewed
def getGameNameFromDom(dom):
    gameNames=dom.by_tag("name")
    for name in gameNames:
        if name.attributes['type']=='primary':
            gameName=name.value
            return gameName
        else:
            return None


#determines how many reviews there are for a game and returns the number of pages needed to request in order
#to get all of the reviews.  If there are problems finding the number of reviews, it's probably because it's 
#coded as a game expansion and not a game in BGG's system- different API query needed.  I figure we just leave out
#expansions for now, though, so I've written the functions to return none and check for that for now.        
def getNumberOfReviewPagesForGame(gameID):
    xml=requestReviewPage(gameID,1)
    dom = web.Element(xml)
    try:
        numReviewsForGame=int(dom.by_tag('comments')[0].attributes['totalitems'])
        numReviewPages=int(np.ceil(numReviewsForGame/100.))
        return numReviewPages
    except:
        print "Error- can't get page count."
        return None

#provided with a pattern.web object and the gameID, returns user and rating info for a reviews page
def getRatingsFromReviewPage(dom,gameID):
    users=[]
    ratings=[]
    gameNames=[]
    gameIDs=[]
    gameName=getGameNameFromDom(dom)
    for review in dom.by_tag('comment'):
        ratings.append(review.attributes['rating'])
        users.append(review.attributes['username'])
        gameNames.append(gameName)
        gameIDs.append(gameID)
    reviewDict={'user':users,'rating':ratings,'gameName':gameNames,'gameID':gameIDs}
    df=pd.DataFrame(reviewDict)
    return df

#Requests the the pageNum page of reviews for the gameID game.
#Creates a pattern.web object from the reviews page
#gets all of the ratings and user info out of the dom object
def buildReviewDictFromPage(gameID, pageNum):
    xml=requestReviewPage(gameID,pageNum)
    dom = web.Element(xml)
    reviewDf=getRatingsFromReviewPage(dom,gameID)
    return reviewDf    


#Assembles a pandas dataframe with columns: gameID, gameName,rating,user.  
#Includes all reviews for a game
def buildReviewDfForGame(gameID):
    numReviewPages=getNumberOfReviewPagesForGame(gameID)  
    #numReviewPages=10
    if numReviewPages:
        gameDf=buildReviewDictFromPage(gameID, pageNum=1)
        for i in range(2,numReviewPages):
            pageDf=buildReviewDictFromPage(gameID,i)
            gameDf=pd.concat([gameDf,pageDf],ignore_index=True)
            if i%10==0:
                print i
        return gameDf
    else:
        return None

#get list of top 100 boardgames and ID numbers
def getListOfTop100Games():
    url='http://boardgamegeek.com/browse/boardgame'
    page = requests.get(url).text
    dom=web.Element(page)
    items=dom.by_class('collection_thumbnail')
    names=[]
    ids=[]
    top100_IDs=[]
    for item in items:
        for link in item('a'):
            gameDetails=link.attributes.get('href').split('/')
            ids.append(gameDetails[2])
            names.append(gameDetails[3])
            top100_IDs=zip(ids,names)
    print 'Top 100 games:', top100_IDs
    return top100_IDs

#Iterate over the top 100 games and create Pandas dataframes out of them
#For now I'm saving them in CSVs that are filled with redundant information (game title, gameID)
def getTop100GameRatings(top100_IDs):
    for game in top100_IDs:
        gameID=game[0]
        name=game[1]
        fileName='gamereviews_id_%s_%s.csv' % (gameID,name)
        print '\nDownloading data for %s, gameID: %s' % (name, gameID)
        gameDf=buildReviewDfForGame(gameID)
        if gameDf:
            print 'saving file: ', fileName
            gameDf.to_csv(fileName,index_label=False, encoding='utf8')
        else: 
            print 'This is not a full game, or some other error has occurred.'


#Takes as arguments a page number corresponding to the nth page of ratings sorted in descending order, as well as
#a list of the gameID tuples that have already had ratings downloaded.  Returns a list of ID tuples that are on the 
#page and not yet downloaded
def getGamesToAddFromPage(pageNum, alreadyDownloadedIds):
    url="http://www.boardgamegeek.com/browse/boardgame/page/%s?sort=numvoters&sortdir=desc" % pageNum
    page = requests.get(url).text
    dom=web.Element(page)
    items=dom.by_class('collection_thumbnail')
    names=[]
    ids=[]
    for item in items:
        for link in item('a'):
            gameDetails=link.attributes.get('href').split('/')
            name=gameDetails[3]
            gameId=gameDetails[2]
            if (gameId,name) not in alreadyDownloadedIds:
                ids.append(gameId)
                names.append(name)
    gamesToAdd=zip(ids,names)
    return gamesToAdd

#provided with a gameID tuple (IDnumber, name), scrape the BGG site for the game site and save HTML to file
def scrapeGamePages(gameID):
    url='http://boardgamegeek.com/boardgame/%s/%s' % (gameID[0],gameID[1])
    page = requests.get(url).text
    filepath='google_drive/game_metadata/%s_%s.txt' % (gameID[0],gameID[1])
    with open(filepath, 'w') as fout:
        fout.write(page.encode("utf-8"))

#provided with a gameID tuple (IDnumber, name), check whether the game site is saved already and return the page DOM 
def getSavedGameSite(gameID):
    try:
        fin=open('google_drive/game_metadata/%s_%s.txt'% (gameID[0],gameID[1]), 'r')
        dom=web.Element(fin.read())
        return dom
    except:
        print 'Saved site for game not found'
        return None

#Looks in the gameRatings directory and returns a list of gameID tuples (IDnumber,name) for which there are ratings files
def getListOfGameRatingsAlreadyScraped():
    dirname='google_drive/gameRatings/'
    fileList=os.listdir(dirname)
    fileList=[filen.replace('.','_') for filen in fileList]
    scrapedGames=[(filen.split('_')[2],filen.split('_')[3]) for filen in fileList]
    return scrapedGames

def buildDictOfAllGameFeatures(gameRatingsAlreadyScraped,gameFeaturesDict):
    allFeaturesDict={'boardgamemechanic':set(),'boardgamepublisher':set(),
                    'boardgamedesigner':set(),'boardgamesubdomain':set(),
                    'boardgamecategory':set(),}
    for gameID in gameRatingsAlreadyScraped:
        gameFeatures=gameFeaturesDict[gameID]
        for featureType in gameFeatures:
            for feature in gameFeatures[featureType]:
                allFeaturesDict[featureType].add(feature)
    return allFeaturesDict


#Takes a GameID, pulls up a downloaded HTML, and strips out features from the text
#still need to add a way to strip the number of players, game time, etc. from the information
def getFeaturesFromSavedGamePage(gameID):
    fin=open('google_drive/game_pages/%s_%s.txt'% (gameID[0],gameID[1]), 'r')
    dom=web.Element(fin.read())
    infoTable=dom.by_tag('.geekitem_infotable')[0]
    featuresDict={'boardgamemechanic':set(),'boardgamepublisher':set(),
                    'boardgamedesigner':set(),'boardgamesubdomain':set(),
                    'boardgamecategory':set(),}
    for link in infoTable('a'):
        try:
            row=link.attributes.get('href','').split('/')
            featureType=row[1]
            if featureType in featuresDict:
                featureID=row[2]
                featureName=row[3]
                featuresDict[featureType].add((featureID,featureName))
        except:
            pass
    return featuresDict


#top100_IDs=getListOfTop100Games()
#getTop100GameRatings(top100_IDs)

 ##########################################
############## Feature analysis ##############
##########################################

#Get the game pages for the games for which ratings are already scraped
gameRatingsAlreadyScraped=getListOfGameRatingsAlreadyScraped()

#Get game metadata (features tages) from downloaded games
#for gameID in gameRatingsAlreadyScraped:
#    scrapeGamePages(gameID)

# gameFeaturesDict=defaultdict(dict)
# for i, gameID in enumerate(gameRatingsAlreadyScraped):
#     print gameID, 'reading game', i,'out of',len(gameRatingsAlreadyScraped)
#     gameFeaturesDict[gameID]=getFeaturesFromSavedGamePage(gameID)
# with open('gameFeaturesDict','w') as fout:
#     pickle.dump(gameFeaturesDict, fout)


fin=open('google_drive/gameFeaturesDict','r')
gameFeaturesDict=pickle.load(fin)
allFeaturesDict=buildDictOfAllGameFeatures(gameRatingsAlreadyScraped,gameFeaturesDict)
featureVector=[]
for featureType in allFeaturesDict:
    featureVector=featureVector+list(allFeaturesDict[featureType])
print 'There are',len(featureVector),'features in the categories:\n', allFeaturesDict.keys()



## Build a dataframe containing 0s and 1s, rows are games, columns are game feature tags
# such as card game or Steve Jackson
def buildGameFeaturesDf(featureVector,gameRatingsAlreadyScraped, gameFeaturesDict):
    getNameFromIDTuple=operator.itemgetter(1)
    getIDFromTuple=operator.itemgetter(0)
    indices=map(getIDFromTuple,alreadyScrapedGames)
    cols=map(getNameFromIDTuple,featureVector)
    fDf = pd.DataFrame(0,index=indices, columns=cols)

    for gameID in alreadyScrapedGames:
        gameFeatures=gameFeaturesDict[gameID]
        for featureType in gameFeatures:
            for feature in gameFeatures[featureType]:
                f=str(getNameFromIDTuple(feature))
             fDf.loc[gameID[0]][f]=1

    return fDf

# fDf=buildGameFeaturesDf(featureVector,gameRatingsAlreadyScraped,gameFeaturesDict)


####Try out a linear regression on the features for games reviewed by a testuser
#chose an alpha arbitrarily here
gamesReviewedByUser=smallDf[smallDf.user==testuser]
xinds=gamesReviewedByUser.gameID.values
xinds=[str(ind) for ind in xinds]
x=fDf.loc[xinds]
y=gamesReviewedByUser['rating'].values
y=[[val] for val in y]
clf = linear_model.Lasso(alpha = 0.05)
clf.fit(x,y)
coefs=clf.coef_
print clf.score(x,y)
sum(abs(coefs)>0.01)





for pageNum in range(4):
    gamesToAdd=getGamesToAddFromPage(pageNum,gameRatingsAlreadyScraped)
    print 'adding games from page %s:' % pageNum
    for game in gamesToAdd:
        gameID=game[0]
        name=game[1]
        fileName='gamereviews_id_%s_%s.csv' % (gameID,name)
        print '\nDownloading data for %s, gameID: %s' % (name, gameID)
        gameDf=buildReviewDfForGame(gameID)
        if gameDf:
            print 'saving file: ', fileName
            gameDf.to_csv(fileName,index_label=False, encoding='utf8')
        else:
            print 'Error, not a game?'






