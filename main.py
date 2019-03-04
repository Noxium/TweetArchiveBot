import sys
import os
import datetime
import praw
import twitter
from twython import TwythonStreamer
from string import Template


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
        t = t.replace('&amp;', '&')
        print("Submitting to /r/" + subreddit.display_name + ":\'" + t + "\' at " + u)
        print('')

        full_text = data['text']
        if('extended_tweet' in data):
            full_text = data['extended_tweet']['full_text']
        elif('retweeted_status' in data):
            if('extended_tweet' in data['retweeted_status']):
                full_text = data['retweeted_status']['extended_tweet']['full_text']
            else:
                full_text = data['retweeted_status']['text']

        #format for reddit
        full_text = full_text.replace('&amp;', '&')
        i = 0
        while(i < len(full_text)-1):
            if(full_text[i] == '\n'):
                if(full_text[i+1] !='\n'):
                    modified = full_text[:i] + "  " + full_text[i:]
                    full_text = modified
                    i = i + 2
                else:
                    while(i < len(full_text)-1 and full_text[i+1] == '\n'):
                        i = i + 1
                i = i + 1
                modified = full_text[:i] + '>' + full_text[i:]
                full_text = modified
            i = i + 1

        media = "Coming soon!"
        #TODO
        #if('extended_entities' in data):
        #    if('media' in data['extended_entities']):
        #        media = data['extended_entities']['media']['media_url']
        post = subreddit.submit(title=t, url=u)
        post.reply(">%s    \n\nAuthor: %s    \nTime: %s    \nLocation: %s    \nVia: %s    \nMedia: %s" %(full_text, data['user']['name'], data['created_at'], data['geo'], 'Coming soon!', media))

#        for i in data:
#            if(type(data[i] == 'list')):
#                for j in data[i]:
#                    print("\t", j, repr(data[j]).encode('utf-8'))
#            print(i, repr(data[i]).encode('utf-8'))
#        self.save_to_csv(data)
    
    def on_error(self, status_code, data):
        print(status_code)
    
    def on_success(self, data):
        if(data['user']['id_str'] in followers):
            if(data['lang'] == 'en' or data['lang'] == 'und'):
                self.PostTweetToReddit(data)

#    def on_timeout(self):
#        print("Stream timeout")
#   TODO
#    def save_to_csv(self, tweet):
#        with open(r'tweet_archive.csv', 'a') as file:
#            csv.writer(file).writerow(list(tweet.values))

stream = tStream(cons_key, cons_secret, access_key, access_secret, 5, 0)
#stream = tStream(cons_key, cons_secret, access_key, access_secret, 0, 5)
try:
    stream.statuses.filter(follow=followers)
except KeyboardInterrupt:
    print('')
    print("Keyboard Interrupt")
#   TODO
#except ConnectionError as e:
#    sys.stderr.write("Disconnected from server, retrying")
#    sleep(1000)
    #stream.statuses.filter(follow=followers)
except Exception as e:
    print(repr(e))
    print(e.args[0])
    message = (type(e).__name__, e.args)
    print message
#    sys.stderr.write("Unexpected exception: %s\n"%(str(e)))
finally:
    print("Disconnecting stream")
    stream.disconnect()

