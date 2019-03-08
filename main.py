import sys
import os
import datetime
import time
import praw
import twitter
import json
import urllib2
import csv
from twython import Twython
from twython import TwythonStreamer
from string import Template

NoPost = False

def check_connection():
    try:
        urllib2.urlopen('https://twitter.com/')
        return True
    except urllib2.URLError as e:
        return False
for arg in sys.argv:
    if(arg.lower() == '-n'):
        NoPost = True
        print("---Posting disabled")

if(not check_connection()):
    print('Twitter is down or (more likely) yo internet broke')
    sys.exit(1)
    
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

twython = Twython(cons_key, cons_secret, access_key, access_secret)
#twython = Twython(cons_key, ACCESS_TOKEN)

bot = praw.Reddit(user_agent='TweetArchiveBotv0.1',
        client_id= os.environ.get("BOT_CLIENT_ID"),
        client_secret=os.environ.get("BOT_CLIENT_SECRET"),
        username=os.environ.get("BOT_USERNAME"),
        password=os.environ.get("BOT_PASSWORD"))


subreddit = bot.subreddit('TweetArchiver')
#comments = subreddit.stream.comments()

def getFollowers():
    followers = []
    for user in api.GetFriends():
        print("\t" + user.name)
        followers.append(user.id_str)
    return followers
    #    print("Program set to track the following users")
    #    for i in followers:
    #        print(i)

def reddit_format(text):
        text = text.replace('&amp;', '&')
        text = '>' + text
        i = 0
        while(i < len(text)-1):
            if(text[i] == '\n'):
                if(text[i+1] !='\n'):
                    modified = text[:i] + "  " + text[i:]
                    text = modified
                    i = i + 2
                else:
                    while(i < len(text)-1 and text[i+1] == '\n'):
                        i = i + 1
                i = i + 1
                modified = text[:i] + '>' + text[i:]
                text = modified
            i = i + 1
        return text

def get_user(data):
    return (twython.show_user(id=data['user_id']))['screen_name']

class tStream(TwythonStreamer):
    followers = []

    def set_followers(self, followers):
        self.followers = followers

    def PostDeleteToReddit(self, data):
        try:
            user = get_user(data['delete']['status'])
            t = (">> Tweet deleted by %s at %s.  ID: %s" %(user, datetime.datetime.now(), data['delete']['status']['id_str']))
            print("Submitting to /r/" + subreddit.display_name + ":\'" + t)
            post = subreddit.submit(title=t, selftext='Actual deleted tweet information will be implemented soon, sorry ):')
        except Exception as e:
            print('')
            print("TA has encountered a strange tweet it doesn't know how to deal with, logging JSON in tweet_fail.json")
            print(str(e))
            f = open("tweet_fail.json","w+")
            f.write(json.dumps(data, indent=4))
            f.close


    def PostTweetToReddit(self, data):
        u = "https://twitter.com/" + data['user']['screen_name'] + "/status/" + data['id_str']
        t = data['user']['name'] + ": " + data['text'] + " (" + data['created_at'] + ")"
        t = t.replace('&amp;', '&')
        print('')
        print("Submitting to /r/" + subreddit.display_name + ":\'" + t + "\' at " + u)

        full_text = data['text']
        if('extended_tweet' in data):
            full_text = data['extended_tweet']['full_text']
        elif('retweeted_status' in data):
            if('extended_tweet' in data['retweeted_status']):
                full_text = data['retweeted_status']['extended_tweet']['full_text']
            else:
                full_text = data['retweeted_status']['text']

        in_response_to = 'None (note: feature only works with retweets ATM)  '
        #TODO make this work with replies
        if('quoted_status' in data):
            if('extended_tweet' in data['quoted_status']):
                in_response_to = reddit_format(data['quoted_status']['extended_tweet']['full_text'])
                in_response_to = '\n\n' + in_response_to + '\n'
            elif('text' in data['quoted_status']):
                in_response_to = reddit_format(data['quoted_status']['text'])
                in_response_to = '\n\n' + in_response_to + '\n'
        #elif('in_reply_to_status_id' in data):
        #TODO
        #    in_response_to = api.show_status(id=data['in_reply_to_status_id'])
        #    print("IN RESPONSE TO")
        #    print(in_response_to)

        media = 'None'
        if('entities' in data):
            if('media' in data['entities']):
                if('media_url_https' in data['entities']['media'][0]):
                    media = data['entities']['media'][0]['media_url_https']

        if(not NoPost):
            post = subreddit.submit(title=t, url=u)
            post.reply("%s    \n\nIn response to: %s\nAuthor: %s    \nTime: %s    \nLocation: %s    \nVia: %s    \nMedia: %s" %(reddit_format(full_text), in_response_to, data['user']['name'], data['created_at'], data['geo'], 'Coming soon!', media))
        with open('archive.csv', 'a') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            t_id    = repr(data['id']).encode('utf-8')
            t_t     = repr(full_text).encode('utf-8')
            t_uid   = repr(data['user']['id']).encode('utf-8')
            t_usn   = repr(data['user']['screen_name']).encode('utf-8')

            csv_writer.writerow([t_id, t_t, t_uid, t_usn])
#            for row in csv_reader:
            #self.save_to_csv(data)
    
    def on_error(self, status_code, data):
        print(status_code)
    
    def on_success(self, data):
        if('user' in data):
            if(data['user']['id_str'] in self.followers):
                if(data['lang'] == 'en' or data['lang'] == 'und'):
                    self.PostTweetToReddit(data)
        elif('delete' in data):
            self.PostDeleteToReddit(data)
        else:
            print("TA has encountered a strange tweet it doesn't know how to deal with, logging JSON in tweet_fail.json")
            f = open("tweet_fail.json","w+")
            f.write(json.dumps(data, indent=4))
            f.close

def stream(followers):
    print("Starting Tweet Archiver at %s" %datetime.datetime.now())
    stream = tStream(cons_key, cons_secret, access_key, access_secret, 5, 0)
    stream.set_followers(followers)
    retry = True
    try:
        stream.statuses.filter(follow=followers)
    except Exception as e:
        message = (type(e).__name__, e.args)
        print message
    except KeyboardInterrupt:
        print('')
        print("Keyboard Interrupt")
        retry = False
    #    sys.stderr.write("Unexpected exception: %s\n"%(str(e)))
    finally:
        print("Disconnecting stream at %s" %datetime.datetime.now())
        stream.disconnect()
        return retry

def main():
    followers = getFollowers()
    while(True):
        retry = stream(followers)
        if(not retry):
            break
        print('Tweet archiver doesn\'t feel like working, retrying in 5 seconds')
        print('')
        time.sleep(5);

main()

