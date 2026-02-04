from datetime import datetime, date
import time
import paho.mqtt.client as mqtt
import streamlit as st

# ============ CONFIG STREAMLIT ============
st.set_page_config(page_title="Monitoramento MQTT", layout="centered")

st.title("🌡️ Monitoramento de Temperatura e Umidade")
st.caption("Fonte: MQTT (test.mosquitto.org) — atualização em tempo quase real")

# ============ ESTADO GLOBAL ============
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = {}  # {date: {"temperature": [(ts, val)], "humidity": [(ts, val)]}}

if "last_update_time" not in st.session_state:
    st.session_state.last_update_time = None

SENSOR_TIMEOUT = 60  # segundos sem dados => considerar ND

# ============ CONFIG MQTT ============
MQTT_SERVER = "test.mosquitto.org"
MQTT_PORT = 1883
# Altere estes tópicos para algo ÚNICO seu, para evitar colisão com outros usuários no broker público:
MQTT_TOPIC_TEMP = "damiao707/casa/sensor/temperatura"
MQTT_TOPIC_HUMIDITY = "damiao707/casa/sensor/umidade"

# ============ FUNÇÕES AUX ============
def clear_old_data():
    today = date.today()
    for d in list(st.session_state.sensor_data):
        if d != today:
            del st.session_state.sensor_data[d]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC_TEMP)
        client.subscribe(MQTT_TOPIC_HUMIDITY)
    else:
        print(f"Falha ao conectar MQTT: {rc}")

def on_message(client, userdata, message):
    try:
        today = date.today()
        timestamp = datetime.now().strftime('%H:%M:%S')
        sd = st.session_state.sensor_data
        sd.setdefault(today, {"temperature": [], "humidity": []})
        if message.topic == MQTT_TOPIC_TEMP:
            value = float(message.payload.decode())
            sd[today]["temperature"].append((timestamp, value))
            st.session_state.last_update_time = time.time()
        elif message.topic == MQTT_TOPIC_HUMIDITY:
            value = float(message.payload.decode())
            sd[today]["humidity"].append((timestamp, value))
            st.session_state.last_update_time = time.time()
    except Exception as e:
        print("Erro MQTT:", e)

# ============ INICIALIZA MQTT UMA ÚNICA VEZ ============
@st.cache_resource
def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_start()
    return client

start_mqtt()

# ============ UI ============
with st.sidebar:
    st.header("Configurações")
    st.write("Broker:", MQTT_SERVER)
    st.write("Tópicos:")
    st.code(f"- {MQTT_TOPIC_TEMP}\n- {MQTT_TOPIC_HUMIDITY}", language="text")
    refresh_sec = st.slider("Intervalo de atualização (s)", 1, 10, 2)

clear_old_data()
today = date.today()

temperature_data = st.session_state.sensor_data.get(today, {}).get("temperature", [])
humidity_data = st.session_state.sensor_data.get(today, {}).get("humidity", [])

# Status de conexão/dados
placeholder_status = st.empty()
if (not st.session_state.last_update_time) or (time.time() - st.session_state.last_update_time > SENSOR_TIMEOUT):
    placeholder_status.warning("⚠️ Sem dados recentes do sensor (ND). Aguarde ou verifique publicação nos tópicos.")
else:
    placeholder_status.success("✅ Recebendo dados do sensor")

# Métricas
col1, col2 = st.columns(2)
if temperature_data:
    col1.metric("Temperatura (°C)", f"{temperature_data[-1][1]:.2f}")
else:
    col1.metric("Temperatura (°C)", "—")

if humidity_data:
    col2.metric("Umidade (%)", f"{humidity_data[-1][1]:.2f}")
else:
    col2.metric("Umidade (%)", "—")

# Gráficos
def to_series(pairs):
    # pairs: [(ts, value), ...] -> dict {ts: value}
    return {ts: val for ts, val in pairs}

if temperature_data:
    st.subheader("📈 Temperatura")
    st.line_chart(to_series(temperature_data))

if humidity_data:
    st.subheader("💧 Umidade")
    st.line_chart(to_series(humidity_data))

# Histórico rápido do dia
with st.expander("Ver últimas leituras"):
    st.write("Temperatura (timestamp, °C):")
    if temperature_data:
        st.write(temperature_data[-10:])
    else:
        st.write("—")
    st.write("Umidade (timestamp, %):")
    if humidity_data:
        st.write(humidity_data[-10:])
    else:
        st.write("—")

# Atualização automática leve (sem loop bloqueante)
time.sleep(refresh_sec)
st.rerun()