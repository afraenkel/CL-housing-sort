### To add:
# Further feature extraction: gps, date available, security deposit, amenities
# Open findings in google maps / make HTML nicer
# Change metric -- use combo of single words and bigrams for body. 


######
# Constants specificed by user / developer
######

# Output File location
FILE_LOCATION = "~/Desktop/Housing_Ads.html"

# Base URL to search:
BASE_URL = 'http://boston.craigslist.org/'

# Sub-location to refine craiglist search:
SUBLOC = 'gbs'   # gbs = greater boston area

# Max price of desired apartment in USD:
PRICE = 1800

# Number of bedrooms desired:
NUM_BEDS = 2

# and size of training set
NUM_POSTS = 200
NUM_TR_POSTS = 40

# Threshold above PRICE to train on:
THRESH = 1.2


######
# Modules to import
######

# General

import math

# HTML / Screen Scraping related

import requests
from bs4 import BeautifulSoup
from urlparse import urljoin

# NLP / Data processing

import string
import re
import nltk

# Local imports:

# apartment rental terms dictionary
from AptRentTerms import rad  

# list of neigborhoods
# large neighborhoods contained in list NBDS
# sub-neighborhoods in lists named by elements of NBDS.
# i.e. need to eval(NBDS[k]) to access variables.
from Neighborhoods import *

######
# Scraping functions
######

# functions that find post URLs and basic
# post data to be processed.

def get_training_posts():
    """ Outputs a list of housing posts that
    make up the training set for 'desirable posts'
    according to users specified constants """
    fancy_price = int(math.ceil(THRESH*PRICE))
    L = collect_posts(NUM_BEDS, NUM_TR_POSTS,
                      m_price = fancy_price )
    L = map( scrape_housing_post, L )
    return( L )

def get_potential_posts():
    """ Outputs a list of potential housing posts
    to be compared with training set. """
    L = collect_posts(NUM_BEDS,NUM_POSTS,
                      M_price = PRICE)
    L = map( scrape_housing_post, L )
    return( L )

def collect_posts(num_beds,num_posts,
                 m_price='',M_price=''):
    """ inputs (1) a minumum price, (2) max price
    (3) number of bedrooms, (4) the number of
    posts to be collected.
    Outputs a list (len = num_posts)
    of posts (dictionaries) """
    post_list = []
    url_iter = 0
    while len( post_list ) < num_posts:
        # craigslist search url based on parameters of function.
        search_url = ''.join([ BASE_URL, "search/", "aap/", SUBLOC,
                        '?s=', str( url_iter*100 ),
                        '&minAsk=', str(m_price), '&maxAsk=', str(M_price),
                        '&bedrooms=', str(num_beds) ])
        L = post_attrs( search_url )
        # retain posts with specified number of bedrooms
        for post in L:
            if post['num_bd'] == num_beds:
                if post not in post_list:
                    post_list.append( post )
        url_iter = url_iter + 1
    # keep only specified amount
    post_list = post_list[:num_posts]
    return( post_list )
        

def post_attrs( url ):
    """ inputs a craigslist search page url.
    Outputs a list of post attributes in form
    {'price', 'bedrooms', 'neighborhood'}"""
    response = requests.get( url )
    soup = BeautifulSoup( response.content )
    # Split posts into a list
    housing_ads = soup.find_all('p',{'class':'row'})
    L = []
    for post in housing_ads:
        D={}
        attr = post.find('span',{'class':'l2'}).stripped_strings
        # number of bedrooms
        num_bed = re.findall('[0-9]br', ' '.join(attr) )
        if num_bed == []:
            num_bed = 0
        else:
            num_bed = int( num_bed[0][0] )
        D['num_bd']= num_bed
        # list price
        price = post.find('span',{'class':'price'})
        if price is None:
            D['price'] = ' '
        else:
            D['price'] = price.contents[0]
        # neighborhood -- first pass
        nbd = post.find('small')
        if nbd is None:
            D['neighborhood']= ''
        else:
            D['neighborhood'] = nbd.contents[0]
        # source url for post
        link = post.find('a').attrs['href']
        source_url = urljoin(BASE_URL, link)
        D['source_url'] = source_url
        L = L + [D]
    return( L )


# functions that add details of
# post dictionaries using source_url for
# each post.


