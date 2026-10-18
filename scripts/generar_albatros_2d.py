"""
generar_albatros_2d.py
Reconstruye la marioneta 2D de Albatros PROTEO integrando el nuevo diseño conceptual 2D (Opción 1),
configurando capas, rig 2D con 23 huesos y cámara ortográfica fija.
Uso: blender --background --python scripts/generar_albatros_2d.py
"""

import bpy
import math
import os
from mathutils import Vector

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RENDERS_DIR = os.path.join(BASE_DIR, "renders_2d")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports_2d")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
REFERENCES_DIR = os.path.join(BASE_DIR, "references")
BLEND_FILE = os.path.join(BASE_DIR, "albatros_proteo_2d.blend")
EXPORT_BLEND = os.path.join(EXPORTS_DIR, "albatros_proteo_2d.blend")
BASE_RENDER_PNG = os.path.join(RENDERS_DIR, "albatros_2d_base.png")

for d in [RENDERS_DIR, EXPORTS_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Limpiar escena
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = 'METERS'
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'

# Colección principal organizada
col_albatros = bpy.data.collections.new("ALBATROS_2D_COLLECTION")
bpy.context.scene.collection.children.link(col_albatros)

# Crear material con textura base del personaje
mat_character = bpy.data.materials.new(name="MAT_Albatros_Texture")
mat_character.use_nodes = True
nodes = mat_character.node_tree.nodes
links = mat_character.node_tree.links
nodes.clear()

out_node = nodes.new(type='ShaderNodeOutputMaterial')
bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
tex_node = nodes.new(type='ShaderNodeTexImage')

# Cargar imagen base
char_img = bpy.data.images.load(BASE_RENDER_PNG)
tex_node.image = char_img

links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
links.new(tex_node.outputs['Alpha'], bsdf_node.inputs['Alpha'])
links.new(bsdf_node.outputs['BSDF'], out_node.inputs['Surface'])

# Crear plano principal de la marioneta 2D
bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, 0.95), rotation=(math.radians(90), 0, 0))
main_plane = bpy.context.active_object
main_plane.name = "ALBATROS_ROOT_PLANE"
main_plane.data.materials.append(mat_character)
col_albatros.objects.link(main_plane)
bpy.context.scene.collection.objects.unlink(main_plane)

# Crear nodos/piezas requeridas para la jerarquía del personaje 2D
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

for pieza in PIEZAS_REQUERIDAS:
    if pieza not in bpy.data.objects:
        obj_empty = bpy.data.objects.new(pieza, None)
        obj_empty.empty_display_type = 'PLAIN_AXES'
        obj_empty.empty_display_size = 0.05
        col_albatros.objects.link(obj_empty)

# ==========================================
# 2. RIGGING 2D: ARMATURE
# ==========================================
print("-> Configurando RIG_AlbatrosProteo_2D...")

arm_data = bpy.data.armatures.new("RIG_AlbatrosProteo_2D_Data")
arm_obj = bpy.data.objects.new("RIG_AlbatrosProteo_2D", arm_data)
col_albatros.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
arm_data.show_names = True

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

b_root = eb.new("root")
b_root.head = (0, 0, 0)
b_root.tail = (0, 0, 0.20)

b_body = eb.new("body")
b_body.head = (0, 0, 0.40)
b_body.tail = (0, 0, 0.75)
b_body.parent = b_root

b_chest = eb.new("chest")
b_chest.head = (0, 0, 0.75)
b_chest.tail = (0, 0, 1.16)
b_chest.parent = b_body

b_neck = eb.new("neck")
b_neck.head = (0, 0, 1.16)
b_neck.tail = (0, 0, 1.46)
b_neck.parent = b_chest

b_head = eb.new("head")
b_head.head = (0, 0, 1.46)
b_head.tail = (0, 0, 1.82)
b_head.parent = b_neck

