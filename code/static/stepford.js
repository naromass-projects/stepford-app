_internal_version = "v 1.3.5";
console.log(_internal_version);


//////////
var question = 0;
var slideDuration = 500;
var results = [];
var awaitingResponses = 0;
var cleaningRE = /([\s\W])+/;

$(function() {
  // slice and dice the text segments
  sliceAndDiceThrice();

  // does this page have questions we need to activate?
  if ($(".commentobservationpair").length > 0) {

    // bind the titles to gotoQuestion() events
    $(".commentobservationpair>div.comment").on("click",function(e){
      var newQuestion = parseInt( $(this).parent().attr("id").substr(1) )-1;
      gotoQuestion( newQuestion );
    });

    // click to bind left-clicks to right questions
    $($("p#parsedtext>span.highlight")).bind('click',function(x){ 
        gotoQuestion( $("p#parsedtext>span.highlight").index(x.target))
    } ); 

    // visually conceal the other buttons
    $(".commentobservationpair").eq(question).slideDown(slideDuration).finish().parent().siblings().find(".suggests").slideUp(slideDuration).finish();

    // hovering a caption makes corresponding one highlight
    $("div.comment>span.commenttext").hover( // rhs
      function(){
        $("span.highlight.highlight"+($(this).parent().parent().attr('id').slice(1) ) ).addClass("hoveractive");
      },
      function(){
        $("span.highlight.highlight"+($(this).parent().parent().attr('id').slice(1) ) ).removeClass("hoveractive");
      }
    );
    $("p#parsedtext>span.highlight").hover( // lhs
      function(){
        $("#q"+ String($(this).index()) ).children(".comment").children(".commenttext").addClass("hoveractive");
      },
      function(){
        $("#q"+ String($(this).index()) ).children(".comment").children(".commenttext").removeClass("hoveractive");
      }
    );

    // questions always have a next button
    $("button#next").on("click", function (event) {
      //console.log("button#next: click = ",event);
      if(event.type=="keydown") {
        event.preventDefault();
        e.stopPropagation();
    	e.stopImmediatePropagation();
        reevaluateNexity();
      }
      //console.log("event", e);
      //console.log("results.length is ",results.length);
      //console.log("object.values(results).length is ", Object.values(results).length);
      if (Object.values(results).length == $(".commentobservationpair").length) {
        // submit the data!
        postData(results);
      } else {
        // find the first unanswered question, looping around, from here
        question = question + 1;
        if(question>=$(".commentobservationpair").length) {
          // find the first unanswered question
          for(var i=0; i<$(".commentobservationpair").length; i++) {
            if (Number.isInteger(results[i])==false) {
              //console.log("off to question ",i," instead!");
              question = i;
              gotoQuestion( i );
              break;
            }
          }
        }
        if(results[question])

				question = question + 1;
				gotoQuestion( question );
			}
    });
/*    $("input[type=radio]").bind("onchange",function(e){
      console.log("I GOT A CHANGE!");
      console.log("Event:",e);
      reevaluateNexity();
    }).bind("mouseup", function(e){
      console.log("CLICK is magic NEXT QUESTION");
      console.log("event:",e);
      question += 1;
      gotoQuestion( question );
    });*/
    enableKeyboardControls();
  }
  // remove extraneous text
  $("div.observation, span.commenttext").each(function(i){
  	var rem = $(this).text().split(":", 2);
  	$(this).text(rem[1]); 
  });
  gotoQuestion(question);

  // is this an admin page?
  if($('#saveprocessed').length>0) {
 	  $('div.storysegment').each(function(i){
	    sendForProcessing(
	      $(this).data("storysegment"),
	      $("input[name=textfile]").val(),
	      $("input[name=conversion_label]").val(),
	      $("input[name=apikey]").val()
	    );
    });
  }
});

function sanitiseTokens(t) {
	//console.log("t is ", typeof(t) );
	return(t.split(cleaningRE));
}

function getTokens(txt){ // turns a string into an array of tokens
	return(txt.split(/\s+/));
}

function getWhitespace(txt) { // gets the whitespace, complement of getTokens()
  return(txt.split(/\S+/));
}

