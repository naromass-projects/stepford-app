import os
import locale
os.environ["PYTHONIOENCODING"] = "utf-8"
myLocale=locale.setlocale(category=locale.LC_ALL, locale="en_GB.UTF-8")

from functools import wraps
import json
#import os
import re
import random
from os import environ as env
from werkzeug.exceptions import HTTPException
import time

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from flask import request
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from pprint import pprint, pp

import openai

import http.client

from flask_mongoalchemy import MongoAlchemy

from stepfordMongo import User, Review, Story, StorySegment,\
    ProcessedStorySegment, Conversion, scaffoldBasicContent


CORPUS_ROOT = "./../corpus"
subject_prefix = "Text: "
comment_prefix = "Comment: "

app = Flask(__name__)
app.secret_key = "we hate complex secret keys, actually"
import admin # pull in the admin sections

# mongoalchemy

app.config['MONGOALCHEMY_DATABASE'] = 'stepford'
app.config['MONGOALCHEMY_SERVER_AUTH'] = False
app.config['MONGOALCHEMY_SAFE_SESSION'] = True
app.config['DEBUG'] = False
db = MongoAlchemy(app)

# is the default story there? (remove after bootstrapping)
with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
    story1 = s.query(Story).filter(Story.story_id == 1).first()
    if story1 is None:
        (story1,
         story_segment1,
         conversion1,
         processed_story_segment1) = scaffoldBasicContent(s)

oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id='CHANGE',
    client_secret='CHANGE',
    api_base_url='https://CHANGE.auth0.com',
    access_token_url='https://CHANGE.auth0.com/oauth/token',
    authorize_url='https://CHANGE.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    }
)


# horror show for auth0 authentication
from six.moves.urllib.request import urlopen

from flask import _request_ctx_stack
from flask_cors import cross_origin

AUTH0_DOMAIN = 'CHANGE.auth0.com'
API_AUDIENCE = 'admin:corpus-management'
ALGORITHMS = ["RS256"]

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                            "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must be"
                            " Bearer token"}, 401)

    token = parts[1]
    return token

def requires_scope(required_scope):
    """Determines if the required scope is present in the Access Token
    Args:
        required_scope (str): The scope required to access the resource
    """
    token = get_token_auth_header()
    unverified_claims = jwt.get_unverified_claims(token)
    if unverified_claims.get("scope"):
            token_scopes = unverified_claims["scope"].split()
            for token_scope in token_scopes:
                if token_scope == required_scope:
                    return True
    return False



# /server.py routes

# Here we're using the /callback route.
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')

# /server.py - Trigger Authentication

@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri='https://app.algowritten.org/callback')

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      #return redirect('/')
      return redirect('/home')
    return f(*args, **kwargs)

  return decorated

# /server.py - Display User Info, depends on above requires_auth decorator

@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           jwt_pretty=json.dumps(session['jwt_payload'], indent=4),
                           profile_pretty=json.dumps(session['profile'],indent=4),
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))

@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('home', _external=True), 'client_id': 'CHANGE ME'}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/')
def home():
    #return ("You probably want to <a href='/login'>login</a> mate")
    return render_template('home.html')


