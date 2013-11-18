
from pattern import web
import requests
import pandas as pd
import numpy as np





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
#to get all of the reviews        
def getNumberOfReviewPagesForGame(gameID):
    xml=requestReviewPage(gameID,1)
    dom = web.Element(xml)
    numReviewsForGame=int(dom.by_tag('comments')[0].attributes['totalitems'])
    if numReviewsForGame:
        numReviewPages=int(np.ceil(numReviewsForGame/100.))
        return numReviewPages
    else:
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
    reviewDict={'user':users,'rating':ratings,'gameName':gameNames,'gameIDs':gameIDs}
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
    gameDf=buildReviewDictFromPage(gameID, pageNum=1)
    for i in range(2,numReviewPages):
        pageDf=buildReviewDictFromPage(gameID,i)
        gameDf=pd.concat([gameDf,pageDf],ignore_index=True)
        if i%10==0:
            print i
    return gameDf


#get list of top 100 boardgames and ID numbers
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
print top100_IDs


#Iterate over the top 100 games and create Pandas dataframes out of them
#For now I'm saving them in CSVs that are filled with redundant information (game title, gameID)
for game in top100_IDs:
    gameID=game[0]
    name=game[1]
    fileName='gamereviews_id_%s_%s.csv' % (gameID,name)
    print 'Downloading data for %s, gameID: %s' % (name, gameID)
    gameDf=buildReviewDfForGame(gameID)
    print 'saving file: ', fileName
    gameDf.to_csv(fileName,index_label=False, encoding='utf8')