b_beak_u = eb.new("beak_upper")
b_beak_u.head = (0, 0, 1.54)
b_beak_u.tail = (0, 0, 1.34)
b_beak_u.parent = b_head

b_beak_l = eb.new("beak_lower")
b_beak_l.head = (0, 0, 1.48)
b_beak_l.tail = (0, 0, 1.38)
b_beak_l.parent = b_head

b_eye_l = eb.new("eye.L")
b_eye_l.head = (0.13, 0, 1.64)
b_eye_l.tail = (0.13, 0, 1.70)
b_eye_l.parent = b_head

b_eye_r = eb.new("eye.R")
b_eye_r.head = (-0.13, 0, 1.64)
b_eye_r.tail = (-0.13, 0, 1.70)
b_eye_r.parent = b_head

b_brow_l = eb.new("eyebrow.L")
b_brow_l.head = (0.13, 0, 1.72)
b_brow_l.tail = (0.18, 0, 1.75)
b_brow_l.parent = b_head

b_brow_r = eb.new("eyebrow.R")
b_brow_r.head = (-0.13, 0, 1.72)
b_brow_r.tail = (-0.18, 0, 1.75)
b_brow_r.parent = b_head

def create_wing_bones_2d(side, sign):
    wu = eb.new(f"wing_upper.{side}")
    wu.head = (sign * 0.24, 0, 1.16)
    wu.tail = (sign * 0.38, 0, 0.88)
    wu.parent = b_chest
    
    wl = eb.new(f"wing_lower.{side}")
    wl.head = (sign * 0.38, 0, 0.88)
    wl.tail = (sign * 0.40, 0, 0.60)
    wl.parent = wu
    
    wt = eb.new(f"wing_tip.{side}")
    wt.head = (sign * 0.40, 0, 0.60)
    wt.tail = (sign * 0.34, 0, 0.34)
    wt.parent = wl

create_wing_bones_2d("L", 1)
create_wing_bones_2d("R", -1)

def create_leg_bones_2d(side, sign):
    leg = eb.new(f"leg.{side}")
    leg.head = (sign * 0.14, 0, 0.50)
    leg.tail = (sign * 0.14, 0, 0.06)
    leg.parent = b_body
    
    foot = eb.new(f"foot.{side}")
    foot.head = (sign * 0.14, 0, 0.06)
    foot.tail = (sign * 0.14, 0, 0.00)
    foot.parent = leg

create_leg_bones_2d("L", 1)
create_leg_bones_2d("R", -1)

b_tail = eb.new("tail")
b_tail.head = (0, 0, 0.56)
b_tail.tail = (0, 0, 0.34)
b_tail.parent = b_body

b_necktie = eb.new("neckerchief")
b_necktie.head = (0, 0, 1.06)
b_necktie.tail = (0, 0, 0.87)
b_necktie.parent = b_chest

bpy.ops.object.mode_set(mode='OBJECT')

# ==========================================
# 3. CÁMARA ORTOGRÁFICA E ILUMINACIÓN
# ==========================================
print("-> Configurando Cámara Ortográfica...")

cam_data = bpy.data.cameras.new("CAM_2D_Ortho")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 2.0
cam_data.clip_start = 0.1
cam_data.clip_end = 50.0

cam_obj = bpy.data.objects.new("CAM_2D_Ortho", cam_data)
cam_obj.location = (0.0, -5.0, 0.95)
cam_obj.rotation_euler = (math.radians(90), 0, 0)
col_albatros.objects.link(cam_obj)
scene.camera = cam_obj

# Guardar archivo .blend principal y copia de exportación
bpy.ops.wm.save_as_mainfile(filepath=BLEND_FILE)
print(f"-> Guardado .blend en: {BLEND_FILE}")

bpy.ops.wm.save_as_mainfile(filepath=EXPORT_BLEND)
print(f"-> Guardado export en: {EXPORT_BLEND}")

print("=== Generación 2D completada exitosamente ===")
