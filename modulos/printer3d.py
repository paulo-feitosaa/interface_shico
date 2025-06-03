import serial
import time


class Printer3d:

    def __init__(self, baudrate=115200):
        self.baudrate = baudrate
        self.serial = None
        self.start_time = None

    def wait_for_ok(self):
        """Aguarda uma linha que contenha 'ok' (pode estar junto de dados, como em M105)."""
        while True:
            response = self.serial.readline().decode('utf-8', errors='ignore').strip()
            if response:
                print(f"<[R: Impressora] {response}")
                if 'ok' in response.lower():
                    break

    def send_gcode(self, clean_line):
        print(f">[Impressora] {clean_line}")     
        self.serial.write((clean_line + '\n').encode('utf-8'))
        self.wait_for_ok()
        if clean_line == "M109 S200":
            self.start_time = time.time()

    def send_file(self, gcode):
        try:
            self.serial.reset_input_buffer()
            print("Conectado. Iniciando envio do G-code...\n")
            lines = gcode.splitlines()
            for line in lines:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith(';'):
                    self.serial.write((clean_line + '\n').encode('utf-8'))
                    print(f"> {clean_line}")
                    self.wait_for_ok()

            print("\n✅ Envio do G-code concluído com sucesso!")
            return 'Ok'

        except serial.SerialException as e:
            print(f"Erro na comunicação serial: {e}")
            return "Erro na comunicação serial"
        except FileNotFoundError:
            print("Arquivo G-code não encontrado.")
            return "Arquivo G-code não encontrado."
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return "Erro inesperado: "