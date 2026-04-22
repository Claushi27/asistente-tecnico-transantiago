import customtkinter as ctk
import time
import threading
import re
import serial
import traceback

# Configuración inicial de la interfaz
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Regex para limpiar la basura visual de la consola Linux (colores ANSI)
ansi_escape = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class ValidadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Ventana principal
        self.title("Asistente Validador Transantiago - Producción")
        self.geometry("1000x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.ser = None # Conector Serial
        self.target_no_version = None # Guardará la carpeta no_ a borrar

        self._crear_interfaz()

    def _crear_interfaz(self):
        # ==================== FRAME IZQUIERDO ====================
        self.frame_izq = ctk.CTkFrame(self, width=350, corner_radius=10)
        self.frame_izq.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.frame_izq.grid_propagate(False)

        self.label_titulo_diag = ctk.CTkLabel(self.frame_izq, text="Estado del Equipo", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_titulo_diag.pack(pady=(20, 10))

        self.lbl_id = ctk.CTkLabel(self.frame_izq, text="ID Validador: DESCONECTADO", text_color="yellow", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_id.pack(pady=10)
        
        self.lbl_ip = ctk.CTkLabel(self.frame_izq, text="IP (eth0): --", font=ctk.CTkFont(size=12))
        self.lbl_ip.pack(pady=5)

        self.frame_versiones = ctk.CTkFrame(self.frame_izq, fg_color="transparent")
        self.frame_versiones.pack(pady=20, padx=10, fill="x")

        self.lbl_v_max = ctk.CTkLabel(self.frame_versiones, text="Versión Alta (v_): --")
        self.lbl_v_max.pack(anchor="w", pady=2)
        self.lbl_ok = ctk.CTkLabel(self.frame_versiones, text="Estado OK_ : --", text_color="green")
        self.lbl_ok.pack(anchor="w", pady=2)
        self.lbl_no = ctk.CTkLabel(self.frame_versiones, text="Estado NO_ : --", text_color="red")
        self.lbl_no.pack(anchor="w", pady=2)
        self.lbl_check = ctk.CTkLabel(self.frame_versiones, text="Estado CHECK_ : --", text_color="orange")
        self.lbl_check.pack(anchor="w", pady=2)

        self.lbl_sam = ctk.CTkLabel(self.frame_izq, text="SAM COLD RESET: --", font=ctk.CTkFont(size=14, weight="bold"), fg_color="gray", corner_radius=5)
        self.lbl_sam.pack(pady=20, ipadx=10, ipady=5)

        # Combo para seleccionar puerto COM
        self.lbl_com = ctk.CTkLabel(self.frame_izq, text="Seleccionar Puerto Serial:")
        self.lbl_com.pack(side="bottom", pady=(0, 5))
        self.combo_com = ctk.CTkComboBox(self.frame_izq, values=["SIMULADOR (Prueba Local)", "COM1", "COM2", "COM3", "COM4"])
        self.combo_com.set("SIMULADOR (Prueba Local)")
        self.combo_com.pack(side="bottom", pady=(0, 20))

        # ==================== FRAME DERECHO ====================
        self.frame_der = ctk.CTkFrame(self, corner_radius=10)
        self.frame_der.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        self.btn_escanear = ctk.CTkButton(self.frame_der, text="🔄 1. Conectar y Analizar Data", height=50, command=lambda: self.arrancar_hilo(self.ejecutar_escaneo))
        self.btn_escanear.pack(pady=10, padx=20, fill="x")

        self.btn_detener = ctk.CTkButton(self.frame_der, text="⏹️ Detener Reinicio", height=40, fg_color="#D97706", hover_color="#B45309", command=lambda: self.arrancar_hilo(self.ejecutar_detener))
        self.btn_detener.pack(pady=10, padx=20, fill="x")

        self.btn_reparar = ctk.CTkButton(self.frame_der, text="🗑️ Eliminar NO y Reiniciar", height=40, fg_color="#DC2626", hover_color="#991B1B", command=lambda: self.arrancar_hilo(self.ejecutar_reparacion))
        self.btn_reparar.pack(pady=10, padx=20, fill="x")

        self.btn_trx = ctk.CTkButton(self.frame_der, text="💳 Extraer Transacción Reciente", height=40, fg_color="#059669", hover_color="#047857", command=lambda: self.arrancar_hilo(self.ejecutar_trx))
        self.btn_trx.pack(pady=10, padx=20, fill="x")

        self.textbox_consola = ctk.CTkTextbox(self.frame_der, height=150, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_consola.pack(padx=20, pady=20, fill="both", expand=True)

    def log(self, texto):
        self.textbox_consola.insert("end", texto + "\n")
        self.textbox_consola.see("end")

    def limpiar_texto(self, texto):
        return ansi_escape.sub('', texto).strip()

    def arrancar_hilo(self, funcion):
        threading.Thread(target=funcion, daemon=True).start()

    # ================= LOGICA SERIAL Y CONSOLA =================
    def enviar_y_leer(self, cmd, delay=1.0):
        # MODO SIMULADOR (Para probar en casa)
        if self.combo_com.get() == "SIMULADOR (Prueba Local)":
            time.sleep(delay / 2) # Falso delay de red
            resp = ""
            if "ifconfig" in cmd: resp = "inet addr:192.168.100.99"
            elif cmd == "": resp = "root@cv4 - 289999"
            elif cmd == "ll": resp = "drwx v_8\n-rw- ok_8\ndrwx v_12\ndrwx no_12\n-rw- check_9"
            elif "tail" in cmd: resp = "INFO log init\nSAM COLD RESET\nWARN low disk"
            elif "rm " in cmd: resp = ""
            elif "trx" in cmd and "ll" in cmd: resp = "drwx 1\ndrwx 50"
            elif cmd == "ll" and "50" in cmd: resp = "-rw- idx_91919191" # Simula entrar a carpeta 50
            else: resp = f"Comando '{cmd}' ejecutado en Validador Falso."
            
            self.log(f"> {cmd}\n{resp}")
            return resp

        # MODO PRODUCCIÓN REAL (PySerial)
        if not self.ser or not self.ser.is_open:
            return ""
        self.ser.write((cmd + "\n").encode('utf-8', errors='ignore'))
        time.sleep(delay)
        output = self.ser.read_all().decode('utf-8', errors='ignore')
        salida_limpia = self.limpiar_texto(output)
        self.log(f"> {cmd}\n{salida_limpia}")
        return salida_limpia

    def abrir_conexion(self):
        try:
            puerto = self.combo_com.get()
            
            if puerto == "SIMULADOR (Prueba Local)":
                self.log("[+] MODO SIMULADOR ACTIVADO. Emulando consola Linux de validador...")
                return True
                
            if self.ser and self.ser.is_open:
                self.ser.close()
            # Validador transantiago usa tipicamente 115200 baudios en su puerto consola
            self.ser = serial.Serial(puerto, 115200, timeout=2)
            self.log(f"[+] Abierto puerto {puerto}")
            time.sleep(0.5)

            # Presionar enter a ver si pide login
            resp = self.enviar_y_leer("", delay=0.5)
            if "login:" in resp.lower() or "root" not in resp:
                self.log("[+] Enviando credenciales de root...")
                self.enviar_y_leer("root", delay=0.5)
                self.enviar_y_leer("mesdk002", delay=1.0)
            
            return True
        except Exception as e:
            self.log(f"[ERROR] No se pudo abrir {puerto}: {e}")
            return False

    # ================= FLUJOS PRINCIPALES =================
    
    def ejecutar_escaneo(self):
        if not self.abrir_conexion():
            return
        
        try:
            # 1. Obtener ID del prompt
            resp = self.enviar_y_leer("", delay=0.5)
            # Buscamos algo como root@cv4 - 2800000
            id_match = re.search(r'root@cv4\s*-\s*28(\d{4})', resp)
            if id_match:
                self.lbl_id.configure(text=f"ID Validador: {id_match.group(1)}", text_color="green")
            else:
                self.lbl_id.configure(text="ID Validador: Desconocido")

            # 2. Revisar IP eth0
            resp_ip = self.enviar_y_leer("ifconfig eth0", delay=0.5)
            ip_match = re.search(r'inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)', resp_ip)
            if ip_match:
                self.lbl_ip.configure(text=f"IP (eth0): {ip_match.group(1)}")
            
            # 3. Leer Versiones
            self.enviar_y_leer("cd /home/pds", delay=0.5)
            listado_ll = self.enviar_y_leer("ll", delay=1.0)
            
            # Parsear resultados
            v_nums = []
            ok_str, no_str, check_str = "--", "--", "--"
            self.target_no_version = None

            for palabra in listado_ll.split():
                if palabra.startswith("v_"):
                    # Extraer digitos
                    num = re.findall(r'\d+', palabra)
                    if num: v_nums.append(int(num[-1]))
                elif palabra.startswith("ok_"):
                    ok_str = palabra
                elif palabra.startswith("no_"):
                    no_str = palabra
                    self.target_no_version = palabra # Guardamos matemáticamente y seguro
                elif palabra.startswith("check_"):
                    check_str = palabra
            
            v_max = f"v_{max(v_nums)}" if v_nums else "--"

            self.lbl_v_max.configure(text=f"Versión Alta (v_): {v_max}")
            self.lbl_ok.configure(text=f"Estado OK_ : {ok_str}", text_color="green" if ok_str != "--" else "white")
            self.lbl_no.configure(text=f"Estado NO_ : {no_str}", text_color="red" if no_str != "--" else "white")
            self.lbl_check.configure(text=f"Estado CHECK_ : {check_str}", text_color="orange" if check_str != "--" else "white")

            if no_str != "--":
                self.log(f"⚠️ ATENCIÓN: Se detectó versión con fallo: {no_str}. Puedes usar el botón de eliminar.")

            # 4. Logs Mval
            # El usuario confirmó que es estático
            salida_log = self.enviar_y_leer("tail -200 /home/pds/logs/Mval/Mval_archivolog.log", delay=1.5)
            if "SAM COLD RESET" in salida_log:
                self.lbl_sam.configure(text="SAM COLD RESET: ALERTA DETECTADA ROJA", fg_color="red", text_color="white")
            else:
                self.lbl_sam.configure(text="SAM COLD RESET: NO HAY ERRORES", fg_color="green", text_color="white")

            self.log("\n[=========== ESCANEO FINALIZADO ===========]")
        
        except Exception as e:
            self.log(f"[ERROR EXCEPCIÓN] {e}")
            self.log(traceback.format_exc())

    def ejecutar_detener(self):
        if not self.ser or not self.ser.is_open:
            self.log("[ERROR] Ejecuta la conexión (Escaneo) primero.")
            return
        self.enviar_y_leer("ngc --stop daemon/generador_partida", delay=1.0)
        self.log("[+] Comando detener enviado. Revisa confirmación de status arriba.")

    def ejecutar_reparacion(self):
        if not self.ser or not self.ser.is_open:
            self.log("[ERROR] Debes conectarte primero.")
            return
        
        # EL ESCUDO DE SEGURIDAD (Safeguard)
        if not self.target_no_version or not self.target_no_version.startswith("no_"):
            self.log("[SEC ERROR] No se detectó ninguna carpeta válida 'no_...' para borrar de forma segura. Operación abortada.")
            return

        self.log(f"\n[!] INICIANDO HIGIENIZACIÓN DE: {self.target_no_version}")
        self.enviar_y_leer(f"rm -r /home/pds/{self.target_no_version}", delay=1.0)
        
        # Validar si se eliminó
        ll_post = self.enviar_y_leer("ll /home/pds", delay=1.0)
        if self.target_no_version in ll_post:
            self.log(f"[!!!] ADVERTENCIA: {self.target_no_version} parece no haberse eliminado. Puede que necesitemos sudo o el comando ll dio error.")
        else:
            self.log(f"[+] Eliminado exitosamente: {self.target_no_version}. Sincronizando...")
        
        self.enviar_y_leer("sync", delay=2.0)
        self.log("[+] Reiniciando Validador (ngreboot)...")
        self.enviar_y_leer("ngreboot", delay=1.0)
        self.ser.close()
        self.log("[-] Conexión cerrada. Espera a que el equipo levante de nuevo.")

    def ejecutar_trx(self):
        if not self.ser or not self.ser.is_open:
            self.log("[ERROR] Ejecuta la conexión (Escaneo) primero para abrir el COM.")
            return
            
        self.log("\n[-] BUSCANDO ÚLTIMAS ID TRX...")
        self.enviar_y_leer("cd /home/pds/btransa/trx", delay=0.5)
        salida_directorios = self.enviar_y_leer("ll", delay=1.0)
        
        # Parse output folder seeking logic
        numeros_carpetas = []
        for linea in salida_directorios.split('\n'):
            linea = linea.strip()
            # La salida de ll suele tener los nombres al final, ejemplo: "drwxr-xr-x 2 root root 4096 oct 24 10:00 45"
            arr = linea.split()
            if arr:
                nombre = arr[-1]
                if nombre.isdigit():
                    num = int(nombre)
                    if 0 <= num <= 99:
                        numeros_carpetas.append(num)
        
        if not numeros_carpetas:
            self.log("[X] No se encontraron carpetas numeradas activas en trx.")
            return
        
        max_carpeta = str(max(numeros_carpetas))
        self.log(f"[+] Ingresando a la carpeta más alta encontrada: {max_carpeta}")
        
        self.enviar_y_leer(f"cd {max_carpeta}", delay=0.5)
        salida_archivos = self.enviar_y_leer("ll", delay=1.0)
        
        idx_final = None
        # Buscamos referencias de archivos idx_
        for texto in salida_archivos.split():
            if texto.startswith("idx_"):
                idx_final = texto
        
        if idx_final:
            self.log(f"\n[=============== TRX ENCONTRADO ===============]")
            self.log(f"Última Transacción ID: {idx_final}")
            self.log(f"[==============================================]\n")
        else:
            self.log("[X] No se hallaron archivos idx_ en la carpeta.")


if __name__ == "__main__":
    app = ValidadorApp()
    app.mainloop()
