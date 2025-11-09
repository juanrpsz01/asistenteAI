# 🧠 Asistente de Programación v3.0

## 📋 Descripción General
**Asistente de Programación v3.0** es una herramienta integral de apoyo al desarrollo técnico y personal del usuario.  
A través de la integración con **Inteligencia Artificial**, el asistente no solo gestiona tareas o recordatorios, sino que también **analiza patrones, ofrece reflexiones personalizadas y guía el crecimiento continuo** del usuario en su proceso de aprendizaje y productividad.

Este proyecto está diseñado con una arquitectura modular y escalable, lo que facilita futuras ampliaciones como:
- 🔗 Integración con APIs de calendarios externos (Google Calendar, Outlook).
- 🔔 Sistema de notificaciones automáticas.
- 📊 Seguimiento de métricas de productividad mediante gráficos interactivos.

---

## ⚙️ Estructura del Proyecto

AsistenteProgramacionV3.0/
│
├── asistente.py # Archivo principal con la lógica del asistente
├── asistente_db.sql # Script SQL para crear la base de datos y las tablas
├── README.md # Documentación del proyecto
└── requirements.txt (opcional)

markdown
Copiar código

---

## 🗃️ Base de Datos

El proyecto utiliza **MySQL** como sistema gestor de base de datos.  
El archivo `asistente_db.sql` crea la base `asistente_db` con las siguientes tablas principales:

| Tabla | Descripción | Campos Principales |
|-------|--------------|-------------------|
| `tareas` | Gestiona las tareas con su estado, importancia y notas. | `id`, `nombre`, `fecha_creacion`, `completada`, `importancia`, `notas` |
| `recordatorios` | Guarda los recordatorios creados por el usuario. | `id`, `texto`, `fecha_creacion` |
| `listas` | Permite crear listas personalizadas con elementos. | `id`, `titulo`, `elementos`, `fecha_creacion` |
| `trabajos` | Registra trabajos o proyectos con su fecha de creación. | `id`, `nombre`, `fecha_hora`, `fecha_creacion` |

---

## 💡 Funcionalidades Principales

- ✅ **Gestión de tareas:** Crear, listar, marcar como completadas y eliminar tareas.  
- 🧾 **Recordatorios automáticos:** Almacena y consulta recordatorios por fecha.  
- 🗂️ **Listas personalizadas:** Permite gestionar listas con varios elementos.  
- 🧠 **Orientación inteligente:** El sistema puede ofrecer reflexiones o recomendaciones basadas en la actividad.  
- 📈 **Escalabilidad:** Su diseño permite agregar módulos adicionales como estadísticas o análisis de productividad.

---

## 🖥️ Requisitos del Sistema

- **Python 3.8 o superior**
- **MySQL 8.0 o superior**
- Librerías recomendadas (si el proyecto las utiliza):
  ```bash
  pip install mysql-connector-python
(Agregar más librerías según las dependencias de asistente.py)

🚀 Instalación y Ejecución
Clonar el repositorio:

bash
Copiar código
git clone https://github.com/tuusuario/asistente-programacion-v3.git
cd asistente-programacion-v3
Configurar la base de datos:

Crear una base de datos en MySQL importando el archivo:

bash
Copiar código
mysql -u root -p < asistente_db.sql
Ejecutar el programa:

bash
Copiar código
python asistente.py
(Opcional) Configurar credenciales de conexión en el archivo asistente.py si es necesario:

python
Copiar código
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="tu_contraseña",
    database="asistente_db"
)
🧩 Posibles Extensiones Futuras
Integración con APIs de calendario para sincronizar eventos.

Sistema de notificaciones por correo o escritorio.

Implementación de un panel web con visualización de métricas y gráficos.

Añadir modelo IA para análisis predictivo del rendimiento del usuario.

👨‍💻 Autor
Juan Francisco Realpe Sánchez
Proyecto académico — 2025
Desarrollado como demostración técnica y funcional de un asistente de programación con IA.

🧠 Licencia
Este proyecto es de uso académico y educativo.
Puede ser modificado o mejorado libremente con fines de aprendizaje.