@app.route('/review')
@app.route('/review/')
@app.route('/review/<int:review_id>')
@requires_auth
def review(review_id=-1):
    all_texts = get_total_parsed_texts_review()
    completed_reviews = get_review_segment_ids_by_userid(session['profile']['user_id'])
    if(review_id == -1):
        candidate_texts=get_unreviewed_text_ids(all_texts, completed_reviews)
        if len(candidate_texts)>0:
          review_id = random.choice(candidate_texts)
        if len(candidate_texts)==0:
          return render_template('thanksforreview.html',
           title="Thank you",
           subtitle="You have reviewed all our current texts.",
           error="All texts have been reviewed.")

    try:
        processedstorysegment = get_text(review_id)
        story_segment = parse_story_segment(processedstorysegment.processed_text)
        return render_template('review.html',
                               ss=story_segment,
                               question_limit = min(3,len(story_segment["questions"])),
                               full_text=processedstorysegment.story_segment.text,
                               title=processedstorysegment.story_segment.story.title,
                               author=processedstorysegment.story_segment.story.author,
                               parsed_story_segment_id=review_id,
                               preview=False,
                               total_texts=str(len(all_texts)),
                               completed_reviews=len(completed_reviews))
    except KeyError as e:
      print("KeyError in /review:")
      pprint(e)
      print(f"title: {processedstorysegment.story_segment.story.title} ")
      print(f"processedstorysegment ID: {review_id} ")
      return render_template('review-error.html',
                            title="Oops",
                            subtitle="There was an internal KeyError.",
                            error="(<tt>"+str(e)+f"</tt>, review_id is <b><tt>{ str(review_id) }</tt></b>, title is <i><b>{ processedstorysegment.story_segment.story.title}</b></i>)"
    )
    except Exception as e:
        print("Exception in /review:")
        pprint(e)
        return render_template('review-error.html',
                              title="Oops",
                              subtitle=f"There was an internal error we didn't anticipate. Apologies. We've logged the problem and will look into it (review_id is { str(review_id) }).",
                              error=str(e)
        )


@app.route("/thanksforreview")
@requires_auth
def thanks_for_review():
    return render_template('thanksforreview.html')

@app.route('/admin/corpus')
@requires_auth
def corpus():
    """This route shows a list of files in the two CORPUS_ROOT subdirectories"""
    new_items = get_textfiles(CORPUS_ROOT+"/unprocessed/")
    old_items = get_textfiles(CORPUS_ROOT+"/processed/")
    return render_template('admin/corpus.html',
                           new=new_items,
                           old=old_items)


@app.route('/admin/corpus/choose_conversion/', methods = ['POST'])
@requires_auth
def corpus_choose_conversion():
    """This route previews the story segments in a file and asks for a conversion type"""
    file_requested = request.form["textfile"]
    (file_path, file_name) = file_requested.split(";;;")
    story_data = parse_story_file(CORPUS_ROOT+"/"+file_path+"/", file_name)
    conversion_labels = get_conversion_labels()
    return render_template('admin/choose_conversion.html',
                           conversions=conversion_labels,
                           processing_status=file_path,
                           textfile=file_requested,
                           story=story_data)


def get_conversion_labels():
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        conversions = s.query(Conversion).all()
        conversion_labels = (conversion.label for conversion in conversions)
        return conversion_labels
    return []

def get_conversions():
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        return s.query(Conversion).all()
    return []

def save_conversion_parameters(conversion):
    """Inserts a new Conversion document"""
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
      s.insert(Conversion(**conversion))

def update_conversion_parameters(original_label, conversion):
    """Updates an existing Conversion document"""
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:  
      old_conversion = s.query(Conversion).filter(
        Conversion.label == original_label ).set(**conversion)
      if old_conversion:
        old_conversion.execute()
      else:
        print("ERROR - COULD NOT FIND ",conversion.get('label')," TO UPDATE IN server::update_conversion_parameters")
        

@app.route('/admin/corpus/handle_processing/', methods=['POST'])
def corpus_handle_processing():
    """deliver the main template for watching processing take place"""
    apikey = request.form["apikey"]
    file_requested = request.form["textfile"]
    conversion_label = request.form["conversion"]
    (file_path, file_name) = file_requested.split(";;;")
    story_data = parse_story_file(CORPUS_ROOT+"/"+file_path+"/", file_name)
    conversion = get_conversion_parameters(conversion_label)
    return render_template('admin/watch_processing.html',
                           processing_status=file_path,
                           conversion_label=conversion_label,
                           textfile=file_requested,
                           story=story_data,
                           apikey=apikey,
                           conversion=conversion)


