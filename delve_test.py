import requests, simplejson, datetime
from requests_oauthlib import OAuth1
import sys, time
import re
from urlparse import urlparse, unquote

class TwitterException(Exception):
  pass

def get_tweets(
    consumer_key="PxvzWak5FxIpDWtWaystmQ",
    consumer_secret="xlgC6Aht6CPS139HGkZb69ST71X1TSISxA8dYNwthk",
    access_token="1250131134-0CsDvuKJ41cBbvlbW0OpiHt9mMkeBGPvntsYOrN",
    access_secret="LdqqSfbFKJG8CxaDUTPfyOcqrVw8OVW2KjUVRX05RYLb5",
    since_id=None,
    max_id=None,
    screen_name=None,
    count=200
  ):
  auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
  data = {'screen_name': screen_name, 'count': count} #swfitebooks
  if max_id:
    data['max_id'] = max_id
  r = requests.get(
    url='https://api.twitter.com/1.1/statuses/user_timeline.json',
    auth=auth,
    params=data
  )
  json = simplejson.loads(r.text)
  if isinstance(json, dict) and json.has_key('errors'):
    raise TwitterException("; ".join([error['message'] for error in json['errors']]))
  return json


def convert_time_string(string):
  """ Take a Twitter datetime string and return its datetime representation
  """
  months = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12
  }
  split_string = string.split()
  d = datetime.date(int(split_string[-1]),
                    months[split_string[1].lower()],
                    int(split_string[2]))
  return d

def convert_string_to_datetime(time_string):
  """ convert regular input to datetime """
  int_string = [int(i) for i in time_string.split('-')]
  return datetime.date(int_string[0], int_string[1], int_string[2])


def get_tweets_in_date_range(start, end, screen_name):
  """ Get tweets from a date range
  """
  start, end = convert_string_to_datetime(start), convert_string_to_datetime(end)
  culled_tweets = []
  first_date, max_id = start, None
  errors = 0
  while first_date >= start:
    try:
      tweets = get_tweets(max_id=max_id, screen_name=screen_name)
    except TwitterException as e:
      errors += 1
      with open('twitter_errors.txt', 'a') as f:
        f.write(e.message + ',' + screen_name + '\n')
      if errors != 5:
        time.sleep(1)
        continue
      else:
        if not culled_tweets:
          return False
        break
    oldest_tweet, newest_tweet = tweets[-1], tweets[0]
    first_date = convert_time_string(oldest_tweet['created_at'])
    last_date = convert_time_string(newest_tweet['created_at'])
    max_id = oldest_tweet['id_str']
    if first_date <= start or last_date >= end:
      tweets = [t for t in tweets
                if convert_time_string(t['created_at']) <= end
                and convert_time_string(t['created_at']) >= start]
    culled_tweets.extend(tweets)

  return culled_tweets

def get_links_from_tweet(tweet):
  """ Get links from tweets, using twitters API documentation
  """
  if tweet.has_key('entities'):
    if tweet['entities'].has_key('urls'):
      if tweet['entities']['urls']:
        return [t['expanded_url'] for t in tweet['entities']['urls']]

  return None



def count_domains(urls, screen_name, domains):
  """ count up domains by screen_name
  """

  def add_domain_to_dict(domains, domain_string):
    """ helper function"""
    domain = urlparse(unquote(domain_string)).netloc.replace('www.', '')
    domain = domain.split(':')[0]
    try:
      new_domain = get_domain(domain)
    except ValueError:
      with open('erroneous_domains.txt', 'a') as f:
        f.write(domain)
      return domains

    if not domains.get(new_domain):
      domains[new_domain] = {}
    domains[new_domain].get(screen_name, {})
    domains[new_domain][screen_name] = domains[new_domain].get(screen_name, 0) + 1

  for u in urls:
    long_url = 'http://api.longurl.org/v2/expand'
    params = {'url': u, 'format': 'json'}
    try:
      r = requests.get(url=long_url, params=params)
    except requests.ConnectionError as e:
        with open('request_errors.txt', 'a') as f:
          f.write(e.message)
        continue

    json = simplejson.loads(r.text)
    r.close()
    if json.has_key('long-url'):
      domain = get_domain(urlparse(u).netloc.replace('www.', ''))
      if json['long-url'] and domain not in json['long-url']:
        add_domain_to_dict(domains, json['long-url'])
        continue
    if json.has_key('messages') and json['messages'] and \
       json['messages'][0]['message'] == 'Input is oversize: NOT_SHORTURL.':
       add_domain_to_dict(domains, u)
    else:
      try:
        request = requests.get(u)
      except requests.ConnectionError as e:
        with open('request_errors.txt', 'a') as f:
          f.write(e.message)
        continue
      if request.status_code == 200:
        add_domain_to_dict(domains, request.url)
      else:
        with open('log.txt', 'a') as f:
          f.write(u + ',' + screen_name + '\n')
      request.close()

  return domains