function normaliseToken(t) {
  if (typeof(t) !== 'undefined') {
    return(t.replaceAll(/[\W]/gi,'')); // strips down to alphanumerics
  }
}

function gotoQuestion(x) { // x starts at 0
  question = x;

  $('p#parsedtext>span.highlight.highlight'+String(x+1)).addClass('active').siblings().removeClass('active');
  
  $('.commentblock #q'+String(x+1)+' div.comment>span.commenttext').addClass('active').parents('.commentblock').siblings('.commentblock').find('.comment>span.commenttext').removeClass('active');

  $(".commentobservationpair").eq(x).find(".suggests").slideDown(slideDuration).parent().parent().siblings().find(".suggests").slideUp(slideDuration);
  $(".commentobservationpair").eq(x).find("div.comment").removeClass("questionCompleteCaption");//.addClass("questionUncompleteCaption");
  $(".commentobservationpair").not(x).find("div.comment").removeClass("questionUncompleteCaption");

  for(var i=0; i<$(".commentobservationpair").length; i++) {
    if(results[i]===undefined) {
      $(".commentobservationpair").eq(i).find("div.comment").removeClass("questionCompleteCaption").addClass("questionUncompleteCaption");
    } else {
      $(".commentobservationpair").eq(i).find("div.comment").removeClass("questionUncompleteCaption").addClass("questionCompleteCaption");
    }
  }
  reevaluateNexity();
}

function reevaluateNexity() {
  // button is disabled if current_q does not have an answer in results
  // button text is 'next' unless results.length is the same as the number of questions
  if(results[question]>-1) {
	  $("button#next").removeClass("disabled");
	  $("button#next").prop("disabled", false);
  } else {
  	// disabled
	  $("button#next").addClass("disabled");
	  $("button#next").prop("disabled", true);
  }
  $("button#next").html( 
    isNextActuallyFinish() ? "Finish" : "Next"
  );
}

function isNextActuallyFinish() {
  return(Object.values(results).length == $(".commentobservationpair").length);
}

function postData(results){
	postingData = {
		"reviews[]":results,
    "comments[]":$("span.commenttext").map(function(){return $(this).text()}).get(),
    "observations[]":$("div.observation").map(function(){return $(this).text()}).get(),
    "processed_story_segment_id":$("#processed_story_segment_id").data("processed_story_segment_id"), // ?
		"version":_internal_version
	};
	//console.log(">>> posting results", postingData);
	$.post("/api/submitreview", postingData, function(e){
		//console.log("got response from server", e);
		if (e == "okay"){
			window.location.href="/review";
		}
	});
}