@app.route('/admin/api/sendForProcessing', methods=['POST','GET'])
def corpus_send_for_processing():
    """JSON API endpoint to be told to send something to openai"""
    if 1==0: #request.method=='GET':
        # this is for debugging! hardcode those values
        file_requested = 'unprocessed;;;banks_useofweapons.txt'
        conversion_label = 'GPT-3-default'
        segmentno = 1
        apikey = 'fakekey'
    else:
        json_params = request.get_json(force=True)
        file_requested = json_params["textfile"]
        conversion_label = json_params["conversion_label"]
        segmentno = json_params["segmentno"]
        apikey = json_params["apikey"]

    print("=====--\nSEND FOR PROCESSING\n---=====")

    (file_path, file_name) = file_requested.split(";;;")
    story_data = parse_story_file(CORPUS_ROOT+"/"+file_path+"/", file_name)
    # insert/update the story and segment tables
    (story,segments,
     segment_documents) = upsert_story(title=story_data["title"],
                                       author=story_data["author"],
                                       text=story_data["text"],
                                       possible_segments=story_data["segments"])

    processed_text = process_text_via_openai(conversion_label,
        story_data["segments"][int(segmentno)], apikey)

    print("\n==================================\n")
    print(story_data)
    print("---became--------------------------\n")
    pprint(processed_text)
    print("==================================\n\n\n")

    this_processed_segment = upsert_processed_segment(
        conversion_label = conversion_label,
        story=story,
        title = story_data["title"],
        segments = segment_documents,
        segmentno = segmentno,
        text=story_data["text"]+"§§\n"+processed_text["choices"][0]["text"]
    )
    
    return jsonify(processed_text)


@app.route('/admin/api/make_segments_live', methods=['POST'])
def corpus_segments_live():
    """get the list of processedstorysegments we have to make live"""
    file_requested = request.form["textfile"]

    (file_path, file_name) = file_requested.split(";;;")
    story_data = parse_story_file(CORPUS_ROOT+"/"+file_path+"/", file_name)
    segments=list(map(int, request.form.getlist("segments")))
    #print("Asked to make live the following segments:")
    #pprint(segments)
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        for segment_id in segments:
            processedsegment=s.query(ProcessedStorySegment).filter(
                ProcessedStorySegment.story_segment.story.title == story_data["title"],
                ProcessedStorySegment.story_segment.story_segment_id == segment_id
            ).first()
            if processedsegment:
                processedsegment.live = True
                s.save(processedsegment)
                s.flush()
        s.flush()
    return render_template('admin/make_segments_live.html')


@app.route('/api/submitreview', methods=['POST'] )
@requires_auth
def submit_results():
    #print( session.keys() )
    if 1 ==1: # 'profile' in session.keys():
        scores = (request.values.getlist("reviews[]"))
        comments = (request.values.getlist("comments[]"))
        observations = (request.values.getlist('observations[]'))
        processed_story_segment_id = request.values.get('processed_story_segment_id')
        version = request.values.get('version')
        with db.session.connect( app.config['MONGOALCHEMY_DATABASE']) as s:
            processed_story_segment = s.query(ProcessedStorySegment).filter(
                ProcessedStorySegment.processed_story_segment_id == int(processed_story_segment_id)).first()
            s.insert(
                Review(
                   user=session['profile']['user_id'],
                   processed_story_segment=processed_story_segment,
                   live=True,
                   observations=observations,
                   comments=comments,
                   scores=scores
                )
            )
            s.flush()
        return("okay")
    else:
        return("not signed in!")


@app.before_request
def before_profile_stuff():
    return

def upsert_story(title="", author="", text="", possible_segments=[]):
    """update/create a story, potentially creating story segments and processed story segments as needed (possbile_segments is a list of strings of text)"""
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        # is this story already in the DB?
        story = s.query(Story).filter(Story.title == title).first()
        if story:
            pass
        else:
            #this is a new story - how many are in there already?
            story_count = s.query(Story).count()
            story = create_story_object(title=title,
                                        author=author,
                                        text=text,
                                        revision=0,
                                        story_id=story_count + 1)
            s.insert(story, safe=True)
            s.flush()
        #print("story is a now id: ",story.story_id,", ", story.title)
        s.flush()

        #add the segments - these are currently raw text in possible_segments[]

        segment_count = 0
        new_segments = []
        for segment in possible_segments:
            segment_count+=1
            new_segment = s.query(StorySegment).filter(
                StorySegment.story.story_id == story.story_id,
                StorySegment.story_segment_id == segment_count
            ).first()
            if new_segment is None:
                new_segment = StorySegment(story_segment_id=segment_count,
                                           story=story,
                                           text=segment,
                                           live=False,
                                           revision=0)
                s.insert(new_segment)
                s.flush()
            else:
                pass

            new_segments.append(new_segment)

        #return the object we just inserted
        s.flush()
        return(story, possible_segments, new_segments)


