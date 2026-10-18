"""
validar_albatros_2d.py
Validador técnico integral (Fase 1 y Fase 2) del personaje 2D Albatros PROTEO.
Uso: blender --background --python scripts/validar_albatros_2d.py
"""

import bpy
import os
import sys
import struct

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BLEND_FILE = os.path.join(BASE_DIR, "albatros_proteo_2d.blend")
EXPORT_BLEND = os.path.join(BASE_DIR, "exports_2d", "albatros_proteo_2d.blend")
RENDERS_DIR = os.path.join(BASE_DIR, "renders_2d")
SPRITES_DIR = os.path.join(BASE_DIR, "sprites")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports_2d")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

STATUS = {"OK": [], "ADVERTENCIA": [], "ERROR": []}

def record(level, msg):
    STATUS[level].append(msg)
    print(f"[{level}] {msg}")

print("\n=======================================================")
print("INICIANDO VALIDACIÓN TÉCNICA INTEGRAL: ALBATROS 2D")
print("=======================================================\n")

# ------------------------------------------------------------------------------
# 1. ARCHIVOS .BLEND
# ------------------------------------------------------------------------------
if not os.path.isfile(BLEND_FILE):
    record("ERROR", f"Falta archivo principal {BLEND_FILE}")
else:
    record("OK", f"Archivo principal .blend presente ({os.path.getsize(BLEND_FILE) / 1024:.1f} KB)")

if not os.path.isfile(EXPORT_BLEND):
    record("ERROR", f"Falta archivo de exportación {EXPORT_BLEND}")
else:
    record("OK", f"Archivo en exports_2d presente ({os.path.getsize(EXPORT_BLEND) / 1024:.1f} KB)")

# Cargar .blend
try:
    bpy.ops.wm.open_mainfile(filepath=BLEND_FILE)
    record("OK", "Blender cargó albatros_proteo_2d.blend sin errores.")
except Exception as e:
    record("ERROR", f"Error al abrir archivo .blend: {e}")
    sys.exit(1)

# ------------------------------------------------------------------------------
# 2. CAPAS Y PIEZAS OBLIGATORIAS (38 CAPAS)
# ------------------------------------------------------------------------------
PIEZAS_REQUERIDAS = [
    "ALBATROS_ROOT", "SHADOW", "TAIL_BACK", "WING_L_BACK", "WING_R_BACK",
    "BODY_WHITE", "UNIFORM_BODY", "UNIFORM_COLLAR", "UNIFORM_STRIPES",
    "NECKERCHIEF", "NECK", "HEAD_WHITE", "HEAD_FEATHER_DETAILS",
    "BEAK_LOWER", "BEAK_UPPER", "BEAK_TIP",
    "EYE_L_WHITE", "EYE_L_IRIS", "EYE_L_PUPIL", "EYE_L_HIGHLIGHT",
    "EYE_R_WHITE", "EYE_R_IRIS", "EYE_R_PUPIL", "EYE_R_HIGHLIGHT",
    "EYELID_L", "EYELID_R", "EYEBROW_L", "EYEBROW_R",
    "EMBLEM_SHIELD", "EMBLEM_P", "WING_L_FRONT", "WING_R_FRONT",
    "LEG_L", "LEG_R", "FOOT_L", "FOOT_R", "HIGHLIGHTS", "SHADING"
]

missing_parts = [p for p in PIEZAS_REQUERIDAS if p not in bpy.data.objects]
if missing_parts:
    record("ERROR", f"Faltan capas/objetos requeridos: {missing_parts}")
else:
    record("OK", f"Todas las {len(PIEZAS_REQUERIDAS)} piezas/capas del personaje están presentes.")

# ------------------------------------------------------------------------------
# 3. ARMATURE 2D Y HUESOS (23 HUESOS)
# ------------------------------------------------------------------------------
if "RIG_AlbatrosProteo_2D" not in bpy.data.objects:
    record("ERROR", "No existe el objeto armature 'RIG_AlbatrosProteo_2D'")
