import customtkinter as ctk
import mysql.connector
from datetime import datetime
import threading
import time
import google.generativeai as genai
import random
import pyperclip

# --- Configuración Global de Estilos y Colores ---
# Paleta de colores más profesional y atractiva
COLOR_PRIMARY_DARK = "#292929"
COLOR_SECONDARY_DARK = "#3a3a3a"
COLOR_ACCENT = "#54A0FF"  # Un azul vibrante pero profesional
COLOR_SUCCESS = "#4CAF50" # Verde para éxito/completado
COLOR_WARNING = "#FFC107" # Amarillo para advertencias
COLOR_ERROR = "#F44336"   # Rojo para errores/eliminar
COLOR_TEXT_LIGHT = "#E0E0E0"
COLOR_TEXT_MEDIUM = "#B0B0B0"
COLOR_TEXT_DARK = "#808080"
COLOR_BORDER = "#505050"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue") # Esto todavía aplica algunos valores por defecto de CTk, podemos sobrescribirlos

# --- Clases de Utilidad para Marcadores de Posición ---

class PlaceholderLabel(ctk.CTkLabel):
    """Un CTkLabel que muestra texto de marcador de posición y se adapta al contenido."""
    def __init__(self, master, text, placeholder_color=COLOR_TEXT_DARK, text_color=COLOR_TEXT_LIGHT, font=None, **kwargs):
        super().__init__(master, text=text, text_color=placeholder_color, font=font, **kwargs)
        self.placeholder_text = text
        self.placeholder_color = placeholder_color
        self.normal_text_color = text_color
        self.font = font
        self.is_placeholder = True

        self._widget_to_bind = None

    def bind_to_widget(self, widget_to_bind):
        """Enlaza los eventos de foco y teclado del widget dado."""
        self._widget_to_bind = widget_to_bind
        widget_to_bind.bind("<FocusIn>", self.on_focus_in)
        widget_to_bind.bind("<FocusOut>", self.on_focus_out)
        widget_to_bind.bind("<KeyRelease>", self.on_key_release)
        widget_to_bind.bind("<ButtonRelease-1>", self.on_key_release) # Para clicks con el mouse

    def on_focus_in(self, event=None):
        """Elimina el texto del marcador de posición cuando se enfoca el widget."""
        if self.is_placeholder:
            self.configure(text="", text_color=self.normal_text_color)
            self.is_placeholder = False

    def on_focus_out(self, event=None):
        """Restaura el texto del marcador de posición si el widget está vacío."""
        if self._widget_to_bind and not self._widget_to_bind.get("1.0", "end-1c").strip():
            self.configure(text=self.placeholder_text, text_color=self.placeholder_color)
            self.is_placeholder = True
        elif not self._widget_to_bind: # En caso de que se llame sin widget_to_bind (ej. al inicio)
            self.configure(text=self.placeholder_text, text_color=self.placeholder_color)
            self.is_placeholder = True

    def on_key_release(self, event):
        """Actualiza el estado del placeholder cuando se escribe texto."""
        if self._widget_to_bind:
            current_text = self._widget_to_bind.get("1.0", "end-1c").strip()
            if self.is_placeholder and current_text:
                self.on_focus_in(event)
            elif not current_text:
                self.on_focus_out(event)

    def configure(self, **kwargs):
        """Sobrescribe configure para manejar el color normal si se establece texto."""
        if "text" in kwargs and kwargs["text"] != self.placeholder_text:
            if self.is_placeholder:
                self.is_placeholder = False
                # Aquí no cambiamos el color de texto del label directamente,
                # sino que el textbox asociado será quien muestre el texto normal.
        super().configure(**kwargs)

class PlaceholderTextbox(ctk.CTkTextbox):
    """Un CTkTextbox que muestra texto de marcador de posición."""
    def __init__(self, master, placeholder_text="", placeholder_color=COLOR_TEXT_DARK, text_color=COLOR_TEXT_LIGHT, font=None, **kwargs):
        super().__init__(master, font=font, text_color=text_color, **kwargs)
        self.placeholder_text = placeholder_text
        self.placeholder_color = placeholder_color
        self.normal_text_color = text_color
        self.font = font
        self.is_placeholder = True

        self.placeholder_label = PlaceholderLabel(self, text=placeholder_text, placeholder_color=placeholder_color, text_color=text_color, font=font)
        self.placeholder_label.place(x=6, y=6)
        self.placeholder_label.bind_to_widget(self)

        # Inicializa el textbox con el color del placeholder si está vacío
        self._apply_placeholder_style()

    def _apply_placeholder_style(self):
        if not self.get("1.0", "end-1c").strip():
            self.configure(text_color=self.placeholder_color)
            self.is_placeholder = True
            self.placeholder_label.configure(text=self.placeholder_text, text_color=self.placeholder_color)
        else:
            self.configure(text_color=self.normal_text_color)
            self.is_placeholder = False
            self.placeholder_label.configure(text="") # Oculta la etiqueta si hay texto

    def get(self, *args, **kwargs):
        if self.is_placeholder:
            return ""
        return super().get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._apply_placeholder_style() # Revisa y aplica el estilo después de borrar

    def insert(self, *args, **kwargs):
        super().insert(*args, **kwargs)
        self._apply_placeholder_style() # Revisa y aplica el estilo después de insertar

    def on_focus_in(self, event=None):
        if self.is_placeholder:
            self.configure(text_color=self.normal_text_color)
            self.is_placeholder = False
            self.placeholder_label.on_focus_in() # Oculta la etiqueta

    def on_focus_out(self, event=None):
        if not self.get("1.0", "end-1c").strip():
            self.configure(text_color=self.placeholder_color)
            self.is_placeholder = True
            self.placeholder_label.on_focus_out() # Muestra la etiqueta
        else:
            self.configure(text_color=self.normal_text_color)
            self.is_placeholder = False
            self.placeholder_label.on_focus_in() # Asegura que la etiqueta esté oculta

    def set_text(self, text):
        """Permite establecer texto programáticamente y maneja el placeholder."""
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self._apply_placeholder_style()