def upsert_processed_segment(conversion_label="",
                             title="",
                             segments=[],
                             segmentno=-1,
                             story=None,
                             text=""):
    try:
        with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as new_sesh:
            #print("CONVERSION LABE:", conversion_label)
            #print("SEGMENTNO:", segmentno)
            conversion = s.query(Conversion).filter(
                Conversion.label == conversion_label
            ).first()

            # find if there's a processed story segment with a story segment id matching this
            processed_story_segment = new_sesh.query(ProcessedStorySegment).filter(
                ProcessedStorySegment.story_segment.story.title == title,
                ProcessedStorySegment.story_segment.story_segment_id == segmentno+1
            ).first()

            inserted_text = "\STORY SEGMENT: "+segments[segmentno].text,

            if processed_story_segment is None:
                total_processed_segments = new_sesh.query(ProcessedStorySegment).count()

                processed_story_segment = ProcessedStorySegment(
                    processed_story_segment_id = total_processed_segments+1,
                    story_segment = segments[segmentno],
                    processed_text = text,
                    conversion = conversion,
                    revision = 0,
                    live = False)
                #pprint(processed_story_segment)
                new_sesh.insert(processed_story_segment)
                new_sesh.flush()
            else:

                processed_story_segment.processed_text = text
                processed_story_segment.conversion = conversion
                processed_story_segment.story_segment = segments[segmentno]
                processed_story_segment.processed_text = text
                new_sesh.save(processed_story_segment)
                new_sesh.flush()
    except AttributeError:
        pp(processed_story_segment)
    finally:
        new_sesh.flush()
        segmentno = segmentno + 1


def get_textfiles(dir_path):
    files = []
    file_list = [textfile for textfile in os.listdir(path=dir_path) if textfile.endswith(".txt")]
    for textfile in file_list:
        story_metadata = parse_story_file(dir_path, textfile)
        files.append(story_metadata)
    return(files)

def parse_story_file( file_path, file_name ):
    transl_table = dict( [ (ord(x), ord(y)) for x,y in zip( u"‘’´“”–-",  u"'''\"\"--") ] ) # via https://stackoverflow.com/a/41516221/203472
    with open(file_path+file_name,mode="r", encoding="utf-8") as f:
        status = ""
        contents = f.readlines()
        extracted_text = "\n".join(contents)

        finished_headers = False;
        extracted_title = extracted_author = None;
        segments = -1;
        extracted_segments = []
        current_segment = []

        try:
            while(finished_headers == False):
                line = contents[0].rstrip()
                contents = contents[1:]
                """line = contents.pop().rstrip()"""
                if(line == "***"):
                    finished_headers = True;
                    continue
                try:
                    title_match = re.search(r'[.]*title:\s*(.+)\s*',
                                            line, re.I | re.S)
                    extracted_title = title_match[1]
                except (TypeError, ValueError):
                    pass
                try:
                    author_match = re.search(r'[.]*author:\s*(.+)\s*',
                                             line, re.I | re.S)
                    extracted_author = author_match[1]
                except (TypeError, ValueError):
                    pass


            # count segments
            #try:
            for line in contents:
                ln = line.translate(transl_table)
                if(ln.rstrip() == "***"):
                    extracted_segments.append("\n".join(current_segment) )
                    current_segment = []
                else:
                    current_segment.append(ln)
        except IndexError:
            status = "bad"
        if(extracted_title is None) or (extracted_author is None):
            status = "bad"
        else:
            if status != "bad":
                status = "ok"

        if(len(extracted_segments) < 1):
            status="bad"

        return({"author": extracted_author,
                "title": extracted_title,
                "name": file_name,
                "path": file_path,
                "text": extracted_text,
                "segments": extracted_segments,
                "status": status})


