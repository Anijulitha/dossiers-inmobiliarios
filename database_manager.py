import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import os

class DatabaseManager:
    def __init__(self, db_path="dossiers_inmobiliarios.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos con las tablas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla principal de propiedades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS propiedades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archivo TEXT NOT NULL,
                precio TEXT,
                habitaciones TEXT,
                metros TEXT,
                zona TEXT,
                estado TEXT,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash_archivo TEXT UNIQUE,
                activo BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabla de historial de cambios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                propiedad_id INTEGER,
                campo TEXT,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (propiedad_id) REFERENCES propiedades (id)
            )
        ''')
        
        # Tabla de estadísticas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estadisticas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_propiedades INTEGER,
                precio_promedio REAL,
                habitaciones_promedio REAL,
                metros_promedio REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Base de datos inicializada: {self.db_path}")
    
    def calcular_hash_archivo(self, archivo_path):
        """Calcula el hash de un archivo para detectar cambios"""
        try:
            with open(archivo_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
    
    def guardar_propiedad(self, datos_propiedad, carpeta_pdf="dossiers_inmobiliarios"):
        """Guarda o actualiza una propiedad en la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        archivo_path = os.path.join(carpeta_pdf, datos_propiedad['archivo'])
        hash_archivo = self.calcular_hash_archivo(archivo_path)
        
        if not hash_archivo:
            conn.close()
            return False
        
        # Verificar si el archivo ya existe
        cursor.execute(
            "SELECT id, archivo, precio, habitaciones, metros, zona, estado FROM propiedades WHERE hash_archivo = ?", 
            (hash_archivo,)
        )
        existente = cursor.fetchone()
        
        if existente:
            # Actualizar propiedad existente
            propiedad_id = existente[0]
            cambios = []
            
            campos = ['archivo', 'precio', 'habitaciones', 'metros', 'zona', 'estado']
            for i, campo in enumerate(campos):
                if existente[i+1] != datos_propiedad[campo]:
                    cambios.append((campo, existente[i+1], datos_propiedad[campo]))
            
            if cambios:
                # Registrar cambios en el historial
                for campo, valor_anterior, valor_nuevo in cambios:
                    cursor.execute(
                        "INSERT INTO historial (propiedad_id, campo, valor_anterior, valor_nuevo) VALUES (?, ?, ?, ?)",
                        (propiedad_id, campo, valor_anterior, valor_nuevo)
                    )
                
                # Actualizar propiedad
                cursor.execute('''
                    UPDATE propiedades 
                    SET archivo=?, precio=?, habitaciones=?, metros=?, zona=?, estado=?, fecha_analisis=?
                    WHERE id=?
                ''', (
                    datos_propiedad['archivo'], datos_propiedad['precio'], 
                    datos_propiedad['habitaciones'], datos_propiedad['metros'],
                    datos_propiedad['zona'], datos_propiedad['estado'],
                    datetime.now(), propiedad_id
                ))
                
                print(f"📝 Actualizada: {datos_propiedad['archivo']}")
            else:
                print(f"ℹ️  Sin cambios: {datos_propiedad['archivo']}")
        else:
            # Insertar nueva propiedad
            cursor.execute('''
                INSERT INTO propiedades (archivo, precio, habitaciones, metros, zona, estado, hash_archivo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datos_propiedad['archivo'], datos_propiedad['precio'], 
                datos_propiedad['habitaciones'], datos_propiedad['metros'],
                datos_propiedad['zona'], datos_propiedad['estado'], hash_archivo
            ))
            print(f"✅ Nueva: {datos_propiedad['archivo']}")
        
        conn.commit()
        conn.close()
        return True
    
    def obtener_todas_propiedades(self, solo_activas=True):
        """Obtiene todas las propiedades de la base de datos"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT archivo, precio, habitaciones, metros, zona, estado, fecha_analisis FROM propiedades"
        if solo_activas:
            query += " WHERE activo = 1"
        
        df = pd.read_sql_query(query + " ORDER BY fecha_analisis DESC", conn)
        conn.close()
        return df
    
    def obtener_estadisticas_historicas(self):
        """Obtiene estadísticas históricas"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('''
            SELECT fecha, total_propiedades, precio_promedio, habitaciones_promedio, metros_promedio
            FROM estadisticas 
            ORDER BY fecha DESC
        ''', conn)
        conn.close()
        return df
    
    def guardar_estadisticas_actuales(self):
        """Guarda las estadísticas actuales en la base de datos"""
        propiedades = self.obtener_todas_propiedades()
        
        if len(propiedades) == 0:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calcular promedios
        precio_promedio = self._calcular_promedio_db(propiedades, 'precio')
        hab_promedio = self._calcular_promedio_db(propiedades, 'habitaciones')
        metros_promedio = self._calcular_promedio_db(propiedades, 'metros')
        
        cursor.execute('''
            INSERT INTO estadisticas (total_propiedades, precio_promedio, habitaciones_promedio, metros_promedio)
            VALUES (?, ?, ?, ?)
        ''', (len(propiedades), precio_promedio, hab_promedio, metros_promedio))
        
        conn.commit()
        conn.close()
        print("📊 Estadísticas guardadas en la base de datos")
    
    def _calcular_promedio_db(self, df, campo):
        """Calcula promedios desde la base de datos"""
        try:
            valores = []
            for valor in df[campo]:
                if valor != 'No encontrado':
                    if campo == 'precio' and '€' in str(valor):
                        limpio = str(valor).replace('€', '').replace('.', '').replace(',', '.').strip()
                    elif campo == 'habitaciones' and 'hab' in str(valor):
                        limpio = str(valor).replace('hab', '').strip()
                    elif campo == 'metros' and 'm²' in str(valor):
                        limpio = str(valor).replace('m²', '').strip()
                    else:
                        limpio = str(valor)
                    
                    try:
                        valores.append(float(limpio))
                    except:
                        continue
            
            return sum(valores) / len(valores) if valores else 0
        except:
            return 0

# Función de prueba
def test_database():
    """Función para probar la base de datos"""
    db = DatabaseManager()
    print("✅ Base de datos creada correctamente")
    
    # Mostrar tablas creadas
    conn = sqlite3.connect("dossiers_inmobiliarios.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()
    print("📊 Tablas creadas:", [tabla[0] for tabla in tablas])
    conn.close()

if __name__ == "__main__":
    test_database()