from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

# Automatically handles reading and seeding initial database records from local backup file
SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# Read active runtime environment configurations
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"

print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

# Establishes collection targeting and forces automated record reloading on boot
db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    """Helper function to parse MongoDB BSON into standard serializable JSON"""
    return json.loads(json_util.dumps(data))

######################################################################
# EXERCISE 1: HEALTH ENDPOINT
######################################################################
@app.route("/health", methods=["GET"])
def healthz():
    return jsonify(dict(status="OK")), 200

######################################################################
# EXERCISE 1: COUNT ENDPOINT
######################################################################
@app.route("/count", methods=["GET"])
def count():
    """Returns the total number of documents inside the collection"""
    count_val = db.songs.count_documents({})
    return {"count": count_val}, 200

######################################################################
# EXERCISE 2: LIST ALL SONGS (GET /song)
######################################################################
@app.route("/song", methods=["GET"])
def songs():
    """Retrieves all documents from the songs collection"""
    results = list(db.songs.find({}))
    return {"songs": parse_json(results)}, 200

######################################################################
# EXERCISE 3: READ ONE SONG BY ID (GET /song/<id>)
######################################################################
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Finds a specific song document by its custom integer id property"""
    song = db.songs.find_one({"id": id})
    if not song:
        return {"message": f"song with id {id} not found"}, 404
    return parse_json(song), 200

######################################################################
# EXERCISE 4: CREATE A SONG (POST /song)
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    """Inserts a unique song document into the database collection"""
    song_in = request.json
    song = db.songs.find_one({"id": song_in["id"]})
    if song:
        return {"Message": f"song with id {song_in['id']} already present"}, 302

    insert_id = db.songs.insert_one(song_in)
    return {"inserted id": parse_json(insert_id.inserted_id)}, 201

######################################################################
# EXERCISE 5: UPDATE A SONG (PUT /song/<id>)
######################################################################
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Updates an existing song resource or returns 200 if nothing changed"""
    song_in = request.json
    song = db.songs.find_one({"id": id})

    if song is None:
        return {"message": "song not found"}, 404

    updated_data = {"$set": song_in}
    result = db.songs.update_one({"id": id}, updated_data)

    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200
    else:
        return parse_json(db.songs.find_one({"id": id})), 201

######################################################################
# EXERCISE 6: DELETE A SONG (DELETE /song/<id>)
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Deletes an existing song resource from the database"""
    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    else:
        return "", 204