def get_total_parsed_texts_review():
    """
    Returns a list of processed_story_segment_ids
    """
    all_live = s.query(ProcessedStorySegment).filter(
        ProcessedStorySegment.live==True
    ).all()
    all_ids = [document.processed_story_segment_id for document in all_live]
    return all_ids


def get_review_segment_ids_by_userid(userid):
    """
    Given a user ID, returns a list of processed_story_segment_ids they
    have already reviewed
    """
    done_reviews = s.query(Review).filter(
        Review.user == userid
    ).distinct(Review.processed_story_segment.processed_story_segment_id)
    return done_reviews #review_segment_ids

def get_conversion_parameters(conversion_label, parameters_only=True):
    """Given a conversion label string, returns an unpacked version of the JSON text from the database as a dictionary"""
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        q = s.query(Conversion).filter(Conversion.label == conversion_label)
        q.raw_output()
        conversion = q.first()
        try:
            if(parameters_only == True):
                #return(json.loads(conversion.parameters, strict=False))
                if "parameters" in conversion:
                  return(conversion.parameters)
                else: 
                  pprint("problem getting conversion.parameters, conversion:",conversion)
                  return({})
            else:
                #return(json.loads(conversion, strict=False))
                return(conversion)
        except json.decoder.JSONDecodeError:
            return({})
        except AttributeError:
            print("-----")
            print("server:get_conversion_parameters(",conversion_label,",",parameters_only,")")
            pprint(conversion)
            print("-----<")

def get_text(id=None):
    """given a id(int), returns a processed story segment object.
    raises a generic exception if there is no matching id."""
    with db.session.connect(app.config['MONGOALCHEMY_DATABASE']) as s:
        processed_story_segment = s.query(ProcessedStorySegment).filter(ProcessedStorySegment.processed_story_segment_id == int(id)).first()
        if(processed_story_segment == None):
            raise("No matching procssed story segment with id of "+str(id))
        return(processed_story_segment)


def get_unreviewed_text_ids(text_ids, reviewed_ids):
    """
    Given a complete list of texts and a list of text IDs reviewed by the user,
    pick an unreviewed item 
    """
    return(list(set(text_ids).difference(set(reviewed_ids))))


def process_text_via_openai(conversion_label, text, apikey):
    #return {"choices":[{'text':'THIS IS DUMMY TEXT WHILST DEBUGGING'}]}
    #print("!!!! CONVERSION: Sending \"",text,"\"")
    conversion_full = get_conversion_parameters(conversion_label, parameters_only=False)
    conversion = json.loads(conversion_full['parameters'])
    openai.api_key = apikey
    x = conversion["prompt"] = re.sub(re.escape(conversion_full["replacement"]), text, conversion["prompt"], flags=re.A)
    if "max_tokens" in conversion:
      conversion["max_tokens"]=int(conversion["max_tokens"])
    if "n" in conversion:
      conversion["n"]=int(conversion["n"])
    if "best_of" in conversion:
      conversion["best_of"]=int(conversion["best_of"])
    y = openai.Completion.create(**conversion)
    return(y)


def create_story_object(title="", author="", text="", story_id=0, revision=0):
    new_story = Story(title=title,
                      author=author,
                      text=text,
                      story_id=story_id,
                      revision=revision)
    return new_story

def parse_story_segment(text):
    question = {}
    questions = []
    segment = (text.split("§§"))
    d={}
    for o in segment[-1].split("\n"):
        if o.startswith("§§"):
            continue
        elif o.startswith(subject_prefix):
            question["subject"]=o
        elif o.startswith(comment_prefix):
            question["comment"]=o
            questions.append(question)
            question = {}
            storysegment =  segment[0].split("STORY SEGMENT: ")[-1].split("**")[0]
            d = { "title":"dummytitle", 
                  "story":storysegment, 
                  "questions":questions }
    return d



