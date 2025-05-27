import streamlit as st
import serial
import time

# Classe que encapsula a conexão com o robô via serial
class RoboSerial:
    def __init__(self, porta, baudrate=115200, timeout=1):
        st.write(f"🔌 Conectando ao robô na porta {porta}...")
        self.conexao = serial.Serial(port=porta, baudrate=baudrate, timeout=timeout)
        time.sleep(2)  # Aguarda a estabilização da conexão
        st.write("✅ Robô conectado com sucesso!")
        while True:
            if self.conexao.in_waiting > 0:
                line = self.conexao.readline().decode('utf-8').rstrip()
                st.write(line)
                break
        self.robo_position = []
        self.__robo_lastposition = []
        self.step = 10
                
                
    def enviar_comando(self, commands):
        st.write(f"📤 Comando enviado: {commands}")
        for gcode in commands:
            self.conexao.write(gcode.encode())
            #self.ser.readline()
            while True:
                if self.conexao.in_waiting > 0:
                    line = self.conexao.readline().decode('utf-8').rstrip()
                    #print(line)
                    return line
                
    def get_position(self):
        self.conexao.reset_input_buffer()
        self.conexao.reset_output_buffer()
        gcode = b'Position\r\n'
        self.conexao.write(gcode)
        # self.conexao.enviar_comando(['Position\r\n',])
        while True:
            if self.conexao.in_waiting > 0:
                line = self.conexao.readline().decode('utf-8').rstrip()
                try:
                    posicaoAtual = [float(num) for num in line.split(',')]
                except ValueError:
                    return None
                return posicaoAtual
        
    def set_position(self): 
        comando = f'G01 X{self.robo_position[0]} Y{self.robo_position[1]} Z{self.robo_position[2]}'
        gcodes = [comando + '\r\n',]
        self.enviar_comando(gcodes)
        response = self.get_position()
        if response:
            self.__robo_lastposition = self.robo_position
            self.robo_position = response
        else:
            self.robo_position = self.__robo_lastposition
        return response
    
    def move_step(self, axis, direction):
        try:
            self.robo_position[axis] += direction * self.step
            response = self.set_position()
        except IndexError:
            response = self.get_position()
        return response

    def fechar_conexao(self):
        self.conexao.close()
        st.write("🔌 Conexão encerrada.")

# Função cacheada para criar uma única instância da conexão
@st.cache_resource
def conectar_robo(porta_serial):
    return RoboSerial(porta_serial)

# Interface de usuário
st.title("🎮 Interface de Controle do Robô (Serial)")

porta = st.text_input("Digite a porta serial do robô (ex: COM9 ou /dev/ttyUSB0):", "COM9")

response = ''
if st.button("Conectar"):
    try:
        st.session_state.robo = conectar_robo(porta)
        st.success(f"🤖 Conectado com sucesso na porta {porta}!")
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")


# Após conexão, apresenta botões de controle
if 'robo' in st.session_state:
    st.subheader("Controles:")
    if st.button("🏠 Home"):
        response = st.session_state.robo.enviar_comando(['G28\r\n',])
        st.session_state.robo.robo_position = st.session_state.robo.get_position()

    if st.button("➡️ X+"):
        response = st.session_state.robo.move_step(axis=0, direction=1)

    if st.button("⬅️ X-"):
        response = st.session_state.robo.move_step(axis=0, direction=-1)

    if st.button("⬆️ Z+"):
        response = st.session_state.robo.move_step(axis=2, direction=1)

    if st.button("⬇️ Z-"):
        response = st.session_state.robo.move_step(axis=2, direction=-1)

    if st.button("⬆️ Y+"):
        response = st.session_state.robo.move_step(axis=1, direction=1)

    if st.button("⬇️ Y-"):
        response = st.session_state.robo.move_step(axis=1, direction=-1)

    if st.button("❌ Desconectar"):
        st.session_state.robo.fechar_conexao()

    st.success(response)