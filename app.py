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
        self.monitor_activo = False
        self.comando_en_curso = False
        self.vigia_iniciado = False

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

        self.lbl_v_max = ctk.CTkLabel(self.frame_versiones, text="Versión Alta: --", font=ctk.CTkFont(size=12))
        self.lbl_v_max.pack(anchor="w", pady=0)
        self.lbl_ok = ctk.CTkLabel(self.frame_versiones, text="OK_ : --", text_color="green", font=ctk.CTkFont(size=12))
        self.lbl_ok.pack(anchor="w", pady=0)
        self.lbl_no = ctk.CTkLabel(self.frame_versiones, text="NO_ : --", text_color="red", font=ctk.CTkFont(size=12))
        self.lbl_no.pack(anchor="w", pady=0)
        self.lbl_check = ctk.CTkLabel(self.frame_versiones, text="CHECK_ : --", text_color="orange", font=ctk.CTkFont(size=12))
        self.lbl_check.pack(anchor="w", pady=0)

        self.lbl_sam = ctk.CTkLabel(self.frame_izq, text="SAM COLD RESET: --", font=ctk.CTkFont(size=12, weight="bold"), fg_color="gray", corner_radius=5)
        self.lbl_sam.pack(pady=(10,20), ipadx=10, ipady=3)

        self.btn_monitor = ctk.CTkButton(self.frame_izq, text="📡 Modo Monitor (Ver Arranque)", fg_color="#6366F1", hover_color="#4F46E5", font=ctk.CTkFont(weight="bold"), command=self.toggle_monitor)
        self.btn_monitor.pack(side="bottom", pady=(5, 20), padx=20, fill="x")

        self.combo_com = ctk.CTkComboBox(self.frame_izq, values=["SIMULADOR (Prueba Local)", "COM1", "COM2", "COM3"])
        self.combo_com.set("COM1") 
        self.combo_com.pack(side="bottom", pady=(0, 5), padx=20, fill="x")
        
        self.lbl_com = ctk.CTkLabel(self.frame_izq, text="Puerto Serial:")
        self.lbl_com.pack(side="bottom", pady=0)

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

        # BATERÍA DE BOTONES COMPACTA (SISTEMA DE PESTAÑAS - Ahorra máximo espacio)
        self.tabview = ctk.CTkTabview(self.frame_der, height=80)
        self.tabview.pack(pady=5, padx=20, fill="x")

        tab_core = self.tabview.add("1. Acciones Básicas")
        tab_diag = self.tabview.add("2. Diagnóstico Técnico")
        tab_usb = self.tabview.add("3. Extraer a USB")

        # --- Pestaña 1: CORE ---
        tab_core.columnconfigure((0, 1, 2), weight=1)
        self.btn_escanear = ctk.CTkButton(tab_core, text="🔄 Conectar y Analizar", font=ctk.CTkFont(weight="bold"), command=lambda: self.arrancar_hilo(self.ejecutar_escaneo))
        self.btn_escanear.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_detener = ctk.CTkButton(tab_core, text="⏹️ Detener Reinicio", fg_color="#D97706", hover_color="#B45309", command=lambda: self.arrancar_hilo(self.ejecutar_detener))
        self.btn_detener.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_reparar = ctk.CTkButton(tab_core, text="🗑️ Eliminar NO y Reiniciar", fg_color="#DC2626", hover_color="#991B1B", command=self.pedir_confirmacion_reparar)
        self.btn_reparar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # --- Pestaña 2: DIAGNOSTICO ---
        tab_diag.columnconfigure((0, 1, 2), weight=1)
        self.btn_trx = ctk.CTkButton(tab_diag, text="💳 Extraer TRX", fg_color="#059669", hover_color="#047857", command=lambda: self.arrancar_hilo(self.ejecutar_trx))
        self.btn_trx.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_test_disco = ctk.CTkButton(tab_diag, text="💽 Estado del Disco", fg_color="#0284c7", hover_color="#0369a1", command=lambda: self.arrancar_hilo(self.ejecutar_test_disco))
        self.btn_test_disco.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_test_red = ctk.CTkButton(tab_diag, text="🌐 Test de Red", fg_color="#7c3aed", hover_color="#5b21b6", command=lambda: self.arrancar_hilo(self.ejecutar_test_red))
        self.btn_test_red.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # --- Pestaña 3: USB ---
        tab_usb.columnconfigure(0, weight=2)
        tab_usb.columnconfigure((1, 2), weight=1)
        self.entry_ruta_usb = ctk.CTkEntry(tab_usb, placeholder_text="/home", font=ctk.CTkFont(family="Consolas", size=12))
        self.entry_ruta_usb.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.entry_ruta_usb.insert(0, "/home")
        
        self.btn_usb_copiar = ctk.CTkButton(tab_usb, text="Montar y Copiar", fg_color="#2563EB", hover_color="#1D4ED8", command=lambda: self.arrancar_hilo(self.rutina_copiar_usb))
        self.btn_usb_copiar.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_usb_expulsar = ctk.CTkButton(tab_usb, text="Desmontar Seguro", fg_color="#475569", hover_color="#334155", command=lambda: self.arrancar_hilo(self.rutina_desmontar_usb))
        self.btn_usb_expulsar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.label_terminal = ctk.CTkLabel(self.frame_der, text="Log Histórico de Acciones:", font=ctk.CTkFont(size=12, weight="bold"))
        self.label_terminal.pack(anchor="w", padx=20, pady=(10, 0))

        # ACÁ ESTÁ EL CAMBIO CLAVE: expand=True permitirá que este campo crezca 
        # y devore mágicamente todo el espacio vertical de la pantalla
        self.textbox_consola = ctk.CTkTextbox(self.frame_der, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_consola.pack(padx=20, pady=(2, 10), fill="both", expand=True)

        # RECUADRO DE COMANDO MANUAL DIRECTO (Evita usar PuTTY totalmente)
        self.frame_manual = ctk.CTkFrame(self.frame_der, fg_color="transparent")
        self.frame_manual.pack(pady=(0, 20), padx=20, fill="x")
        
        self.entry_manual = ctk.CTkEntry(self.frame_manual, placeholder_text="Escribe un comando personalizado aquí (Ej: ls -la)...", font=ctk.CTkFont(family="Consolas", size=13))
        self.entry_manual.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_manual.bind("<Return>", lambda event: self.arrancar_hilo(self.enviar_comando_manual))
        
        self.btn_ctrl_c = ctk.CTkButton(self.frame_manual, text="🛑 Ctrl+C", width=80, fg_color="#DC2626", hover_color="#991B1B", command=self.enviar_ctrl_c)
        self.btn_ctrl_c.pack(side="left", padx=(0, 10))
        
        self.btn_manual = ctk.CTkButton(self.frame_manual, text="📤 Enviar", width=100, fg_color="#4F46E5", hover_color="#4338CA", command=lambda: self.arrancar_hilo(self.enviar_comando_manual))
        self.btn_manual.pack(side="right")

    def log(self, texto):
        self.textbox_consola.insert("end", texto + "\n")
        self.textbox_consola.see("end")

    def limpiar_texto(self, texto):
        return ansi_escape.sub('', texto).strip()

    def arrancar_hilo(self, funcion):
        threading.Thread(target=funcion, daemon=True).start()

    def toggle_monitor(self):
        if self.monitor_activo:
            self.monitor_activo = False
            self.btn_monitor.configure(text="📡 Modo Monitor (Ver Arranque)", fg_color="#6366F1", hover_color="#4F46E5")
            self.log("\n[+] MODO MONITOR APAGADO. El log vuelve a estar dedicado a respuesta de comandos.")
        else:
            if not self.ser or not self.ser.is_open:
                exito = self.abrir_puerto_bruto()
                if not exito: return
            
            self.monitor_activo = True
            self.btn_monitor.configure(text="⏹️ APAGAR Monitor de Arranque", fg_color="#BE123C", hover_color="#9F1239")
            self.log("\n[!] ===============================================")
            self.log("[📡] MODO MONITOR CONTINUO ACTIVADO")
            self.log("[📡] Escuchando puro RAW como PuTTY. NO ENVIES COMANDOS MIENTRAS ESTO ESTE ACTIVO.")
            self.log("[!] ===============================================\n")
            self.arrancar_hilo(self.rutina_monitor_continuo)

    def rutina_monitor_continuo(self):
        # Esta rutina lee indiscriminadamente el puerto sin comandos previos y escupe en la consola
        while self.monitor_activo and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting)
                    limpio = self.limpiar_texto(chunk.decode('utf-8', errors='ignore'))
                    # Insertamos directo sin salto de linea estricto para respetar el espaciado de arranque de linux
                    self.textbox_consola.insert("end", limpio)
                    self.textbox_consola.see("end")
            except Exception:
                break
            time.sleep(0.05)

    # ================= LOGICA SERIAL Y DE TEXTO =================
    def enviar_y_leer(self, cmd, delay=1.0):
        if self.monitor_activo:
            self.log("\n[ERROR] Apaga primero el Modo Monitor (Botón Rojo Izquierdo) antes de inyectar comandos.")
            return ""
            
        self.comando_en_curso = True
        try:
            return self._enviar_y_leer_interno(cmd, delay)
        finally:
            self.comando_en_curso = False
            
    def _enviar_y_leer_interno(self, cmd, delay=1.0):
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
            
        # Limpiar cualquier basura vieja del cable antes de mandar el comando nuevo
        self.ser.reset_input_buffer()
        
        self.ser.write((cmd + "\n").encode('utf-8', errors='ignore'))
        
        # Eliminada espera 'delay' (time.sleep) aquí. Previene que Windows sobrescriba 
        # su pequeño buffer UART original si el hardware responde muy rápido.
        
        output = b""
        tiempo_arranque = time.time()
        timeout_inactividad = 3.0 # Segundos de inactividad de red para morir
        timeout_absoluto = 15.0 # Segundos maximos en caso de spam infinito
        tiempo_inicio_absoluto = time.time()
        
        # Bucle de Drenaje Ultharrápido
        while True:
            if self.ser.in_waiting > 0:
                output += self.ser.read(self.ser.in_waiting)
                tiempo_arranque = time.time() # Refrescar latido (sigue vivo)
                
                cola = output[-800:]
                cola_lower = cola.lower()
                
                # Caza Inteligente de Prompt Estricto (Resiliente a Spam):
                if b"root@" in cola:
                    idx_root = cola.rfind(b"root@")
                    if b"#" in cola[idx_root:]:
                        time.sleep(0.05)
                        if self.ser.in_waiting > 0:
                            output += self.ser.read(self.ser.in_waiting)
                        break 
                
                elif b"login:" in cola_lower or b"password:" in cola_lower:
                    time.sleep(0.05)
                    if self.ser.in_waiting > 0:
                        output += self.ser.read(self.ser.in_waiting)
                    break
            else:
                # Si pasa mucho tiempo sin recibir ni un byte, abortar (Corte de emergencia o comando colgado)
                if time.time() - tiempo_arranque > timeout_inactividad:
                    break
                    
            if time.time() - tiempo_inicio_absoluto > timeout_absoluto:
                self.log("\n[⚠️] TIMEOUT ABSOLUTO (Posible spam infinito). Cortando lectura...")
                break
            
            time.sleep(0.02) # Respirar microsegundos
                
        salida_limpia = self.limpiar_texto(output.decode('utf-8', errors='ignore'))
        
        self.log(f"> {cmd}\n{salida_limpia}")
        
        return salida_limpia

    def abrir_puerto_bruto(self):
        try:
            puerto = self.combo_com.get()
            if puerto == "SIMULADOR (Prueba Local)": return True
            if self.ser and self.ser.is_open: self.ser.close()
            self.ser = serial.Serial(puerto, 115200, timeout=1)
            try: self.ser.set_buffer_size(rx_size=1048576)
            except Exception: pass
            return True
        except Exception as e:
            self.log(f"[ERROR CRÍTICO] No se pudo conectar a {puerto}: {e}")
            return False

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
            self.ser = serial.Serial(puerto, 115200, timeout=1)
            
            # Ampliar el buffer nativo de Windows (Rx) a 1 MB para evitar que los comandos
            # masivos desborden la memoria y borren los logs más antiguos del tail.
            try:
                self.ser.set_buffer_size(rx_size=1048576)
            except Exception:
                pass
                
            # Limpiar rastro de versiones anteriores visualmente al conectar un equipo nuevo
            self.lbl_id.configure(text="ID VAL: Escaneando...")
            time.sleep(0.5)

            # --- TEST VITALIDAD FÍSICA ---
            self.log("[⏳] Comprobando pulso eléctrico de la placa...")
            resp_vital = self.enviar_y_leer("", delay=0.5)
            
            # Si PySerial no extrae texto en su tiempo de espera, la placa esta muerta o desconectada.
            if not resp_vital.strip():
                self.log(f"\n{'='*55}\n[❌] ERROR ELÉCTRICO DE COMUNICACIÓN \n[❌] El puerto en Windows abrió, pero la Placa NO RESPONDIÓ.\n{'='*55}")
                self.log(" -> CAUSA 1: El cable de datos está físicamente desconectado de la placa.")
                self.log(" -> CAUSA 2: El Validador está apagado (sin energía).")
                self.log(" -> CAUSA 3: Los cables internos rotos (RX/TX muertos).\n")
                if self.ser and self.ser.is_open:
                    self.ser.close()
                return False
                
            self.log(f"\n{'='*55}\n[✅] LINK ELÉCTRICO ESTABLECIDO CON ÉXITO\n[✅] Equipo detectado vivo y latiendo en {puerto}\n{'='*55}")

            # Activar Vigía de fondo si no estaba corriendo
            self.iniciar_vigia_fondo()

            # Presionar enter a ver si pide login 
            if "login:" in resp_vital.lower() or "root" not in resp_vital.lower():
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
                self.lbl_ip.configure(text=f"IP (eth0): {ip_match.group(1)}", text_color="white")
            else:
                self.lbl_ip.configure(text="IP (eth0): NO DETECTADA ❌", text_color="#EF4444")
            
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

            self.lbl_v_max.configure(text=f"Versión Alta: {v_max_str}")
            if v_max_str == "--":
                self.lbl_v_max.configure(text="Versión Alta: NO DETECTADA ❌", text_color="#EF4444")
                
            self.lbl_ok.configure(text=f"OK_ : {ok_str}", text_color="green" if ok_str != "--" else "white")
            
            if no_str == "--":
                self.lbl_no.configure(text="NO_ : AUSENTE ❌", text_color="#EF4444")
            else:
                self.lbl_no.configure(text=f"NO_ : {no_str}", text_color="red")
                
            self.lbl_check.configure(text=f"CHECK_ : {check_str}", text_color="orange" if check_str != "--" else "white")

            salida_log = self.enviar_y_leer("tail -200 /home/pds/logs/Mval/Mval_archivolog.log", delay=1.5)
            
            sam_cold = "SAM COLD RESET" in salida_log
            sam_dump = "SAM_DumpSecretKey" in salida_log or "SAM no preparada" in salida_log
            yml_error = "Error archivo Yml no encontrado" in salida_log
            medio_nulo = "Medio de acceso de virtual nulo" in salida_log or "El archivo ./etc/Hal" in salida_log
            
            if sam_cold and medio_nulo:
                self.lbl_sam.configure(text="SAM / LECTOR NULO: CABLE/HARDWARE DAÑADO", fg_color="orange", text_color="black")
                self.log("\n>>> [ALERTA DE DIAGNÓSTICO AVANZADO] <<<")
                self.log("Se detectó un 'SAM COLD RESET' en el historial, PERO el error más actual")
                self.log("es 'Medio de acceso virtual nulo' o falla de archivos de Hardware HAL.")
                self.log("CAUSA: El cable IDE/Flex de la placa al lector está suelto o el lector murió.")
                self.log("ACCIÓN: Un comando de reparación NO arreglará esto. Ve a REVISIÓN FÍSICA.")
                self.log(">>> -------------------------------- <<<\n")
            elif sam_dump:
                self.lbl_sam.configure(text="SAM NO PREPARADA: ERROR DE LLAVES", fg_color="#8B5CF6", text_color="white")
                self.log("\n[!] ALERTA CRÍTICA: ERROR DE LLAVES SAM_DumpSecretKey (6A 82).")
                self.log(">>> La SAM responde eléctricamente pero no está autorizada o está virgen.")
            elif sam_cold:
                self.lbl_sam.configure(text="SAM COLD RESET: ALERTA ROJA", fg_color="red", text_color="white")
                self.log("\n[!] ALERTA CRITICA: 'SAM COLD RESET' DETECTADO (Error lógico puro).")
                self.log(">>> PROCEDE CON REPARACIÓN Y REINICIO.")
            elif yml_error:
                self.lbl_sam.configure(text="ERROR MREF: ARCHIVO YML AUSENTE", fg_color="#F43F5E", text_color="white")
                self.log("\n[!] ALERTA DE SISTEMA: El validador reporta que le falta un archivo YML de configuración.")
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
        
    def enviar_ctrl_c(self):
        if not self.ser or not self.ser.is_open:
            self.log("[ERROR] Conecta primero al puerto COM.")
            return
        # El caracter ASCII para un Ctrl+C en terminales es el Byte 0x03
        self.ser.write(b'\x03')
        self.log("\n[!] Señal de Interrupción enviada (Ctrl+C).")

    def enviar_comando_manual(self):
        comando = self.entry_manual.get().strip()
        if not comando: return
        
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero para enviar comandos.")
            return
            
        self.log(f"\n[-] MODO MANUAL INYECTÓ COMANDO:")
        self.enviar_y_leer(comando, delay=1.0)
        self.entry_manual.delete(0, "end")

    def enviar_lectura_larga(self, cmd, timeout_mins=8):
        """Función especializada que ignora el timeout de inactividad de 3s y espera la completitud de comandos lentos."""
        self.comando_en_curso = True
        try:
            return self._enviar_lectura_larga_interno(cmd, timeout_mins)
        finally:
            self.comando_en_curso = False
            
    def _enviar_lectura_larga_interno(self, cmd, timeout_mins=8):
        if not self.ser or not self.ser.is_open:
            return ""
            
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\n").encode('utf-8', errors='ignore'))
        
        output = b""
        tiempo_arranque = time.time()
        timeout_absoluto = timeout_mins * 60
        
        while True:
            if self.ser.in_waiting > 0:
                output += self.ser.read(self.ser.in_waiting)
                
                # Caza Inteligente de Prompt Estricto (Resiliente a Spam)
                cola = output[-800:]
                if b"root@" in cola:
                    idx_root = cola.rfind(b"root@")
                    if b"#" in cola[idx_root:]:
                        time.sleep(0.1)
                        if self.ser.in_waiting > 0:
                            output += self.ser.read(self.ser.in_waiting)
                        break 
                        
            if time.time() - tiempo_arranque > timeout_absoluto:
                self.log(f"[WARNING] Comando excedió el tiempo máximo de {timeout_mins} minutos.")
                break
            
            time.sleep(0.05)
            
        return self.limpiar_texto(output.decode('utf-8', errors='ignore'))

    def rutina_copiar_usb(self):
        ruta_origen = self.entry_ruta_usb.get().strip()
        if not ruta_origen:
            self.log("[X] Error: Debes especificar una carpeta o archivo a respaldar.")
            return
            
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero al puerto COM.")
            return

        self.log(f"\n{'-'*40}\n[⏳] 1. Montando el Pendrive USB al sistema Linux...")
        self.enviar_y_leer("mount /dev/sda1 /mnt", delay=1.0)
        
        amid_nombre = self.target_id if hasattr(self, 'target_id') and self.target_id else "0000X"
        ruta_destino = f"/mnt/amid_{amid_nombre}"
        
        self.log(f"[⏳] 2. Iniciando COPIA desde '{ruta_origen}' hacia '{ruta_destino}'...")
        self.log("[⚠️] EL PROGRAMA SE CONGELARÁ ESPERANDO QUE TERMINE, ALGUNAS CARPETAS PESAN MEGAS. SOLO ESPERA.")
        
        comando_copiar = f"cp -r {ruta_origen} {ruta_destino}"
        
        if self.combo_com.get() == "SIMULADOR (Prueba Local)":
            time.sleep(3)
            self.log(f"> {comando_copiar}\n[Simulador] Carpeta {ruta_origen} copiada virtualmente.")
        else:
            salida = self.enviar_lectura_larga(comando_copiar, timeout_mins=8)
            self.log(f"> {comando_copiar}\n{salida}\n[✅] MEGA-COPIA FINALIZADA. Haz clic en 'Desmontar Seguro' ahora.")

    def rutina_desmontar_usb(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            return
            
        self.log("\n[⏳] Aplicando sincronización de disco (sync)...")
        self.enviar_y_leer("sync", delay=1.0)
        
        self.log("[⏳] Desmontando la unidad USB (/mnt)...")
        self.enviar_y_leer("umount /mnt", delay=2.0)
        self.log("[✅] ¡Extracción Segura Completada! Ya puedes retirar tu pendrive del validador de Sonda.")

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

    # ================= RUTINAS NUEVAS (VIGÍA Y DIAGNÓSTICO) =================
    def ejecutar_test_disco(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero.")
            return
            
        self.log("\n[⏳] Analizando estado de la memoria interna...")
        salida = self.enviar_y_leer("df -h /home", delay=1.0)
        
        # Parseo simple para buscar el porcentaje de uso
        if "100%" in salida or "99%" in salida or "98%" in salida or "97%" in salida:
            self.log(f"\n[❌] ¡ALERTA CRÍTICA DE ALMACENAMIENTO! [❌]")
            self.log("La carpeta /home está saturada al borde del colapso.")
            self.log("Se recomienda eliminar carpetas NO_ o ejecutar una limpieza masiva.")
        else:
            self.log("\n[✅] Memoria Interna: Estado Saludable con espacio libre.")

    def ejecutar_test_red(self):
        if self.combo_com.get() != "SIMULADOR (Prueba Local)" and (not self.ser or not self.ser.is_open):
            self.log("[ERROR] Conecta primero.")
            return
            
        self.log("\n[⏳] Comprobando antenas móviles y conectividad al DNS global...")
        salida = self.enviar_y_leer("ping -c 3 8.8.8.8", delay=2.5)
        
        if "3 packets transmitted, 3 received" in salida or "3 packets transmitted, 3 packets received" in salida:
            self.log("\n[✅] EXITO: Módem 3G/4G operativo y conectado a Internet.")
        elif "Network is unreachable" in salida or "100% packet loss" in salida:
            self.log("\n[❌] FALLA DE RED: El validador NO tiene salida a Internet.")
            self.log(" -> Posible fallo de SIM Card o chip Módem desconectado.")
        else:
            self.log("\n[⚠️] Estado Incierto. Revisa el log manualmente arriba.")

    def iniciar_vigia_fondo(self):
        if not self.vigia_iniciado:
            self.vigia_iniciado = True
            self.arrancar_hilo(self.rutina_vigia_fondo)

    def rutina_vigia_fondo(self):
        while True:
            # Solo escuchamos si hay puerto abierto, nadie está mandando comandos 
            # y el monitor manual morado NO está activo.
            if self.ser and self.ser.is_open and not self.comando_en_curso and not self.monitor_activo:
                try:
                    if self.ser.in_waiting > 0:
                        chunk = self.ser.read(self.ser.in_waiting)
                        texto = chunk.decode('utf-8', errors='ignore')
                        
                        if "U-Boot" in texto or "Starting kernel" in texto or "% system/" in texto or "daemon/" in texto:
                            self.lbl_id.configure(text="[ ⏳ MÁQUINA REINICIANDO / CARGANDO... ]", text_color="orange")
                        elif "login:" in texto:
                            self.lbl_id.configure(text="ID VAL: ESPERANDO LOGIN 🟢", text_color="green")
                except Exception:
                    pass
            time.sleep(0.5)

if __name__ == "__main__":
    app = ValidadorApp()
    app.mainloop()
