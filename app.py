import customtkinter as ctk
import tkinter.messagebox as messagebox
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
        self.combo_com = ctk.CTkComboBox(self.frame_izq, values=["SIMULADOR (Prueba Local)", "COM1", "COM2", "COM3", "COM4", "COM5"])
        self.combo_com.set("COM1") # Por defecto real en producción
        self.combo_com.pack(side="bottom", pady=(0, 20))

        # ==================== FRAME DERECHO ====================
        self.frame_der = ctk.CTkFrame(self, corner_radius=10)
        self.frame_der.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        self.btn_escanear = ctk.CTkButton(self.frame_der, text="🔄 1. Conectar y Analizar Data", height=50, command=lambda: self.arrancar_hilo(self.ejecutar_escaneo))
        self.btn_escanear.pack(pady=10, padx=20, fill="x")

        self.btn_detener = ctk.CTkButton(self.frame_der, text="⏹️ Detener Reinicio", height=40, fg_color="#D97706", hover_color="#B45309", command=lambda: self.arrancar_hilo(self.ejecutar_detener))
        self.btn_detener.pack(pady=10, padx=20, fill="x")

        self.btn_reparar = ctk.CTkButton(self.frame_der, text="🗑️ Eliminar NO y Reiniciar", height=40, fg_color="#DC2626", hover_color="#991B1B", command=self.pedir_confirmacion_reparar)
        self.btn_reparar.pack(pady=10, padx=20, fill="x")

        self.btn_trx = ctk.CTkButton(self.frame_der, text="💳 Extraer Transacción Reciente", height=40, fg_color="#059669", hover_color="#047857", command=lambda: self.arrancar_hilo(self.ejecutar_trx))
        self.btn_trx.pack(pady=10, padx=20, fill="x")

        self.label_terminal = ctk.CTkLabel(self.frame_der, text="Salida de Consola:", font=ctk.CTkFont(size=12, weight="bold"))
        self.label_terminal.pack(anchor="w", padx=20, pady=(10, 0))

        self.textbox_consola = ctk.CTkTextbox(self.frame_der, height=150, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_consola.pack(padx=20, pady=(5, 20), fill="both", expand=True)

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
            if "ifconfig" in cmd: resp = "inet 10.38.64.10"
            elif cmd == "": resp = "root@cv4-28000001847:/home/pds#"
            elif cmd == "ll" and "trx" not in cmd: resp = "drwx V_8\n-rw- ok_8\ndrwx v_12\ndrwx NO_12\n-rw- check_V_8"
            elif "tail" in cmd: resp = "INFO log init\nSAM COLD RESET\nWARN low disk"
            elif "rm " in cmd: resp = ""
            elif "trx" in cmd and "ll" in cmd: resp = "drwx 1\ndrwx 21\n-rw- idx_21_07401847_2026.idx"
            else: resp = f"Comando '{cmd}'."
            
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
            self.log(f"\n[+] Abierto puerto {puerto}")
            time.sleep(0.5)

            # Presionar enter a ver si pide login o tira el prompt
            resp = self.enviar_y_leer("", delay=0.5)
            if "login:" in resp.lower() or "root" not in resp:
                self.log("[+] Enviando credenciales de root...")
                self.enviar_y_leer("root", delay=0.5)
                self.enviar_y_leer("mesdk002", delay=1.0)
            
            return True
        except Exception as e:
            self.log(f"[ERROR] No se pudo conectar a {puerto}: {e}")
            return False

    # ================= FLUJOS PRINCIPALES =================
    
    def ejecutar_escaneo(self):
        if not self.abrir_conexion():
            return
        
        try:
            # 1. Obtener ID del prompt
            resp = self.enviar_y_leer("", delay=0.5)
            # Buscamos los ultimos 4 digitos antes de los dospuntos o arrobas: ej root@cv4-28000001847
            id_match = re.search(r'280+(\d{4})(?!\d)', resp)
            if id_match:
                self.lbl_id.configure(text=f"ID Validador: {id_match.group(1)}", text_color="green")
            else:
                self.lbl_id.configure(text="ID Validador: --")

            # 2. Revisar IP eth0 (Mejorado para buscar ips limpias tambien)
            resp_ip = self.enviar_y_leer("ifconfig eth0", delay=0.5)
            ip_match = re.search(r'inet\s+(?:addr:)?(\d+\.\d+\.\d+\.\d+)', resp_ip)
            if ip_match:
                self.lbl_ip.configure(text=f"IP (eth0): {ip_match.group(1)}")
            
            # 3. Leer Versiones
            self.enviar_y_leer("cd /home/pds", delay=0.5)
            listado_ll = self.enviar_y_leer("ll", delay=1.0)
            
            # Parsear resultados insensible a MAYUSCULAS
            v_nums = []
            ok_str, no_str, check_str = "--", "--", "--"
            self.target_no_version = None

            for palabra in listado_ll.split():
                p_lower = palabra.lower()
                if p_lower.startswith("v_"):
                    num = re.findall(r'\d+', p_lower)
                    if num: v_nums.append((int(num[-1]), palabra))
                elif p_lower.startswith("ok_"):
                    ok_str = palabra
                elif p_lower.startswith("no_"):
                    no_str = palabra
                    self.target_no_version = palabra # Guardamos EXACTO para borrarlo bien
                elif p_lower.startswith("check_"):
                    check_str = palabra
            
            # Seleccionar el v_ más alto si existen varios
            v_max_str = max(v_nums, key=lambda x: x[0])[1] if v_nums else "--"

            self.lbl_v_max.configure(text=f"Versión Alta (v_): {v_max_str}")
            self.lbl_ok.configure(text=f"Estado OK_ : {ok_str}", text_color="green" if ok_str != "--" else "white")
            self.lbl_no.configure(text=f"Estado NO_ : {no_str}", text_color="red" if no_str != "--" else "white")
            self.lbl_check.configure(text=f"Estado CHECK_ : {check_str}", text_color="orange" if check_str != "--" else "white")

            # 4. Logs Mval
            salida_log = self.enviar_y_leer("tail -200 /home/pds/logs/Mval/Mval_archivolog.log", delay=1.5)
            if "SAM COLD RESET" in salida_log:
                self.lbl_sam.configure(text="SAM COLD RESET: ALERTA ROJA", fg_color="red", text_color="white")
            else:
                self.lbl_sam.configure(text="SAM COLD RESET: OK (No hay error)", fg_color="green", text_color="white")

            self.log("\n[=========== ESCANEO FINALIZADO ===========]")
        
        except Exception as e:
            self.log(f"[ERROR EXCEPCIÓN] {e}")

    def ejecutar_detener(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Ejecuta la conexión (Conectar y Analizar Data) primero.")
            return
        
        self.log("\n[-] Enviando comando para DETENER GENERADOR...")
        self.enviar_y_leer("ngc --stop daemon/generador_partida", delay=1.0)
        self.log("[+] Comando enviado exitosamente.")

    def pedir_confirmacion_reparar(self):
        # Escudo UI para confirmación del comando a ejecutar
        if not self.target_no_version or not self.target_no_version.lower().startswith("no_"):
            messagebox.showwarning("Invalido", "El sistema NO reportó ninguna versión con error (NO_). No hay nada que borrar.")
            return
            
        comandos_str = f"1. rm -r /home/pds/{self.target_no_version}\n2. sync\n3. ngreboot"
        
        # Leemos confirmación antes de la destrucción
        resp = messagebox.askyesno("CONFIRMACIÓN DE COMANDOS CRÍTICOS", f"¿Estás completamente seguro de enviar esto al Validador?\n\n{comandos_str}")
        if resp:
            self.arrancar_hilo(self.ejecutar_reparacion_real)
        else:
            self.log("[+] Acción Cancelada por el Usuario.")

    def ejecutar_reparacion_real(self):
        # Esta es la ruta segura, corre en Hilo por detras despues de apretar YES
        self.log(f"\n[!] PROCEDIENDO A HIGIENIZAR CARPETA: {self.target_no_version}")
        self.enviar_y_leer(f"rm -r /home/pds/{self.target_no_version}", delay=1.0)
        
        ll_post = self.enviar_y_leer("ll /home/pds", delay=1.0)
        if self.target_no_version in ll_post:
            self.log(f"[!!!] FALLO: {self.target_no_version} sigue apareciendo en el LL. Puede requerir permisos sudo o estaba bloqueada.")
        else:
            self.log(f"[+] BORRADO VERIFICADO: {self.target_no_version} fue eliminada. Sincronizando FS...")
            
        self.enviar_y_leer("sync", delay=2.0)
        self.log("[+] Forzando Reinicio (ngreboot)...")
        self.enviar_y_leer("ngreboot", delay=1.0)
        
        if self.ser: self.ser.close()
        self.log("[-] Validador Cerrado. Espera a que prenda físicamente.")

    def ejecutar_trx(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Ejecuta la conexión primero para abrir el COM.")
            return
            
        self.log("\n[-] BUSCANDO DIRECTORIO DE ÚLTIMA TRANSACCIÓN...")
        self.enviar_y_leer("cd /home/pds/btransa/trx", delay=0.5)
        salida_ll = self.enviar_y_leer("ll", delay=1.0)
        
        # Tu dijiste que las TRX (.idx) salen en el MISMO LL junto con las carpetas.
        # Buscamos todas las palabras que sean idx_ algo
        idx_archivos = []
        for linea in salida_ll.split('\n'):
            linea = linea.strip()
            arr = linea.split()
            if arr:
                nombre = arr[-1]
                if nombre.lower().startswith("idx_"):
                    # Extraer el numero intermedio para comparar y sacar el maximo
                    # ejemplo: idx_21_07401847_2026.idx
                    try:
                        partes = nombre.split('_')
                        if len(partes) > 1 and partes[1].isdigit():
                            num = int(partes[1])
                            idx_archivos.append((num, nombre))
                    except:
                        pass
        
        if idx_archivos:
            # Ordenamos por numero y agarramos el mas alto (la mas nueva)
            max_idx_nombre = max(idx_archivos, key=lambda x: x[0])[1]
            self.log(f"\n[=============== TRX ENCONTRADO ===============]")
            self.log(f"Último Archivo IDX Extraído:")
            self.log(f"-> {max_idx_nombre}")
            self.log(f"[==============================================]\n")
        else:
            self.log("[X] No se hallaron archivos idx_ en la carpeta raíz trx.")


if __name__ == "__main__":
    app = ValidadorApp()
    app.mainloop()
