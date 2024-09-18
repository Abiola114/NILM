from flask import Flask, render_template
from flask_socketio import SocketIO
from datetime import datetime
import gspread
import numpy as np
from sklearn.preprocessing import StandardScaler
from threading import Lock
from sklearn.ensemble import RandomForestClassifier
import pickle

COST_PER_KWH = 225  # Cost in your local currency

# Initialize cost for each appliance
cost = {
    "light_bulb": 0.0,
    "fan": 0.0,
    "pressing_iron": 0.0
}

# Power consumption in watts
POWER_CONSUMPTION = {
    "light_bulb": 10.5,
    "fan": 110,
    "pressing_iron": 1800
}

# Initialize energy consumption in kWh and last updated time
energy_consumption = {
    "light_bulb": 0.0,
    "fan": 0.0,
    "pressing_iron": 0.0
}

last_updated_time = {
    "light_bulb": None,
    "fan": None,
    "pressing_iron": None
}

gc = gspread.service_account(r'C:\Users\ADMIN\Desktop\My Final Year Project\Web_Page\savvy-arbor-433608-f0-ba84f63d84ab.json')
sh = gc.open("NILM_DATABASE")
wks = sh.worksheet("Sheet1")

last_value = wks.get_all_values()[-1][2:]
last_value_float = [float(i) for i in last_value]

thread = None
thread_lock = Lock()

app = Flask(__name__)
socketio = SocketIO(app)

scaler = StandardScaler()
with open('scaler.pkl', 'rb') as file:
    scaler = pickle.load(file)

# Load the model
with open('model.pkl', 'rb') as file:
    loaded_model = pickle.load(file)

def get_current_datetime():
    now = datetime.now()
    return now.strftime("%m/%d/%Y %H:%M:%S")

def get_updated_data(updated_data):
    global last_value_float
    if last_value_float != updated_data:
        last_value_float = updated_data
        return last_value_float
    return None

@app.route('/')
def index():
    return render_template('index.html')

def background_thread():
    global last_value_float
    
    with app.app_context():
        while True:
            socketio.sleep(10)  # Assuming data arrives every 10 seconds

            last_row = wks.get_all_values()[-1]  # Get the latest row of data
            updated_data = [float(last_row[i]) for i in range(len(last_row)) if i not in [0, 1,2, 5, 6, 7]]
            print(updated_data)
            if get_updated_data(updated_data):
                input_data_to_numpy_array = np.asarray([last_value_float])
                input_data_scaled = scaler.transform(input_data_to_numpy_array)

                prediction = loaded_model.predict(input_data_scaled).flatten()

                print(f"Prediction: {prediction}")

                # Initialize data dictionary for emitting
                data = {
                    "lightbulb": int(prediction[0]),
                    "fan": int(prediction[1]),
                    "iron": int(prediction[2]),
                    "lightbulb_energy": energy_consumption["light_bulb"],
                    "fan_energy": energy_consumption["fan"],
                    "iron_energy": energy_consumption["pressing_iron"],
                    "lightbulb_cost": cost["light_bulb"],
                    "fan_cost": cost["fan"],
                    "iron_cost": cost["pressing_iron"],
                    "last_updated_lightbulb": last_updated_time["light_bulb"],
                    "last_updated_fan": last_updated_time["fan"],
                    "last_updated_iron": last_updated_time["pressing_iron"]
                }

                # Cost calculation and energy update
                if prediction[0] == 1:
                    energy_consumption["light_bulb"] += (POWER_CONSUMPTION["light_bulb"] * 10) / 3600000  # 10 seconds in kWh
                    cost["light_bulb"] = energy_consumption["light_bulb"] * COST_PER_KWH
                    last_updated_time["light_bulb"] = get_current_datetime()
                    data["lightbulb_energy"] = energy_consumption["light_bulb"]
                    data["lightbulb_cost"] = cost["light_bulb"]

                if prediction[1] == 1:
                    energy_consumption["fan"] += (POWER_CONSUMPTION["fan"] * 10) / 3600000
                    cost["fan"] = energy_consumption["fan"] * COST_PER_KWH
                    last_updated_time["fan"] = get_current_datetime()
                    data["fan_energy"] = energy_consumption["fan"]
                    data["fan_cost"] = cost["fan"]

                if prediction[2] == 1:
                    energy_consumption["pressing_iron"] += (POWER_CONSUMPTION["pressing_iron"] * 10) / 3600000
                    cost["pressing_iron"] = energy_consumption["pressing_iron"] * COST_PER_KWH
                    last_updated_time["pressing_iron"] = get_current_datetime()
                    data["iron_energy"] = energy_consumption["pressing_iron"]
                    data["iron_cost"] = cost["pressing_iron"]

                # Emit the data to the HTML page
                socketio.emit('updateSensorData', data)

@socketio.on('connect')
def connect():
    global thread
    print('Client connected')

    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)

@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app)
