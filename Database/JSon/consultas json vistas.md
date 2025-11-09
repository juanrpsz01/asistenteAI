# 🧩 Consultas JSON — Asistente de Programación v3.0

Este archivo contiene todas las **consultas SQL** diseñadas para el proyecto **Asistente de Programación v3.0**, transformadas en **vistas** que retornan la información en **formato JSON**.  
Cada vista incluye una breve explicación de su propósito y cómo puede ser utilizada dentro del asistente o desde una API externa.

---

## ⚙️ Configuración previa

Antes de crear las vistas, asegúrate de estar usando la base de datos correcta:

```sql
USE asistente_db;
```

---

## 🧠 Vista: `vista_tareas_json`
**Descripción:** Devuelve todas las tareas creadas con su información completa en formato JSON. Ideal para obtener un listado completo de tareas desde el asistente o la API.

```sql
CREATE OR REPLACE VIEW vista_tareas_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'nombre', nombre,
            'fecha_creacion', fecha_creacion,
            'completada', completada,
            'importancia', importancia,
            'notas', notas
        )
    ) AS tareas_json
FROM tareas;
```

---

## 🕒 Vista: `vista_recordatorios_json`
**Descripción:** Retorna todos los recordatorios almacenados con su fecha de creación en formato JSON.

```sql
CREATE OR REPLACE VIEW vista_recordatorios_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'texto', texto,
            'fecha_creacion', fecha_creacion
        )
    ) AS recordatorios_json
FROM recordatorios;
```

---

## 🧾 Vista: `vista_listas_json`
**Descripción:** Devuelve todas las listas creadas por el usuario con su respectivo título, elementos y fecha de creación. Ideal para mostrar colecciones o listas personalizadas.

```sql
CREATE OR REPLACE VIEW vista_listas_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'titulo', titulo,
            'elementos', elementos,
            'fecha_creacion', fecha_creacion
        )
    ) AS listas_json
FROM listas;
```

---

## 💼 Vista: `vista_trabajos_json`
**Descripción:** Devuelve todos los trabajos o proyectos registrados junto con sus fechas en formato JSON. Útil para vincular tareas a proyectos concretos.

```sql
CREATE OR REPLACE VIEW vista_trabajos_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'nombre', nombre,
            'fecha_hora', fecha_hora,
            'fecha_creacion', fecha_creacion
        )
    ) AS trabajos_json
FROM trabajos;
```

---

## 🔗 Vista: `vista_tareas_y_recordatorios_json`
**Descripción:** Muestra las tareas y recordatorios que fueron creados el mismo día, lo que permite visualizar la productividad o la relación entre ambos tipos de registros.

```sql
CREATE OR REPLACE VIEW vista_tareas_y_recordatorios_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'fecha', t.fecha_creacion,
            'tarea', t.nombre,
            'recordatorio', r.texto
        )
    ) AS tareas_y_recordatorios_json
FROM tareas t
JOIN recordatorios r
  ON DATE(t.fecha_creacion) = DATE(r.fecha_creacion);
```

---

## 🔗 Vista: `vista_trabajos_y_tareas_json`
**Descripción:** Relaciona los trabajos con las tareas que se registraron en fechas cercanas (±2 días). Muy útil para análisis de progreso por proyecto.

```sql
CREATE OR REPLACE VIEW vista_trabajos_y_tareas_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'trabajo', tr.nombre,
            'fecha_trabajo', tr.fecha_hora,
            'tareas_relacionadas', (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'tarea', t.nombre,
                        'importancia', t.importancia,
                        'completada', t.completada
                    )
                )
                FROM tareas t
                WHERE DATE(t.fecha_creacion) BETWEEN DATE(tr.fecha_creacion) - INTERVAL 2 DAY AND DATE(tr.fecha_creacion) + INTERVAL 2 DAY
            )
        )
    ) AS trabajos_y_tareas_json
FROM trabajos tr;
```

---

