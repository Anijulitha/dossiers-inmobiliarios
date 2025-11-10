import os
import re
import pandas as pd
import pdfplumber
from pathlib import Path
from database_manager import DatabaseManager  # ✅ NUEVA IMPORTACIÓN

print("🏠 EXTRACTOR DE DOSSIERS INMOBILIARIOS - VERSIÓN MEJORADA")
print("=" * 60)

# Configuración
carpeta_pdf = "dossiers_inmobiliarios"
archivo_salida = "resultados_dossiers.xlsx"

# Verificar carpeta
if not os.path.exists(carpeta_pdf):
    print(f"❌ La carpeta '{carpeta_pdf}' no existe")
    os.makedirs(carpeta_pdf)
    print("💡 Carpeta creada. Coloca tus PDFs y ejecuta de nuevo.")
    exit()

# Buscar archivos PDF
archivos = [f for f in os.listdir(carpeta_pdf) if f.lower().endswith('.pdf')]

if not archivos:
    print(f"❌ No hay archivos PDF en '{carpeta_pdf}'")
    print("💡 Archivos encontrados en la carpeta:")
    for f in os.listdir(carpeta_pdf):
        print(f"   - {f}")
    exit()

print(f"📁 Encontrados {len(archivos)} archivos PDF:")
for archivo in archivos:
    print(f"   📄 {archivo}")
print("=" * 60)

datos = []

# ✅ NUEVO: Crear instancia de la base de datos
db = DatabaseManager()
print("🗃️ Base de datos inicializada")

# Patrones más flexibles para diferentes formatos
patrones = {
    'precio': [
        r'precio:\s*([\d\.,]+)\s*[€€]',
        r'valor:\s*([\d\.,]+)\s*[€€]',
        r'([\d\.,]+)\s*[€€]',
        r'precio.?(\d{1,3}(?:\.\d{3})(?:,\d{2})?)',
        r'importe:\s*([\d\.,]+)',
        r'coste:\s*([\d\.,]+)',
        r'€\s*([\d\.,]+)'
    ],
    'habitaciones': [
        r'(\d+)\s*hab',
        r'habitaciones:\s*(\d+)',
        r'dormitorios:\s*(\d+)',
        r'(\d+)\s*dorm',
        r'habitacion:\s*(\d+)',
        r'dormitorio:\s*(\d+)'
    ],
    'metros': [
        r'(\d+(?:[.,]\d+)?)\s*m²',
        r'(\d+(?:[.,]\d+)?)\s*m2',
        r'superficie:\s*(\d+(?:[.,]\d+)?)',
        r'metros:\s*(\d+(?:[.,]\d+)?)',
        r'm²:\s*(\d+(?:[.,]\d+)?)',
        r'superficie.*?(\d+(?:[.,]\d+)?)'
    ],
    'zona': [
        r'zona:\s*([^\n\r.,;]+)',
        r'ubicaci[oó]n:\s*([^\n\r.,;]+)',
        r'barrio:\s*([^\n\r.,;]+)',
        r'distrito:\s*([^\n\r.,;]+)',
        r'situad[ao]\s*en\s*([^\n\r.,;]+)',
        r'localizaci[oó]n:\s*([^\n\r.,;]+)'
    ],
    'estado': [
        r'estado:\s*([^\n\r.,;]+)',
        r'conservaci[oó]n:\s*([^\n\r.,;]+)',
        r'calidad:\s*([^\n\r.,;]+)',
        r'(nuevo|seminuevo|reformado|a reformar|excelente|bueno|regular)'
    ]
}

def buscar_dato(texto, tipo_dato):
    """Busca un dato en el texto usando múltiples patrones"""
    if tipo_dato not in patrones:
        return 'No encontrado'
    
    for patron in patrones[tipo_dato]:
        try:
            coincidencia = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if coincidencia:
                resultado = coincidencia.group(1).strip()
                # Limpiar resultado
                if tipo_dato in ['precio', 'metros']:
                    resultado = resultado.replace('.', '').replace(',', '.')
                return resultado
        except Exception as e:
            continue
    return 'No encontrado'

