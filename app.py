from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import certifi
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
app = Flask(__name__)
CORS(app)
uri = "mongodb+srv://hariharakrishnanofficial:t44W3v9vbWEDrxab@cluster0.9gzgp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(uri,tlsCAFile=certifi.where())
db = client["iot_db"]
sensor_collection = db["sensor_datas"]
control_collection = db["led_control"]


@app.route("/insert", methods=["POST"])
def insert_data():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        result = sensor_collection.insert_one(data)
        if result.inserted_id:
            return jsonify({"message": "Sensor data stored successfully"}), 201
        else:
            return jsonify({"error": "Failed to insert sensor data"}), 500

    except Exception as e:
        print("Error inserting data:", str(e))
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route("/set-led", methods=["POST"])
def set_led():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        result = control_collection.update_one({}, {"$set": data}, upsert=True)
        if result.matched_count > 0 or result.upserted_id:
            return jsonify({"message": "LED state updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update LED state"}), 500

    except Exception as e:
        print("Error updating LED state:", str(e))
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/get-data', methods=['GET'])
def get_data():
    try:
        latest_data = list(collection.find().sort("_id", -1).limit(10))
        if not latest_data:
            return jsonify({"message": "No data found"}), 404  # Handle empty database case

        for data in latest_data:
            data["_id"] = str(data["_id"])  # Convert ObjectId to string

        return jsonify(latest_data), 200
    except Exception as e:
        print("Error retrieving data:", str(e))  # Log error in server
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500



@app.route("/get-led", methods=["GET"])
def get_led():
    try:
        data = control_collection.find_one({}, {"_id": 0})
        if data:
            return jsonify(data), 200
        else:
            return jsonify({"message": "No LED status found, defaulting to OFF", "led": "OFF"}), 200  

    except Exception as e:
        print("Error retrieving LED status:", str(e))
        return jsonify({"error": "Failed to retrieve LED status", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