function sliceAndDiceThrice() {
  var possibleMatchAnchor=[];
  var matchCount=[];
  var matches=[];
  toFind = []; // each is a list of segments corresponding to a question

  var storyTokens = getTokens($("#fulltext").text());

  for(var i=0; i<$(".commentobservationpair").length; i++) {
    // clunky but fingers crossed
    try {
  	  toFind[i] = getTokens($(".commentobservationpair>div.comment>span.commenttext")[i].
                            textContent.
                            match(/[\s*]Text:[\s+]\"([^\0]+)\"[\s+]/i)[1] );
    } catch (err) { // openai forgot the quotes
  	  toFind[i] = getTokens($(".commentobservationpair>div.comment>span.commenttext")[i].
                            textContent.
                            match(/[\s*]Text:[\s+]([^\0]+)[\s+]/i)[1] );
    }
	  possibleMatchAnchor[i]=-1;
    matchCount[i]=matches[i]=0;
  }

  for(i=0; i<storyTokens.length; i++) {
  	for(var j=0;j<toFind.length; j++) {
      if(matches[j]!==0) continue; // this indicates a match has been found
		  if( (matchCount[j]<=toFind[j].length) &&
          (normaliseToken(storyTokens[i]) == normaliseToken(toFind[j][matchCount[j]]) ) ) {
		    // we have a possible match
		    if(possibleMatchAnchor[j]>-1) {
			    matchCount[j]++;
		    } else {
			    possibleMatchAnchor[j] = i;
			    matchCount[j]=1;
		    }
		  } else {
		    if(possibleMatchAnchor[j]>-1) {
			    if (matchCount[j]===toFind[j].length) {
			      // yes, a valid match, starting at token possibleMatchAnchor and running
			      // for matchCount tokens
			      matches[j]=[ possibleMatchAnchor[j],(possibleMatchAnchor[j] + matchCount[j]-1) ];
			    } else {
            // we were matching, but the latest token pair does not match; reset it
            matchCount[j]=0;
            possibleMatchAnchor[j]=-1;
          }
		    }
		  }
    }
  }


  var storySpace = getWhitespace($("#fulltext").text()); // white space between segments
  var reconstructed = []; // parts added in order for reconstruction
  var openClasses=[]; // which questions have a class open
  var activeMatches; // which questions belong to this segment

  for(i=0;i<matches.length;i++) { openClasses[i]=false }

  for (i=0; i<storyTokens.length; i++) {
    reconstructed.push(storySpace[i]);
    // is this token number inside a segment?
    activeMatches = segmentSlice(i);
//    if(inSegment(i)===false) {
      // we have something in here
    if(areOpenClassesSameAsNewClasses()===false) {
      //if(areClassesClosed()===false) {
        // we need to close a span
        if(i>0) {
          reconstructed.push("</span>");
          openClasses.forEach(function(item,idx,array){array[idx]=false}); // flag them as closed
        }
      }
//    }

    // do we need to open some classes?
/*    for(var j=0;j<activeMatches.length; j++) {
      if(activeMatches[j]===true) {
        openClasses[j]=true;
      }
      } // maybe this whole above block is just openClasses=activeMatches...?*/

    if(areOpenClassesSameAsNewClasses/*areClassesClosed*/()===false) {
      //  add a span opening with the matched classes
      var spanTxt="<span class='highlight";
      for(var j=0;j<matches.length; j++) {
        if(activeMatches[j]===true) {
          spanTxt=spanTxt+" highlight"+String(j+1);
        }
      }
      spanTxt=spanTxt+"'>";
      reconstructed.push(spanTxt);
    }
    openClasses=activeMatches.slice();

    reconstructed.push(storyTokens[i]);
  }

  // do we have a span hanging open?
  if(areClassesClosed()===false) {
    reconstructed.push("</span>");
  }

  var processedFullText=reconstructed.join("").replace("\n","<br>");

  $('#fulltext').hide(0,function (){
    $('#parsedtext').html(processedFullText);
  });

  function areOpenClassesSameAsNewClasses() { // true if activeMatches and openClasses are the same
    for(var k=0; k<matches.length; k++) {
      if(activeMatches[k]!==openClasses[k]) {
        return false;
      }
    }
    return true;
  }

  function areClassesClosed() { // false if any of openClasses is true
    for(var l = 0; l<matches.length; l++) {
      if(openClasses[l]===true) {
        return false;
      }
    }
    return true;
  }

  function inSegment(i) { // are any highlights needed for this segment?
    for (var j=0; j<matches.length; j++) {
      if( (i>=matches[j][0]) && (i<=matches[j][1]) ) {
        return true;
      }
    }
    return false;
  }

  function segmentSlice(i) { // a list of which matches are in this segment
    var segments = [];
    for (var j=0; j<matches.length; j++) {
      segments[j]=( (i>=matches[j][0]) && (i<=matches[j][1]) )?true:false;
    }
    return segments;
  }
}

var awaitingResponses = 0;

function handleSendForProcessingCallback(results){
  var _parameters = JSON.parse(this.data)
  var response_data = (results.choices[0]); // (results["text"].choices[0]);
  var response_id = (results["id"]); // this is the ID for review previews
  console.log("I think this is for storysegment "+String(results["id"]), _parameters);
  $("div.storysegment."+String(_parameters["segmentno"]))
    .parent().find("div.processedstorysegment").text(response_data["text"])
    .parent().parent().find("div.count input[type=checkbox]").removeAttr('disabled').attr('checked', true);
  // add a regenerate button
  $("div.storysegment."+String(_parameters["segmentno"]))
    .parent().find("div.regenerate").html("<button class='regenerate'>regenerate</button>");
  $("div.storysegment."+String(_parameters["segmentno"]))
    .parent().find("div.regenerate").find("button.regenerate")
      .click(function(e){
        alert("regenerate!");
        sendForProcessing(                     
          $("div.storysegment."+String(
            $('div.storysegment').index($(e.target))+1
          )).data("storysegment"),
          $("input[name=textfile]").val(),
          $("select[name=conversion] option:selected").val(), // take the value from the drop-down, not the baked-in label
          $("input[name=apikey]").val()
        );
        e.stopPropagation();
    	e.stopImmediatePropagation();
        return(false);
      });
  // add a preview button
  $("div.storysegment."+String(_parameters["segmentno"]))
    .parent().find("div.preview")
    .html(
       "<button class='preview' data-pssid='"+results["id"]+"'><a href='/review/"+results['id']+"?preview' onclick='window.open(this.href,\"stepford-preview-"+results['id']+"\");return false;'>preview</a></button>"
    );
  awaitingResponses--;
  if(awaitingResponses==0) {
    $("input[type=submit]").attr('disabled',false);
  }
}

function sendForProcessing(segmentno, textfile, conversion_label, apikey) {
  awaitingResponses++;
  this._parameters = {
    "segmentno":segmentno,
    "textfile":textfile,
    "conversion_label":conversion_label,
    "apikey": apikey
  }
  var parameters = JSON.stringify(this._parameters);
  //console.log("About to send this payload for processing: ", parameters);
  $.post('/admin/api/sendForProcessing',
          parameters,
          handleSendForProcessingCallback,
          "json")
    .fail(function(jqXHR, textStatus, errorThrown) {
        awaitingResponses--;
        alert(textStatus);
        console.log("ERROR from openai - ",jqXHR, textStatus, errorThrown);
        $("div.storysegment"+String(segmentno)).next("div.resultgpt3").html('<span class="error">'+response+'</span>');
    });
}

function enableKeyboardControls() {
  // make the 1-5s work!
  $("div.score label").click(function (e) {
    console.log("LABEL CLICK:",e);
  });
  $("div.score>input").change(function (e) {
    console.log("1-5 change: ",e);
    //$("button#next").removeClass("disabled");
    //$("button#next").prop("disabled", false);
    results[ parseInt($(e.target).data("q"))-1 ] = parseInt($(e.target).val());
    reevaluateNexity();
    e.stopPropagation();
	e.stopImmediatePropagation();
	e.preventDefault();
//    $("#q"+String(question+1)+"-"+String(triggeredScore)).trigger("click",{propagate:false});
    if( ( (e.type=="click")&&(isNextActuallyFinish()===false) ) || ( (e.data != null)&&(e.data.propagation!==false) ) ) {
      $("#next").trigger("click");
    }
  });
  $(document).keydown(function (e) {
    if(parseInt(e.originalEvent.key)>-1){
      // its a number key
      var target="#q"+String(question+1)+"-"+e.originalEvent.key;
      $(target).trigger("click");
      console.log(target,"current q="+String(question));
      //$("#next").trigger("click");
      e.stopPropagation();
  	  e.stopImmediatePropagation();
      e.preventDefault();	  
      reevaluateNexity();
      //return;
    }
    if(e.originalEvent.key=="Enter") {
      if ( $("button#next").prop("disabled")==false ) {
        $("#next").trigger("click");
      }
      //return;
    }
    var current = $(".commentblock").eq(question).find(".scores.row").find("input:checked").val();
    var triggeredScore;
    if(e.originalEvent.key=="ArrowLeft") {
      triggeredScore = -1;
      if(current === undefined) {
        triggeredScore = 5;
      } else {
        triggeredScore = parseInt(current) - 1;
      }
      if (triggeredScore > 0) {
        e.stopPropagation();
        e.preventDefault();
        $("#q"+String(question+1)+"-"+String(triggeredScore)).trigger("click",{propagate:false});
      }
      return;
    }
    if(e.originalEvent.key=="ArrowRight") {
      triggeredScore = -1;
      if(current === undefined) {
        triggeredScore = 1;
      } else {
        triggeredScore = parseInt(current) + 1;
      }
      if (triggeredScore > 0) {
	    e.stopPropagation();
	  	e.stopImmediatePropagation();
        e.preventDefault();
        $("#q"+String(question+1)+"-"+String(triggeredScore)).trigger("click",{propagate:false});
      }
      return;
    }
  });
}