def analizar_texto_completo(texto):
    """Analiza el texto completo para entender su estructura"""
    print("  🔍 Analizando estructura del documento...")
    
    # Dividir en líneas y buscar patrones
    lineas = texto.split('\n')
    
    # Buscar líneas que contengan información relevante
    lineas_interesantes = []
    for linea in lineas:
        linea_limpia = linea.strip()
        if len(linea_limpia) > 5:  # Ignorar líneas muy cortas
            # Buscar patrones clave
            if any(palabra in linea_limpia.lower() for palabra in 
                  ['precio', 'habitacion', 'dormitorio', 'metro', 'superficie', 'zona', 'estado', '€', 'm²']):
                lineas_interesantes.append(linea_limpia)
    
    # Mostrar líneas interesantes para debugging
    if lineas_interesantes:
        print("  📝 Líneas con información potencial:")
        for linea in lineas_interesantes[:5]:  # Mostrar solo las primeras 5
            print(f"     '{linea}'")
    
    return lineas_interesantes

for archivo in archivos:
    print(f"\n📄 Procesando: {archivo}")
    
    ruta_completa = os.path.join(carpeta_pdf, archivo)
    
    try:
        # Extraer texto del PDF
        texto_completo = ""
        with pdfplumber.open(ruta_completa) as pdf:
            for pagina_num, pagina in enumerate(pdf.pages):
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += f"\n--- Página {pagina_num + 1} ---\n{texto_pagina}"
        
        if not texto_completo.strip():
            print("  ⚠️  No se pudo extraer texto del PDF")
            continue
        
        # Analizar estructura del documento
        lineas_interesantes = analizar_texto_completo(texto_completo)
        
        # Buscar datos específicos
        precio = buscar_dato(texto_completo, 'precio')
        habitaciones = buscar_dato(texto_completo, 'habitaciones')
        metros = buscar_dato(texto_completo, 'metros')
        zona = buscar_dato(texto_completo, 'zona')
        estado = buscar_dato(texto_completo, 'estado')
        
        # Formatear resultados
        if precio != 'No encontrado':
            try:
                precio_num = float(precio)
                precio = f"€ {precio_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except:
                precio = f"€ {precio}"
        
        if habitaciones != 'No encontrado':
            habitaciones = f"{habitaciones} hab"
        
        if metros != 'No encontrado':
            try:
                metros_num = float(metros)
                metros = f"{metros_num:.0f} m²"
            except:
                metros = f"{metros} m²"
        
        # Guardar datos
        datos_archivo = {
            'archivo': archivo,
            'precio': precio,
            'habitaciones': habitaciones,
            'metros': metros,
            'zona': zona,
            'estado': estado
        }
        
        # ✅ NUEVO: Guardar en base de datos
        try:
            db.guardar_propiedad(datos_archivo, carpeta_pdf)
        except Exception as e:
            print(f"  ❌ Error guardando en BD: {e}")
        
        datos.append(datos_archivo)
        
        # Mostrar resultados
        print("  📊 DATOS EXTRAÍDOS:")
        print(f"     💰 Precio: {precio}")
        print(f"     🛏️  Habitaciones: {habitaciones}")
        print(f"     📏 Metros: {metros}")
        print(f"     📍 Zona: {zona}")
        print(f"     🏗️  Estado: {estado}")
        
    except Exception as e:
        print(f"  ❌ Error procesando {archivo}: {str(e)}")
        continue

# Guardar resultados en Excel
if datos:
    df = pd.DataFrame(datos)
    
    # Reordenar columnas
    columnas_orden = ['archivo', 'precio', 'habitaciones', 'metros', 'zona', 'estado']
    df = df[columnas_orden]
    
    # Guardar
    df.to_excel(archivo_salida, index=False)
    
    print(f"\n✅ RESULTADOS GUARDADOS:")
    print(f"   📊 Archivo: {archivo_salida}")
    print(f"   📈 Registros: {len(datos)}")
    print(f"   📋 Columnas: {', '.join(columnas_orden)}")
    
    # ✅ NUEVO: Guardar estadísticas en la base de datos
    try:
        db.guardar_estadisticas_actuales()
        print("   🗃️  Datos guardados en base de datos")
    except Exception as e:
        print(f"   ❌ Error guardando estadísticas: {e}")
    
    # Mostrar preview de los datos
    print(f"\n📋 VISTA PREVIA:")
    print(df.head(10).to_string(index=False))
    
else:
    print("❌ No se pudieron extraer datos de ningún archivo")

print("=" * 60)
print("🎉 Proceso completado!")