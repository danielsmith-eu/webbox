#    Copyright (C) 2011-2013 University of Southampton
#    Copyright (C) 2011-2013 Daniel Alexander Smith
#    Copyright (C) 2011-2013 Max Van Kleek
#    Copyright (C) 2011-2013 Nigel R. Shadbolt
#    Copyright (C) 2011-2013 Ramine Tinati
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License, version 3,
#    as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse, ast, logging, getpass, sys, urllib2, json, sys, tweepy, datetime, time, threading
from datetime import datetime
from threading import Timer
from indxclient import IndxClient
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import API
from tweepy import Status

appid = "twitter_service"

class TwitterService:

    def __init__(self, credentials, configs, twitter_add_info):
        #logging.debug("Got config items {0}".format(self.config))        
        try:
            if len(credentials)==4 and len(configs)>=4:
                self.credentials = credentials
                self.configs = configs
                self.twitter_add_info = twitter_add_info
                print "loading Service Instance"
                self.indx_con = IndxClient(self.credentials['address'], self.credentials['box'], self.credentials['username'], self.credentials['password'], appid)
                self.consumer_key= self.configs['consumer_key']
                self.consumer_secret= self.configs['consumer_secret']
                self.access_token = self.configs['access_token']
                self.access_token_secret = self.configs['access_token_secret']
                self.twitter_username = self.configs['twitter_username']
                self.since_id = 0
                self.version = 0
                self.batch = []
                
                #set the auth access control
                self.auth = OAuthHandler(self.consumer_key, self.consumer_secret)
                self.auth.set_access_token(self.access_token, self.access_token_secret)
        except:
            logging.error("could not start TwitterService, check config details - params might be missing")

    def stop_and_exit_service(self):
        print "HARD QUIT - TWITTER SERVICE"
        sys.exit()
   

    def run_main_services(self):
        #now get the tweets
        words_to_search = self.get_search_criteria()
        self.get_tweets(words_to_search)

    def run_additional_services(self):
        #see if other harvesters needed (indx con needed to sumbit data)
        self.load_additional_harvesters(self.twitter_add_info, self)


    def load_additional_harvesters(self, additional_params, service):
        try:
            #if the user want's to
            is_get_status = additional_params['twitter_status']
            #establish a search connection as welll...
            if "True" in str(is_get_status):
                logging.debug("Adding Twitter Status Harvester/Timer")
                #threading.Timer(15, self.run_timeline_harvest, args=(service,)).start()
                self.run_timeline_harvest(service)
                print "GETTING STATUS"
        except:
            logging.error("couldnt get status "+str(sys.exc_info()) )

        try:
            is_get_network = additional_params['twitter_network']
            if "True" in str(is_get_network):
                print "GETTING NETWORK"
                logging.debug("Adding Twitter Network Harvester")
                self.harvest_network(service)
        except:
            logging.error("couldnt get Twitter friends network")



    #this needs to call the database to get the search criteria...    
    def get_search_criteria(self):
        search_terms = []
        username = self.configs['twitter_username']
        words = self.configs['twitter_search_words'].split(",")
        search_terms.append(username)
        for word in words:
            search_terms.append(word)
        return words


    def get_tweets(self, words_to_track):
        l = INDXListener(self)

        stream = Stream(self.auth, l)
        if len(words_to_track) > 0:
            print 'getting tweets...'
            stream.filter(track=words_to_track)
        else:
            stream.sample()


    #datamodel is {timestamp: {friends:[friend_id]}
    def harvest_network(self, service):
        try:
            self.api = tweepy.API(service.auth)
            friends_list = self.api.followers_ids(service.twitter_username)
            current_timestamp = str(datetime.now())
            uniq_id = "friends_at_"+current_timestamp
            friends_objs = {"@id":uniq_id, "app_object": appid, "timestamp":current_timestamp, "friends_list": friends_list}
            
            #now append the results
            self.insert_object_to_indx(service, friends_objs)
        except:
            print "harvest network failed"

    def run_timeline_harvest(self, service):

        #first check if INDX has already got the latest version...
        #to-do
        try:
            print "SINCE_ID "+str(service.since_id)
            self.api = tweepy.API(service.auth)
            try:
                if service.since_id > 0:
                    status_timeline = self.api.user_timeline(service.twitter_username, service.since_id)
                else:
                    status_timeline = self.api.user_timeline(service.twitter_username)
            except:
                print "COULDNT GET STATUS, PROBABLY NO UPDATES AS OF YET..."
                status_timeline = {}

            print "GOT STATUS TIMELINE: "+str(len(status_timeline))
            #have we got any statuses?
            if len(status_timeline)>0:
                #guess so - lets commit these to INDX
                #update since_id
                service.since_id = status_timeline[len(status_timeline)-1].id
                print "NEW SINCE_ID :"+str(service.since_id)
                current_timestamp = str(datetime.now())
                uniq_id = "timeline_at_"+current_timestamp
                status_list = []
                for x in status_timeline:
                    #convert date
                    timestamp =  x.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    status = {"user": x.author.name, "created_at": timestamp, "id": x.id, "text": x.text,  "coordinates": x.coordinates, "retweet_count": x.retweet_count}
                    status_list.append(status)
                status_objs = {"@id":uniq_id, "app_object": appid, "timestamp":current_timestamp, "since_id": service.since_id, "status_list": status_list}

            #now append the results
                self.insert_object_to_indx(service, status_objs)
        except:
            "harvest status failed "+str(sys.exc_info())
    
    def insert_object_to_indx(self, service, obj):
     
        try:
            if len(obj)>0:
                response = service.indx_con.update(service.version, obj)
                logging.debug("Inserted Object into INDX: ".format(response))
        except Exception as e:
            if isinstance(e, urllib2.HTTPError): # handle a version incorrect error, and update the version
                if e.code == 409: # 409 Obsolete
                    response = e.read()
                    json_response = json.loads(response)
                    service.version = json_response['@version']
                    logging.error('INDX insert error in Twitter Service Object: '+str(response))
                    try:
                        response = service.indx_con.update(service.version, obj)
                        print "INSERT SUCCESS A SECOND TIME OBJECT"
                    except:
                        print '-------ERROR on second insert: '+str(response)
                else:
                    print '-------ERROR: ',e.read()
            else:
                logging.error("Error updating INDX: {0}".format(e))


