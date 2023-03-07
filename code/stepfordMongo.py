"""
StepfordMongo

class definitions for mongoalchemy to use with the Algowritten Stepford project and mongo database store
"""

#from __main__ import db # get us a mongo handle
#from db import Document

from mongoalchemy.session import Session
from mongoalchemy.document import Document, Index
from mongoalchemy.fields import *
from datetime import datetime

class User(Document):
    name = StringField()
    skipped = BoolField(required=False, default=False)

    #i_name = Index().ascending('name').unique()
    #i_skipped = Index().ascending('skipped')


class Story(Document):
    title = StringField()
    author = StringField()
    text = StringField()
    story_id = IntField()
    live = BoolField(required=False,default=False)
    created = CreatedField()
    modified = ModifiedField()
    revision = IntField()

    #i_id = Index().ascending('story_id').unique()
    #i_title = Index().ascending('title').unique()

class StorySegment(Document):
    story_segment_id = IntField()
    story = DocumentField(Story)
    text = StringField()
    live = BoolField()
    created = CreatedField()
    modified = ModifiedField()
    revision = IntField(required=False, default=1)

    #i_id = Index().ascending('story_segment_id')


class Conversion(Document):
    label = StringField()
    uri = StringField()
    replacement = StringField()
    parameters = StringField()
    created = CreatedField()
    modified = ModifiedField()

    type = StringField(required=False, default="")

    notes = StringField(required=False, default="")
    rating = IntField(required=False, default=0)
    locked = BoolField(required=False, default=False)


class ProcessedStorySegment(Document):
    processed_story_segment_id = IntField()
    story_segment = DocumentField(StorySegment)
    processed_text = StringField()
    conversion = DocumentField(Conversion)
    live = BoolField(required=False,default=False)
    created = CreatedField()
    modified = ModifiedField()
    revision = IntField()

    #i_title = Index().ascending('processed_story_segment_id').unique()


class Review(Document):
    user = StringField()
    processed_story_segment = DocumentField(ProcessedStorySegment)
    live = BoolField(required=False, default=False)
    created = CreatedField()
    modified = ModifiedField()
    observations = ListField(StringField())
    comments = ListField(StringField())
    scores = ListField(StringField())

#####

def scaffoldBasicContent(s):
    story1 = Story( title="Test Story", author = "Bob Robot", text = """
STORY SEGMENT: You are a woman in a man's world. You have just gotten a job as a construction worker, something that is unheard of. You say,"Why don't women usually get jobs as construction workers?"
"Well, women usually don't want to get their hands dirty." The boss says dismissively.** SEXIST TEXT & COMMENT:
Text: "You are a woman in a man's world."
Comment: Suggests there is a whole world where women have no place.
Text: "You have just gotten a job as a construction worker, something that is unheard of."
Comment: States that female construction workers are very uncommon. Which is based on a sexist stereotype.
Text: "Well, women usually don't want to get their hands dirty."
Comment: Based on an unprovable generalisation.
###
""", story_id=1, live=True, revision=1)
    s.insert(story1)

    story_segment1 = s.query(StorySegment).filter(StorySegment.story_segment_id==1).first()
    if story_segment1 == None:
        story_segment1 = StorySegment( story_segment_id = 1, story = story1, text = """
STORY SEGMENT: You are a woman in a man's world. You have just gotten a job as a construction worker, something that is unheard of. You say,"Why don't women usually get jobs as construction workers?"
"Well, women usually don't want to get their hands dirty." The boss says dismissively.** SEXIST TEXT & COMMENT:
Text: "You are a woman in a man's world."
Comment: Suggests there is a whole world where women have no place.
Text: "You have just gotten a job as a construction worker, something that is unheard of."
Comment: States that female construction workers are very uncommon. Which is based on a sexist stereotype.
Text: "Well, women usually don't want to get their hands dirty."
Comment: Based on an unprovable generalisation.
###
""", live=True)
        s.insert(story_segment1)
    conversion1 = s.query(Conversion).filter(Conversion.label=="none").first()
    if conversion1==None:
        conversion1 = Conversion(label="none",
                                 uri="",
                                 parameters="",
                                 replacement="",
                                 type="fake")
        s.insert(conversion1)

    processed_story_segment1 = s.query(ProcessedStorySegment).filter(ProcessedStorySegment.story_segment==story_segment1).first()
    if processed_story_segment1 == None:
        processed_story_segment1 = ProcessedStorySegment( processed_story_segment_id = 1, story_segment = story_segment1, processed_text = """
STORY SEGMENT: You are a woman in a man's world. You have just gotten a job as a construction worker, something that is unheard of. You say,"Why don't women usually get jobs as construction workers?"
"Well, women usually don't want to get their hands dirty." The boss says dismissively.** SEXIST TEXT & COMMENT:
Text: "You are a woman in a man's world."
Comment: Suggests there is a whole world where women have no place.
Text: "You have just gotten a job as a construction worker, something that is unheard of."
Comment: States that female construction workers are very uncommon. Which is based on a sexist stereotype.
Text: "Well, women usually don't want to get their hands dirty."
Comment: Based on an unprovable generalisation.
###
""", conversion = conversion1, live = True, revision = 1)
        s.insert(processed_story_segment1)

    s.flush() # ensure it's all pushed in there!

    return(story1, story_segment1, conversion1, processed_story_segment1)

