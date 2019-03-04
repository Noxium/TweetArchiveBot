import sys
import os
import datetime
import praw
import twitter
from twython import TwythonStreamer


name = 'TweetArchiveBot'

cons_key = os.environ.get("TWIT_CONS_KEY")
cons_secret = os.environ.get("TWIT_CONS_SECRET")
access_key = os.environ.get("TWIT_ACCESS_KEY")
access_secret = os.environ.get("TWIT_ACCESS_SECRET")

api = twitter.Api(consumer_key=cons_key,
        consumer_secret=cons_secret,
        access_token_key=access_key,
        access_token_secret=access_secret,
        sleep_on_rate_limit=True)

api.VerifyCredentials()

bot = praw.Reddit(user_agent='TweetArchiveBotv0.1',
        client_id= os.environ.get("BOT_CLIENT_ID"),
        client_secret=os.environ.get("BOT_CLIENT_SECRET"),
        username=os.environ.get("BOT_USERNAME"),
        password=os.environ.get("BOT_PASSWORD"))

subreddit = bot.subreddit('TweetArchiver')
comments = subreddit.stream.comments()

followers = []
print("Starting Tweet Archiver at %s" %datetime.datetime.now())
print("Following:")
for user in api.GetFriends():
    print("\t" + user.name)
    followers.append(user.id_str)

class tStream(TwythonStreamer):
    def PostTweetToReddit(self, data):
        u = "https://twitter.com/" + data['user']['screen_name'] + "/status/" + data['id_str']
        t = data['user']['name'] + ": " + data['text'] + " (" + data['created_at'] + ")"
        print("Submitting to /r/" + subreddit.display_name + ":\'" + t + "\' at " + u)
        print('')
        post = subreddit.submit(title=t, url=u)
        post.reply(">%s    \n\nAuthor: %s    \nTime: %s    \nLocation: %s    \nVia: %s    \nMedia: %s" %(data['text'], data['user']['name'], data['created_at'], data['geo'], 'Coming soon!', 'Coming soon!'))
#        self.save_to_csv(data)
    
    def on_error(self, status_code, data):
        print(status_code)
    
    def on_success(self, data):
        if(data['user']['id_str'] in followers):
            self.PostTweetToReddit(data)
#   TODO
#    def save_to_csv(self, tweet):
#        with open(r'tweet_archive.csv', 'a') as file:
#            csv.writer(file).writerow(list(tweet.values))

stream = tStream(cons_key, cons_secret, access_key, access_secret)
try:
    stream.statuses.filter(follow=followers)
except KeyboardInterrupt:
    print('')
    print("Keyboard Interrupt")
    pass
#   TODO
#except IncompleteRead as e:
#    sys.stderr.write("Disconnected from server, retrying")
#    sleep(1000)
    #stream.statuses.filter(follow=followers)
except Exception as e:
    if(str(e) == 'IncompleteRead'):
        print("INCOMP READ DETECTED")
    print(e)
#    sys.stderr.write("Unexpected exception: %s\n"%(str(e)))
finally:
    print("Disconnecting stream")
    stream.disconnect()