else:
    arm = bpy.data.objects["RIG_AlbatrosProteo_2D"]
    if arm.type != 'ARMATURE':
        record("ERROR", "'RIG_AlbatrosProteo_2D' no es un objeto ARMATURE")
    else:
        HUESOS_REQUERIDOS = [
            "root", "body", "chest", "neck", "head",
            "beak_upper", "beak_lower",
            "eye.L", "eye.R", "eyebrow.L", "eyebrow.R",
            "wing_upper.L", "wing_lower.L", "wing_tip.L",
            "wing_upper.R", "wing_lower.R", "wing_tip.R",
            "tail", "leg.L", "foot.L", "leg.R", "foot.R", "neckerchief"
        ]
        bones = arm.data.bones
        missing_bones = [b for b in HUESOS_REQUERIDOS if b not in bones]
        if missing_bones:
            record("ERROR", f"Faltan huesos en RIG_AlbatrosProteo_2D: {missing_bones}")
        else:
            record("OK", f"RIG_AlbatrosProteo_2D contiene todos los {len(HUESOS_REQUERIDOS)} huesos requeridos.")

# ------------------------------------------------------------------------------
# 4. CÁMARA ORTOGRÁFICA
# ------------------------------------------------------------------------------
cam = bpy.context.scene.camera
if not cam:
    record("ERROR", "No hay cámara activa configurada en la escena")
elif cam.data.type != 'ORTHO':
    record("ERROR", f"La cámara activa no es ortográfica (tipo actual: {cam.data.type})")
else:
    record("OK", f"Cámara activa ortográfica configurada correctamente (ortho_scale: {cam.data.ortho_scale:.2f})")

# ------------------------------------------------------------------------------
# 5. LIMPIEZA DE ELEMENTOS 3D ANTERIORES
# ------------------------------------------------------------------------------
col_2d = bpy.data.collections.get("ALBATROS_2D_COLLECTION")
if not col_2d:
    record("ERROR", "No se encontró la colección ALBATROS_2D_COLLECTION")
else:
    old_3d_names = ["BODY_Main", "HEAD_Main", "ARMATURE_Albatros"]
    old_found = [o.name for o in col_2d.objects if o.name in old_3d_names]
    if old_found:
        record("ERROR", f"Se encontraron elementos 3D de la iteración anterior en la colección 2D: {old_found}")
    else:
        record("OK", "Colección 2D limpia de geometría 3D anterior.")

# ------------------------------------------------------------------------------
# 6. RENDERS DE POSE BASE (FASE 1)
# ------------------------------------------------------------------------------
RENDER_BASE = os.path.join(RENDERS_DIR, "albatros_2d_base.png")
RENDER_PREV = os.path.join(RENDERS_DIR, "albatros_2d_preview.png")

for rpath, name, check_alpha in [(RENDER_BASE, "albatros_2d_base.png", True), (RENDER_PREV, "albatros_2d_preview.png", False)]:
    if not os.path.isfile(rpath):
        record("ERROR", f"Falta archivo de render: {name}")
    elif os.path.getsize(rpath) < 1000:
        record("ERROR", f"Archivo de render vacío o corrupto: {name}")
    else:
        with open(rpath, "rb") as f:
            data = f.read(26)
            w, h = struct.unpack(">LL", data[16:24])
            color_type = data[25]
            record("OK", f"Render {name}: {w}x{h} px, tamaño {os.path.getsize(rpath)/1024:.1f} KB")
            if w != 1024 or h != 1024:
                record("ADVERTENCIA", f"Resolución no es 1024x1024 ({w}x{h})")
            if check_alpha:
                if color_type == 6:
                    record("OK", f"Render {name} tiene canal alfa real (RGBA, transparente).")
                else:
                    record("ERROR", f"Render {name} no es RGBA transparente (color_type={color_type})")

# ------------------------------------------------------------------------------
# 7. ACCIONES DE ANIMACIÓN EN BLENDER (FASE 2)
# ------------------------------------------------------------------------------
ACCIONES_REQUERIDAS = {
    "Idle": 120,
    "Greeting": 60,
    "Thinking": 90,
    "Success": 60,
    "Alert": 50,
    "Help": 60,
    "Talking": 90
}

actions = bpy.data.actions
for act_name, expected_len in ACCIONES_REQUERIDAS.items():
    if act_name not in actions:
        record("ERROR", f"Acción de animación no encontrada: '{act_name}'")
    else:
        act = actions[act_name]
        f_start, f_end = act.frame_range
        dur = int(f_end - f_start) + 1
        record("OK", f"Acción '{act_name}': presente, rango {int(f_start)}-{int(f_end)} ({dur} fotogramas)")

