from datetime import datetime, date
import time
import threading
import paho.mqtt.client as mqtt
import streamlit as st

# ===============================
# CONFIG STREAMLIT
# ===============================
st.set_page_config(page_title="Monitoramento MQTT", layout="centered")

# ===============================
# ARMAZENAMENTO GLOBAL
# ===============================
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = {}

if "last_update_time" not in st.session_state:
    st.session_state.last_update_time = None

SENSOR_TIMEOUT = 60

# ===============================
# MQTT CONFIG
# ===============================
MQTT_SERVER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC_TEMP = "casa/sensor/temperatura"
MQTT_TOPIC_HUMIDITY = "casa/sensor/umidade"

# ===============================
# LIMPA DADOS ANTIGOS
# ===============================
def clear_old_data():
    today = date.today()
    for day in list(st.session_state.sensor_data):
        if day != today:
            del st.session_state.sensor_data[day]

# ===============================
# MQTT CALLBACKS
# ===============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC_TEMP)
        client.subscribe(MQTT_TOPIC_HUMIDITY)

def on_message(client, userdata, message):
    today = date.today()
    timestamp = datetime.now().strftime('%H:%M:%S')

    st.session_state.sensor_data.setdefault(today, {
        "temperature": [],
        "humidity": []
    })

    if message.topic == MQTT_TOPIC_TEMP:
        value = float(message.payload.decode())
        st.session_state.sensor_data[today]["temperature"].append((timestamp, value))
        st.session_state.last_update_time = time.time()

    elif message.topic == MQTT_TOPIC_HUMIDITY:
        value = float(message.payload.decode())
        st.session_state.sensor_data[today]["humidity"].append((timestamp, value))
        st.session_state.last_update_time = time.time()

# ===============================
# MQTT THREAD (IMPORTANTE)
# ===============================
@st.cache_resource
def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start()
    return client

start_mqtt()

# ===============================
# INTERFACE STREAMLIT
# ===============================
st.title("🌡️ Monitoramento de Temperatura e Umidade")

clear_old_data()
today = date.today()

temperature_data = st.session_state.sensor_data.get(today, {}).get("temperature", [])
humidity_data = st.session_state.sensor_data.get(today, {}).get("humidity", [])

# Verifica timeout
if (
    not st.session_state.last_update_time or
    time.time() - st.session_state.last_update_time > SENSOR_TIMEOUT
):
    st.warning("⚠️ Sensor sem dados (ND)")
else:
    col1, col2 = st.columns(2)

    if temperature_data:
        col1.metric("Temperatura (°C)", temperature_data[-1][1])

    if humidity_data:
        col2.metric("Umidade (%)", humidity_data[-1][1])

# Gráficos
if temperature_data:
    st.subheader("📈 Temperatura")
    st.line_chart(
        {t[0]: t[1] for t in temperature_data}
    )

if humidity_data:
    st.subheader("💧 Umidade")
    st.line_chart(
        {h[0]: h[1] for h in humidity_data}
    )

# Atualização automática
time.sleep(2)
st.rerun()