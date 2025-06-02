# app.py
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import serial
import serial.tools.list_ports
import time
import os
app = Flask(__name__)
app.secret_key = "chave-secreta"

robo_serial = None
homed = False

class RoboSerial:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate
        self.serial = None
        self.speed = 200      # Valor padrão
        self.acceleration = 1200    # Valor padrão
        self.step = 10             # Valor padrão
        self.connected = False
        self.homed = False
        self.current_position = []

    def send_gcodes(self, gcodes):
        for gcode in gcodes:
            try:
                self.serial.write(gcode.encode())
                while True:
                    if self.serial.in_waiting > 0:
                        line = self.serial.readline().decode('utf-8').rstrip()
                        return line
            except serial.SerialTimeoutException:
                print("Timeout: Não foi possível escrever na serial no tempo definido.")
                return None
            
    def get_position(self, timeout=2):
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        gcode = b'Position\r\n'
        self.serial.write(gcode)

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8').rstrip()
                try:
                    posicaoAtual = [float(num) for num in line.split(',')]
                    return posicaoAtual
                except ValueError:
                    return None
        print("Timeout ao ler posição")
        return None
            
    def set_position(self): 
        comando = f'G01 X{self.current_position[0]} Y{self.current_position[1]} Z{self.current_position[2]}'
        gcodes = [comando + '\r\n',]
        response = self.send_gcodes(gcodes)
        return response
    
    def move_step(self, axis, direction):
        self.current_position[axis] += direction * self.step
        response = self.set_position()
        nova_posicao = self.get_position()
        if nova_posicao:
            self.current_position = nova_posicao
        else:
            print("Erro: posição não retornada.")
        return response

    def atualizar_parametros(self, velocidade, aceleracao, step):
        self.step = step
        self.speed = velocidade
        comando = f'G01 F{self.speed}\r\n'
        response1 = robo_serial.send_gcodes([comando,])
        self.acceleration = aceleracao
        comando = f'M204 A{self.acceleration}\r\n'
        response2 = robo_serial.send_gcodes([comando,])
        if response1=='Ok' and response2=='Ok':
            return 'Ok'
        return f"Response speed: {response1}; Response aceleration: {response2}"


def inicializar_conexao():
    global robo_serial
    print('Conectando...')
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        try:
            robo_serial.serial = serial.Serial(port.device, 115200, timeout=1, write_timeout=1)
            time.sleep(0.1)
            robo_serial.serial.reset_input_buffer()
            robo_serial.serial.reset_output_buffer()
            response = robo_serial.send_gcodes(['IsDelta\r\n'])          
            if response == 'YesDelta':
                print(f'Device found on {port.device}')
                return True
            robo_serial.serial.close()
            robo_serial.serial = None
        except (serial.SerialException, OSError):
            continue
    return False

@app.route("/")
def index():
    if not robo_serial.serial.is_open:
        return "<h3>Erro: Não foi possível conectar ao robô na porta serial.</h3>", 500
    return render_template("index.html")

@app.route("/comando", methods=["POST"])
def comando():
    cmd = request.json.get("cmd")
    try:
        if robo_serial.serial:
            if "Home" in cmd:
                response = robo_serial.send_gcodes(['G28\r\n',])
                if response == 'Ok':
                    robo_serial.homed = True
                    robo_serial.current_position = robo_serial.get_position()
            if robo_serial.homed: 
                print(f"Comando: {cmd}")
                if "X-" in cmd:
                    response = robo_serial.move_step(axis=0, direction=-1)
                if "X+" in cmd:
                    response = robo_serial.move_step(axis=0, direction=1)
                if "Z-" in cmd:
                    response = robo_serial.move_step(axis=2, direction=-1)
                if "Z+" in cmd:
                    response = robo_serial.move_step(axis=2, direction=1)
                if "Y-" in cmd:
                    response = robo_serial.move_step(axis=1, direction=-1)
                if "Y+" in cmd:
                    response = robo_serial.move_step(axis=1, direction=1)
            else:
                response = "Realize o Home primeiro!"
            return jsonify({"status": response})
        else:
            inicializar_conexao()
        return jsonify({"status": "erro"})
    except serial.SerialException:
        inicializar_conexao()
        return jsonify({"status": "erro"})

@app.route("/parametros", methods=["POST"])
def parametros():
    global robo_serial
    if not robo_serial.serial:
        return jsonify({"status": "erro", "msg": "Robô não conectado"})

    data = request.json
    try:
        velocidade = int(data.get("velocidade", 30))
        aceleracao = int(data.get("aceleracao", 1000))
        step = int(data.get("step", 1))
        if velocidade > 0 and velocidade <= 800 and aceleracao > 0 and aceleracao <= 20000 and step > 0 and step <= 50:
            response = robo_serial.atualizar_parametros(velocidade, aceleracao, step)
        else:
            response = "Existem valores fora dos limites"
        return jsonify({"status": response})
    except Exception as e:
        return jsonify({"status": "Erro. Verifique a conexão!", "msg": str(e)})

@app.route("/posicao", methods=["GET"])
def posicao():
    if not robo_serial.serial:
        return jsonify({"status": "erro", "msg": "Robô não conectado"})
    
    return jsonify({
        "status": "ok",
        "posicao": robo_serial.current_position
    })

@app.route("/desenhar", methods=["POST"])
def desenhar():
    if not robo_serial.serial:
        return jsonify({"status": "erro", "msg": "Robô não conectado"})
    
    cmd = request.json.get("cmd")
    drawing = request.json.get("desenho")
    height = request.json.get("altura")
    print(f"{cmd}: {drawing} - {height}")
    return jsonify({
        "status": "ok",
        "posicao": robo_serial.current_position
    })


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # Conectar à serial só no processo final
        robo_serial = RoboSerial()
        if inicializar_conexao():
            app.run(host="0.0.0.0", port=5000, debug=True)
        else:
            print("Erro ao conectar com o robô.")
    else:
        # Processo inicial — não conecta ainda
        app.run(host="0.0.0.0", port=5000, debug=True)
  