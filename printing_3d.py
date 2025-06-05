import serial
import time

# Configurações
SERIAL_PORT = 'COM4'        # Altere para sua porta serial
BAUDRATE = 115200
GCODE_FILE = 'g_codes\CE3E3V2_cube2m_Z20V10.gcode'

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

            print(f"Conectado. Iniciando envio do G-code {gcode_path}...\n")

            with open(gcode_path, 'r') as file:
                for line in file:
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith(';'):
                        ser.write((clean_line + '\n').encode('utf-8'))
                        print(f"> {clean_line}")
                        wait_for_ok(ser)
                        if clean_line == "M109 S200":
                            start_time = time.time()

            end_time = time.time() - start_time
            print("\n✅ Envio do G-code concluído com sucesso!")
            print(f"Duração da impressão: {end_time} s")
            ser.close()
            
    except serial.SerialException as e:
        print(f"Erro na comunicação serial: {e}")     
    except FileNotFoundError:
        print("Arquivo G-code não encontrado.")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    except KeyboardInterrupt:
        ser.close()

if __name__ == "__main__":
    send_gcode(SERIAL_PORT, BAUDRATE, GCODE_FILE)
