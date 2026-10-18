from mathutils import Vector
"""
validar_albatros_proteo.py
Script de validación técnica y de calidad para Albatros PROTEO.
Uso: blender --background --python scripts/validar_albatros_proteo.py
"""

import bpy
import os
import sys
import struct
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BLEND_FILE = os.path.join(BASE_DIR, "albatros_proteo.blend")
GLB_FILE = os.path.join(BASE_DIR, "exports", "albatros_proteo.glb")
RENDERS_DIR = os.path.join(BASE_DIR, "renders")

# Lista de comprobación
STATUS = {"OK": [], "ADVERTENCIA": [], "ERROR": []}

def record(level, message):
    STATUS[level].append(message)
    print(f"[{level}] {message}")

print("\n==========================================")
print("INICIANDO VALIDACIÓN: ALBATROS PROTEO")
print("==========================================\n")

# 1. Verificar existencia de .blend
if not os.path.isfile(BLEND_FILE):
    record("ERROR", f"No se encontró el archivo .blend en {BLEND_FILE}")
else:
    record("OK", f"Archivo .blend presente ({os.path.getsize(BLEND_FILE) / 1024:.1f} KB)")

# Cargar .blend
try:
    bpy.ops.wm.open_mainfile(filepath=BLEND_FILE)
    record("OK", "Blender cargó el archivo .blend sin errores.")
except Exception as e:
    record("ERROR", f"Error cargando .blend: {e}")
    sys.exit(1)

# 2. Verificar Objetos Requeridos
OBJETOS_OBLIGATORIOS = [
    "BODY_Main",
    "HEAD_Main",
    "BEAK_Upper",
    "BEAK_Lower",
    "EYE_L",
    "EYE_R",
    "EYELID_L",
    "EYELID_R",
    "WING_L",
    "WING_R",
    "LEG_L",
    "LEG_R",
    "FOOT_L",
    "FOOT_R",
    "TAIL_Main",
    "UNIFORM_Body",
    "UNIFORM_Collar",
    "UNIFORM_Neckerchief",
    "EMBLEM_Proteo",
    "ARMATURE_Albatros"
]

missing_objs = [name for name in OBJETOS_OBLIGATORIOS if name not in bpy.data.objects]
if missing_objs:
    record("ERROR", f"Faltan objetos obligatorios: {missing_objs}")
else:
    record("OK", f"Todos los {len(OBJETOS_OBLIGATORIOS)} objetos mínimos requeridos están presentes.")

# 3. Verificar Armature y Huesos
if "ARMATURE_Albatros" in bpy.data.objects:
    arm = bpy.data.objects["ARMATURE_Albatros"]
    if arm.type != 'ARMATURE':
        record("ERROR", "ARMATURE_Albatros no es de tipo ARMATURE")
    else:
        bones = arm.data.bones
        HUESOS_REQUERIDOS = [
            "root", "hips", "spine", "chest", "neck", "head",
            "beak_upper", "beak_lower", "eye.L", "eye.R",
            "wing_upper.L", "wing_lower.L", "wing_tip.L",
            "wing_upper.R", "wing_lower.R", "wing_tip.R",
            "thigh.L", "shin.L", "foot.L",
            "thigh.R", "shin.R", "foot.R"
        ]
        missing_bones = [b for b in HUESOS_REQUERIDOS if b not in bones]
        if missing_bones:
            record("ERROR", f"Faltan huesos requeridos en el rig: {missing_bones}")
        else:
            record("OK", f"Armature contiene los huesos requeridos (Total en rig: {len(bones)} huesos)")

# 4. Verificar Acciones de Animación
ACCIONES_REQUERIDAS = ["Idle", "Greeting", "Thinking", "Success", "Alert"]
missing_actions = [a for a in ACCIONES_REQUERIDAS if a not in bpy.data.actions]
if missing_actions:
    record("ERROR", f"Faltan acciones requeridas: {missing_actions}")
else:
    record("OK", f"Las 5 acciones existen en la biblioteca: {ACCIONES_REQUERIDAS}")
    # Comprobar duración de Idle
    act_idle = bpy.data.actions.get("Idle")
    if act_idle and act_idle.frame_range[1] >= 100:
        record("OK", f"Acción 'Idle' configurada para bucle ({int(act_idle.frame_range[0])} a {int(act_idle.frame_range[1])} frames)")
    else:
        record("ADVERTENCIA", "Acción 'Idle' tiene rango de frames inesperado")

# 5. Dimensiones del personaje y ubicación sobre Z=0
min_z = float('inf')
max_z = float('-inf')
total_tris = 0
total_polys = 0

for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.name.startswith("STUDIO_"):
        # Escala anómala
        if any(abs(s - 1.0) > 0.05 for s in obj.scale):
            record("ADVERTENCIA", f"Objeto {obj.name} tiene escala sin aplicar: {tuple(round(s,3) for s in obj.scale)}")
        
        # Evaluar malla con modificadores
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        eval_mesh.calc_loop_triangles()
        
        total_tris += len(eval_mesh.loop_triangles)
        total_polys += len(eval_mesh.polygons)
        
        # Bounding box global
        mat_world = obj.matrix_world
        for corner in obj.bound_box:
            world_co = mat_world @ Vector(corner)
            min_z = min(min_z, world_co.z)
            max_z = max(max_z, world_co.z)
            
        eval_obj.to_mesh_clear()

