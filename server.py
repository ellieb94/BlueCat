import flask
from flask import render_template
from flask import request
from flask import url_for
from flask import jsonify # For AJAX transactions

import json
import logging

# Mongo database
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

# Date handling
import arrow # Replacement for datetime, based on moment.js
import datetime # But we still need time
from dateutil import tz  # For interpreting local times

# Our own module
#import pre  # Preprocess schedule file


###
# Globals
###
app = flask.Flask(__name__)
#schedule = "static/schedule.txt"  # This should be configurable
import CONFIG


import uuid
app.secret_key = str(uuid.uuid4())
app.debug = CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)

try:
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.service
    collectionSchedules = db.schedules
    collectionClients = db.clients
except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    #sys.exit(1)

###
# Pages
###


### Home Page ###

@app.route("/")
@app.route("/index")
def index():
    app.logger.debug("Main page entry")
  #if 'page' not in flask.session:
  #    app.logger.debug("Processing raw schedule file")
  #    raw = open('static/schedule.txt')
  #    flask.session['page'] = pre.process(raw)

    return flask.render_template('index.html')

### Client Page ###

@app.route("/client")
def client():
    app.logger.debug("client page entry")
    return flask.render_template('client.html')

### Admin Page ###

@app.route("/admin")
def admin():
    app.logger.debug("admin page entry")
    flask.session['clients'] = get_list("Clients")
    flask.session['schedules'] = get_list("Schedules")
    #for sch in flask.session['schedules']:
        #app.logger.debug("schedule: " + str(sch))
    return flask.render_template('admin.html')

@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    flask.session['linkback'] = flask.url_for("index")
    return flask.render_template('page_not_found.html'), 404

################

###functions###

################

@app.route("/_login")
def portalSelector():
    objId = request.args.get('login', 0, type=str)
    app.logger.debug(objId)
    if objId == "client":
        return flask.redirect(url_for('client'))
    else:
        return flask.redirect(url_for('admin'))

@app.route("/_ClientsConfig")
@app.route("/_submitClientInfo")
def clientConfig():
    #collectionTemp = collectionClients
    app.logger.debug("Got a JSON request")
    funct = request.args.get('clientSetting',0,type=str)
    app.logger.debug(funct)
    if funct == "addClient":
        objId1 = request.args.get('fname',0,type=str)
        objId2 = request.args.get('studentid',0,type=str)
        objId3 = request.args.get('phonenum',0,type=str)
        objId4 = request.args.get('riders',0,type=str)
        objId5 = request.args.get('time',0,type=str)
        objId6 = request.args.get('pickup',0,type=str)
        objId7 = request.args.get('dropoff',0,type=str)
        ####################### if verifyinformation(val) #################
        record = { "name": objId1, "date":  arrow.utcnow().naive, 
        "ID": objId2 , "phoneNum": objId3, "riders": objId4, 
        "time": objId5, "pickup": objId6, "dropoff":objId7, "type": "Client", "status": "pending"}
        collectionClients.insert(record)
        d = {'result':'added'}
    elif funct == "removeClient":
        objId = request.args.get('ClientId',0,type=str)
        collectionClients.remove({"_id": ObjectId(objId)});
        return flask.redirect(url_for('admin'))
        #d = {'result':'removed'}
    else:
        d = {'result':'failed'}
    d = json.dumps(d)
    return jsonify(result = d)
    #return flask.redirect(url_for('client'))

@app.route("/_ScheduleConfig")
def scheduleConfig():
    #collectionTemp = collectionSchedules
    objId = request.args.get('ScheduleSetting',0,type=str)
    app.logger.debug(objId)
    if objId == "addSchedule":
        #name = request.args.get('name',0,type=str)
        numSchedules = request.args.get('name',0,type=int)
        #app.logger.debug("schedule added!")
        tempCount = collectionSchedules.find({}).count() + 1
        app.logger.debug(tempCount)
        if tempCount > 1:
            app.logger.debug("failed! schedules already here")
            #d = {'result':'failed! 4 schedules already'}
            #d = json.dumps(d)
            #return jsonify(result = d)
            return flask.redirect(url_for('admin'))
        slider1 = request.args.get('scheduleStart',0,type=str)
        app.logger.debug(slider1)
        slider1 = arrow.get(slider1,'H:mm A')
        sliderS = slider1.format('H:mm')
        app.logger.debug(sliderS)
        slider2 = request.args.get('scheduleEnd',0,type=str)
        slider2 = arrow.get(slider2,'H:mm A')
        sliderF = slider2.format('H:mm')
        timeBlock = 5
        tTable = {}
        clientList = []
        while(sliderS!=sliderF):
            tTable.update({sliderS:clientList})
            slider1 = slider1.replace(minutes=+timeBlock)
            sliderS = slider1.format('H:mm')
        tTable.update({sliderS:clientList})
        for i in range(1,numSchedules+1):
            #record = { "name": i, "date":  arrow.utcnow().naive, "ID": "29838472983" ,"type": "Schedule"}
            record = { "name": i, "date":  arrow.utcnow().naive, "ID": "29838472983" ,"type": "Schedule", "tTable": tTable}
            app.logger.debug(tTable)
            collectionSchedules.insert(record)
        #d = {'result':'success! added schedule'+tempCount}
        #d = json.dumps(d)
    elif objId == "removeSchedule":
        ScheduleId = request.args.get('ScheduleId',0,type=str)
        app.logger.debug(ScheduleId)
        if ScheduleId == "0":
            app.logger.debug("deleting all schedules")
            collectionSchedules.remove({})
        else:
            app.logger.debug("attempting to remove schedule" + str(ScheduleId))
            if collectionSchedules.remove({"_id": ObjectId(ScheduleId)}):
                app.logger.debug("success!")
            else:
                app.logger.debug("failed!")
    else:
        app.logger.debug("wat")
    return flask.redirect(url_for('admin'))

@app.route("/stream")
def stream():
    def eventStream():
        import time
        while True:
        #pull data from database, see if new client submission
            if collectionClients.find({}).count() > 0:
                yield "data: %i %s\n\n" % (collectionClients.find({}).count(), " new rides requested")
                time.sleep(30)
    return flask.Response(eventStream(), mimetype="text/event-stream")        


##############################

def get_list(aType):
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = []
    #tempCollection = collection.find().sort( { date: 1 } )
    if aType == "Schedules":
        collectionTemp = collectionSchedules
    elif aType == "Clients":
        collectionTemp = collectionClients
    else:
        collectionTemp = collectionClients
    for record in collectionTemp.find( {} ).sort("date",1): #"type": "Driver" "status": "pending"
        record['date'] = arrow.get(record['date']).isoformat()
        try:
            record['_id'] = str(record['_id'])
        except:
            del record['_id']
        records.append(record)
    return records


if __name__ == "__main__":
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    app.run(port=CONFIG.PORT)
