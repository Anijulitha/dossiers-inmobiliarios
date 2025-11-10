import sqlite3
from datetime import datetime

DB_NAME = "dossiers_inmobiliarios.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crear tabla con nombre CORRECTO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo TEXT,
            precio TEXT,
            habitaciones TEXT,
            metros TEXT,
            zona TEXT,
            estado TEXT,
            fecha_analisis TEXT,
            activo INTEGER DEFAULT 1
        )
    ''')
    
    # FORZAR MIGRACIÓN SI EXISTE COLUMNA VIEJA
    cursor.execute("PRAGMA table_info(propiedades)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if 'habitacione' in columnas:
        print("MIGRANDO columna 'habitacione' → 'habitaciones'...")
        cursor.execute("ALTER TABLE propiedades RENAME COLUMN habitacione TO habitaciones")
    
    conn.commit()
    conn.close()

def insertar_propiedad(datos):
    init_db()  # aseguramos que existe
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO propiedades 
        (archivo, precio, habitaciones, metros, zona, estado, fecha_analisis)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos['archivo'],
        datos.get('precio', 'No encontrado'),
        datos.get('habitaciones', 'No encontrado'),
        datos.get('metros', 'No encontrado'),
        datos.get('zona', 'No encontrado'),
        datos.get('estado', 'No encontrado'),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# Inicializar siempre
init_db()