class INDXListener(StreamListener):
    """ A listener handles tweets are the received from the stream.
    This is a basic listener that just prints received tweets to stdout.

    """

    def __init__(self, twitter_serv):
        self.service = twitter_serv        


    def on_data(self, tweet_data):
        """ Assert the tweet into INDX.
        If the version is incorrect, the correct version will be grabbed and the update re-sent.
        
        tweet -- The tweet to assert into the box.
        """

        global appid

        try:
            tweet = json.loads(tweet_data)
            #logging.debug("{0}, {1}".format(type(tweet), tweet))
            if not tweet.get('text'):
                # TODO: log these for provenance?                
                #logging.info("Skipping informational message: '{0}'".format(tweet_data.encode("utf-8")))
                return
            #logging.info("Adding tweet: '{0}'".format(tweet['text'].encode("utf-8")))            
            tweet["@id"] = unicode(tweet['id'])
            tweet["app_object"] = appid
            text = unicode(tweet['text'])
            #print text
            self.service.batch.append(tweet)
            if len(self.service.batch) > 25:
                response = self.service.indx_con.update(self.service.version, self.service.batch)
                self.service.version = response['data']['@version'] # update the version
                self.service.batch = []
                logging.info('inserted batch of tweets')
        except Exception as e:
            if isinstance(e, urllib2.HTTPError): # handle a version incorrect error, and update the version
                if e.code == 409: # 409 Obsolete
                    response = e.read()
                    json_response = json.loads(response)
                    self.service.version = json_response['@version']
                    self.on_data(tweet_data) # try updating again now the version is correct
                else:
                    print '-------ERROR: ',e.read()
            else:
                print "didnt insert tweet"
                logging.error("Error updating INDX: {0}".format(e))
                sys.exit(0)                    
        return True

    def on_error(self, status):
        print "Status Error ",status


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.function   = function
        self.interval   = interval
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False