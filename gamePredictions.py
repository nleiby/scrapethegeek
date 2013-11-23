
 ##########################################
############## Feature analysis ##############
##########################################


# gameFeaturesDict=defaultdict(dict)
# for i, gameID in enumerate(gameRatingsAlreadyScraped):
#     print gameID, 'Building features for', i,'out of',len(gameRatingsAlreadyScraped)
#     gameFeaturesDict[gameID]=getFeaturesFromSavedGamePage(gameID)
# with open('google_drive/gameFeaturesDict','w') as fout:
#     pickle.dump(gameFeaturesDict, fout)


fin=open('google_drive/gameFeaturesDict','r')
gameFeaturesDict=pickle.load(fin)

featuresToInclude=['boardgamecategory','boardgamesubdomain','boardgamepublisher','boardgamemechanic','playTime','bestNumPlayers']
allFeaturesDict=buildDictOfAllGameFeatures(gameRatingsAlreadyScraped,gameFeaturesDict,featuresToInclude)
featureVector=[]
for featureType in featuresToInclude:
    featureVector=featureVector+list(allFeaturesDict[featureType])
print 'There are',len(featureVector),'features in the categories:\n', allFeaturesDict.keys()
print allFeaturesDict
fDf=buildGameFeaturesDf(featureVector,gameRatingsAlreadyScraped,gameFeaturesDict)


####Try out a linear regression on the features for games reviewed by a testuser
#chose an alpha arbitrarily here
#testuser='Mease19'
testuser='nicodemus055'

gamesReviewedByUser=smallDf[smallDf.user==testuser]
xinds=gamesReviewedByUser.gameID.values
xinds=[str(ind) for ind in xinds]
x=fDf.loc[xinds]
y=gamesReviewedByUser['rating'].values
y=[[val] for val in y]
clf = linear_model.Lasso(alpha = 0.015,fit_intercept=True)
clf.fit(x,y)
coefs=clf.coef_
intc=clf.intercept_ 
print clf.score(x,y), intc
sum(abs(coefs)>0.01)
######## Also, normalize Y to mean so the magnitude of coefficients is right.  Check number of coefs- do I have an intercept here?

#sort the features in descending order by highest absolute value of the coefs, take those with coefs>0.01
usefulFeatureInds=abs(coefs)>0.01
numUsefulFeatures=sum(usefulFeatureInds)
print 'Number of useful features',numUsefulFeatures
sortedInds=np.argsort(abs(coefs))[::-1][0:numUsefulFeatures]
print 'intercept:',intc,'\ncoefs', coefs[sortedInds]
for ind in sortedInds: 
    print featureVector[ind],coefs[ind]