# --- 1. CONFIGURACIÓN GLOBAL Y LÓGICA DE BACKEND ---

# Configuración de la Base de Datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'redes2025', # <-- CAMBIA ESTO SI ES NECESARIO
    'database': 'asistente_db'
}

# Configuración de la IA
# IMPORTANTE: Reemplaza "TU_API_KEY_AQUI" con tu clave real de Google AI
API_KEY = "AIzaSyAVv478fM4fEyomm81Av-MHPHDVawx1DNY" # <-- CAMBIA ESTO
try:
    genai.configure(api_key=API_KEY)
    # 💥 CORRECCIÓN APLICADA: Cambiamos 'gemini-1.5-flash' por el nombre actual del modelo
    AI_MODEL = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    AI_MODEL = None
    print(f"Error de conexión con la IA: {e}")
    print("Asegúrate de que tu API_KEY sea correcta y que el servicio de IA esté disponible.")

# Temas de estudio enfocados en programación
TEMAS_DE_ESTUDIO_IA = [
    'Arquitectura de microservicios',
    'Desarrollo de APIs RESTful con Python',
    'Estructuras de datos avanzadas',
    'Principios de DevOps y CI/CD',
    'Machine learning con TensorFlow'
]

def conectar_bd():
    """Establece la conexión con la base de datos."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        return None

def crear_tablas():
    """Crea las tablas de la base de datos si no existen."""
    conn = conectar_bd()
    if conn:
        cursor = conn.cursor()
        queries = [
            # La tabla 'tareas' ahora incluye 'importancia' y 'notas'
            "CREATE TABLE IF NOT EXISTS tareas (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(255) NOT NULL, fecha_creacion DATETIME, completada BOOLEAN DEFAULT FALSE, importancia VARCHAR(50) DEFAULT 'Media', notas TEXT)",
            "CREATE TABLE IF NOT EXISTS recordatorios (id INT AUTO_INCREMENT PRIMARY KEY, texto VARCHAR(255) NOT NULL, fecha_creacion DATETIME)",
            "CREATE TABLE IF NOT EXISTS listas (id INT AUTO_INCREMENT PRIMARY KEY, titulo VARCHAR(255) NOT NULL, elementos TEXT, fecha_creacion DATETIME)"
        ]
        for query in queries:
            try:
                cursor.execute(query)
            except mysql.connector.Error as err:
                print(f"Error al crear tabla (puede que ya exista): {err}")
        conn.commit()
        cursor.close()
        conn.close()
    else:
        print("No se pudo conectar a la base de datos para crear tablas.")

def ejecutar_consulta_bd(query, values=None):
    """Ejecuta una consulta en la base de datos y maneja errores."""
    conn = conectar_bd()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error al ejecutar consulta: {err}")
            if err.errno == 1054: # Error de columna desconocida
                print("Posible causa: La columna especificada no existe en la tabla.")
                print("Asegúrate de que la tabla se haya creado correctamente con todas las columnas necesarias (ej. 'importancia' y 'notas' para tareas).")
                print("Si la tabla existía antes de añadir estas columnas, considera usar ALTER TABLE o borrar y recrear la tabla.")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def obtener_datos_bd(query):
    """Obtiene datos de la base de datos y maneja errores."""
    conn = conectar_bd()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            data = cursor.fetchall()
            return data
        except mysql.connector.Error as err:
            print(f"Error al obtener datos: {err}")
            return []
        finally:
            cursor.close()
            conn.close()
    return []

def obtener_tema_ia():
    """Genera un tema de estudio usando la IA o la lista predefinida."""
    if AI_MODEL:
        try:
            response = AI_MODEL.generate_content("Sugiere un tema de estudio específico y práctico para un programador en una frase corta. Puede ser sobre lenguajes, frameworks, metodologías, o conceptos avanzados.")
            tema = response.text.replace("*", "").strip()
            if not tema:
                return random.choice(TEMAS_DE_ESTUDIO_IA)
            return tema
        except Exception as e:
            print(f"Error al generar tema con IA: {e}")
            return random.choice(TEMAS_DE_ESTUDIO_IA)
    return random.choice(TEMAS_DE_ESTUDIO_IA)

def analizar_datos_con_ia():
    """Obtiene datos de la BD y los envía a la IA para su análisis."""
    recordatorios_db = obtener_datos_bd("SELECT texto FROM recordatorios")
    listas_db = obtener_datos_bd("SELECT titulo FROM listas")
    tareas_db = obtener_datos_bd("SELECT id, nombre, completada, importancia, notas, fecha_creacion FROM tareas")

    recordatorios_str = [r[0] for r in recordatorios_db if r[0]]
    listas_str = [l[0] for l in listas_db if l[0]]
    tareas_str = [f"{t[1]} (Importancia: {t[3]}, Completada: {t[2]}, Notas: {t[4][:50]}...)" for t in tareas_db if t[1]] # Limita notas a 50 chars

    prompt = f"""
    Analiza mi actividad de programación basada en los siguientes datos:
    - Recordatorios ({len(recordatorios_str)}): {recordatorios_str if recordatorios_str else 'Ninguno'}
    - Listas ({len(listas_str)}): {listas_str if listas_str else 'Ninguna'}
    - Tareas ({len(tareas_str)}): {tareas_str if tareas_str else 'Ninguna'}

    Dame un resumen conciso de mi progreso, identifica posibles áreas de mejora o patrones de productividad, y ofrece 1-2 consejos prácticos y profesionales. Prioriza la acción y la eficiencia.
    """

    if AI_MODEL:
        try:
            response = AI_MODEL.generate_content(prompt)
            analisis = response.text.replace("*", "").strip()
            if not analisis:
                return "La IA no proporcionó un análisis. Inténtalo de nuevo."
            return analisis
        except Exception as e:
            # Aquí capturamos el error y devolvemos un mensaje descriptivo
            return f"❌ Error al generar el análisis de la IA: {e}"
    else:
        return "❌ No se pudo conectar a la IA. Revisa tu clave de API y la conexión a internet."

# --- 2. GESTIÓN DE LA INTERFAZ DE USUARIO (GUI) ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Asistente de Programación v3.0")
        self.geometry("1000x800")
        self.config_gui_style() # Configuración de estilos en un método separado

        crear_tablas() # Asegura que las tablas existan al iniciar

        self.create_widgets()
        self.show_panel("Dashboard")

        self.current_task_importance = "Media" # Valor por defecto para la creación de tareas

    def config_gui_style(self):
        """Configura los estilos y colores globales de la aplicación."""
        self.configure(fg_color=COLOR_PRIMARY_DARK) # Fondo de la ventana principal
        ctk.set_widget_scaling(1.1) # Escala de widgets para mejor visibilidad en pantallas HiDPI

        # Sobrescribir colores de la librería para un tema más profesional
        ctk.set_default_color_theme("blue") # Esto todavía aplica algunas bases
        
        # Ajustes manuales para el tema "Dark" (se aplican después de set_default_color_theme)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def create_widgets(self):
        # Panel de navegación (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0, fg_color=COLOR_SECONDARY_DARK)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        ctk.CTkLabel(self.sidebar, text="Menú Principal", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_TEXT_LIGHT).grid(row=0, column=0, padx=20, pady=20)
        
        # FIX PREVIO: Se cambia 'medium' a 'bold' para compatibilidad con _tkinter
        button_font = ctk.CTkFont(size=14, weight="bold") 
        button_args = {"fg_color": COLOR_ACCENT, "hover_color": "#4A90D9", "text_color": COLOR_TEXT_LIGHT, "font": button_font, "height": 40}
        
        ctk.CTkButton(self.sidebar, text="Panel Principal", command=lambda: self.show_panel("Dashboard"), **button_args).grid(row=1, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Mis Tareas", command=lambda: self.show_panel("Tasks"), **button_args).grid(row=2, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Mis Listas", command=lambda: self.show_panel("Lists"), **button_args).grid(row=3, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Análisis IA", command=lambda: self.show_panel("AI_Analysis"), **button_args).grid(row=4, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Configuración", command=lambda: self.show_panel("Settings"), **button_args).grid(row=6, column=0, padx=20, pady=(10, 40))

        # Contenedor principal para los paneles
        self.main_container = ctk.CTkFrame(self, fg_color=COLOR_PRIMARY_DARK)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.panels = {}
        self.create_dashboard_panel()
        self.create_tasks_panel()
        self.create_lists_panel()
        self.create_ai_analysis_panel()
        self.create_settings_panel()

        self.current_panel = None

    def show_panel(self, name):
        """Oculta el panel actual y muestra el panel solicitado."""
        if self.current_panel:
            self.current_panel.grid_forget()
        self.current_panel = self.panels[name]
        self.current_panel.grid(row=0, column=0, sticky="nsew")

        if name == "Tasks":
            self.load_tasks()
        elif name == "Lists":
            self.load_lists()
        elif name == "AI_Analysis":
            self.ai_analysis_text.delete("1.0", "end")

    def create_dashboard_panel(self):
        panel = ctk.CTkFrame(self.main_container, fg_color=COLOR_PRIMARY_DARK)
        self.panels["Dashboard"] = panel
        
        ctk.CTkLabel(panel, text="Panel Principal", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(20, 30))

        # Frame para añadir tareas
        add_task_frame = ctk.CTkFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        add_task_frame.pack(fill="x", pady=15, padx=30, ipady=15)
        
        ctk.CTkLabel(add_task_frame, text="Crear Nueva Tarea", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=10)

        self.task_entry = ctk.CTkEntry(add_task_frame, placeholder_text="Nombre de la tarea", fg_color=COLOR_PRIMARY_DARK, text_color=COLOR_TEXT_LIGHT, border_color=COLOR_BORDER, height=35)
        self.task_entry.pack(fill="x", padx=20, pady=(5,10))

        # Selector de importancia de la tarea
        importance_frame = ctk.CTkFrame(add_task_frame, fg_color="transparent")
        importance_frame.pack(fill="x", padx=20, pady=(0,10))
        # Se usa 'normal' para un texto descriptivo
        ctk.CTkLabel(importance_frame, text="Importancia:", text_color=COLOR_TEXT_LIGHT, font=ctk.CTkFont(size=13, weight="normal")).pack(side="left", padx=(0, 10))
        self.task_importance_menu = ctk.CTkOptionMenu(importance_frame, values=["Baja", "Media", "Alta"], command=self.set_task_importance, fg_color=COLOR_PRIMARY_DARK, button_color=COLOR_ACCENT, button_hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT)
        self.task_importance_menu.set("Media")
        self.task_importance_menu.pack(side="left", fill="x", expand=True)

        # Área para notas/proceso de la tarea
        # Se usa 'normal' para un texto descriptivo
        notes_label = ctk.CTkLabel(add_task_frame, text="Notas / Proceso:", text_color=COLOR_TEXT_LIGHT, font=ctk.CTkFont(size=13, weight="normal"))
        notes_label.pack(anchor="w", padx=20, pady=(5,0))
        self.task_notes_entry = PlaceholderTextbox(add_task_frame, height=80, placeholder_text="Añade notas o los pasos del proceso aquí...", font=ctk.CTkFont(size=12), fg_color=COLOR_PRIMARY_DARK, border_color=COLOR_BORDER)
        self.task_notes_entry.pack(fill="x", expand=True, padx=20, pady=(0,10))

        ctk.CTkButton(add_task_frame, text="Añadir Tarea", command=self.add_task, fg_color=COLOR_SUCCESS, hover_color="#45A049", text_color=COLOR_TEXT_LIGHT, height=40).pack(pady=(10,5))

        # Separador visual
        ctk.CTkFrame(panel, height=2, fg_color=COLOR_BORDER).pack(fill="x", padx=30, pady=20)

        # Frame para obtener tema de estudio
        study_topic_frame = ctk.CTkFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        study_topic_frame.pack(fill="x", pady=15, padx=30, ipady=15)
        ctk.CTkLabel(study_topic_frame, text="Tema de Estudio del Día", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=10)
        self.study_topic_label = ctk.CTkLabel(study_topic_frame, text="Presiona el botón para obtener un tema.", wraplength=400, justify="center", text_color=COLOR_TEXT_MEDIUM)
        self.study_topic_label.pack(pady=10, padx=20)
        ctk.CTkButton(study_topic_frame, text="Obtener Tema", command=self.get_study_topic, fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, height=40).pack(pady=(0,5))

        # Área de notificaciones
        self.notification_frame = ctk.CTkFrame(panel, fg_color=COLOR_PRIMARY_DARK, corner_radius=5)
        self.notification_frame.pack(fill="x", pady=10, padx=30)
        self.notification_label = ctk.CTkLabel(self.notification_frame, text="", wraplength=500, justify="left", text_color=COLOR_TEXT_MEDIUM)
        self.notification_label.pack(padx=10, pady=5)

    def create_tasks_panel(self):
        panel = ctk.CTkFrame(self.main_container, fg_color=COLOR_PRIMARY_DARK)
        self.panels["Tasks"] = panel
        
        ctk.CTkLabel(panel, text="Mis Tareas", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(20, 30))

        # Botón para añadir nueva tarea
        add_task_button_frame = ctk.CTkFrame(panel, fg_color="transparent")
        add_task_button_frame.pack(fill="x", padx=30, pady=(0, 10))
        ctk.CTkButton(add_task_button_frame, text="Añadir Nueva Tarea", command=lambda: self.show_panel("Dashboard"), fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, height=35).pack(side="right")

        # Scrollable Frame para la lista de tareas
        self.tasks_list_frame = ctk.CTkScrollableFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        self.tasks_list_frame.pack(fill="both", expand=True, padx=30, pady=10)

    def create_lists_panel(self):
        panel = ctk.CTkFrame(self.main_container, fg_color=COLOR_PRIMARY_DARK)
        self.panels["Lists"] = panel
        
        ctk.CTkLabel(panel, text="Mis Listas", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(20, 30))

        # Frame para añadir nuevas listas
        add_list_frame = ctk.CTkFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        add_list_frame.pack(fill="x", pady=15, padx=30, ipady=15)
        
        ctk.CTkLabel(add_list_frame, text="Crear Nueva Lista", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=10)

        self.list_title_entry = ctk.CTkEntry(add_list_frame, placeholder_text="Título de la lista", fg_color=COLOR_PRIMARY_DARK, text_color=COLOR_TEXT_LIGHT, border_color=COLOR_BORDER, height=35)
        self.list_title_entry.pack(fill="x", padx=20, pady=(5,10))

        self.list_elements_entry = PlaceholderTextbox(add_list_frame, height=100, placeholder_text="Elementos (uno por línea)", font=ctk.CTkFont(size=12), fg_color=COLOR_PRIMARY_DARK, border_color=COLOR_BORDER)
        self.list_elements_entry.pack(fill="x", padx=20, pady=(0,10))

        ctk.CTkButton(add_list_frame, text="Crear Lista", command=self.add_list, fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, height=40).pack(pady=(10,5))

        # Scrollable Frame para mostrar las listas
        self.lists_scrollable_frame = ctk.CTkScrollableFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        self.lists_scrollable_frame.pack(fill="both", expand=True, padx=30, pady=10)

    def create_ai_analysis_panel(self):
        panel = ctk.CTkFrame(self.main_container, fg_color=COLOR_PRIMARY_DARK)
        self.panels["AI_Analysis"] = panel
        
        ctk.CTkLabel(panel, text="Análisis con IA", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(20, 30))
        ctk.CTkButton(panel, text="Generar Análisis", command=self.analyze_with_ai, fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, height=40).pack(pady=(0, 20))

        self.ai_analysis_text = ctk.CTkTextbox(panel, height=500, width=800, wrap="word", fg_color=COLOR_SECONDARY_DARK, text_color=COLOR_TEXT_LIGHT, border_color=COLOR_BORDER, corner_radius=10)
        self.ai_analysis_text.pack(pady=10, padx=30, fill="both", expand=True)

    def create_settings_panel(self):
        panel = ctk.CTkFrame(self.main_container, fg_color=COLOR_PRIMARY_DARK)
        self.panels["Settings"] = panel
        
        ctk.CTkLabel(panel, text="Configuración", font=ctk.CTkFont(size=28, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(20, 30))

        settings_frame = ctk.CTkFrame(panel, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        settings_frame.pack(fill="x", pady=15, padx=30, ipady=15)

        # FIX PREVIO: Se cambia 'medium' a 'bold' para compatibilidad
        ctk.CTkLabel(settings_frame, text="Tema de la interfaz:", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(anchor="w", padx=20, pady=(10,5))
        ctk.CTkOptionMenu(settings_frame, values=["Dark", "Light"], command=ctk.set_appearance_mode, fg_color=COLOR_PRIMARY_DARK, button_color=COLOR_ACCENT, button_hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT).pack(fill="x", padx=20, pady=(0,10))

    def set_notification(self, message, color=COLOR_TEXT_MEDIUM):
        """Muestra un mensaje de notificación en el panel principal."""
        self.notification_label.configure(text=message, text_color=color)
        self.notification_frame.configure(fg_color=COLOR_SECONDARY_DARK if message else COLOR_PRIMARY_DARK) # Fondo si hay mensaje
        if message:
            self.after(5000, lambda: self.set_notification("")) # Limpia después de 5 segundos

    # --- Métodos para Tareas ---

    def set_task_importance(self, importance):
        self.current_task_importance = importance

    def add_task(self):
        task_name = self.task_entry.get().strip()
        task_notes = self.task_notes_entry.get("1.0", "end-1c").strip()
        importance = self.current_task_importance

        if not task_name:
            self.set_notification("❌ El nombre de la tarea está vacío.", COLOR_ERROR)
            return

        query = "INSERT INTO tareas (nombre, fecha_creacion, importancia, notas) VALUES (%s, %s, %s, %s)"
        if ejecutar_consulta_bd(query, (task_name, datetime.now(), importance, task_notes)):
            self.set_notification(f"✅ Tarea añadida: '{task_name}'", COLOR_SUCCESS)
            self.task_entry.delete(0, "end")
            self.task_notes_entry.set_text("") # Usa set_text para manejar el placeholder
            self.task_importance_menu.set("Media")
            self.current_task_importance = "Media"
            self.load_tasks() # Recarga la lista de tareas
        else:
            self.set_notification("❌ Error al añadir la tarea. Revisa la consola para más detalles.", COLOR_ERROR)

    def load_tasks(self):
        for widget in self.tasks_list_frame.winfo_children():
            widget.destroy()

        query = "SELECT id, nombre, completada, importancia, notas, fecha_creacion FROM tareas ORDER BY fecha_creacion DESC"
        tasks = obtener_datos_bd(query)

        if not tasks:
            ctk.CTkLabel(self.tasks_list_frame, text="No hay tareas en tu lista.", font=ctk.CTkFont(size=14, slant="italic"), text_color=COLOR_TEXT_MEDIUM).pack(pady=20)
            return

        for task in tasks:
            task_id, name, completed, importance, notes, creation_date = task
            
            task_item_frame = ctk.CTkFrame(self.tasks_list_frame, fg_color=COLOR_PRIMARY_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
            task_item_frame.pack(fill="x", pady=5, padx=10)
            task_item_frame.grid_columnconfigure(0, weight=1) # Checkbox y nombre
            task_item_frame.grid_columnconfigure(1, weight=0) # Botones

            # Contenedor para checkbox y nombre (parte izquierda)
            left_section_frame = ctk.CTkFrame(task_item_frame, fg_color="transparent")
            left_section_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
            left_section_frame.grid_columnconfigure(1, weight=1) # Para que el nombre se expanda

            check_state = ctk.BooleanVar(value=completed)
            checkbox = ctk.CTkCheckBox(left_section_frame, text="", variable=check_state, command=lambda id=task_id: self.toggle_task_completion(id),
                                       fg_color=COLOR_ACCENT, hover_color="#4A90D9", border_color=COLOR_BORDER, width=20)
            checkbox.grid(row=0, column=0, padx=(0,10), pady=5, sticky="w")
            
            # Etiqueta para el nombre de la tarea (se ajusta el color según el estado)
            # Se usa 'bold' para destacar el nombre de la tarea
            task_name_label = ctk.CTkLabel(left_section_frame, text=name, font=ctk.CTkFont(size=14, weight="bold"), justify="left")
            task_name_label.grid(row=0, column=1, sticky="ew", pady=5)

            if completed:
                task_name_label.configure(text_color=COLOR_SUCCESS, font=ctk.CTkFont(size=14, weight="bold", overstrike=1))
            else:
                task_name_label.configure(text_color=COLOR_TEXT_LIGHT)
                # Mostrar importancia con un círculo de color y texto
                importance_color_map = {"Baja": "#8BC34A", "Media": "#FFC107", "Alta": "#E53935"}
                # Usar un CTkCanvas para dibujar un círculo
                importance_canvas = ctk.CTkCanvas(left_section_frame, width=10, height=10, bg=left_section_frame.cget("fg_color"), highlightthickness=0)
                importance_canvas.create_oval(0, 0, 10, 10, fill=importance_color_map.get(importance, COLOR_TEXT_MEDIUM), outline="")
                importance_canvas.grid(row=0, column=2, padx=(10,5), sticky="w")
                
                ctk.CTkLabel(left_section_frame, text=f"({importance})", font=ctk.CTkFont(size=11, slant="italic"), text_color=COLOR_TEXT_MEDIUM).grid(row=0, column=3, sticky="w")
            
            # Contenedor para botones (parte derecha)
            right_section_frame = ctk.CTkFrame(task_item_frame, fg_color="transparent")
            right_section_frame.grid(row=0, column=1, sticky="e", padx=10, pady=5)

            detail_button = ctk.CTkButton(right_section_frame, text="Detalles", width=80, height=28, 
                                          fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, 
                                          command=lambda id=task_id, n=name, imp=importance, nt=notes, cd=creation_date: self.show_task_details_window(id, n, imp, nt, cd))
            detail_button.pack(side="left", padx=(0,5))

            delete_button = ctk.CTkButton(right_section_frame, text="Eliminar", width=80, height=28, 
                                          fg_color=COLOR_ERROR, hover_color="#D32F2F", text_color=COLOR_TEXT_LIGHT, 
                                          command=lambda id=task_id: self.delete_task(id))
            delete_button.pack(side="left")

    def toggle_task_completion(self, task_id):
        query = "UPDATE tareas SET completada = NOT completada WHERE id = %s"
        if ejecutar_consulta_bd(query, (task_id,)):
            self.load_tasks()
        else:
            self.set_notification("❌ Error al actualizar el estado de la tarea.", COLOR_ERROR)

    def delete_task(self, task_id):
        query = "DELETE FROM tareas WHERE id = %s"
        if ejecutar_consulta_bd(query, (task_id,)):
            self.set_notification("🗑️ Tarea eliminada.", COLOR_TEXT_MEDIUM)
            self.load_tasks()
        else:
            self.set_notification("❌ Error al eliminar la tarea.", COLOR_ERROR)

    def show_task_details_window(self, task_id, name, importance, notes, creation_date):
        """Muestra una ventana CTkToplevel con los detalles de la tarea."""
        details_window = ctk.CTkToplevel(self)
        details_window.title(f"Detalles de la Tarea: {name}")
        details_window.geometry("500x400")
        details_window.resizable(False, False)
        details_window.transient(self) # Hace que la ventana de detalles sea hija de la principal
        details_window.grab_set() # Bloquea interacción con la ventana principal

        # Centrar la ventana de detalles
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (details_window.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (details_window.winfo_height() // 2)
        details_window.geometry(f"+{x}+{y}")

        details_window.configure(fg_color=COLOR_PRIMARY_DARK)

        frame = ctk.CTkFrame(details_window, fg_color=COLOR_SECONDARY_DARK, corner_radius=10)
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(frame, text="Detalles de la Tarea", font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_TEXT_LIGHT).pack(pady=(15,10))
        
        # Mostrar los detalles de la tarea
        detail_font = ctk.CTkFont(size=14)
        # Se usa 'bold' para los títulos de los detalles
        detail_title_font = ctk.CTkFont(size=14, weight="bold") 

        ctk.CTkLabel(frame, text="Nombre:", font=detail_title_font, text_color=COLOR_TEXT_LIGHT).pack(anchor="w", padx=20, pady=(10,0))
        ctk.CTkLabel(frame, text=name, font=detail_font, text_color=COLOR_TEXT_MEDIUM, wraplength=400, justify="left").pack(anchor="w", padx=20)

        ctk.CTkLabel(frame, text="Importancia:", font=detail_title_font, text_color=COLOR_TEXT_LIGHT).pack(anchor="w", padx=20, pady=(10,0))
        ctk.CTkLabel(frame, text=importance, font=detail_font, text_color=COLOR_TEXT_MEDIUM, wraplength=400, justify="left").pack(anchor="w", padx=20)
        
        ctk.CTkLabel(frame, text="Fecha de Creación:", font=detail_title_font, text_color=COLOR_TEXT_LIGHT).pack(anchor="w", padx=20, pady=(10,0))
        ctk.CTkLabel(frame, text=creation_date.strftime("%d-%m-%Y %H:%M"), font=detail_font, text_color=COLOR_TEXT_MEDIUM, wraplength=400, justify="left").pack(anchor="w", padx=20)

        ctk.CTkLabel(frame, text="Notas:", font=detail_title_font, text_color=COLOR_TEXT_LIGHT).pack(anchor="w", padx=20, pady=(10,0))
        # Usamos un CTkTextbox para las notas para que sean scrollable si son largas
        notes_display = ctk.CTkTextbox(frame, height=80, wrap="word", font=detail_font, text_color=COLOR_TEXT_MEDIUM,
                                       fg_color=COLOR_PRIMARY_DARK, border_color=COLOR_BORDER, corner_radius=5)
        notes_display.insert("1.0", notes if notes else "No hay notas adicionales.")
        notes_display.configure(state="disabled") # Para que no sea editable
        notes_display.pack(fill="x", padx=20, pady=(0,15))

        ctk.CTkButton(frame, text="Cerrar", command=details_window.destroy, fg_color=COLOR_ACCENT, hover_color="#4A90D9", text_color=COLOR_TEXT_LIGHT, height=35).pack(pady=(5,15))
        
        # Manejar el cierre de la ventana
        details_window.protocol("WM_DELETE_WINDOW", lambda: self._on_details_close(details_window))

    def _on_details_close(self, window):
        """Libera el grab cuando la ventana de detalles se cierra."""
        window.grab_release()
        window.destroy()

    # --- Métodos para Listas ---

    def add_list(self):
        list_title = self.list_title_entry.get().strip()
        list_elements = self.list_elements_entry.get("1.0", "end-1c").strip()

        if not list_title:
            self.set_notification("❌ El título de la lista no puede estar vacío.", COLOR_ERROR)
            return

        # Limpia los elementos de líneas vacías adicionales
        cleaned_elements = "\n".join(filter(None, [line.strip() for line in list_elements.split('\n')]))

        query = "INSERT INTO listas (titulo, elementos, fecha_creacion) VALUES (%s, %s, %s)"
        if ejecutar_consulta_bd(query, (list_title, cleaned_elements, datetime.now())):
            self.set_notification(f"✅ Lista '{list_title}' creada.", COLOR_SUCCESS)
            self.list_title_entry.delete(0, "end")
            self.list_elements_entry.set_text("") # Usa set_text para manejar el placeholder
            self.load_lists()
        else:
            self.set_notification("❌ Error al crear la lista. Revisa la consola.", COLOR_ERROR)

    def load_lists(self):
        for widget in self.lists_scrollable_frame.winfo_children():
            widget.destroy()

        query = "SELECT id, titulo, elementos FROM listas ORDER BY fecha_creacion DESC"
        lists = obtener_datos_bd(query)

        if not lists:
            ctk.CTkLabel(self.lists_scrollable_frame, text="No hay listas creadas.", font=ctk.CTkFont(size=14, slant="italic"), text_color=COLOR_TEXT_MEDIUM).pack(pady=20)
            return

        for list_item in lists:
            list_id, title, elements_text = list_item
            
            list_item_frame = ctk.CTkFrame(self.lists_scrollable_frame, fg_color=COLOR_PRIMARY_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=8)
            list_item_frame.pack(fill="x", pady=5, padx=10)
            
            title_frame = ctk.CTkFrame(list_item_frame, fg_color="transparent")
            title_frame.pack(fill="x", pady=(10,5), padx=10)
            ctk.CTkLabel(title_frame, text=f"• {title}", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT_LIGHT, justify="left").pack(side="left", anchor="w")
            
            delete_button = ctk.CTkButton(title_frame, text="Eliminar", width=80, height=28, 
                                          fg_color=COLOR_ERROR, hover_color="#D32F2F", text_color=COLOR_TEXT_LIGHT, 
                                          command=lambda id=list_id: self.delete_list(id))
            delete_button.pack(side="right")

            if elements_text:
                element_list = elements_text.split('\n')
                for element in element_list:
                    if element.strip():
                        ctk.CTkLabel(list_item_frame, text=f"  - {element.strip()}", font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MEDIUM, justify="left", wraplength=500).pack(anchor="w", padx=30)
            else:
                ctk.CTkLabel(list_item_frame, text="  (Lista vacía)", font=ctk.CTkFont(size=12, slant="italic"), text_color=COLOR_TEXT_MEDIUM, justify="left").pack(anchor="w", padx=30)
            
            ctk.CTkFrame(list_item_frame, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=10, pady=(10,0)) # Separador interno

    def delete_list(self, list_id):
        query = "DELETE FROM listas WHERE id = %s"
        if ejecutar_consulta_bd(query, (list_id,)):
            self.set_notification("🗑️ Lista eliminada.", COLOR_TEXT_MEDIUM)
            self.load_lists()
        else:
            self.set_notification("❌ Error al eliminar la lista.", COLOR_ERROR)

    # --- Otros métodos ---

    def get_study_topic(self):
        self.study_topic_label.configure(text="Generando tema, por favor espere...", text_color=COLOR_TEXT_MEDIUM)
        threading.Thread(target=self._fetch_study_topic_in_background).start()

    def _fetch_study_topic_in_background(self):
        tema = obtener_tema_ia()
        self.after(0, lambda: self.study_topic_label.configure(text=f"✨ Tema del día: {tema}", text_color=COLOR_ACCENT))

    def analyze_with_ai(self):
        self.ai_analysis_text.delete("1.0", "end")
        self.ai_analysis_text.insert("1.0", "⌛ Analizando tu información y generando un resumen profesional...", "center")
        
        # FIX PREVIO: Se eliminó el argumento 'font' de tag_config para resolver el error de escalado
        self.ai_analysis_text.tag_config("center", justify="center", foreground=COLOR_TEXT_MEDIUM)
        
        self.update_idletasks() # Asegura que el mensaje de carga se muestre

        threading.Thread(target=self._fetch_ai_analysis_in_background).start()

    def _fetch_ai_analysis_in_background(self):
        analysis = analizar_datos_con_ia()
        self.after(0, lambda: self._display_ai_analysis(analysis))

    def _display_ai_analysis(self, analysis):
        self.ai_analysis_text.delete("1.0", "end")
        self.ai_analysis_text.insert("1.0", analysis)
        self.ai_analysis_text.tag_remove("center", "1.0", "end") # Elimina el tag de centrado una vez que el contenido real se carga
        self.ai_analysis_text.configure(text_color=COLOR_TEXT_LIGHT)


# --- 3. INICIO DE LA APLICACIÓN ---

if __name__ == "__main__":
    if conectar_bd() is None:
        print("\n--- ADVERTENCIA CRÍTICA ---")
        print("No se pudo establecer conexión con la base de datos MySQL.")
        print(f"Por favor, verifica la configuración en DB_CONFIG (host, user, password, database).")
        print(f"Asegúrate de que el servidor MySQL esté corriendo y la base de datos '{DB_CONFIG.get('database')}' exista.")
        print("El programa continuará, pero las funcionalidades de tareas y listas no funcionarán.")
        print("----------------------------\n")
        # En una aplicación real, aquí podrías cerrar la app o deshabilitar funcionalidades de BD.

    app = App()
    app.mainloop()