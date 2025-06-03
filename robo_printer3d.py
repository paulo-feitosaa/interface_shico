import serial
import time
import re

# PORTAS e BAUDRATES - Ajuste conforme necessário
PRINTER_PORT = 'COM3'
ROBOT_PORT = 'COM4'
BAUDRATE = 115200
GCODE_FILE = 'g_codes/CE3E3V2_cube2mZ1.gcode'
# GCODE_FILE = 'g_codes/teste.gcode'
# Comandos específicos
ROBOT_ONLY_COMMANDS = {'G28'}
SHARED_COMMANDS = {'G90', 'G91'}
MOVEMENT_COMMANDS = {'G0', 'G1'}

def wait_for_ok(ser, origem):
    while True:
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        if response:
            print(f"<[{origem}] {response}")
            if 'ok' in response.lower():
                break

def send_command(ser, line, origem):
    # ser.write((line + '\n').encode('utf-8'))
    print(f">[{origem}] {line}")
    # print("\n")
    # wait_for_ok(ser, origem)


Z_OFFSET = -380.0  # Conversão de origem do eixo Z para o robô (mm)
def route_command(line, printer_ser, robot_ser):
    print(f"\n> Linha original: {line}")
    clean_line = line.split(';', 1)[0].strip()  # Remove comentário
    tokens = clean_line.split()
    if not tokens:
        return

    cmd = tokens[0]

    if cmd in SHARED_COMMANDS:
        send_command(robot_ser, clean_line, "Robô")
        send_command(printer_ser, clean_line, "Impressora")

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
                    z_robot = z_value + Z_OFFSET
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
            if robot_params:
                send_command(robot_ser, f"{cmd} {' '.join(robot_params)}", "Robô")
            if printer_params:
                send_command(printer_ser, f"{cmd} {' '.join(printer_params)}", "Impressora")
        else:
            send_command(robot_ser, f"{cmd} {' '.join(robot_params)}", "Robô")

    elif cmd in ROBOT_ONLY_COMMANDS:
        send_command(robot_ser, clean_line, "Robô")

    else:
        send_command(printer_ser, clean_line, "Impressora")

def process_gcode(printer_port, robot_port, baudrate, gcode_path):
    try:


            print("Inicializando conexões...")
            # time.sleep(2)
            # printer_ser.reset_input_buffer()
            # robot_ser.reset_input_buffer()
            printer_ser='Serial printer'
            robot_ser = 'Serial robo'
            # wait_for_ok(printer_ser, "Impressora")
            # wait_for_ok(robot_ser, "Robô")

            print("\nConectado. Iniciando envio do G-code...\n")

            with open(gcode_path, 'r') as file:
                for line in file:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith(';'):
                        route_command(clean_line, printer_ser, robot_ser)

            print("\n✅ Impressão híbrida finalizada com sucesso!")

    except serial.SerialException as e:
        print(f"Erro na comunicação serial: {e}")
    except FileNotFoundError:
        print("Arquivo G-code não encontrado.")
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    process_gcode(PRINTER_PORT, ROBOT_PORT, BAUDRATE, GCODE_FILE)
