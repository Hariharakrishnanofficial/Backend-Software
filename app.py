from flask import Flask, request, jsonify, session
from flask_cors import CORS
from pymongo import MongoClient
import certifi
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import logging
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

# 🔹 Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Set Timezone
IST = pytz.timezone("Asia/Kolkata")

# 🔹 Flask Secret Key (Set in Environment Variables)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# 🔹 Database Connection
uri = "mongodb+srv://hariharakrishnanofficial:t44W3v9vbWEDrxab@cluster0.9gzgp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["iot_db"]
sensor_collection = db["sensor_datas"]
control_collection = db["pump_control"]
users_collection = db["users"]
email_collection = db["emails"]

# 🔹 APScheduler
scheduler = BackgroundScheduler(timezone=IST, daemon=True)

def start_scheduler():
    logger.info("Starting APScheduler...")
    scheduler.start()

scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

# 🔹 Email Sending Function
def send_email(recipient_email, subject, message):
    sender_email = "hariharakrishnan117@gmail.com"
    sender_password = "einn jmhq fehl pabr"  # App Password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

# 🔹 Scheduled Task Function
def scheduled_task(action, revert_delay):
    control_collection.update_one({}, {"$set": {"pump": action}}, upsert=True)
    logger.info(f"Task executed at {datetime.now(IST)} with action: {action}")

    for user in email_collection.find():
        send_email(user['email'], "Scheduled Task", f"Pump is turned {action}")

    revert_time = datetime.now(IST) + timedelta(minutes=revert_delay)
    scheduler.add_job(revert_action, 'date', run_date=revert_time, args=['OFF'])

# 🔹 Revert Function
def revert_action(action):
    control_collection.update_one({}, {"$set": {"pump": action}}, upsert=True)
    logger.info(f"Pump state reverted to {action} at {datetime.now(IST)}")

    # for user in email_collection.find():
    #     send_email(user['email'], "Scheduled Task", f"Pump has been turned {action}")

# 🔹 API Endpoints

@app.route('/schedule-task', methods=['POST'])
def schedule_task():
    data = request.json
    schedule_type = data.get('schedule_type')
    action = data.get('action', '').upper()
    delay = int(data.get('delay', 0))
    revert_delay = int(data.get('revert_delay', 0))

    if not schedule_type or not action:
        return jsonify({"error": "Missing required fields"}), 400

    job_id = 'scheduled-task'
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)

    now_ist = datetime.now(IST) + timedelta(minutes=delay)

    if schedule_type == 'daily':
        time_str = data.get('time')
        if not time_str:
            return jsonify({"error": "Time is required for daily schedule"}), 400
        hour, minute = map(int, time_str.split(':'))
        trigger = CronTrigger(hour=hour, minute=minute, timezone=IST)

    elif schedule_type == 'hourly':
        trigger = IntervalTrigger(hours=1, start_date=now_ist)

    elif schedule_type == 'specific':
        datetime_str = data.get('datetime')
        if not datetime_str:
            return jsonify({"error": "Datetime is required for specific schedule"}), 400
        run_date = IST.localize(datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')) + timedelta(minutes=delay)
        trigger = DateTrigger(run_date=run_date)

    elif schedule_type == 'minute':
        interval = int(data.get('interval', 0))
        if interval <= 0:
            return jsonify({"error": "Interval must be greater than 0 for minute schedule"}), 400
        trigger = IntervalTrigger(minutes=interval, start_date=now_ist)

    else:
        return jsonify({"error": "Invalid schedule type"}), 400

    scheduler.add_job(
        scheduled_task, 
        trigger, 
        id=job_id, 
        args=[action, revert_delay], 
        replace_existing=True
    )

    return jsonify({"message": "Task scheduled successfully"}), 200

@app.route("/get-pump", methods=["GET"])
def get_pump():
    try:
        data = control_collection.find_one({}, {"_id": 0})
        return jsonify(data if data else {"pump": "OFF"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve pump status", "details": str(e)}), 500

@app.route("/set-pump", methods=["POST"])
def set_pump():
      try:
          data = request.json
          if not data:
              return jsonify({"error": "No JSON data received"}), 400

          result = control_collection.update_one({}, {"$set": data}, upsert=True)
          if result.matched_count > 0 or result.upserted_id:
              return jsonify({"message": "Pump state updated successfully"}), 200
          else:
              return jsonify({"error": "Failed to update pump state"}), 500

      except Exception as e:
          return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    try:
        # Retrieve the latest 20 sensor data entries
        latest_data = list(sensor_collection.find().sort("_id", -1).limit(10))
        if not latest_data:
            logger.warning("No sensor data found in the database.")
            return jsonify({"error": "No sensor data available"}), 404

        for data in latest_data:
            data["_id"] = str(data["_id"])   

        return jsonify(latest_data), 200
    except Exception as e:
        logger.error(f"Error retrieving sensor data: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if users_collection.find_one({'username': username}):
        return jsonify({'error': 'Username already exists'}), 400

    hashed_password = generate_password_hash(password)
    users_collection.insert_one({'username': username, 'password': hashed_password})
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/signin', methods=['POST'])
def signin():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        return jsonify({'message': 'Sign-in successful'}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@app.route("/insert", methods=["POST"])
def insert_data():
    try:
        data = request.json
        sensor_collection.insert_one(data)
        return jsonify({"message": "Sensor data stored successfully"}), 201
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/get-data', methods=['GET'])
def get_data():
    try:
        latest_data = list(sensor_collection.find().sort("_id", -1).limit(1))
        if not latest_data:
            return jsonify({"message": "No data found"}), 404  # Handle empty database case

        for data in latest_data:
            data["_id"] = str(data["_id"])  

        return jsonify(latest_data), 200
    except Exception as e:
        print("Error retrieving data:", str(e))  # Log error in server
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/delete-email', methods=['POST'])
def delete_email():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    result = email_collection.delete_one({"email": email})

    if result.deleted_count > 0:
        return jsonify({"message": "Email deleted successfully"}), 200
    else:
        return jsonify({"error": "Email not found"}), 404
# 🔹 Start Flask App

@app.route('/get-emails', methods=['GET'])
def get_emails():
    emails = list(email_collection.find({}, {"_id": 0, "email": 1}))
    return jsonify(emails), 200

@app.route('/store-email', methods=['POST'])
def store_email():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    if email_collection.find_one({'email': email}):
        return jsonify({"error": "Email already exists"}), 400

    email_collection.insert_one({'email': email})
    return jsonify({"message": "Email stored successfully"}), 201






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
