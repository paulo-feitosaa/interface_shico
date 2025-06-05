# app.py
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import serial
import serial.tools.list_ports
import time
import os
from modulos.printer3d import Printer3d
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = "chave-secreta"

robo_serial = None
homed = False
printer_3d = None

ROBOT_ONLY_COMMANDS = {'G28'}
SHARED_COMMANDS = {'G90', 'G91'}
MOVEMENT_COMMANDS = {'G0', 'G1'}

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

    def send_gcodes(self, gcodes, timeout=3):
        for gcode in gcodes:
            try:
                self.serial.write(gcode.encode())
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.serial.in_waiting > 0:
                        line = self.serial.readline().decode('utf-8').rstrip()
                        return line
            except serial.SerialTimeoutException:
                # print("Timeout: Não foi possível escrever na serial no tempo definido.")
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
    global printer_3d
    print('Conectando...')
    if printer_3d.connect():
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
    else:
        return False
        
    
    

def send_command(line, origem):
    # ser.write((line + '\n').encode('utf-8'))
    print(f">[{origem}] {line}")
    # print("\n")
    # wait_for_ok(ser, origem)

def route_command(line, z_offset):
    global robo_serial
    global printer_3d
    print(f"\n> Linha original: {line}")
    clean_line = line.split(';', 1)[0].strip()  # Remove comentário
    tokens = clean_line.split()
    if not tokens:
        return

    cmd = tokens[0]

    if cmd in SHARED_COMMANDS:
        # send_command(clean_line, "Impressora")
        printer_3d.send_gcode(clean_line)
        # send_command(clean_line, "Robô")
        print(f">[Robo] {clean_line}")   
        response = robo_serial.send_gcodes([f"{clean_line}\r\n",])
        print(f"<[R: Robo] {response}")

    elif cmd in MOVEMENT_COMMANDS:
        has_e = any(token.startswith('E') for token in tokens[1:])
        robot_params = []
        printer_params = []

        for token in tokens[1:]:
            if token.startswith(('X', 'Y')):
                robot_params.append(token)

            elif token.startswith('Z'):
                try:
                    z_value = float(token[1:])
                    z_robot = z_value + z_offset
                    robot_params.append(f"Z{z_robot:.3f}")
                except ValueError:
                    pass

            elif token.startswith('F'):
                try:
                    f_value = float(token[1:])
                    f_robot = f"F{f_value / 60:.2f}"  # mm/min → mm/s
                    robot_params.append(f_robot)
                    if has_e:
                        printer_params.append(token)  # Envia F original para impressora se tiver E
                except ValueError:
                    pass

            elif token.startswith('E'):
                printer_params.append(token)

        if has_e:
            if printer_params:
                # send_command(f"{cmd} {' '.join(printer_params)}", "Impressora")
                printer_3d.send_gcode(f"{cmd} {' '.join(printer_params)}")
            if robot_params:
                # send_command(f"{cmd} {' '.join(robot_params)}", "Robô")
                command = f"{cmd} {' '.join(robot_params)}\r\n"
                print(f">[Robo] {command}")  
                response = robo_serial.send_gcodes([command,])   
                print(f"<[R: Robo] {response}")       
        else:
            # send_command(f"{cmd} {' '.join(robot_params)}", "Robô")
            command = f"{cmd} {' '.join(robot_params)}\r\n"
            print(f">[Robo] {command}")  
            response = robo_serial.send_gcodes([command,])
            print(f"<[R: Robo] {response}")

    elif cmd in ROBOT_ONLY_COMMANDS:
        # send_command(clean_line, "Robô")
        print(f">[Robo] {clean_line}")  
        response = robo_serial.send_gcodes([f"{clean_line}\r\n",])
        print(f"<[R: Robo] {response}")

    else:
        # send_command(clean_line, "Impressora")
        printer_3d.send_gcode(clean_line)

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
            print(f"Comando: {cmd}")
            if "Home" in cmd:
                response = robo_serial.send_gcodes(['G28\r\n',], timeout=6)
                if response == 'Ok':
                    robo_serial.homed = True
                    robo_serial.current_position = robo_serial.get_position()
            elif robo_serial.homed:               
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
    if not robo_serial.serial or not printer_3d.serial:
        return jsonify({"status": "erro", "msg": "Robô ou impressora não conectado"})
    
    if "gcode" not in request.files:
        return jsonify({"status": "erro", "msg": "Arquivo G-code não enviado"})

    gcode_file = request.files["gcode"]
    filename = secure_filename(gcode_file.filename)

    # Exibe o conteúdo no terminal (como solicitado)
    conteudo = gcode_file.read().decode("utf-8")
    print("📄 Conteúdo do G-code recebido:")
    # print(conteudo)

    height = request.form.get("altura")
    print(f'Altura: {height}')
    # response = printer_3d.send_gcode(conteudo)

    try:
        print("Conectado. Iniciando envio do G-code...\n")
        lines = conteudo.splitlines()
        for line in lines:
            clean_line = line.strip()
            if clean_line and not clean_line.startswith(';'):
                route_command(clean_line, float(height))

        end_time = time.time() - printer_3d.start_time
        print("\n✅ Envio do G-code concluído com sucesso!")
        print(f"Duração da impressão: {end_time} s")
        response = f"\n✅ Envio do G-code concluído com sucesso!\nDuração da impressão: {end_time} s"
        
    except serial.SerialException as e:
        print(f"Erro na comunicação serial: {e}")
        response = "Erro na comunicação serial"
    except FileNotFoundError:
        print("Arquivo G-code não encontrado.")
        response = "Arquivo G-code não encontrado."
    # except Exception as e:
    #     print(f"Erro inesperado: {e}")
    #     response = "Erro inesperado: "

    return jsonify({
        "status": response,
    })


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # Conectar à serial só no processo final
        robo_serial = RoboSerial()
        printer_3d = Printer3d()
        if inicializar_conexao():
            app.run(host="0.0.0.0", port=5000, debug=True)
        else:
            print("Erro ao conectar com o robô ou impressora")
    else:
        # Processo inicial — não conecta ainda
        app.run(host="0.0.0.0", port=5000, debug=True)
  