def scrape_housing_post( post ):
    """ Extract info from a single posting (dictionary),
    and update the posting dictionary. """
    url = post['source_url']
    response = requests.get(url)
    soup = BeautifulSoup(response.content)
    #
    # Subject / Body extraction
    subject_soup = soup.find('h2', {'class':'postingtitle'})
    if subject_soup is None:
        subject_soup = ['']
    else:
        subject_soup = subject_soup.stripped_strings
    body_soup = soup.find('section', {'id':'postingbody'}).stripped_strings
    subject_text = " ".join( [ text for text in subject_soup ] )
    body_text = " ".join( [text for text in body_soup ] )
    #
    # Main apt amenities extraction
    #apt_attrib = soup.find('p',{'class':'attrgroup'})   # apt attributes tag
    #attrib_list = [tag.get_text() for tag in apt_attrib.find_all('span')]
    #
    # Number of Bedrooms extraction
    #num_bd = int( attrib_list[0][0] )
    #
    # dictionary with apt data
    post['subject'] = subject_text  # subject line
    post['body'] = body_text    # posting body
    #post['attr'] = attrib_list,
    post['datetime'] = soup.find('time').attrs['datetime']
    return( post )


######
# Data pre-processing functions + initial
# NLP data collection
######

def process_posts( list ):
    map( add_neighborhood, list )
    map( clean_body, list )
    map( clean_subject, list )
    map( fee_no_fee, list )
    map( subject_fd, list )
    map( body_fd, list )
    return( list )

def clean_body( post ):
    """ cleans body text / adds key 'str_body' """
    str_body = post['body']
    # find words to be split (lowerUpper-case pairs)
    pairs = re.findall('[a-z][A-Z]', str_body )
    for pair in pairs:
        str_body = string.replace(str_body, pair, pair[0] + ' ' + pair[1] )
    # Convert body to lowercase
    str_body = str_body.lower()
    # translate via the Apt-rental dictionary
    for term in rad.keys():
        str_body = re.sub('[^a-zA-Z]'+term+ '[^a-zA-Z]', ' '+ rad[term] +' ', str_body )
    # remove all non-alphanumeric characters / extra spaces
    str_body = re.sub('[^a-zA-Z\s]'," ",str_body)
    str_body = re.sub(' +',' ', str_body)
    post['str_body'] = str_body
    return( post )

def clean_subject( post ):
    """ cleans subject text / adds new key 'str_subject' """
    str_subject = post['subject']
    # find words to be split (lowerUpper-case pairs)
    pairs = re.findall('[a-z][A-Z]', str_subject )
    for pair in pairs:
        str_subject = string.replace(str_subject, pair, pair[0] + ' ' + pair[1] )
    # Convert subject to lowercase
    str_subject = str_subject.lower()
    # translate via the Apt-rental dictionary
    for term in rad.keys():
        str_subject = re.sub('[^a-zA-Z]'+term+ '[^a-zA-Z]', ' '+ rad[term] +' ', str_subject )
    # remove (1) all non-alphanumeric characters
    # (2) the "bd" from the start of each post
    # (3) extra blank space
    str_subject = re.sub('[^a-zA-Z\s]'," ",str_subject) 
    str_subject = re.sub('[^a-zA-Z]'+'bd'+'[^a-zA-Z]'," ", str_subject)
    str_subject = re.sub(' +',' ', str_subject)
    post['str_subject'] = str_subject
    return( post )

def fee_no_fee( post ):
    """ outputs postings 'fee' or 'no_fee' for a post """
    url = post['source_url']
    if url.count('fee') != 0:
        fee = 'fee   '
    else:
        fee = 'no fee'
    post['fee'] = fee
    return( post )

def add_neighborhood( post ):
    """ Pulls neighborhood from the subject line """
    neighborhood = post['neighborhood'] + post['subject']
    if neighborhood is not None:
        # clean text: make lowercase / remove non-alphanumeric
        neighborhood = neighborhood.lower()
        neighborhood = re.sub('[^a-zA-Z\s]'," ", neighborhood )
        # match to neighborhood in list NBDS:
        (n1,n2) = (None,None)
        for nbd in NBDS:
            if nbd in neighborhood:
                n1 = nbd
                for sub_nbd in eval(nbd):
                    if sub_nbd in neighborhood:
                        n2 = sub_nbd
            else:
                for sub_nbd in eval(nbd):
                    if sub_nbd in neighborhood:
                        n1 = nbd
                        n2 = sub_nbd
    else:
        (n1,n2) = (None,None)
    post['neighborhood'] = (n1,n2)
    return( post )

