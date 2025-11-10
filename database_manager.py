import sqlite3
from datetime import datetime

DB_NAME = "dossiers_inmobiliarios.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo TEXT,
            precio TEXT,
            habitaciones TEXT,    -- ← CON S
            metros TEXT,
            zona TEXT,
            estado TEXT,
            fecha_analisis DATE,
            activo INTEGER DEFAULT 1
        )
    ''')
    
    
    cursor.execute("PRAGMA table_info(propiedades)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'habitacione' in columns and 'habitaciones' not in columns:
        print("Migrando columna antigua 'habitacione' → 'habitaciones'...")
        cursor.execute("ALTER TABLE propiedades RENAME COLUMN habitacione TO habitaciones")
    
    conn.commit()
    conn.close()

def insertar_propiedad(datos):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO propiedades 
        (archivo, precio, habitaciones, metros, zona, estado, fecha_analisis, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    ''', (
        datos['archivo'],
        datos['precio'],
        datos['habitaciones'],  
        datos['metros'],
        datos['zona'],
        datos['estado'],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    conn.commit()
    conn.close()


init_db()
