# Documentación del Proyecto: Asistente Técnico Validadores

## 1. Información General
*   **Nombre del Proyecto:** Asistente Validador Transantiago (Desktop App).
*   **Persona/Rol:** Técnico Inicial (Triaje y Revisión de Laboratorio).
*   **Objetivo Principal:** Automatizar el proceso manual de diagnóstico (uso de PuTTY) mediante una interfaz visual rápida, precisa y segura, reduciendo tiempos de resolución y errores de tipeo.

## 2. Cómo Funciona (Flujo Técnico)
La aplicación interactúa en un plano de "Cliente-Servidor" mínimo. El PC actúa como cliente enviando comandos automatizados estándar de Linux (`ls`, `tail`, `ngc --stop`, `rm`) mediante la consola invisible, y captura la salida de texto, transformándola en luces verdes/rojas legibles en un panel de control local. 

## 3. Matriz de Riesgos y Mitigación (¡Muy Importante!)

Dado que estaremos interactuando con dispositivos reales en producción (validadores), es fundamental gestionar los riesgos. Instalar Python o la aplicación en tu PC **no le hace absolutamente nada** a los validadores. El único riesgo existe al momento de apretar los botones de acción destructiva, para los cuales he diseñado **3 escudos de seguridad**:

| Riesgo Identificado | Nivel de Daño | Cómo lo mitigaremos en el código (Safeguards) |
| :--- | :---: | :--- |
| **Borrar la carpeta equivocada (`rm -r`)** | 🔴 ALTO | Peligro: Si el código envía `rm -r /home` destruiría el equipo. <br>**Solución:** El programa tendrá *Reglas Estrictas*. Nunca usará variables dinámicas no validadas o comodines (`*`). Forzaremos matemáticamente a que la variable a eliminar DEBA empezar con `no_`. Si no coincide, bloquea el comando. |
| **Comandos desfasados o colapso del buffer** | 🟡 MEDIO | Peligro: Enviar el reboot antes de que termine el sync. <br>**Solución:** Establecer comandos sincrónicos. El código de Python "esperará" a ver en la pantalla el prompt (`root@...`) antes de escribir el siguiente comando. |
| **Accidentes por un clic erróneo (Human Error)** | 🟢 BAJO | Peligro: Hacer clic en "Borrar" sin querer. <br>**Solución:** Añadir **Doble Confirmación Visual**. Antes de ejecutar un comando que modifique el validador, saltará una mini ventana de Windows preguntando: *"⚠️ ¿Estás seguro que deseas eliminar la versión no_14?"* con botones de SI/NO. |

## 4. Mejoras Propuestas a Futuro (Ideas extra)
1. **Auto-Carga Excel:** Como al final del día debes llenar un "Google Sheets", si el programa detectó 10 equipos hoy, podría botarte un pequeño botón al final que diga "Copiar Resumen del Día", copiando a tu portapapeles una fila lista para llegar y pegar en el Excel con la fecha, la IP, el ID y el estado encontrado.
2. **Ping Automático:** Antes de iniciar cualquier análisis, que tire un ping rápido por fondo para confirmar que el cable de red realmente detectó el validador y evitar que el programa se quede cargando en el vacío.
