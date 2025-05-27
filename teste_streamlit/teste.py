import streamlit as st
import serial
import time

# Classe de controle do robô
class RoboSerial:
    def __init__(self, porta, baudrate=9600):
        self.porta = porta
        self.baudrate = baudrate
        self.serial = None

    def conectar(self):
        try:
            self.serial = serial.Serial(self.porta, self.baudrate, timeout=1)
            time.sleep(2)  # Aguarda inicialização
            return True
        except serial.SerialException as e:
            st.error(f"Erro ao conectar: {e}")
            return False

    def enviar_comando(self, comando):
        if self.serial and self.serial.is_open:
            self.serial.write(f"{comando}\n".encode())

    def fechar_conexao(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

# Estado inicial
if "robo" not in st.session_state:
    st.session_state.robo = None
    st.session_state.homed = False

st.set_page_config(page_title="Controle XYZ", layout="centered")
st.title("🤖 Controle do Robô XYZ")

# Tela de conexão
if st.session_state.robo is None:
    porta = st.text_input("Porta Serial (ex: COM3 ou /dev/ttyUSB0)")
    if st.button("Conectar") and porta:
        robo = RoboSerial(porta)
        if robo.conectar():
            st.session_state.robo = robo
            st.success("Conectado com sucesso!")
else:
    # Funções de comando
    def comando_home():
        st.session_state.robo.enviar_comando("H")
        st.session_state.homed = True

    def comando_movimento(cmd):
        st.session_state.robo.enviar_comando(cmd)

    def desconectar():
        st.session_state.robo.fechar_conexao()
        st.session_state.robo = None
        st.session_state.homed = False

    # Layout dos botões
    st.markdown("### 🎮 Controles XYZ")

    col1, col2, col3 = st.columns(3)

    with col2:
        st.button("⬆️ Y+", on_click=comando_movimento, args=("Y+",), disabled=not st.session_state.homed)

    with col1:
        st.button("⬅️ X-", on_click=comando_movimento, args=("X-",), disabled=not st.session_state.homed)

    with col2:
        st.button("🏠 Home", on_click=comando_home)

    with col3:
        st.button("➡️ X+", on_click=comando_movimento, args=("X+",), disabled=not st.session_state.homed)

    with col2:
        st.button("⬇️ Y-", on_click=comando_movimento, args=("Y-",), disabled=not st.session_state.homed)

    st.divider()

    colz1, colz2, colz3 = st.columns(3)

    with colz1:
        st.button("⬆️ Z+", on_click=comando_movimento, args=("Z+",), disabled=not st.session_state.homed)

    with colz3:
        st.button("⬇️ Z-", on_click=comando_movimento, args=("Z-",), disabled=not st.session_state.homed)

    st.divider()

    st.button("❌ Desconectar", on_click=desconectar, type="primary")