## 🧩 Vista: `vista_resumen_general_json`
**Descripción:** Devuelve un resumen completo del sistema con tareas, listas y recordatorios en un único objeto JSON. Perfecta para mostrar un panel general del asistente.

```sql
CREATE OR REPLACE VIEW vista_resumen_general_json AS
SELECT JSON_OBJECT(
    'tareas', (
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT('nombre', nombre, 'importancia', importancia)
        ) FROM tareas
    ),
    'recordatorios', (
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT('texto', texto, 'fecha', fecha_creacion)
        ) FROM recordatorios
    ),
    'listas', (
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT('titulo', titulo, 'elementos', elementos)
        ) FROM listas
    )
) AS resumen_general_json;
```

---

## 📊 Vista: `vista_estadisticas_json`
**Descripción:** Ofrece métricas generales del sistema: número total de tareas, completadas, listas, trabajos y recordatorios.

```sql
CREATE OR REPLACE VIEW vista_estadisticas_json AS
SELECT JSON_OBJECT(
    'total_tareas', (SELECT COUNT(*) FROM tareas),
    'tareas_completadas', (SELECT COUNT(*) FROM tareas WHERE completada = 1),
    'total_recordatorios', (SELECT COUNT(*) FROM recordatorios),
    'total_listas', (SELECT COUNT(*) FROM listas),
    'total_trabajos', (SELECT COUNT(*) FROM trabajos)
) AS estadisticas_json;
```

---

## 📅 Vista: `vista_tareas_recientes_json`
**Descripción:** Devuelve las 5 tareas más recientes para priorización o seguimiento de progreso.

```sql
CREATE OR REPLACE VIEW vista_tareas_recientes_json AS
SELECT JSON_ARRAYAGG(
    JSON_OBJECT('tarea', nombre, 'fecha_creacion', fecha_creacion)
) AS tareas_recientes_json
FROM tareas
ORDER BY fecha_creacion DESC
LIMIT 5;
```

---

## 📈 Vista: `vista_actividad_semana_json`
**Descripción:** Genera un historial de actividad semanal, combinando tareas y recordatorios creados por día.

```sql
CREATE OR REPLACE VIEW vista_actividad_semana_json AS
SELECT 
    JSON_ARRAYAGG(
        JSON_OBJECT(
            'fecha', DATE(t.fecha_creacion),
            'tareas_creadas', COUNT(t.id),
            'recordatorios_creados', (
                SELECT COUNT(r.id) FROM recordatorios r
                WHERE DATE(r.fecha_creacion) = DATE(t.fecha_creacion)
            )
        )
    ) AS actividad_semana_json
FROM tareas t
WHERE t.fecha_creacion >= NOW() - INTERVAL 7 DAY
GROUP BY DATE(t.fecha_creacion);
```

---

## ⚙️ Vista: `vista_productividad_json`
**Descripción:** Calcula el porcentaje de tareas completadas en comparación con el total, mostrando un indicador de productividad general.

```sql
CREATE OR REPLACE VIEW vista_productividad_json AS
SELECT JSON_OBJECT(
    'porcentaje_completado', 
    ROUND((SELECT COUNT(*) FROM tareas WHERE completada = 1) * 100.0 / (SELECT COUNT(*) FROM tareas), 2)
) AS productividad_json;
```

---

## ✅ Ejemplo de uso en MySQL
Puedes consultar cualquiera de las vistas directamente:

```sql
SELECT * FROM vista_resumen_general_json;
SELECT * FROM vista_estadisticas_json;
SELECT * FROM vista_tareas_y_recordatorios_json;
```

Cada una devolverá un resultado en **formato JSON**, ideal para integraciones con **Python**, **Node.js**, **Flask** o **FastAPI**.

---

## 👨‍💻 Autor
**Juan Francisco Realpe Sánchez**  
Proyecto académico — 2025  
Integración de Inteligencia Artificial y SQL estructurado con salida JSON.

---
