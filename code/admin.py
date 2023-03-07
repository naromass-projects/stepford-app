from server import app
import server

import json

from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import url_for
from flask import request
from flask_mongoalchemy import MongoAlchemy

from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, DecimalField, IntegerField, IntegerRangeField, URLField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, InputRequired, NumberRange, NoneOf

from stepfordMongo import User, Review, Story, StorySegment, \
    ProcessedStorySegment, Conversion, scaffoldBasicContent

from beeprint import pp

ConversionFormTooltips = {
    # logit_bias, stream, user:  skipped
    'label':['The name used for this converter (must be unique)','',False],
    'uri':['HTTP endpoint for processor; leave blank for openAI','',False],
    'replacement':['The string to be replaced in the template','',False],

    'engine':['OpenAI engine to use: currently only davinci supported','',True],
    'best_of':['How many completions to generate before picking the best','https://beta.openai.com/docs/api-reference/completions/create#completions/create-best_of',True],
    'temperature':['Sampling temperature: 0=safe answers, .9=creative, default=1 (use only this or top_p, not both)','https://beta.openai.com/docs/api-reference/completions/create#completions/create-temperature',True],
    'max_tokens':['How many tokens to consume for response: default=16','https://beta.openai.com/docs/api-reference/completions/create#completions/create-max_tokens',True],
    'top_p':['Nucleus sampling: .1=only draw from top 10% of tokens, default=1 (use only this or temperature, not both)','https://beta.openai.com/docs/api-reference/completions/create#completions/create-top_p',True],
    'n':['Number of completions to generate: default=1','https://beta.openai.com/docs/api-reference/completions/create#completions/create-n',True],
    'presence_penalty':['Positive values increase likelihood of new topic discussion: -2.0 to 2.0','https://beta.openai.com/docs/api-reference/completions/create#completions/create-presence_penalty',True],
    'frequency_penalty':['Positive values reduce likelihook of repeating text verbatim, -2.0 to 2.0','https://beta.openai.com/docs/api-reference/completions/create#completions/create-frequency_penalty',True],
    'prompt':['Must contain Replacement String','https://beta.openai.com/docs/api-reference/completions/create#completions/create-prompt',True],
    'stop':['A single string marking the point to stop generating more tokens','https://beta.openai.com/docs/api-reference/completions/create#completions/create-stop',True],
    'notes':['Freeform notes about this converter (optional)','', False],
    'rating':['Quality rating about this converer, 1-5 (think stars)','', False],
    'locked':['Turn on to prevent this converter from being editable.','', False]
}

class ConversionForm(FlaskForm):
        
    original_label = HiddenField('original_label',[])
    label = StringField('Label',
                        [InputRequired(), Length(max=10)])
    uri = HiddenField('URI', []) # was StringField, but not using for now
    replacement = StringField('Replacement String',
                              [InputRequired()])
    #--- the following need to be repackaged from/to the json property 'parameters'
    engine = HiddenField('engine')
    #best_of =IntegerRangeField('Best Of')
    best_of =DecimalField('Best Of',
                [InputRequired(),NumberRange(min=1, max=3)])  
    temperature = DecimalField('Temperature',
                               [InputRequired()], places=1)
    max_tokens = IntegerField('Max Tokens',
                                   [NumberRange(min=1, max=4096)])
    top_p = DecimalField('top_p',
                         [NumberRange(min=0.0, max=1.0)],
                         places=2,)
    n = IntegerField('n',
                     [NumberRange(min=1, max=10)])
    presence_penalty = DecimalField('presence_penalty',
                                    [NumberRange(min=-2.0, max=2.0)])
    frequency_penalty = DecimalField('frequency_penalty',
                                     [NumberRange(min=-2.0, max=2.0)])
    prompt = TextAreaField('prompt',
                           [InputRequired()])
    #prompt = TextAreaField('prompt',
    #                          [InputRequired(), ContainsField(field=replacement,#message="Must contain text of 'Replacement String'")])
    stop = StringField('Stop',
                       [InputRequired()])

    notes = StringField('notes',[])
    rating = IntegerField('rating',[NumberRange(min=1,max=5)])
    locked = BooleanField('locked',[])

    submit = SubmitField(label=('Save'))
    new = SubmitField(label=('Create New'))
    

                
    """
    _id
    label
    uri
    replacement
    parameters:
    { "engine" : "davinci",
      "best_of": 2,
      "temperature" : 0.6,
      "max_tokens" : 269,
      "top_p" : 1.0,
      "frequency_penalty" : 0.0,
      "presence_penalty" : 0.0,
      "stop" : [ "###" ],
      "prompt" : "This ..." }
"""

@app.route('/admin')
def admin():
    """Static page for handling overview of admin functions and provide an entry point"""
    return render_template('admin/index.html')


@app.route('/admin/conversion')
def admin_conversions():
    """This route shows a list of conversions in the DB"""
    conversions = server.get_conversions()
    return render_template('admin/conversion/list_conversions.html',
                           conversions=conversions)


@app.context_processor
def utility_processor():
    def tooltipise(item):
        if item in ConversionFormTooltips:
            tt='<span class="tip">'
            if ConversionFormTooltips[item][1] != "":
                return f'<span class="tip">{ConversionFormTooltips[item][0]}<a href="{ConversionFormTooltips[item][1]}" target="stepfordOpenAIDocs">📖</a></span>'
            else:
                return f'<span class="tip">{ConversionFormTooltips[item][0]}</span>'
    return dict(tooltipise=tooltipise)


