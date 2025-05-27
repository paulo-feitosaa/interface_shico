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
        self.velocidade = 30      # Valor padrão
        self.aceleracao = 1000    # Valor padrão
        self.step = 10             # Valor padrão
        self.posicao_atual = [0, 0, 0]  # X, Y, Z
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
            
    def get_position(self):
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        gcode = b'Position\r\n'
        self.serial.write(gcode)
        while True:
            if self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8').rstrip()
                try:
                    posicaoAtual = [float(num) for num in line.split(',')]
                except ValueError:
                    return None
                return posicaoAtual
            
    def set_position(self): 
        comando = f'G01 X{self.current_position[0]} Y{self.current_position[1]} Z{self.current_position[2]}'
        gcodes = [comando + '\r\n',]
        response = self.send_gcodes(gcodes)
        return response
    
    def move_step(self, axis, direction):
        robo_serial.current_position[axis] += direction * robo_serial.step
        response = robo_serial.set_position()                   
        robo_serial.current_position = robo_serial.get_position()
        return response

    def atualizar_posicao(self, cmd):
        # Atualiza posição com base no comando enviado
        if cmd == "X+":
            self.posicao_atual[0] += self.step
        elif cmd == "X-":
            self.posicao_atual[0] -= self.step
        elif cmd == "Y+":
            self.posicao_atual[1] += self.step
        elif cmd == "Y-":
            self.posicao_atual[1] -= self.step
        elif cmd == "Z+":
            self.posicao_atual[2] += self.step
        elif cmd == "Z-":
            self.posicao_atual[2] -= self.step
        elif cmd == "H":
            self.posicao_atual = [0, 0, 0]

    def atualizar_parametros(self, velocidade, aceleracao, step):
        self.velocidade = velocidade
        self.aceleracao = aceleracao
        self.step = step

    def desconectar(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

def inicializar_conexao():
    global robo_serial, homed
    mensagem = ""
    print('Conectando...')
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        try:
            robo_serial.serial = serial.Serial(port.device, 115200, timeout=1, write_timeout=1)
            time.sleep(0.1)
            robo_serial.serial.reset_input_buffer()
            robo_serial.serial.reset_output_buffer()
            response = robo_serial.send_gcodes(['IsDelta\r\n'])
            print(response)
            if response == 'YesDelta':
                print(f'Device found on {port.device}')
                return True
            robo_serial.serial.close()
            robo_serial.serial = None
        except (serial.SerialException, OSError):
            continue
    return False


@app.route("/loading")
def loading():
    return render_template("loading.html")

@app.route("/verificar_conexao")
def verificar_conexao():
    if robo_serial.serial and robo_serial.serial.is_open:
        return redirect(url_for("index"))
    else:
        return redirect(url_for("erro"))
    

@app.route("/")
def index():
    if not robo_serial.serial.is_open:
        return "<h3>Erro: Não foi possível conectar ao robô na porta serial.</h3>", 500
    return render_template("index.html")


@app.route("/erro")
def erro():
    return render_template("erro.html")    

@app.route("/comando", methods=["POST"])
def comando():
    global homed

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

@app.route("/desconectar", methods=["POST"])
def desconectar():
    global robo_serial, homed
    if robo_serial:
        robo_serial.desconectar()
    session.clear()
    robo_serial = None
    homed = False
    return redirect("/")

@app.route("/parametros", methods=["POST"])
def parametros():
    global robo_serial
    if not session.get("conectado") or not robo_serial:
        return jsonify({"status": "erro", "msg": "Robô não conectado"})

    data = request.json
    try:
        velocidade = int(data.get("velocidade", 30))
        aceleracao = int(data.get("aceleracao", 1000))
        step = int(data.get("step", 1))

        robo_serial.atualizar_parametros(velocidade, aceleracao, step)
        return jsonify({"status": "ok", "msg": "Parâmetros atualizados"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})

@app.route("/posicao", methods=["GET"])
def posicao():
    if not robo_serial:
        return jsonify({"status": "erro", "msg": "Robô não conectado"})
    
    return jsonify({
        "status": "ok",
        "posicao": robo_serial.current_position
    })

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # Conectar à serial só no processo final
        robo_serial = RoboSerial()
        if inicializar_conexao():
            app.run(host="0.0.0.0", port=5000, debug=False)
        else:
            print("Erro ao conectar com o robô.")
    else:
        # Processo inicial — não conecta ainda
        app.run(host="0.0.0.0", port=5000, debug=True)
  