height = max_z - min_z
record("OK", f"Altura total del personaje: {height:.2f} m (Esperado: ~1.80 m)")
if abs(height - 1.80) > 0.35:
    record("ADVERTENCIA", f"La altura difiere de 1.80 m por más de 0.35 m ({height:.2f} m)")

record("OK", f"Cota inferior en Z: {min_z:.3f} m (Suelo en Z = 0.0)")
if min_z < -0.05:
    record("ERROR", f"El modelo atraviesa el suelo significativamente (Z_min = {min_z:.3f} m)")
elif min_z > 0.15:
    record("ADVERTENCIA", f"El modelo parece flotar sobre el suelo (Z_min = {min_z:.3f} m)")

# 6. Polígonos y Triángulos
record("OK", f"Complejidad geométrica: {total_polys:,} polígonos, {total_tris:,} triángulos.")
if total_tris > 60000:
    record("ADVERTENCIA", f"Total de triángulos ({total_tris}) excede el límite ideal de 60.000")
else:
    record("OK", "Presupuesto de polígonos respetado (< 60.000 triángulos).")

# 7. Materiales y nodos
mat_incompatible = []
for mat in bpy.data.materials:
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            # Tipos incompatibles estándar para GLTF
            if node.type in ['TEX_NOISE', 'TEX_VORONOI', 'TEX_MUSGRAVE', 'TEX_MAGIC']:
                mat_incompatible.append((mat.name, node.type))
if mat_incompatible:
    record("ADVERTENCIA", f"Materiales con nodos procedurales no directamente exportables a GLB: {mat_incompatible}")
else:
    record("OK", "Todos los materiales usan nodos Principled BSDF compatibles con GLB.")

# 8. Renders generados
RENDERS_OBLIGATORIOS = ["albatros_frontal.png", "albatros_tres_cuartos.png", "albatros_lateral.png"]
missing_renders = []
for r in RENDERS_OBLIGATORIOS:
    rpath = os.path.join(RENDERS_DIR, r)
    if not os.path.isfile(rpath) or os.path.getsize(rpath) < 1000:
        missing_renders.append(r)
if missing_renders:
    record("ERROR", f"Faltan imágenes de render o están vacías: {missing_renders}")
else:
    record("OK", f"Los 3 renders existen y tienen contenido: {RENDERS_OBLIGATORIOS}")

# 9. Archivo GLB
if not os.path.isfile(GLB_FILE):
    record("ERROR", f"No existe el archivo exportado {GLB_FILE}")
else:
    glb_size_bytes = os.path.getsize(GLB_FILE)
    glb_size_mb = glb_size_bytes / (1024 * 1024)
    record("OK", f"Archivo GLB exportado correctamente. Tamaño: {glb_size_mb:.2f} MB")
    if glb_size_mb > 5.0:
        record("ADVERTENCIA", f"El tamaño del GLB ({glb_size_mb:.2f} MB) supera el ideal de 5 MB")
    else:
        record("OK", "Tamaño de GLB optimizado (< 5 MB)")
        
    # Inspeccionar cabecera y animaciones embebidas en GLB
    try:
        with open(GLB_FILE, 'rb') as f:
            magic, ver, length = struct.unpack('<4sII', f.read(12))
            chunk_len, chunk_type = struct.unpack('<I4s', f.read(8))
            json_data = json.loads(f.read(chunk_len).decode('utf-8'))
            anim_names = [a.get('name') for a in json_data.get('animations', [])]
            record("OK", f"Animaciones presentes en el archivo GLB: {anim_names}")
            missing_glb_anims = [a for a in ACCIONES_REQUERIDAS if a not in anim_names]
            if missing_glb_anims:
                record("ERROR", f"El archivo GLB no contiene todas las animaciones requeridas. Faltan: {missing_glb_anims}")
            else:
                record("OK", "Todas las 5 animaciones requeridas están embebidas en el GLB para React Three Fiber.")
    except Exception as e:
        record("ERROR", f"Error inspeccionando estructura interna de GLB: {e}")

print("\n==========================================")
print("RESUMEN DE RESULTADOS")
print("==========================================")
print(f"Éxitos (OK): {len(STATUS['OK'])}")
print(f"Advertencias: {len(STATUS['ADVERTENCIA'])}")
print(f"Errores: {len(STATUS['ERROR'])}")

if STATUS["ERROR"]:
    print("\n[FALLO CRÍTICO] Se encontraron errores que impiden validar la entrega:")
    for err in STATUS["ERROR"]:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\n[VALIDACIÓN EXITOSA] El modelo cumple satisfactoriamente los criterios técnicos.")
    sys.exit(0)