tlds = [line.strip() for line in open('tlds.txt') if line[0] not in "/\n"]
def get_domain(url, tlds=tlds):
  """ taken from stack overflow to get true domain"""

  url_elements = url.split('.')
  for i in range(-len(url_elements), 0):
      last_i_elements = url_elements[i:]

      candidate = ".".join(last_i_elements)
      wildcard_candidate = ".".join(["*"] + last_i_elements[1:])
      exception_candidate = "!" + candidate

      if (exception_candidate in tlds):
          return ".".join(url_elements[i:]) 
      if (candidate in tlds or wildcard_candidate in tlds):
          return ".".join(url_elements[i-1:])

  raise ValueError("Domain not in global list of TLDs")


def get_problem(endpoint="http://delvenews.com/api/matador/"):
  r = requests.get(url=endpoint, data={
      'email': 'pmavfmoura@gmail.com',
      'format': 'json'
    })
  json = simplejson.loads(r.text)
  return json

def submit_problem(data, endpoint="http://delvenews.com/api/matador/"):
  r = requests.post(url=endpoint, data=data, headers={
    'content-type': 'application/json'
    })
  return r.text



if __name__ == "__main__":
  #problem_data = get_problem()
  problem_data = {u'twitter_handles': [u'ClintonHealth', u'ConnectWell', u'ConversationAge', u'CoralMDavenport', u'DKThomp', u'DLeonhardt', u'DTWillingham', u'Dahlialithwick', u'DanSchawbel', u'DanWaldo', u'DanielMorain', u'DanielPink', u'DanielSnowSmith', u'DavidAaker', u'DavidBannister', u'DavidFerris', u'DavidGrann', u'DavidGurteen', u'DavidLat', u'DawnC331', u'DebMeier', u'Dezeen', u'DianeEMeier', u'DianeRavitch', u'DickKnox', u'Doctor_V', u'DonaldShoup', u'DrOz', u'DrSBoyer', u'DrWeil', u'DuaneForrester', u'Duncande', u'EICES_Columbia', u'ENERGY', u'EPRINews', u'EW', u'EYellin', u'EdwardLangJr', u'ElectricAirwave', u'ElenaVerlee', u'EllnMllr', u'Emma_Marris', u'Epocrates', u'EricTopol', u'EricaMartinson', u'ErnestMoniz', u'Eurasiagroup', u'FCousteau', u'Farzad_ONC', u'FishBizCo'], u'begin_date': u'2014-02-20', u'end_date': u'2014-03-05', u'match_criteria': 3}


  twitter_handles = problem_data["twitter_handles"]
  start_date = problem_data['begin_date']
  end_date = problem_data['end_date']
  match_count = problem_data['match_criteria']
  domains = {}
  
  
  errors = 0
  for handle in twitter_handles:
    print handle
    
    tweets = get_tweets_in_date_range(start_date, end_date, screen_name=handle)
    
    if tweets is False:
      errors += 1
      with open('broken_handles.txt', 'a') as f:
        f.write(handle + '\n')

      if errors != 10:
        continue
      else:
        with open('temp_domains.txt', 'w') as f:
          f.write(str(domains))
        sys.exit(0)

    all_urls = []
    for tweet in tweets:
      tweet_urls = get_links_from_tweet(tweet)
      if tweet_urls:
        all_urls.extend(tweet_urls)
    domains = count_domains(all_urls, handle, domains)

    with open('temp.txt', 'w') as f:
      f.write(str(domains))


  
  # create submission object
  users = {}  
  for domain, user_counts in domains.iteritems():
    for handle, count in user_counts.iteritems():
      if not users.has_key(handle):
        users[handle] = {}
      
      for handle_again, count_again in user_counts.iteritems():
        if handle_again == handle:
          continue
        elif count_again >= match_count and count >= match_count:
          if not users[handle].has_key(handle_again):
            users[handle][handle_again] = {}
          users[handle][handle_again][domain] = True

  s = submit_problem(simplejson.dumps(users))
  print s


