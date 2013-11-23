scrapethegeek
=============

Board game recommendation engine

## Setup


##To do:
Make predictions about new games coming out based on game features and the early votes, and push recommendations to people
(newsletter for people who have 

Boardgamegeek recommendations- not very good.  Quantify how much better our system is to theirs.
Access their recommendations in this format:
http://boardgamegeek.com/user/nicodemus055/recommendations
Use a dummy account login: recommendTheGeek pass: geekscraper to query other peoples' recs- need to be logged in (cookies) to see recs


###Small To Do

Modify function getFeaturesFromSavedGamePage, adding a way to strip the number of players, game time, etc. from the information- right now only taking out features encoded in links

###Network analysis of boardgame neighborhoods
Make a network graph showing the user’s rated boardgames in red and recommended boardgames in blue.  Make it interactive- mouse-over a node to show game details, why it’s recommended
Add visualization/feedback step for sure that explains the main drivers of recommendations (designer name, mechanic, etc.). Use something like this to allow users to provide feedback on suggestions (close off related game nodes): http://mbostock.github.io/d3/talk/20111116/force-collapsible.html

