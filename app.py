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

# Regex para borrar colores de Linux ANSI
ansi_escape = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class ValidadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Asistente Validador Transantiago - Producción")
        self.geometry("1050x750")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.ser = None 
        self.target_no_version = None 
        self.simulacion_en_carpeta_21 = False

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

        self.lbl_com = ctk.CTkLabel(self.frame_izq, text="Seleccionar Puerto Serial:")
        self.lbl_com.pack(side="bottom", pady=(0, 5))
        self.combo_com = ctk.CTkComboBox(self.frame_izq, values=["SIMULADOR (Prueba Local)", "COM1", "COM2", "COM3"])
        self.combo_com.set("COM1") 
        self.combo_com.pack(side="bottom", pady=(0, 20))

        # ==================== FRAME DERECHO ====================
        self.frame_der = ctk.CTkFrame(self, corner_radius=10)
        self.frame_der.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")

        # RECUADRO DE COMANDO ACTUAL (Panel Arriba-Derecha)
        self.frame_comando = ctk.CTkFrame(self.frame_der, fg_color="#0F172A", border_width=2, border_color="#38BDF8", corner_radius=8, height=120)
        self.frame_comando.pack(pady=(20, 10), padx=20, fill="x")
        self.frame_comando.pack_propagate(False)
        
        ctk.CTkLabel(self.frame_comando, text="⚡ TERMINAL DE COMANDOS EN VIVO", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8").pack(pady=(5,0), anchor="w", padx=10)
        
        self.textbox_comandos = ctk.CTkTextbox(self.frame_comando, height=80, fg_color="transparent", text_color="#A7F3D0", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"))
        self.textbox_comandos.pack(pady=(5, 5), padx=10, fill="both", expand=True)
        self.textbox_comandos.insert("end", "[Esperando instrucción...]\n")

        # BOTONES
        self.btn_escanear = ctk.CTkButton(self.frame_der, text="🔄 1. Conectar y Analizar Data", height=50, command=lambda: self.arrancar_hilo(self.ejecutar_escaneo))
        self.btn_escanear.pack(pady=10, padx=20, fill="x")

        self.btn_detener = ctk.CTkButton(self.frame_der, text="⏹️ Detener Reinicio", height=40, fg_color="#D97706", hover_color="#B45309", command=lambda: self.arrancar_hilo(self.ejecutar_detener))
        self.btn_detener.pack(pady=10, padx=20, fill="x")

        self.btn_reparar = ctk.CTkButton(self.frame_der, text="🗑️ Eliminar NO y Reiniciar", height=40, fg_color="#DC2626", hover_color="#991B1B", command=self.pedir_confirmacion_reparar)
        self.btn_reparar.pack(pady=10, padx=20, fill="x")
        
        self.btn_reinicio = ctk.CTkButton(self.frame_der, text="🔄 Forzar Reinicio (ngreboot)", height=40, fg_color="#475569", hover_color="#334155", command=self.pedir_confirmacion_reinicio)
        self.btn_reinicio.pack(pady=10, padx=20, fill="x")

        self.btn_trx = ctk.CTkButton(self.frame_der, text="💳 Extraer Transacción Reciente", height=40, fg_color="#059669", hover_color="#047857", command=lambda: self.arrancar_hilo(self.ejecutar_trx))
        self.btn_trx.pack(pady=10, padx=20, fill="x")

        self.label_terminal = ctk.CTkLabel(self.frame_der, text="Log Histórico de Acciones:", font=ctk.CTkFont(size=12, weight="bold"))
        self.label_terminal.pack(anchor="w", padx=20, pady=(5, 0))

        self.textbox_consola = ctk.CTkTextbox(self.frame_der, height=120, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_consola.pack(padx=20, pady=(5, 10), fill="both", expand=True)

        # RECUADRO DE COMANDO MANUAL DIRECTO (Evita usar PuTTY totalmente)
        self.frame_manual = ctk.CTkFrame(self.frame_der, fg_color="transparent")
        self.frame_manual.pack(pady=(0, 20), padx=20, fill="x")
        
        self.entry_manual = ctk.CTkEntry(self.frame_manual, placeholder_text="Escribe un comando personalizado aquí (Ej: ls -la)...", font=ctk.CTkFont(family="Consolas", size=13))
        self.entry_manual.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_manual.bind("<Return>", lambda event: self.arrancar_hilo(self.enviar_comando_manual))
        
        self.btn_manual = ctk.CTkButton(self.frame_manual, text="📤 Enviar", width=100, fg_color="#4F46E5", hover_color="#4338CA", command=lambda: self.arrancar_hilo(self.enviar_comando_manual))
        self.btn_manual.pack(side="right")

    def log(self, texto):
        self.textbox_consola.insert("end", texto + "\n")
        self.textbox_consola.see("end")

    def limpiar_texto(self, texto):
        return ansi_escape.sub('', texto).strip()

    def arrancar_hilo(self, funcion):
        threading.Thread(target=funcion, daemon=True).start()

    # ================= LOGICA SERIAL Y DE TEXTO =================
    def enviar_y_leer(self, cmd, delay=1.0):
        
        # --- 1. Actualizar "Plantallita Mágica de Comandos en vivo" ---
        comando_para_mostrar = "[ENTER]" if cmd == "" else f"> {cmd}"
        self.textbox_comandos.insert("end", comando_para_mostrar + "\n")
        self.textbox_comandos.see("end")
        self.update_idletasks() # Forzar refresco visual inmediato

        # --- 2. Flujo de Simulación (Para pruebas puras en PC casa) ---
        if self.combo_com.get() == "SIMULADOR (Prueba Local)":
            time.sleep(delay / 2)
            resp = ""
            if "ifconfig" in cmd: resp = "inet 10.38.64.10"
            elif cmd == "": resp = "root@cv4-28000001847:/home/pds#"
            # Si estamos dentro de la carpeta TRX y pedimos listado:
            elif cmd == "ll" and self.simulacion_en_carpeta_21: resp = "-rw- trx_2190_07401847.bin\n-rw- trx_2191_07401847.bin\n-rw- trx_2193_07401847.bin"
            # Si estamos en ll general o pds:
            elif cmd == "ll" and "trx" not in cmd: resp = "drwx V_8\n-rw- ok_8\ndrwx v_12\ndrwx NO_12\n-rw- check_V_8\n-rw- infoval_07401847.csv"
            # Si estamos pidiendo la lista de directorios TRX principales
            elif "trx" in cmd and "ll" in cmd: resp = "drwxr-xr-x 0/\ndrwxr-xr-x 1/\ndrwxr-xr-x 21/\n-rw- idx_21_0740.idx"
            elif "tail" in cmd: resp = "INFO log init\nSAM COLD RESET\nWARN low disk"
            elif "rm " in cmd: resp = ""
            elif "cd 21" in cmd: 
                self.simulacion_en_carpeta_21 = True
                resp = ""
            elif "cd" in cmd:
                self.simulacion_en_carpeta_21 = False
                resp = ""
            else: resp = f"Ejecución simulada."
            
            self.log(f"> {cmd}\n{resp}")
            return resp

        # --- 3. Flujo Real PySerial hacia el Validador Físico ---
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
                self.log("\n[+] MODO SIMULADOR ACTIVADO. Emulando comandos locales...")
                self.simulacion_en_carpeta_21 = False
                return True
                
            if self.ser and self.ser.is_open:
                self.ser.close()
            # Validador transantiago usa tipicamente 115200 baudios en su puerto consola
            self.ser = serial.Serial(puerto, 115200, timeout=2)
            self.log(f"\n[+] Abierto puerto FÍSICO: {puerto}")
            time.sleep(0.5)

            # Presionar enter a ver si pide login 
            resp = self.enviar_y_leer("", delay=0.5)
            if "login:" in resp.lower() or "root" not in resp:
                self.log("[+] Enviando credenciales root...")
                self.enviar_y_leer("root", delay=0.5)
                self.enviar_y_leer("mesdk002", delay=1.0)
            
            return True
        except Exception as e:
            self.log(f"[ERROR CRÍTICO] No se pudo conectar a {puerto}. Verificá que no esté el PuTTY agarrando el puerto.\nDetalle: {e}")
            return False

    # ================= FLUJOS PRINCIPALES =================
    
    def ejecutar_escaneo(self):
        if not self.abrir_conexion():
            return
        
        try:
            # 1. Obtener ID (AMID Seguro) desde /home/pds/btransa
            self.enviar_y_leer("cd /home/pds/btransa", delay=0.5)
            salida_btransa = self.enviar_y_leer("ll", delay=1.0)
            
            amid_match = re.search(r'infoval_(\d+)\.csv', salida_btransa)
            if amid_match:
                self.lbl_id.configure(text=f"ID Validador: {amid_match.group(1)}", text_color="#00FFAA")
            else:
                self.lbl_id.configure(text="ID Validador: NO ENCONTRADO", text_color="red")

            resp_ip = self.enviar_y_leer("ifconfig eth0", delay=0.5)
            ip_match = re.search(r'inet\s+(?:addr:)?(\d+\.\d+\.\d+\.\d+)', resp_ip)
            if ip_match:
                self.lbl_ip.configure(text=f"IP (eth0): {ip_match.group(1)}")
            
            self.enviar_y_leer("cd /home/pds", delay=0.5)
            listado_ll = self.enviar_y_leer("ll", delay=1.0)
            
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
                    self.target_no_version = palabra 
                elif p_lower.startswith("check_"):
                    check_str = palabra
            
            v_max_str = max(v_nums, key=lambda x: x[0])[1] if v_nums else "--"

            self.lbl_v_max.configure(text=f"Versión Alta (v_): {v_max_str}")
            self.lbl_ok.configure(text=f"Estado OK_ : {ok_str}", text_color="green" if ok_str != "--" else "white")
            self.lbl_no.configure(text=f"Estado NO_ : {no_str}", text_color="red" if no_str != "--" else "white")
            self.lbl_check.configure(text=f"Estado CHECK_ : {check_str}", text_color="orange" if check_str != "--" else "white")

            salida_log = self.enviar_y_leer("tail -200 /home/pds/logs/Mval/Mval_archivolog.log", delay=1.5)
            if "SAM COLD RESET" in salida_log:
                self.lbl_sam.configure(text="SAM COLD RESET: ALERTA ROJA", fg_color="red", text_color="white")
            else:
                self.lbl_sam.configure(text="SAM COLD RESET: OK (No hay error)", fg_color="green", text_color="white")

            self.log("\n[=========== ESCANEO FINALIZADO ===========]")
            
            if self.target_no_version:
                self.log(f"[!] IMPORTANTE: Puedes pulsar el Botón Rojo para destruir ({self.target_no_version}) de forma segura.")
        
        except Exception as e:
            self.log(f"[ERROR EXCEPCIÓN] {e}")

    def ejecutar_detener(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero.")
            return
        
        self.enviar_y_leer("ngc --stop daemon/generador_partida", delay=1.0)
        self.log("[+] Comando detener enviado. Revisa confirmación visual.")

    def pedir_confirmacion_reinicio(self):
        resp = messagebox.askyesno("CONFIRMACIÓN", "¿Estás seguro que deseas enviar el comando ngreboot para reiniciar el equipo?")
        if resp:
            self.arrancar_hilo(self.ejecutar_reinicio_real)

    def ejecutar_reinicio_real(self):
        self.log("\n[!] Forzando Reinicio Térmico (ngreboot)...")
        self.enviar_y_leer("ngreboot", delay=1.0)
        if self.ser: self.ser.close()
        self.log("[-] Apagado. Desconecta cable y espera que prenda físico.")

    def enviar_comando_manual(self):
        comando = self.entry_manual.get().strip()
        if not comando: return
        
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero para enviar comandos.")
            return
            
        self.log(f"\n[-] MODO MANUAL INYECTÓ COMANDO:")
        self.enviar_y_leer(comando, delay=1.0)
        self.entry_manual.delete(0, "end")

    def pedir_confirmacion_reparar(self):
        if not self.target_no_version or not self.target_no_version.lower().startswith("no_"):
            messagebox.showwarning("Invalido", "El sistema detectó que tu equipo no tiene una versión NO_. No hay basura que borrar.")
            return
            
        comandos_str = f"1. rm -r /home/pds/{self.target_no_version}\n2. sync\n3. ngreboot"
        
        # PREGUNTA SEGURIDAD
        resp = messagebox.askyesno("CONFIRMACIÓN DE COMANDOS", f"Estás a punto de alterar el FileSystem del Validador.\n\nSe inyectará:\n{comandos_str}\n\n¿Estás de acuerdo?")
        if resp:
            self.arrancar_hilo(self.ejecutar_reparacion_real)
        else:
            self.log("[+] Comando abortado por el usuario.")

    def ejecutar_reparacion_real(self):
        self.log(f"\n[!] PROCEDIENDO A DESTRUIR CARPETA: {self.target_no_version}")
        self.enviar_y_leer(f"rm -r /home/pds/{self.target_no_version}", delay=1.0)
        
        # Doble Check
        ll_post = self.enviar_y_leer("ll /home/pds", delay=1.0)
        if self.target_no_version in ll_post:
            self.log(f"[!!!] No se borró {self.target_no_version}. Archivo protegido o comando rebotó.")
        else:
            self.log(f"[+] BORRADO VERIFICADO: Se destruyó completamente. Sincronizando...")
            
        self.enviar_y_leer("sync", delay=2.0)
        self.log("[+] Forzando Reinicio Térmico (ngreboot)...")
        self.enviar_y_leer("ngreboot", delay=1.0)
        
        if self.ser: self.ser.close()
        self.log("[-] Apagado. Desconecta cable y espera que prenda físico.")

    def ejecutar_trx(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero.")
            return
            
        self.log("\n[-] BUSCANDO CARPETAS GENERALES TRX...")
        self.enviar_y_leer("cd /home/pds/btransa/trx", delay=0.5)
        salida_ll = self.enviar_y_leer("ll", delay=1.0)
        
        # 1. Buscar las carpetas con números (ejemplo: 0/, 1/... 21/)
        carpetas_ids = []
        for linea in salida_ll.split('\n'):
            linea = linea.strip()
            # Asegurarse de que la línea corresponde a un directorio (empieza con 'd')
            # Esto evita el error de atrapar la línea inicial 'total 1580'
            if linea.startswith('d'):
                arr = linea.split()
                if arr:
                    # Quitar la barra inclinada si la tiene
                    nombre = arr[-1].replace("/", "") 
                    if nombre.isdigit():
                        carpetas_ids.append(int(nombre))
        
        if not carpetas_ids:
            self.log("[X] No se encontraron carpetas numeradas (0, 1... 21) en trx.")
            return
            
        max_carpeta = str(max(carpetas_ids))
        self.log(f"[+] Entrando a la sub-carpeta de transacciones: {max_carpeta}")
        
        # 2. ENTRAR A ESA CARPETA
        self.enviar_y_leer(f"cd {max_carpeta}", delay=0.5)
        self.log(f"[-] Buscando archivos trx_ en /{max_carpeta}/...")
        salida_interior = self.enviar_y_leer("ll", delay=1.0)

        # 3. Extraer el archivo trx_ con el número interno más alto
        trx_lista = []
        
        for linea in salida_interior.split('\n'):
            linea = linea.strip()
            arr = linea.split()
            if arr:
                nom_arch = arr[-1]
                # Buscar estricto los que empiezan validamente con trx_
                if nom_arch.startswith("trx_"):
                    # Ejemplo: trx_2193_07401847_2026.bin
                    partes = nom_arch.split('_')
                    if len(partes) > 1 and partes[1].isdigit():
                        trx_lista.append((int(partes[1]), nom_arch))

        if trx_lista:
            # Seleccionamos el trx mas alto
            max_trx = max(trx_lista, key=lambda x: x[0])
            max_trx_num = max_trx[0]
            max_trx_nombre = max_trx[1]
            
            self.log(f"\n[=============== TRX IDENTIFICADA ===============]")
            self.log(f"Última Transacción registrada: ID {max_trx_num}")
            self.log(f"-> Registrada en el archivo: {max_trx_nombre}")
            self.log(f"[================================================]\n")
        else:
            self.log(f"[X] No se detectaron archivos de transaccion trx_ en la carpeta /{max_carpeta}/")


if __name__ == "__main__":
    app = ValidadorApp()
    app.mainloop()
