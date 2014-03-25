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
  twitter_handles = []
  
  
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

  domains = {u'one.org': {u'EllnMllr': 2}, u'sharecare.com': {u'DrOz': 1}, u'ssireview.org': {u'DianeEMeier': 1}, u'C3Enet.org': {u'ENERGY': 1}, u'mommabears.org': {u'DianeRavitch': 1}, u'capitalandmain.com': {u'DianeRavitch': 1}, u'fairfaxea.org': {u'DianeRavitch': 1}, u'entrepreneur.com': {u'ElenaVerlee': 3}, u'salesengine.com': {u'DanWaldo': 4}, u'thrillist.com': {u'FishBizCo': 1}, u'christianitytoday.com': {u'DianeRavitch': 2}, u'thescanfoundation.org': {u'DianeEMeier': 1}, u'kevinmd.com': {u'Doctor_V': 1}, u'thesaleshunter.com': {u'DanWaldo': 12}, u'bnl.gov': {u'ENERGY': 2}, u'inboundpro.net': {u'DanWaldo': 1}, u'cgdev.org': {u'EllnMllr': 1}, u'betakit.com': {u'DanWaldo': 1}, u'theatlantic.com': {u'DKThomp': 32, u'DianeEMeier': 1, u'DanielPink': 1, u'Doctor_V': 2, u'DavidGrann': 1, u'DianeRavitch': 1}, u'aarp.org': {u'DianeEMeier': 2}, u'radiolab.org': {u'DianeEMeier': 3}, u'energy.gov': {u'ErnestMoniz': 3, u'ENERGY': 63}, u'psychcentral.com': {u'DTWillingham': 1}, u'ozy.com': {u'DLeonhardt': 1}, u'boingboing.net': {u'DanielPink': 1}, u'politico.com': {u'DianeRavitch': 1, u'Eurasiagroup': 17, u'DavidGrann': 1, u'DLeonhardt': 1, u'EricaMartinson': 1}, u'johnniemoore.com': {u'DavidGurteen': 3}, u'salesaerobicsforengineersblog.com': {u'DanWaldo': 8}, u'healio.com': {u'EricTopol': 1}, u'snl.com': {u'EricaMartinson': 1}, u'cbssports.com': {u'DanielPink': 1}, u'pewinternet.org': {u'DKThomp': 1, u'Doctor_V': 1}, u'crossborderpr.com': {u'ElenaVerlee': 1}, u'craigslist.org': {u'DanielPink': 1}, u'haymarketbooks.org': {u'DTWillingham': 1}, u'cjr.org': {u'EricTopol': 1, u'DLeonhardt': 1}, u'nber.org': {u'DLeonhardt': 1}, u'educationnext.org': {u'DTWillingham': 1}, u'offerpop.com': {u'EW': 1}, u'Cinncinnati.com': {u'DianeRavitch': 1}, u'cnn.com': {u'DanielPink': 1, u'Eurasiagroup': 1, u'EricaMartinson': 1, u'DrWeil': 1}, u'nickmom.com': {u'DrOz': 1}, u'thewire.com': {u'DKThomp': 4, u'DanielPink': 1}, u'transportevolved.com': {u'DavidFerris': 1}, u'nickmilton.com': {u'DavidGurteen': 1}, u'jarche.com': {u'DavidGurteen': 2}, u'nytimes.com': {u'DKThomp': 7, u'DianeRavitch': 4, u'Doctor_V': 1, u'DLeonhardt': 8, u'FishBizCo': 2, u'EricTopol': 8, u'EllnMllr': 4, u'DianeEMeier': 5, u'DanielPink': 1, u'DanielMorain': 1, u'FCousteau': 1, u'DTWillingham': 4, u'DavidFerris': 2, u'DavidGrann': 8, u'EICES_Columbia': 4, u'DavidLat': 3, u'CoralMDavenport': 4}, u'jamanetwork.com': {u'DianeEMeier': 2}, u'sellingfearlessly.com': {u'DanWaldo': 10}, u'casnocha.com': {u'DanSchawbel': 1}, u'dezeen.com': {u'Dezeen': 396}, u'esajournals.org': {u'Emma_Marris': 1}, u'iamaneducator.com': {u'DianeRavitch': 1}, u'thesalesblog.com': {u'DanWaldo': 14}, u'bobbraunsledger.com': {u'DianeRavitch': 2}, u'om.co': {u'ConversationAge': 1}, u'express.co.uk': {u'Emma_Marris': 1}, u'gopublicschool.com': {u'DianeRavitch': 1}, u'leaderswest.com': {u'DanWaldo': 3}, u'ow.ly': {u'DKThomp': 1, u'Dezeen': 7}, u'federalreserve.gov': {u'DKThomp': 1}, u'journalgazette.net': {u'DianeRavitch': 1}, u'topsalesworld.com': {u'DanWaldo': 15}, u'ew.com': {u'EW': 314}, u'nejm.org': {u'EricTopol': 4, u'DianeEMeier': 1}, u'sfgate.com': {u'ConversationAge': 1, u'DanielMorain': 1}, u'byliner.com': {u'DavidGrann': 1}, u'fnal.gov': {u'ENERGY': 1}, u'social-hire.com': {u'DanWaldo': 1}, u'stltoday.com': {u'DianeEMeier': 1}, u'towcenter.org': {u'DLeonhardt': 1}, u'apnews.com': {u'Emma_Marris': 2}, u'medpagetoday.com': {u'DianeEMeier': 2}, u'bounceenergy.com': {u'EPRINews': 1}, u'ascopost.com': {u'DianeEMeier': 1}, u'wired.co.uk': {u'ConversationAge': 1}, u'michaeltrow.com': {u'DanWaldo': 1}, u'digitaltonto.com': {u'ConversationAge': 1}, u'geripal.org': {u'DianeEMeier': 7}, u'gawker.com': {u'DKThomp': 3}, u'womenonbusiness.com': {u'ElenaVerlee': 2}, u'chicagoreader.com': {u'DianeRavitch': 1}, u'nymag.com': {u'DKThomp': 2, u'DavidGrann': 2}, u'nationalgeographic.com': {u'DTWillingham': 2, u'DKThomp': 1, u'EricTopol': 1, u'EICES_Columbia': 2}, u'cambridge.org': {u'DTWillingham': 1}, u'nature.com': {u'EricTopol': 5, u'EICES_Columbia': 1, u'Emma_Marris': 1}, u'tes.co.uk': {u'DTWillingham': 1}, u'cell.com': {u'EricTopol': 1}, u'pnnl.gov': {u'ENERGY': 2}, u'spotify.com': {u'EW': 1}, u'cambiahealthfoundation.org': {u'DianeEMeier': 1}, u'schoolhouselive.org': {u'DianeRavitch': 7}, u'informz.net': {u'DianeEMeier': 1}, u'starresults.com': {u'DanWaldo': 1}, u'wearableworldnews.com': {u'Doctor_V': 1, u'DuaneForrester': 15}, u'aps.edu': {u'ENERGY': 1}, u'whitehouse.gov': {u'ENERGY': 7}, u'sunlightfoundation.com': {u'EllnMllr': 13}, u'thenation.com': {u'EllnMllr': 1}, u'jonathanpelto.com': {u'DianeRavitch': 1}, u'sociallogical.com': {u'DanWaldo': 1}, u'rebekahradice.com': {u'DanWaldo': 2}, u'sacbee.com': {u'DanielMorain': 12, u'DrWeil': 1}, u'dianeravitch.net': {u'DianeRavitch': 236}, u'moz.com': {u'DuaneForrester': 10}, u'himss.org': {u'Doctor_V': 1}, u'thetimes.co.uk': {u'EricaMartinson': 1}, u'ustwo.com': {u'ConversationAge': 1}, u'springwise.com': {u'DanielPink': 2}, u'blogspot.co.uk': {u'DavidGurteen': 2}, u'scientificamerican.com': {u'DavidFerris': 2}, u'newsalescoach.com': {u'DanWaldo': 1}, u'variety.com': {u'DKThomp': 1, u'ConversationAge': 1}, u'fwe.ca': {u'ElenaVerlee': 1}, u'techpresident.com': {u'EllnMllr': 1}, u'people-press.org': {u'DKThomp': 1, u'DLeonhardt': 1}, u'typepad.com': {u'ElenaVerlee': 2, u'DanielPink': 2}, u'ctnewsjunkie.com': {u'DianeRavitch': 1}, u'lisabadams.com': {u'DianeEMeier': 1}, u'elderbranch.com': {u'DianeEMeier': 1}, u'people.com': {u'EW': 1}, u'diverseeducation.com': {u'DianeRavitch': 1}, u'computerworld.com': {u'Doctor_V': 1, u'EricTopol': 1}, u'govfresh.com': {u'EllnMllr': 3}, u'mondaynote.com': {u'ConversationAge': 1}, u'twitpic.com': {u'DavidLat': 1}, u'beyondchron.org': {u'DianeRavitch': 1}, u'nopassiveincome.com': {u'DanWaldo': 2}, u'prweb.com': {u'DanWaldo': 2}, u'cynthiakocialski.com': {u'DanWaldo': 2}, u'flipboard.com': {u'Dezeen': 1}, u'coindesk.com': {u'DanielPink': 1}, u'lessig.org': {u'DianeEMeier': 1}, u'snarketing2dot0.com': {u'ConversationAge': 2}, u'broadwayworld.com': {u'DanWaldo': 1}, u'grantland.com': {u'DKThomp': 1, u'DLeonhardt': 1}, u'niftyniblets.com': {u'DavidGrann': 1}, u'campaign-archive1.com': {u'DanWaldo': 1}, u'bobmannblog.com': {u'DianeRavitch': 1}, u'oxfordmuse.com': {u'DavidGurteen': 1}, u'commonwealthfund.org': {u'DianeEMeier': 4}, u'yesmagazine.org': {u'DianeRavitch': 1}, u'repec.org': {u'DTWillingham': 1}, u'deadspin.com': {u'DKThomp': 1}, u'electionlawblog.org': {u'DavidLat': 2}, u'thedailybeast.com': {u'DKThomp': 1}, u'forbes.com': {u'DavidGurteen': 2, u'EricTopol': 1, u'DanSchawbel': 2, u'DanielPink': 1}, u'capitalnewyork.com': {u'DianeEMeier': 1, u'DianeRavitch': 1}, u'macobserver.com': {u'ConversationAge': 1}, u'noahbrier.com': {u'ConversationAge': 1}, u'theonion.com': {u'DianeRavitch': 1}, u'bloombergview.com': {u'DKThomp': 1}, u'jeffshore.com': {u'DanWaldo': 4}, u'thedoctorblog.com': {u'Doctor_V': 3}, u'idonethis.com': {u'DanielPink': 1}, u'scoremoresales.com': {u'DanWaldo': 5}, u'theparisreview.org': {u'DavidGrann': 1}, u'amda.com': {u'DianeEMeier': 1}, u'shareaholic.com': {u'ElenaVerlee': 1}, u'utsandiego.com': {u'EricTopol': 1}, u'rt.com': {u'DKThomp': 1}, u'dailymail.co.uk': {u'Doctor_V': 1, u'DavidGrann': 4}, u'retronaut.com': {u'DavidGrann': 1}, u'ahrq.gov': {u'DianeEMeier': 1}, u'bekdavis.com': {u'DanWaldo': 1}, u'edgyquotes.com': {u'DanWaldo': 2}, u'conversationagent.com': {u'ConversationAge': 15}, u'salesandmanagementblog.com': {u'DanWaldo': 3}, u'contently.com': {u'Doctor_V': 1}, u'eventbrite.com': {u'DavidGurteen': 1, u'ENERGY': 2}, u'wired.com': {u'ConversationAge': 2}, u'space.com': {u'DanielPink': 1}, u'canadianbusiness.com': {u'ElenaVerlee': 1}, u'cbsnews.com': {u'Eurasiagroup': 1}, u'fearless-selling.ca': {u'DanWaldo': 2}, u'chalkbeat.org': {u'DianeRavitch': 1}, u'reuters.com': {u'DavidLat': 1, u'DKThomp': 1, u'EricaMartinson': 1, u'Eurasiagroup': 12}, u'careersingovernment.com': {u'DanWaldo': 1}, u'noozhawk.com': {u'FCousteau': 1}, u'littlesis.org': {u'EllnMllr': 1}, u'converge-health.com': {u'Doctor_V': 1}, u'nestlenutrition-institute.org': {u'Doctor_V': 1}, u'salestrainingconnection.com': {u'DanWaldo': 6}, u'cbslocal.com': {u'DKThomp': 1}, u'soundcloud.com': {u'EW': 7}, u'qz.com': {u'DKThomp': 3, u'DanSchawbel': 1, u'DanielPink': 3}, u'ted.com': {u'DanielPink': 1}, u'wordpress.com': {u'DavidGurteen': 1, u'Doctor_V': 1, u'DianeEMeier': 1, u'DianeRavitch': 9}, u'informationweek.com': {u'Epocrates': 1}, u'indyvanguard.org': {u'DianeRavitch': 1}, u'kottke.org': {u'DavidGrann': 2}, u'asalesguyrecruiting.com': {u'DanWaldo': 3}, u'scripting.com': {u'ConversationAge': 3}, u'networkforpubliceducation.org': {u'DianeRavitch': 5}, u'globalpolicyjournal.com': {u'EricTopol': 1}, u'proceranetworks.com': {u'DKThomp': 2}, u'inc.com': {u'DanWaldo': 1}, u'npr.org': {u'DickKnox': 1, u'EW': 2, u'DianeEMeier': 1, u'DanielPink': 3, u'DavidLat': 1}, u'cdc.gov': {u'DianeEMeier': 1}, u'graigmeyer.com': {u'DianeRavitch': 1}, u'chronicle.com': {u'DavidGrann': 1}, u'hud.gov': {u'ENERGY': 3}, u'tinyurl.com': {u'DianeRavitch': 1}, u'pallimed.org': {u'DianeEMeier': 1}, u'trainingindustry.com': {u'DanWaldo': 1}, u'turner.com': {u'DKThomp': 1}, u'wiley.com': {u'EricTopol': 1, u'DTWillingham': 2}, u'rethinkmedia.org': {u'EllnMllr': 1}, u'sfist.com': {u'DanielPink': 1}, u'sabew.org': {u'DKThomp': 1}, u'state.gov': {u'EricaMartinson': 1}, u'businessnewsdaily.com': {u'DanSchawbel': 1}, u'businessweek.com': {u'DKThomp': 1, u'DianeEMeier': 1, u'ENERGY': 1}, u'longform.org': {u'DavidGrann': 1}, u'wsj.com': {u'DKThomp': 1, u'DianeEMeier': 4, u'ConversationAge': 2, u'DanielPink': 1, u'Doctor_V': 3, u'DavidGurteen': 1, u'EricTopol': 10}, u'nationalinterest.org': {u'Eurasiagroup': 4}, u'getbase.com': {u'DanWaldo': 12}, u'thesalesthoughtleaders.com': {u'DanWaldo': 3}, u'poets.org': {u'DTWillingham': 1}, u'slate.com': {u'DawnC331': 1, u'DKThomp': 3, u'DavidGrann': 4, u'Doctor_V': 1, u'EricTopol': 1}, u'nih.gov': {u'DianeEMeier': 1}, u'solonline.org': {u'DavidGurteen': 1}, u'linkedin.com': {u'DavidGurteen': 2, u'Eurasiagroup': 2, u'Dezeen': 5, u'DanielPink': 3}, u'alixpartners.com': {u'DonaldShoup': 1}, u'intuit.com': {u'DanSchawbel': 10}, u'bing.com': {u'DuaneForrester': 3}, u'mobileworldlive.com': {u'DuaneForrester': 8}, u'rawstory.com': {u'DKThomp': 1}, u'sloansportsconference.com': {u'DKThomp': 2}, u'amorebeautifulquestion.com': {u'DanielPink': 1}, u'jessicaannmedia.com': {u'DanWaldo': 2}, u'theglobeandmail.com': {u'DanSchawbel': 2}, u'krdo.com': {u'DianeRavitch': 1}, u'moveon.org': {u'DianeRavitch': 2}, u'nyshealthfoundation.org': {u'DianeEMeier': 1}, u'popsci.com': {u'EICES_Columbia': 1}, u'scribd.com': {u'DianeRavitch': 1}, u'pando.com': {u'DKThomp': 1, u'DianeRavitch': 2}, u'theenergycollective.com': {u'EPRINews': 1}, u'intrepid-llc.com': {u'DanWaldo': 3}, u'mit.edu': {u'EricTopol': 1}, u'politicopro.com': {u'EricaMartinson': 4}, u'kidney.org': {u'DrOz': 1}, u'kinja.com': {u'DKThomp': 1, u'DavidGrann': 1}, u'aacte.org': {u'DianeRavitch': 1}, u'bloomberg.com': {u'DawnC331': 1, u'Eurasiagroup': 3, u'ConversationAge': 1}, u'recode.net': {u'DawnC331': 1}, u'commercialappeal.com': {u'DKThomp': 1}, u'jccdigital.org': {u'DianeRavitch': 1}, u'go.com': {u'DKThomp': 1, u'EW': 2, u'DanielPink': 1}, u'klagroup.com': {u'DanWaldo': 1}, u'douglaserice.com': {u'DanWaldo': 2}, u'atthechalkface.com': {u'DianeRavitch': 3}, u'biomedcentral.com': {u'EricTopol': 2}, u'bourncreative.com': {u'DanWaldo': 3}, u'deadline.com': {u'DKThomp': 1}, u'edgyconversations.com': {u'DanWaldo': 73}, u'google.com': {u'ENERGY': 9, u'EW': 2}, u'alternet.org': {u'DianeRavitch': 2}, u'openmedicine.ca': {u'DianeEMeier': 1}, u'astd.org': {u'DanWaldo': 1}, u'politicalwire.com': {u'EllnMllr': 7}, u'millerstime.net': {u'EllnMllr': 1}, u'mobilemarketingwatch.com': {u'DuaneForrester': 21}, u'psmag.com': {u'DanielPink': 1}, u'stanford.edu': {u'Doctor_V': 2}, u'constantcontact.com': {u'DianeRavitch': 1}, u'newsweek.com': {u'Duncande': 1}, u'socialstrategies.net.au': {u'DanWaldo': 2}, u'abovethelaw.com': {u'DavidLat': 17}, u'columbia.edu': {u'EICES_Columbia': 2}, u'sellbetter.ca': {u'DanWaldo': 4}, u'thefuturebuzz.com': {u'ConversationAge': 1}, u'cultureby.com': {u'ConversationAge': 1}, u'wikipedia.org': {u'DavidLat': 1}, u'web-strategist.com': {u'DanSchawbel': 1}, u'thoughtcatalog.com': {u'DKThomp': 2}, u'trustedadvisor.com': {u'DanWaldo': 1}, u'threesixtygiving.com': {u'EllnMllr': 1}, u'usatoday.com': {u'DawnC331': 1, u'EricTopol': 1, u'DuaneForrester': 1}, u'nathaliaholt.com': {u'Doctor_V': 1}, u'neatoday.org': {u'DianeRavitch': 1}, u'sxsw.com': {u'Doctor_V': 2}, u'townsendwardlaw.com': {u'DanWaldo': 5}, u'praiseindy.com': {u'DianeRavitch': 1}, u'ritetag.com': {u'DanWaldo': 1}, u'tumblr.com': {u'EllnMllr': 1, u'DKThomp': 1, u'DianeRavitch': 1, u'DTWillingham': 1, u'Emma_Marris': 9, u'EW': 2}, u'danariely.com': {u'DanSchawbel': 1}, u'dezeenguide.com': {u'Dezeen': 2}, u'newrepublic.com': {u'DianeEMeier': 1, u'DavidGrann': 2}, u'edweek.org': {u'DTWillingham': 2, u'DianeRavitch': 3}, u'monthlyreview.org': {u'DianeRavitch': 2}, u'thenferblog.org': {u'DianeRavitch': 1}, u'acs.org': {u'EricTopol': 1}, u'jhartfound.org': {u'DianeEMeier': 2}, u'huffingtonpost.com': {u'DianeEMeier': 1, u'DianeRavitch': 1}, u'citizenuniversity.us': {u'EllnMllr': 1}, u'internetmedicine.com': {u'EricTopol': 1}, u'ap.org': {u'EricaMartinson': 1}, u'nrdc.org': {u'EPRINews': 1}, u'hhnmag.com': {u'EricTopol': 1}, u'examiner.com': {u'DianeRavitch': 1}, u'mcclatchydc.com': {u'DavidGrann': 1}, u'businessinsider.com': {u'DKThomp': 5, u'Eurasiagroup': 3}, u'girardatlarge.com': {u'DianeRavitch': 1}, u'retroreport.org': {u'DavidGrann': 1}, u'eenews.net': {u'DavidFerris': 8}, u'publicintegrity.org': {u'EllnMllr': 1}, u'esquire.com': {u'DavidGrann': 1, u'DianeRavitch': 1}, u'tedrubin.com': {u'DanWaldo': 4}, u'rsrresearch.com': {u'ConversationAge': 1}, u'smartrecruiters.com': {u'DanWaldo': 1}, u'cincinnati.com': {u'DianeRavitch': 1}, u'indiewire.com': {u'DavidGrann': 1}, u'healthinaging.org': {u'DianeEMeier': 1}, u'nasa.gov': {u'ENERGY': 3}, u'danielwillingham.com': {u'DTWillingham': 5}, u'sciencefriday.com': {u'ErnestMoniz': 1, u'ENERGY': 1}, u'edwardboches.com': {u'ConversationAge': 2}, u'danieldromm.com': {u'DianeRavitch': 2}, u'thewpca.org': {u'DianeEMeier': 1}, u'earthtechling.com': {u'DavidFerris': 1}, u'yale.edu': {u'DavidFerris': 2}, u'salesforce.com': {u'DanWaldo': 1}, u'gigaom.com': {u'EllnMllr': 1, u'EPRINews': 1, u'ConversationAge': 3}, u'thefiscaltimes.com': {u'EllnMllr': 1}, u'marcandangel.com': {u'DanWaldo': 1}, u'chicagonow.com': {u'DianeRavitch': 1}, u'blogspot.com': {u'DavidLat': 1, u'DianeRavitch': 11, u'DanielPink': 1}, u'psfk.com': {u'ConversationAge': 1}, u'imgur.com': {u'DTWillingham': 2}, u'medicalfutureslab.org': {u'Doctor_V': 2}, u'merriam-webster.com': {u'DTWillingham': 1}, u'theguardian.com': {u'EllnMllr': 2, u'ConversationAge': 1, u'DLeonhardt': 3, u'DavidFerris': 1, u'DavidGrann': 6, u'DianeRavitch': 1, u'EricTopol': 1}, u'niemanlab.org': {u'ConversationAge': 4}, u'seattlechildrens.org': {u'Doctor_V': 1}, u'wingofzock.org': {u'Doctor_V': 1, u'EricTopol': 1}, u'kickstarter.com': {u'DavidLat': 1}, u'metering.com': {u'EPRINews': 1}, u'britishmediaawards.com': {u'Dezeen': 1}, u'salon.com': {u'DianeRavitch': 2}, u'wittyparrot.com': {u'DanWaldo': 1}, u'cbc.ca': {u'DianeEMeier': 1}, u'prinyourpajamas.com': {u'ElenaVerlee': 21}, u'couriermail.com.au': {u'DKThomp': 1}, u'bigthink.com': {u'DanielPink': 1}, u'danwaldschmidt.com': {u'DanWaldo': 34}, u'gizmodo.com': {u'EricTopol': 1, u'DavidGrann': 7}, u'nbcnews.com': {u'DianeEMeier': 1, u'EricaMartinson': 1}, u'cloakinginequity.com': {u'DianeRavitch': 1}, u'openculture.com': {u'DavidGrann': 2}, u'outandaboutinparis.com': {u'ConversationAge': 1}, u'buzzfeed.com': {u'Doctor_V': 1}, u'theverge.com': {u'DKThomp': 1, u'ConversationAge': 1}, u'dumblittleman.com': {u'ElenaVerlee': 5}, u'pmdigital.com': {u'ConversationAge': 1}, u'webcontentblog.com': {u'DanWaldo': 1}, u'asalesguy.com': {u'DanWaldo': 8}, u'globalnews.ca': {u'DianeEMeier': 1}, u'simonjordan.com': {u'DanWaldo': 1}, u'thenextwomen.com': {u'ElenaVerlee': 1}, u'boxofcrayons.biz': {u'ElenaVerlee': 1}, u'altenergymag.com': {u'EPRINews': 1}, u'problogger.net': {u'ElenaVerlee': 5}, u'solidcactus.com': {u'DuaneForrester': 1}, u'commondreams.org': {u'DianeRavitch': 1}, u'techcrunch.com': {u'ConversationAge': 1, u'DanielPink': 1}, u'echelonseo.com': {u'DanWaldo': 3}, u'theeuropean-magazine.com': {u'Doctor_V': 1}, u'reddit.com': {u'DavidGrann': 1}, u'nptechforgood.com': {u'EllnMllr': 1}, u'johnpaulaguiar.com': {u'DanWaldo': 1}, u'arstechnica.com': {u'ConversationAge': 2}, u'ourfuture.org': {u'DianeRavitch': 1}, u'latimes.com': {u'DawnC331': 3}, u'yoursalesmanagementguru.com': {u'DanWaldo': 1}, u'personalbrandingblog.com': {u'DanSchawbel': 38}, u'fastcocreate.com': {u'DavidGrann': 1}, u'foreffectivegov.org': {u'EllnMllr': 2}, u'geeklesstech.com': {u'DanWaldo': 8}, u'accountabilityindia.in': {u'EllnMllr': 2}, u'33charts.com': {u'Doctor_V': 13}, u'drweilblog.com': {u'DrWeil': 1}, u'policymic.com': {u'DanWaldo': 6, u'DLeonhardt': 1}, u'nativemobile.com': {u'ConversationAge': 1}, u'propublica.org': {u'EllnMllr': 1, u'DianeEMeier': 1}, u'time.com': {u'DanielPink': 1, u'Doctor_V': 2, u'EricTopol': 1, u'DavidGrann': 1, u'EW': 2, u'Eurasiagroup': 1}, u'wnyc.org': {u'DianeRavitch': 1}, u'richardson.com': {u'DanWaldo': 6}, u'searchenginejournal.com': {u'DuaneForrester': 40}, u'amazon.com': {u'DanWaldo': 1, u'DavidLat': 2, u'Doctor_V': 4, u'EW': 1}, u'ottawacitizen.com': {u'DianeEMeier': 1}, u'escapefromcubiclenation.com': {u'ElenaVerlee': 1}, u'washingtonpost.com': {u'DKThomp': 7, u'DLeonhardt': 2, u'EricTopol': 1, u'EllnMllr': 4, u'DanielPink': 5, u'DTWillingham': 2, u'DavidFerris': 2, u'DavidGrann': 1, u'DianeRavitch': 5, u'DavidLat': 1, u'EricaMartinson': 4}, u'sciencemag.org': {u'EricTopol': 3}, u'motherjones.com': {u'DKThomp': 1, u'ConversationAge': 1}, u'thenextweb.com': {u'ConversationAge': 1}, u'bbc.co.uk': {u'DavidGrann': 2}, u'medscape.com': {u'EricTopol': 3}, u'pinterest.com': {u'ENERGY': 1, u'Dezeen': 1}, u'venturebeat.com': {u'ConversationAge': 1}, u'instagram.com': {u'DanWaldo': 1, u'DrOz': 7, u'EW': 11, u'EricaMartinson': 1}, u'vulture.com': {u'DKThomp': 1}, u'copyblogger.com': {u'ElenaVerlee': 4}, u'foodily.com': {u'ConversationAge': 1}, u'macrumors.com': {u'FCousteau': 1}, u'tennessean.com': {u'DianeRavitch': 1}, u'hbr.org': {u'DavidLat': 1, u'DanielPink': 5}, u'flavorwire.com': {u'DavidGrann': 1}, u'medium.com': {u'DKThomp': 1, u'DianeRavitch': 1}, u'nola.com': {u'DianeRavitch': 1}, u'lrb.co.uk': {u'EllnMllr': 1, u'DavidGrann': 2}, u'globalccsinstitute.com': {u'EPRINews': 1}, u'twitter.com': {u'DKThomp': 2, u'DanielPink': 1, u'DLeonhardt': 1, u'DavidGurteen': 1, u'DavidGrann': 2, u'DavidLat': 1, u'EW': 1}, u'mindmulch.net': {u'DanWaldo': 1}, u'allbusiness.com': {u'DanSchawbel': 1}, u'veadailyreports.com': {u'DianeRavitch': 1}, u'treatmentactiongroup.org': {u'DickKnox': 1}, u'hin.com': {u'DianeEMeier': 2}, u'thirteen.org': {u'DianeEMeier': 1}, u'dashes.com': {u'ConversationAge': 1}, u'farnamstreetblog.com': {u'DanielPink': 1}, u'thehorse.com': {u'Emma_Marris': 1}, u'literacytrust.org.uk': {u'DTWillingham': 1}, u'searchengineland.com': {u'DuaneForrester': 64}, u'benton.org': {u'EllnMllr': 7}, u'contrarydomino.com': {u'DanWaldo': 4}, u'sunjournal.com': {u'DianeRavitch': 1}, u'digg.com': {u'DavidGrann': 1}, u'nationaljournal.com': {u'DKThomp': 1}, u'sagepub.com': {u'DianeEMeier': 1, u'DTWillingham': 1, u'DanielPink': 1}, u'yahoo.com': {u'Doctor_V': 1, u'DavidGrann': 1, u'DanielPink': 1}, u'drweil.com': {u'DrWeil': 1}, u'citylimits.org': {u'DianeRavitch': 1}, u'shankman.com': {u'ElenaVerlee': 1}, u'perfectpath.co.uk': {u'DavidGurteen': 1}, u'searchenginewatch.com': {u'DuaneForrester': 48}, u'seen.co': {u'DianeRavitch': 1}, u'dotcomplicated.co': {u'DanWaldo': 5}, u'amazonaws.com': {u'DanWaldo': 1}, u'jccmanhattan.org': {u'DianeRavitch': 4}, u'smartbrief.com': {u'DianeEMeier': 4}, u'nobaproject.com': {u'DTWillingham': 1}, u'uahealth.com': {u'DrWeil': 1}, u'mashable.com': {u'ElenaVerlee': 1}, u'healthaffairs.org': {u'DianeEMeier': 1}, u'impatientoptimists.org': {u'DavidGurteen': 1}, u'washingtonexaminer.com': {u'DTWillingham': 1}, u'triadps.com': {u'DanielPink': 1}, u'on24.com': {u'DanWaldo': 1}, u'brassring.com': {u'Epocrates': 4}, u'foodandwine.com': {u'EW': 1}, u'brenebrown.com': {u'ConversationAge': 1}, u'bizjournals.com': {u'Doctor_V': 1, u'DanielPink': 2}, u'apa.org': {u'DTWillingham': 1, u'DanielPink': 1}, u'tandfonline.com': {u'DTWillingham': 1}, u'psychologicalscience.org': {u'DanielPink': 1}, u'history.com': {u'EW': 22}, u'capc.org': {u'DianeEMeier': 4}, u'ft.com': {u'Eurasiagroup': 5}, u'greenchameleon.com': {u'DavidGurteen': 1}, u'mirror.co.uk': {u'Emma_Marris': 1}, u'zenhabits.net': {u'ElenaVerlee': 3}, u'sheownsit.com': {u'DanWaldo': 23}, u'ralfskirr.com': {u'DanWaldo': 1}, u'dezeenwatchstore.com': {u'Dezeen': 5}, u'zephoria.org': {u'ConversationAge': 1}, u'fiercehealthpayer.com': {u'DianeEMeier': 1}, u'bankingtech.com': {u'DavidBannister': 1}, u'bizzieliving.com': {u'ElenaVerlee': 1}, u'brainshark.com': {u'DianeEMeier': 2}, u'taxpolicycenter.org': {u'DLeonhardt': 1}, u'lisapetrilli.com': {u'DanWaldo': 1}, u'texasobserver.org': {u'DianeRavitch': 1}, u'nydailynews.com': {u'DavidGrann': 1}, u'lww.com': {u'DianeEMeier': 1}, u'peersforprogress.org': {u'DianeEMeier': 1}, u'bwwstatic.com': {u'EW': 1}, u'sciencedaily.com': {u'DTWillingham': 2, u'EICES_Columbia': 9}, u'umich.edu': {u'DKThomp': 1}, u'pewresearch.org': {u'Doctor_V': 1}, u'fastcompany.com': {u'ElenaVerlee': 3}, u'searchengineguide.com': {u'DuaneForrester': 3}, u'fastcolabs.com': {u'ElenaVerlee': 1}, u'hollywoodreporter.com': {u'DanielPink': 1}, u'theadvocate.com': {u'DianeRavitch': 2}, u'defenseone.com': {u'DanielPink': 1}, u'republicreport.org': {u'EllnMllr': 3}, u'qualtrics.com': {u'EW': 2}, u'healthycal.org': {u'DianeEMeier': 1}, u'vanityfair.com': {u'DKThomp': 2}, u'telegraph.co.uk': {u'DKThomp': 1, u'DavidGrann': 5}, u'youtube.com': {u'EPRINews': 1, u'DKThomp': 2, u'ENERGY': 9, u'EW': 4, u'DanWaldo': 1, u'DrOz': 1, u'DanielPink': 1, u'DTWillingham': 1, u'DavidGurteen': 2, u'DavidGrann': 3, u'DianeRavitch': 5, u'DavidLat': 1}, u'eia.gov': {u'EPRINews': 1}, u'marketwatch.com': {u'EricTopol': 1, u'FCousteau': 1}, u'dezeenjobs.com': {u'Dezeen': 3}, u'paleycenter.org': {u'EW': 1}, u'marketplace.org': {u'DanielPink': 2}, u'craigconnects.org': {u'EllnMllr': 2}, u'inxpo.com': {u'Epocrates': 1}, u'knowcademy.com': {u'DavidGurteen': 2}, u'marketingland.com': {u'DuaneForrester': 1, u'ConversationAge': 2}, u'cnbc.com': {u'Eurasiagroup': 1}, u'marketingprofs.com': {u'ElenaVerlee': 3}, u'epri.com': {u'EPRINews': 1}, u'thepowerofintroverts.com': {u'DanSchawbel': 1}, u'advisory.com': {u'DKThomp': 1, u'DianeEMeier': 2}, u'newyorker.com': {u'DKThomp': 1, u'DianeEMeier': 3, u'DavidGrann': 12, u'DianeRavitch': 3, u'DavidLat': 1, u'EricaMartinson': 1}, u'campaign-archive2.com': {u'DanWaldo': 1}, u'truthdig.com': {u'EllnMllr': 2}, u'mymodernmet.com': {u'DavidGrann': 1}, u'krocam.com': {u'Doctor_V': 1}, u'arpae-summit.com': {u'ENERGY': 1}, u'socialmediaexplorer.com': {u'ElenaVerlee': 3}, u'discoverbing.com': {u'DuaneForrester': 3}, u'gillin.com': {u'ConversationAge': 1}, u'jackmalcolm.com': {u'DanWaldo': 10}, u'socialmediaweek.org': {u'FCousteau': 1}, u'renewgridmag.com': {u'EPRINews': 1}, u'ca.gov': {u'DanielMorain': 1}, u'facebook.com': {u'DrOz': 1, u'ENERGY': 1, u'ElenaVerlee': 7, u'EW': 1, u'DianeRavitch': 6}, u'barbaragiamanco.com': {u'DanWaldo': 1}, u'raintoday.com': {u'DanWaldo': 1}, u'colabria.com': {u'DavidGurteen': 1}, u'prophet.com': {u'DavidAaker': 3}, u'oxfordjournals.org': {u'EricTopol': 2}, u'kingsfund.org.uk': {u'DianeEMeier': 1}, u'ornl.gov': {u'ENERGY': 1}, u'dilbert.com': {u'DavidGurteen': 1, u'DanielPink': 1}, u'infosthetics.com': {u'EllnMllr': 2}, u'ameslab.gov': {u'ENERGY': 1}, u'tamaractalk.com': {u'DianeRavitch': 1}, u'timesreview.com': {u'DianeRavitch': 4}, u'llnl.gov': {u'ENERGY': 1}, u'smithsonianmag.com': {u'DavidGrann': 3}, u'doctoroz.com': {u'DrOz': 16}, u'beaconreader.com': {u'DavidFerris': 1}, u'blogtalkradio.com': {u'DianeRavitch': 1}, u'plosmedicine.org': {u'EricTopol': 1}, u'okfn.org': {u'EllnMllr': 6}, u'fastcodesign.com': {u'DKThomp': 1, u'ConversationAge': 1, u'DanielPink': 1}, u'gurteen.com': {u'DavidGurteen': 35}, u'coreknowledge.org': {u'DTWillingham': 1}, u'bbh-labs.com': {u'ConversationAge': 1}, u'upyourtelesales.com': {u'DanWaldo': 5}, u'sciencedirect.com': {u'DTWillingham': 1}, u'poynter.org': {u'EllnMllr': 2}, u'smartsellingtools.com': {u'DanWaldo': 2}, u'americanedtv.com': {u'DianeRavitch': 1}, u'twitlonger.com': {u'DianeRavitch': 1}, u'vh1.com': {u'EW': 1}, u'brennancenter.org': {u'EllnMllr': 1}, u'project-syndicate.org': {u'Eurasiagroup': 2}, u'ucla.edu': {u'DonaldShoup': 1}, u'economist.com': {u'EricTopol': 1}, u'prospectingsummit.com': {u'DanWaldo': 2}}
  
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