def subject_fd( post ):
    """ obtain the frequency distribution of *words* of subject line of a post """
    tokens = nltk.word_tokenize( post['str_subject'] )
    fd = nltk.FreqDist( tokens  )
    post['fd_subject'] = fd
    return( post )

def body_fd( post ):
    """ obtain the frequency distribution of *bigrams* of body of a post """
    tokens = nltk.word_tokenize( post['str_body'] )
    fd = nltk.FreqDist( nltk.bigrams( tokens ) )
    post['fd_body'] = fd
    return( post )

#######
# Functions for constructing the training set metric
#######


def training_set():
    """ outputs 2 dictionaries in a dictionary:
    'sw' gives subject-word : weights
    'bw' gives body-bigram : weights """
    ts = get_training_posts()
    ts = process_posts( ts )
    sw = subject_weights( ts )
    bw = body_weights( ts )
    return( {'sub_wts' : sw, 'body_wts' : bw} )

def subject_weights( train_set ):
    """ collects the documents counts of each word
   in training set and weights each unique word. """
    N = float( len( train_set ) )
    L = []
    for post in train_set:
        L = L + post['fd_subject'].keys() 
    subject_counts = nltk.FreqDist(L)
    subject_wts = {}
    for word in subject_counts.keys():
        subject_wts[word] = math.log10( N / subject_counts[word] )
    return( subject_wts )

def body_weights( train_set ):
    """ collects the document counts of each bigram
    in training set and weights each unique bigram."""
    N = float( len( train_set ) )
    L = []
    for post in train_set:
        L = L + post['fd_body'].keys()
    body_counts = nltk.FreqDist(L)
    body_wts = {}
    for bigrm in body_counts.keys():
        body_wts[ bigrm ] = math.log10( N / body_counts[bigrm] )
    return( body_wts )

#######
# Functions for constructing dictionary of ranked posts
#######

def ranked_posts(train_set):
    """ outputs list of potential housing posts with
    ranks given by training set T.
    A list of dictionaries with keys given by:
    """
    pp = get_potential_posts()
    pp = process_posts( pp )
    for post in pp:
        s_rank = 0
        for word in post['fd_subject'].keys():
            s_words = train_set['sub_wts'].keys()
            if word in s_words:
                s_rank = s_rank + train_set['sub_wts'][word]
        post['s_rank'] = s_rank
        b_rank = 0
        for bgrm in post['fd_body'].keys():
            b_words = train_set['body_wts'].keys()
            if bgrm in b_words:
                b_rank = b_rank + train_set['body_wts'][bgrm]
        post['b_rank'] = b_rank
        post['rank'] = s_rank + b_rank
    sorted_pp = sorted( pp, key=lambda k: k['rank'] )
    sorted_pp = list( reversed( sorted_pp ) )
    return( sorted_pp )


#######
# HTML Output functions
#######

# title w/ number of bedrooms and price.
title = str(NUM_BEDS) + ' bedrooms listed under ' + str(PRICE)

# list of headers for the subject
HEADER = [ 'rank', 'price', 'neighborhood', 'fee/no fee', 'url' ]

def pretable( housing_list ):
    """ input list of potential housing,
    outputs a list of lists, to be made into
    an HTML table. """
    L = []
    for k in range( len( housing_list )):
        post = housing_list[k]
        N = [ nbd if nbd is not None else '' for nbd in post['neighborhood'] ]
        nbd_str = ': '.join( N )
        if post['price'] is None:
            P = ''
        else:
            P = post['price']
        url = '<a href=\"%(s)s\">%(s)s</a>' % {'s': post['source_url']}
        row = [str(k+1), P, nbd_str, post['fee'], url ]
        L = L + [row]
    return( L )

def table_to_HTML( L ):
    """ input a list of lists, outputs HTML table """
    yield '<table>'
    for row in L:
        yield '<head>'
        yield '<title>'+title+'</title>'
        yield '</head>'
        yield ' <tr><td>'
        yield '   </td><td>'.join( row )
        yield ' </td></tr>'
    yield '</table>'

def make_HTML_page( D ):
    """ inputs a list of housing posts,
    and generates an HTML page """
    T = [HEADER] + pretable( D )
    page = '\n'.join( table_to_HTML(T) )
    file = open( FILE_LOCATION, "w")
    file.write( page )
    file.close()
    
#####
# Executing the process
#####

T = training_set()
D = ranked_posts( T )
make_HTML_page( D )