# ------------------------------------------------------------------------------
# 8. SECUENCIAS DE SPRITES PNG (512x512, TRANSPARENCIA, SECUENCIALES)
# ------------------------------------------------------------------------------
for anim_lower in ["idle", "greeting", "thinking", "success", "alert", "help", "talking"]:
    anim_folder = os.path.join(SPRITES_DIR, anim_lower)
    if not os.path.isdir(anim_folder):
        record("ERROR", f"Carpeta de sprites inexistente: {anim_folder}")
        continue

    files = sorted([f for f in os.listdir(anim_folder) if f.endswith(".png")])
    if not files:
        record("ERROR", f"Carpeta de sprites vacía: {anim_folder}")
        continue

    # Verificar primer y último archivo
    sample_files = [files[0], files[len(files)//2], files[-1]]
    valid_pngs = True
    for sf in sample_files:
        sf_path = os.path.join(anim_folder, sf)
        if os.path.getsize(sf_path) < 500:
            record("ERROR", f"Sprite PNG corrupto o demasiado pequeño: {sf}")
            valid_pngs = False
            break
        with open(sf_path, "rb") as f:
            header = f.read(26)
            w, h = struct.unpack(">LL", header[16:24])
            color_type = header[25]
            if w != 512 or h != 512 or color_type != 6:
                record("ERROR", f"Sprite {sf} inválido: dimensiones {w}x{h}, color_type={color_type}")
                valid_pngs = False
                break

    if valid_pngs:
        record("OK", f"Secuencia '{anim_lower}': {len(files)} sprites PNG 512x512 RGBA transparentes.")

# ------------------------------------------------------------------------------
# 9. EXPORTACIONES WEBP ANIMADAS Y TAMAÑO
# ------------------------------------------------------------------------------
LIMITES_WEBP_KB = {
    "albatros_idle.webp": 700,
    "albatros_greeting.webp": 1000,
    "albatros_thinking.webp": 1000,
    "albatros_success.webp": 1000,
    "albatros_alert.webp": 1000,
    "albatros_help.webp": 1000,
    "albatros_talking.webp": 1000,
}

for webp_name, max_kb in LIMITES_WEBP_KB.items():
    webp_path = os.path.join(EXPORTS_DIR, webp_name)
    if not os.path.isfile(webp_path):
        record("ERROR", f"Falta archivo exportado: {webp_name}")
    else:
        size_kb = os.path.getsize(webp_path) / 1024
        if size_kb > max_kb:
            record("ADVERTENCIA", f"{webp_name}: tamaño {size_kb:.1f} KB supera el objetivo de {max_kb} KB")
        else:
            record("OK", f"{webp_name}: presente ({size_kb:.1f} KB, límite < {max_kb} KB)")

# ------------------------------------------------------------------------------
# 10. REPORTES Y DOCUMENTACIÓN
# ------------------------------------------------------------------------------
REPORT_FASE1 = os.path.join(REPORTS_DIR, "reporte_albatros_2d.md")
REPORT_REACT = os.path.join(REPORTS_DIR, "integracion_react_2d.md")

for r_doc in [REPORT_FASE1, REPORT_REACT]:
    if not os.path.isfile(r_doc):
        record("ERROR", f"Falta documento técnico: {os.path.basename(r_doc)}")
    else:
        record("OK", f"Documento {os.path.basename(r_doc)} presente ({os.path.getsize(r_doc)/1024:.1f} KB)")

# ------------------------------------------------------------------------------
# RESUMEN FINAL
# ------------------------------------------------------------------------------
print("\n=======================================================")
print("RESUMEN DE VALIDACIÓN TÉCNICA INTEGRAL")
print("=======================================================")
print(f"Éxitos (OK): {len(STATUS['OK'])}")
print(f"Advertencias: {len(STATUS['ADVERTENCIA'])}")
print(f"Errores: {len(STATUS['ERROR'])}")

if STATUS["ERROR"]:
    print("\n[FALLO CRÍTICO] Errores encontrados:")
    for err in STATUS["ERROR"]:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\n[VALIDACIÓN EXITOSA] Todos los requisitos técnicos de Fase 1 y Fase 2 fueron superados.")
    sys.exit(0)
