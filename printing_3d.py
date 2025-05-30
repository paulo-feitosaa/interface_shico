import serial
import time

# Configurações
SERIAL_PORT = 'COM3'        # Altere para sua porta serial
BAUDRATE = 115200
GCODE_FILE = 'CE3E3V2_cube2mZ1.gcode'

def wait_for_ok(ser):
    """Aguarda uma linha que contenha 'ok' (pode estar junto de dados, como em M105)."""
    while True:
        response = ser.readline().decode('utf-8', errors='ignore').strip()
        if response:
            print(f"< {response}")
            if 'ok' in response.lower():
                break

def send_gcode(port, baudrate, gcode_path):
    try:
        with serial.Serial(port, baudrate, timeout=5) as ser:
            print("Conectando à impressora...")
            time.sleep(5)  # Aguarda inicialização
            ser.reset_input_buffer()

            # Espera pela primeira resposta da impressora (ex: "start" ou "echo:..."), até o primeiro "ok"
            # wait_for_ok(ser)

            print("Conectado. Iniciando envio do G-code...\n")

            with open(gcode_path, 'r') as file:
                for line in file:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith(';'):
                        ser.write((clean_line + '\n').encode('utf-8'))
                        print(f"> {clean_line}")
                        wait_for_ok(ser)

            print("\n✅ Envio do G-code concluído com sucesso!")

    except serial.SerialException as e:
        print(f"Erro na comunicação serial: {e}")
    except FileNotFoundError:
        print("Arquivo G-code não encontrado.")
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    send_gcode(SERIAL_PORT, BAUDRATE, GCODE_FILE)