@app.route('/admin/conversion/', methods=['GET', 'POST'])
def admin_conversion_edit():
    """This route is for editing or creating conversions. It recovers the record from the DB (if a label is supplied) and populates a form with any properties recovered."""
    """`clone_converter` items are duplicated from an existing item - this can fail if 'new' is selected"""
    conversion_elements = {}
    update_not_insert = False
    make_new = False
                    
    if( request.method=="GET"):
        label = request.args.get('label', default="")
        original_label = request.args.get("label", default=None)
        go_save = False
    else:
        label = request.form.get('label', default="")
        original_label = request.form.get('original_label',None)
        go_save = request.form.get("submit", None)

    if go_save:
        # is this an update or insert?
        update_not_insert = False
        if(request.form.get('original_label',None)!=None):
            update_not_insert = True

    if request.form.get("submit", False):
        make_new=False
        
    if request.form.get("new", False):
        make_new=True
        update_not_insert = False


    
    validation_form = ConversionForm(request.form)
    existing_labels = list(server.get_conversion_labels() )
    if(make_new == True):
        validation_form.label.validators.append(NoneOf(existing_labels,
            message = "This label is already in use."
        ))    
        if validation_form.validate()==False:
            return render_template('admin/conversion/conversion_edit.html',
                   form=validation_form,
                   conversion_id=label,
                   conversion_elements=conversion_elements,
                   tooltips=ConversionFormTooltips,
                   original_label=original_label
               )

        
    #if request.form.get('label', None) is not None:
    if request.method == "POST":
        conversion_elements = dict(request.form)
        if make_new == False:
            existing_labels[:]=[label for label in existing_labels if label is not original_label ]           
            validation_form.label.validators.append(NoneOf(existing_labels,
                message = "This label is already in use."
            ))    
            if validation_form.validate()==False:
                return render_template('admin/conversion/conversion_edit.html',
                       form=validation_form,
                       conversion_id=label,
                       conversion_elements=conversion_elements,
                       tooltips=ConversionFormTooltips,
                       original_label=original_label
                   )

            
            locked = bool(request.form.get('locked',False))
            
            pre_json_parameters = {}
            try:
                del conversion_elements['csrf_token']
                del conversion_elements['submit']
                del conversion_elements['new']
            except:
                pass
            for i in ConversionFormTooltips:
                if ConversionFormTooltips[i][2]==True:
                    # try avoid storing numbers as strings....
                    try:
                        pre_json_parameters[i] = float(conversion_elements[i])
                    except:
                        pre_json_parameters[i] = conversion_elements[i]
                    del conversion_elements[i]
            # we need to reconstruct the parameters string property
            pre_json_parameters['stop'] = [pre_json_parameters['stop']]                    
            conversion_elements['parameters'] =  json.dumps(pre_json_parameters)
            try:
                conversion_elements['rating'] = int(conversion_elements.get('rating',0))
            except ValueError:
                conversion_elements['rating'] = 0
            conversion_elements['uri'] = ''
            del(conversion_elements['original_label'])
            pp(conversion_elements)
            
            if update_not_insert:
                server.update_conversion_parameters(original_label, conversion_elements)
            else:
                server.save_conversion_parameters(conversion_elements)
            return redirect(url_for('admin_conversions'))
        else:
            try:
                if "parameters" in conversion_elements:
                    try:
                        new_parameters = json.loads(conversion_elements['parameters'])
                    except json.decoder.JSONDecodeError:
                        pass
                    conversion_elements.update(new_parameters)
                    
                for i in conversion_elements:
                    try:
                        conversion_elements[i] = float(conversion_elements[i])
                    except:
                        pass
                conversion_elements['rating']=int(conversion_elements['rating'])
                conversion_elements = {i:conversion_elements[i] for i in conversion_elements if i not in ('csrf_token','submit','new','original_label')}
                conversion_elements['uri'] = ''
                conversion_elements['engine'] = 'davinci'
                pre_json_parameters = {}
                for i in ConversionFormTooltips:
                    if ConversionFormTooltips[i][2]==True:
                        try:
                            pre_json_parameters[i] = float(conversion_elements[i])
                        except:
                            pre_json_parameters[i] = conversion_elements[i]
                        del conversion_elements[i]
                conversion_elements['parameters'] =  json.dumps(pre_json_parameters)
                
                server.save_conversion_parameters(conversion_elements)
                # return to index to avoid renaming madness
                return redirect(url_for('admin_conversions'))                        
            except TypeError:
                pass
                #print("conversion_elements is a NoneType")
    
    # populate the form instead
    conversion_elements = server.get_conversion_parameters(original_label, parameters_only=False)
    conversion_elements['original_label']=request.form.get('label', default=label)
    # unpackage JSON parameters, if needed
    if "parameters" in conversion_elements:
        try:
            new_parameters = json.loads(conversion_elements['parameters'])
            conversion_elements.update(new_parameters)
        except json.decoder.JSONDecodeError:
            pass
        
    for i in conversion_elements:
        try:
            conversion_elements[i] = float(conversion_elements[i])
        except:
            pass
    conversion_elements['rating']=int(conversion_elements['rating'])
    # dance around 'stop' being a list for saving, string for printing
    if isinstance(conversion_elements['stop'], list):
        conversion_elements['stop']=conversion_elements['stop'][0]

    #existing_labels = list(server.get_conversion_labels() )

    form = ConversionForm(request.form, **conversion_elements)

    # wtforms checkbox fixing courtesy of https://stackoverflow.com/a/29907194
    return render_template('admin/conversion/conversion_edit.html',
                           form=form,
                           conversion_id=label,
                           conversion_elements=conversion_elements,
                           tooltips=ConversionFormTooltips,
                           original_label=label
                       )



