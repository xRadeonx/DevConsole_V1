"""
generar_albatros_proteo.py
Genera modelo 3D funcional, animable y estilizado de la mascota 'Albatros PROTEO'.
Ejecución: blender --background --python scripts/generar_albatros_proteo.py
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Euler, Matrix

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RENDERS_DIR = os.path.join(BASE_DIR, "renders")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
BLEND_FILE = os.path.join(BASE_DIR, "albatros_proteo.blend")
GLB_FILE = os.path.join(EXPORTS_DIR, "albatros_proteo.glb")

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
scene.render.film_transparent = False

def create_material(name, hex_color, roughness=0.45, metallic=0.0, specular=0.5):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    node_out = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    hex_clean = hex_color.lstrip('#')
    r_srgb = int(hex_clean[0:2], 16) / 255.0
    g_srgb = int(hex_clean[2:4], 16) / 255.0
    b_srgb = int(hex_clean[4:6], 16) / 255.0
    
    def srgb_to_linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    
    color_linear = (srgb_to_linear(r_srgb), srgb_to_linear(g_srgb), srgb_to_linear(b_srgb), 1.0)
    
    if 'Base Color' in node_bsdf.inputs:
        node_bsdf.inputs['Base Color'].default_value = color_linear
    if 'Roughness' in node_bsdf.inputs:
        node_bsdf.inputs['Roughness'].default_value = roughness
    if 'Metallic' in node_bsdf.inputs:
        node_bsdf.inputs['Metallic'].default_value = metallic
    if 'Specular IOR Level' in node_bsdf.inputs:
        node_bsdf.inputs['Specular IOR Level'].default_value = specular
    elif 'Specular' in node_bsdf.inputs:
        node_bsdf.inputs['Specular'].default_value = specular
        
    links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])
    return mat

# Paleta base
MAT_WHITE_FEATHER = create_material("MAT_WhiteFeather", "#F8FAFC", roughness=0.5)
MAT_NAVY_BLUE    = create_material("MAT_NavyBlue", "#062B50", roughness=0.35)
MAT_SLATE_BLUE   = create_material("MAT_SlateBlue", "#345474", roughness=0.45)
MAT_LIGHT_BLUE   = create_material("MAT_LightBlue", "#73A9D1", roughness=0.35)
MAT_LIGHT_GRAY   = create_material("MAT_LightGray", "#CBD5E1", roughness=0.5)
MAT_GRAPHITE     = create_material("MAT_Graphite", "#33383F", roughness=0.5)
MAT_BEAK_ORANGE  = create_material("MAT_BeakOrange", "#D98A45", roughness=0.35)
MAT_BEAK_TIP     = create_material("MAT_BeakTip", "#55575A", roughness=0.4)
MAT_BLACK_NECK   = create_material("MAT_BlackNeckerchief", "#171A1F", roughness=0.5)
MAT_EYE_PUPIL    = create_material("MAT_EyePupil", "#0A0C10", roughness=0.1, specular=1.0)
MAT_EYE_IRIS     = create_material("MAT_EyeIris", "#3D2714", roughness=0.2, specular=0.9)
MAT_EYE_WHITE    = create_material("MAT_EyeWhite", "#FFFFFF", roughness=0.2, specular=0.9)
MAT_LEG_ORANGE   = create_material("MAT_LegOrange", "#CF7E35", roughness=0.45)

def assign_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def smooth_mesh(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True

def new_mesh_obj(name):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj

# ==========================================
# 1. MODELADO ANATÓMICO ESTILIZADO
# ==========================================

print("-> Modelando Cabeza y Cuello (HEAD_Main)...")
head_obj = new_mesh_obj("HEAD_Main")
bm = bmesh.new()

# Proporciones orgánicas de cabeza y cuello según la referencia
head_profile = [
    # z, rx, ry, cy
    (1.18, 0.17, 0.19,  0.03),
    (1.28, 0.16, 0.18,  0.02),
    (1.38, 0.17, 0.19,  0.00),
    (1.48, 0.20, 0.21, -0.01),
    (1.58, 0.23, 0.23, -0.01),
    (1.66, 0.22, 0.22,  0.01),
    (1.73, 0.18, 0.18,  0.03),
    (1.78, 0.11, 0.11,  0.05),
]

segments = 24
prev_ring = []
for z, rx, ry, cy in head_profile:
    ring = []
    for s in range(segments):
        theta = 2.0 * math.pi * s / segments
        vx = math.cos(theta) * rx
        vy = cy + math.sin(theta) * ry
        vz = z
        ring.append(bm.verts.new((vx, vy, vz)))
    if prev_ring:
        for s in range(segments):
            s_n = (s + 1) % segments
            bm.faces.new([prev_ring[s], prev_ring[s_n], ring[s_n], ring[s]])
    prev_ring = ring

tip_vh = bm.verts.new((0, 0.05, 1.80))
for s in range(segments):
    s_n = (s + 1) % segments
    bm.faces.new([prev_ring[s], prev_ring[s_n], tip_vh])

bm.to_mesh(head_obj.data)
bm.free()
smooth_mesh(head_obj)
assign_mat(head_obj, MAT_WHITE_FEATHER)

# Mechón plumaje posterior de la nuca
bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.08, depth=0.18, location=(0, 0.22, 1.62), rotation=(math.radians(-42), 0, 0))
crest = bpy.context.active_object
crest.scale = (1.2, 0.8, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
smooth_mesh(crest)
assign_mat(crest, MAT_WHITE_FEATHER)
bpy.ops.object.select_all(action='DESELECT')
crest.select_set(True)
head_obj.select_set(True)
bpy.context.view_layer.objects.active = head_obj
bpy.ops.object.join()
head_obj.name = "HEAD_Main"

print("-> Modelando Torso (BODY_Main)...")
body_obj = new_mesh_obj("BODY_Main")
bm = bmesh.new()
body_profile = [
    # z, rx, ry, cy
    (0.48, 0.12, 0.14,  0.04),
    (0.55, 0.26, 0.28,  0.03),
    (0.68, 0.35, 0.35,  0.01),
    (0.82, 0.38, 0.36, -0.01),
    (0.98, 0.36, 0.34, -0.01),
    (1.12, 0.31, 0.30,  0.00),
    (1.22, 0.22, 0.22,  0.01),
]
prev_b_ring = []
for z, rx, ry, cy in body_profile:
    ring = []
    for s in range(segments):
        theta = 2.0 * math.pi * s / segments
        vx = math.cos(theta) * rx
        vy = cy + math.sin(theta) * ry
        vz = z
        ring.append(bm.verts.new((vx, vy, vz)))
    if prev_b_ring:
        for s in range(segments):
            s_n = (s + 1) % segments
            bm.faces.new([prev_b_ring[s], prev_b_ring[s_n], ring[s_n], ring[s]])
    prev_b_ring = ring

bot_vb = bm.verts.new((0, 0.04, 0.46))
for s in range(segments):
    s_n = (s + 1) % segments
    bm.faces.new([bot_vb, prev_b_ring[s_n], prev_b_ring[s]])

bm.to_mesh(body_obj.data)
bm.free()
smooth_mesh(body_obj)
assign_mat(body_obj, MAT_WHITE_FEATHER)

print("-> Modelando Pico (BEAK_Upper y BEAK_Lower)...")
beak_u = new_mesh_obj("BEAK_Upper")
bm = bmesh.new()
beak_u_profile = [
    (0.00, 0.12, 0.10,  0.00),
    (0.10, 0.10, 0.09, -0.01),
    (0.20, 0.08, 0.08, -0.02),
    (0.30, 0.07, 0.07, -0.04),
    (0.38, 0.06, 0.065,-0.08),
    (0.44, 0.04, 0.05, -0.14),
]
prev_bk = []
for dy, rx, rz, dz in beak_u_profile:
    y = -0.14 - dy
    cz = 1.54 + dz
    ring = []
    for s in range(segments):
        theta = 2.0 * math.pi * s / segments
        vx = math.cos(theta) * rx
        vz = math.sin(theta) * rz
        ring.append(bm.verts.new((vx, y, cz + vz)))
    if prev_bk:
        for s in range(segments):
            s_n = (s + 1) % segments
            bm.faces.new([prev_bk[s], prev_bk[s_n], ring[s_n], ring[s]])
    prev_bk = ring

tip_bk = bm.verts.new((0, -0.14 - 0.46, 1.54 - 0.18))
for s in range(segments):
    s_n = (s + 1) % segments
    bm.faces.new([prev_bk[s], prev_bk[s_n], tip_bk])

bm.to_mesh(beak_u.data)
bm.free()
smooth_mesh(beak_u)
assign_mat(beak_u, MAT_BEAK_ORANGE)

bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=14, radius=0.058, location=(0, -0.54, 1.40))
beak_tip = bpy.context.active_object
beak_tip.name = "BEAK_Tip"
beak_tip.scale = (0.75, 1.25, 0.95)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(beak_tip)
assign_mat(beak_tip, MAT_BEAK_TIP)

bpy.ops.object.select_all(action='DESELECT')
beak_tip.select_set(True)
beak_u.select_set(True)
bpy.context.view_layer.objects.active = beak_u
bpy.ops.object.join()
beak_u.name = "BEAK_Upper"

beak_l = new_mesh_obj("BEAK_Lower")
bm = bmesh.new()
beak_l_profile = [
    (0.00, 0.10, 0.06,  0.00),
    (0.12, 0.08, 0.05, -0.01),
    (0.24, 0.065,0.045,-0.02),
    (0.35, 0.045,0.035,-0.04),
]
prev_bkl = []
for dy, rx, rz, dz in beak_l_profile:
    y = -0.14 - dy
    cz = 1.47 + dz
    ring = []
    for s in range(segments):
        theta = 2.0 * math.pi * s / segments
        vx = math.cos(theta) * rx
        vz = math.sin(theta) * rz
        ring.append(bm.verts.new((vx, y, cz + vz)))
    if prev_bkl:
        for s in range(segments):
            s_n = (s + 1) % segments
            bm.faces.new([prev_bkl[s], prev_bkl[s_n], ring[s_n], ring[s]])
    prev_bkl = ring

tip_bkl = bm.verts.new((0, -0.14 - 0.38, 1.47 - 0.06))
for s in range(segments):
    s_n = (s + 1) % segments
    bm.faces.new([prev_bkl[s], prev_bkl[s_n], tip_bkl])

bm.to_mesh(beak_l.data)
bm.free()
smooth_mesh(beak_l)
assign_mat(beak_l, MAT_BEAK_ORANGE)

print("-> Modelando Ojos y Párpados expresivos (EYE_L, EYE_R, EYELID_L, EYELID_R)...")
def create_eye_system(side, sign):
    # Ojo situado en la cara frontal-lateral del albatros
    eye_x = sign * 0.14
    eye_y = -0.22
    eye_z = 1.62
    
    # Globo ocular blanco
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.068, location=(eye_x, eye_y, eye_z))
    eye = bpy.context.active_object
    eye.name = f"EYE_{side}"
    smooth_mesh(eye)
    assign_mat(eye, MAT_EYE_WHITE)
    
    # Iris marrón suave frontal
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.042, location=(eye_x + sign * 0.008, eye_y - 0.052, eye_z))
    iris = bpy.context.active_object
    iris.scale = (1.0, 0.25, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(iris)
    assign_mat(iris, MAT_EYE_IRIS)
    
    # Pupila negra destacada
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.028, location=(eye_x + sign * 0.008, eye_y - 0.062, eye_z))
    pupil = bpy.context.active_object
    pupil.scale = (1.0, 0.2, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(pupil)
    assign_mat(pupil, MAT_EYE_PUPIL)
    
    # Brillo de ojo
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.013, location=(eye_x + sign * 0.018, eye_y - 0.072, eye_z + 0.015))
    glint = bpy.context.active_object
    smooth_mesh(glint)
    assign_mat(glint, MAT_EYE_WHITE)
    
    bpy.ops.object.select_all(action='DESELECT')
    glint.select_set(True)
    pupil.select_set(True)
    iris.select_set(True)
    eye.select_set(True)
    bpy.context.view_layer.objects.active = eye
    bpy.ops.object.join()
    eye.name = f"EYE_{side}"
    
    # Párpado superior estilizado
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.076, location=(eye_x, eye_y, eye_z))
    eyelid = bpy.context.active_object
    eyelid.name = f"EYELID_{side}"
    eyelid.rotation_euler = (math.radians(-14), 0, math.radians(sign * 12))
    
    bm_el = bmesh.new()
    bm_el.from_mesh(eyelid.data)
    del_v = [v for v in bm_el.verts if v.co.z < 0.012]
    bmesh.ops.delete(bm_el, geom=del_v, context='VERTS')
    bm_el.to_mesh(eyelid.data)
    bm_el.free()
    smooth_mesh(eyelid)
    assign_mat(eyelid, MAT_WHITE_FEATHER)
    
    # Ceja arqueada albatros
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.012, depth=0.09, location=(eye_x + sign * 0.01, eye_y - 0.03, eye_z + 0.072), rotation=(0, math.radians(sign * 75), math.radians(sign * -10)))
    brow = bpy.context.active_object
    brow.scale = (0.5, 1.0, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(brow)
    assign_mat(brow, MAT_GRAPHITE)
    
    bpy.ops.object.select_all(action='DESELECT')
    brow.select_set(True)
    eyelid.select_set(True)
    bpy.context.view_layer.objects.active = eyelid
    bpy.ops.object.join()
    eyelid.name = f"EYELID_{side}"

create_eye_system("L", 1)
create_eye_system("R", -1)

print("-> Modelando Alas Anatómicas (WING_L, WING_R)...")
def create_solid_wing(side, sign):
    wing_obj = new_mesh_obj(f"WING_{side}")
    bm = bmesh.new()
    
    wing_sections = [
        (sign * 0.32,  0.04, 1.15, 0.10, 0.18, math.radians(-sign * 12)),
        (sign * 0.38,  0.05, 0.98, 0.11, 0.22, math.radians(-sign * 10)),
        (sign * 0.40,  0.07, 0.80, 0.10, 0.24, math.radians(-sign * 8)),
        (sign * 0.39,  0.09, 0.62, 0.08, 0.22, math.radians(-sign * 6)),
        (sign * 0.36,  0.11, 0.45, 0.06, 0.18, math.radians(-sign * 4)),
        (sign * 0.33,  0.12, 0.30, 0.03, 0.10, 0),
    ]
    
    prev_w_ring = []
    seg_w = 16
    for wx, wy, wz, rx, ry, rot_y in wing_sections:
        ring = []
        cos_r = math.cos(rot_y)
        sin_r = math.sin(rot_y)
        for s in range(seg_w):
            th = 2.0 * math.pi * s / seg_w
            lx = math.cos(th) * rx
            ly = math.sin(th) * ry
            rx_rot = lx * cos_r
            rz_rot = lx * sin_r
            ring.append(bm.verts.new((wx + rx_rot, wy + ly, wz + rz_rot)))
        if prev_w_ring:
            for s in range(seg_w):
                s_n = (s + 1) % seg_w
                bm.faces.new([prev_w_ring[s], prev_w_ring[s_n], ring[s_n], ring[s]])
        prev_w_ring = ring
        
    tip_w = bm.verts.new((sign * 0.31, 0.13, 0.22))
    for s in range(seg_w):
        s_n = (s + 1) % seg_w
        bm.faces.new([prev_w_ring[s], prev_w_ring[s_n], tip_w])
        
    bm.to_mesh(wing_obj.data)
    bm.free()
    smooth_mesh(wing_obj)
    assign_mat(wing_obj, MAT_NAVY_BLUE)
    
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.09, depth=0.28, location=(sign * 0.34, 0.12, 0.32), rotation=(math.radians(175), math.radians(sign * 8), 0))
    w_tip_mesh = bpy.context.active_object
    w_tip_mesh.scale = (0.7, 1.3, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(w_tip_mesh)
    assign_mat(w_tip_mesh, MAT_GRAPHITE)
    
    bpy.ops.object.select_all(action='DESELECT')
    w_tip_mesh.select_set(True)
    wing_obj.select_set(True)
    bpy.context.view_layer.objects.active = wing_obj
    bpy.ops.object.join()
    wing_obj.name = f"WING_{side}"

create_solid_wing("L", 1)
create_solid_wing("R", -1)

print("-> Modelando Cola (TAIL_Main)...")
tail_obj = new_mesh_obj("TAIL_Main")
bm = bmesh.new()
n_feathers = 5
for i in range(n_feathers):
    ang = (i - 2) * 10
    rad = math.radians(ang)
    base_x = math.sin(rad) * 0.12
    base_y = 0.30 + math.cos(rad) * 0.08
    base_z = 0.62
    
    tip_x = math.sin(rad) * 0.18
    tip_y = base_y + 0.22
    tip_z = base_z - 0.22
    
    v1 = bm.verts.new((base_x - 0.035, base_y, base_z))
    v2 = bm.verts.new((base_x + 0.035, base_y, base_z))
    v3 = bm.verts.new((tip_x + 0.045, tip_y, tip_z))
    v4 = bm.verts.new((tip_x, tip_y + 0.04, tip_z - 0.03))
    v5 = bm.verts.new((tip_x - 0.045, tip_y, tip_z))
    bm.faces.new([v1, v2, v3, v4, v5])
bm.to_mesh(tail_obj.data)
bm.free()
smooth_mesh(tail_obj)
assign_mat(tail_obj, MAT_GRAPHITE)

mod_tsol = tail_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod_tsol.thickness = 0.022
bpy.context.view_layer.objects.active = tail_obj
bpy.ops.object.modifier_apply(modifier="Solidify")

print("-> Modelando Patas y Pies (LEG_L, LEG_R, FOOT_L, FOOT_R)...")
def create_legs(side, sign):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.032, depth=0.48, location=(sign * 0.15, 0.02, 0.26))
    leg = bpy.context.active_object
    leg.name = f"LEG_{side}"
    smooth_mesh(leg)
    assign_mat(leg, MAT_LEG_ORANGE)
    
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=0.042, location=(sign * 0.15, 0.015, 0.34))
    knee = bpy.context.active_object
    knee.scale = (0.9, 1.15, 0.9)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth_mesh(knee)
    assign_mat(knee, MAT_LEG_ORANGE)
    
    bpy.ops.object.select_all(action='DESELECT')
    knee.select_set(True)
    leg.select_set(True)
    bpy.context.view_layer.objects.active = leg
    bpy.ops.object.join()
    leg.name = f"LEG_{side}"
    
    foot = new_mesh_obj(f"FOOT_{side}")
    bm = bmesh.new()
    hx = sign * 0.15
    hy = 0.04
    hz = 0.03
    v_heel = bm.verts.new((hx, hy, hz))
    v_ankle = bm.verts.new((hx, hy - 0.02, hz + 0.04))
    
    angles = [-22, 0, 22] if sign > 0 else [22, 0, -22]
    lengths = [0.18, 0.22, 0.18]
    tips = []
    
    for i, a in enumerate(angles):
        rad = math.radians(a)
        l = lengths[i]
        tx = hx + math.sin(rad) * l
        ty = hy - math.cos(rad) * l
        tz = 0.005
        tip = bm.verts.new((tx, ty, tz))
        tips.append(tip)
        claw = bm.verts.new((tx, ty - 0.02, 0.002))
        bm.faces.new([tip, claw, bm.verts.new((tx + sign * 0.01, ty - 0.008, 0.008))])
        
    bm.faces.new([v_heel, tips[0], tips[1]])
    bm.faces.new([v_heel, tips[1], tips[2]])
    bm.faces.new([v_ankle, v_heel, tips[0]])
    bm.faces.new([v_ankle, tips[2], v_heel])
    
    bm.to_mesh(foot.data)
    bm.free()
    smooth_mesh(foot)
    assign_mat(foot, MAT_LEG_ORANGE)
    
    mod_f = foot.modifiers.new(name="Solidify", type='SOLIDIFY')
    mod_f.thickness = 0.028
    bpy.context.view_layer.objects.active = foot
    bpy.ops.object.modifier_apply(modifier="Solidify")

create_legs("L", 1)
create_legs("R", -1)

print("-> Modelando Uniforme Naval Adaptado (UNIFORM_Body, UNIFORM_Collar, UNIFORM_Neckerchief, EMBLEM_Proteo)...")
u_body = new_mesh_obj("UNIFORM_Body")
bm = bmesh.new()
u_profile = [
    (0.74, 0.37, 0.36, -0.01),
    (0.85, 0.38, 0.37, -0.01),
    (0.98, 0.37, 0.35, -0.01),
    (1.12, 0.32, 0.31,  0.00),
    (1.22, 0.24, 0.24,  0.01),
]
prev_u = []
for z, rx, ry, cy in u_profile:
    ring = []
    for s in range(segments):
        th = 2.0 * math.pi * s / segments
        vx = math.cos(th) * rx
        vy = cy + math.sin(th) * ry
        ring.append(bm.verts.new((vx, vy, z)))
    if prev_u:
        for s in range(segments):
            s_n = (s + 1) % segments
            bm.faces.new([prev_u[s], prev_u[s_n], ring[s_n], ring[s]])
    prev_u = ring
bm.to_mesh(u_body.data)
bm.free()
smooth_mesh(u_body)
assign_mat(u_body, MAT_NAVY_BLUE)

mod_ub_sol = u_body.modifiers.new(name="Solidify", type='SOLIDIFY')
mod_ub_sol.thickness = 0.015
bpy.context.view_layer.objects.active = u_body
bpy.ops.object.modifier_apply(modifier="Solidify")

# Cuello marinero solapado ceñido
u_collar = new_mesh_obj("UNIFORM_Collar")
bm = bmesh.new()

vb_tl = bm.verts.new(( 0.24, 0.22, 1.20))
vb_tr = bm.verts.new((-0.24, 0.22, 1.20))
vb_bl = bm.verts.new(( 0.24, 0.23, 0.98))
vb_br = bm.verts.new((-0.24, 0.23, 0.98))
bm.faces.new([vb_tl, vb_tr, vb_br, vb_bl])

vsh_l = bm.verts.new(( 0.27, 0.04, 1.21))
vsh_r = bm.verts.new((-0.27, 0.04, 1.21))
bm.faces.new([vsh_l, vb_tl, vb_bl, bm.verts.new(( 0.26, 0.12, 1.08))])
bm.faces.new([vb_tr, vsh_r, bm.verts.new((-0.26, 0.12, 1.08)), vb_br])

vf_l = bm.verts.new(( 0.14, -0.20, 1.18))
vf_r = bm.verts.new((-0.14, -0.20, 1.18))
vf_v = bm.verts.new(( 0.00, -0.28, 1.06))
bm.faces.new([vsh_l, vf_l, vf_v, bm.verts.new(( 0.14, -0.10, 1.11))])
bm.faces.new([vf_r, vsh_r, bm.verts.new((-0.14, -0.10, 1.11)), vf_v])

bm.to_mesh(u_collar.data)
bm.free()
smooth_mesh(u_collar)
assign_mat(u_collar, MAT_NAVY_BLUE)

mod_uc_sol = u_collar.modifiers.new(name="Solidify", type='SOLIDIFY')
mod_uc_sol.thickness = 0.012
bpy.context.view_layer.objects.active = u_collar
bpy.ops.object.modifier_apply(modifier="Solidify")

# Rayas blancas ceñidas
bpy.ops.mesh.primitive_torus_add(major_radius=0.22, minor_radius=0.004, major_segments=32, minor_segments=8, location=(0, 0.02, 1.20), rotation=(math.radians(12), 0, 0))
c_stripe1 = bpy.context.active_object
c_stripe1.scale = (1.0, 1.05, 0.65)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(c_stripe1)
assign_mat(c_stripe1, MAT_WHITE_FEATHER)

bpy.ops.mesh.primitive_torus_add(major_radius=0.205, minor_radius=0.0035, major_segments=32, minor_segments=8, location=(0, 0.02, 1.21), rotation=(math.radians(12), 0, 0))
c_stripe2 = bpy.context.active_object
c_stripe2.scale = (1.0, 1.05, 0.65)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(c_stripe2)
assign_mat(c_stripe2, MAT_WHITE_FEATHER)

bpy.ops.object.select_all(action='DESELECT')
c_stripe1.select_set(True)
c_stripe2.select_set(True)
u_collar.select_set(True)
bpy.context.view_layer.objects.active = u_collar
bpy.ops.object.join()
u_collar.name = "UNIFORM_Collar"

# Pañuelo marinero
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=0.045, location=(0, -0.31, 1.05))
knot = bpy.context.active_object
knot.name = "KNOT_Center"
knot.scale = (1.1, 0.75, 1.1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(knot)
assign_mat(knot, MAT_BLACK_NECK)

def create_scarf_tail(sign):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.028, depth=0.18, location=(sign * 0.038, -0.32, 0.95))
    st = bpy.context.active_object
    st.rotation_euler = (math.radians(-8), math.radians(sign * 12), math.radians(sign * 6))
    st.scale = (1.2, 0.45, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    smooth_mesh(st)
    assign_mat(st, MAT_BLACK_NECK)
    return st

st_l = create_scarf_tail(1)
st_r = create_scarf_tail(-1)

bpy.ops.mesh.primitive_torus_add(major_radius=0.11, minor_radius=0.015, major_segments=24, minor_segments=8, location=(0, -0.19, 1.12), rotation=(math.radians(45), 0, 0))
s_loop = bpy.context.active_object
s_loop.scale = (1.1, 1.15, 0.7)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(s_loop)
assign_mat(s_loop, MAT_BLACK_NECK)

bpy.ops.object.select_all(action='DESELECT')
knot.select_set(True)
st_l.select_set(True)
st_r.select_set(True)
s_loop.select_set(True)
bpy.context.view_layer.objects.active = knot
bpy.ops.object.join()
knot.name = "UNIFORM_Neckerchief"

# Escudo ficticio con 'P'
emblem = new_mesh_obj("EMBLEM_Proteo")
bm = bmesh.new()
v_e1 = bm.verts.new((0.14, -0.33, 1.06))
v_e2 = bm.verts.new((0.24, -0.31, 1.06))
v_e3 = bm.verts.new((0.24, -0.30, 0.96))
v_e4 = bm.verts.new((0.19, -0.32, 0.90))
v_e5 = bm.verts.new((0.14, -0.32, 0.96))
bm.faces.new([v_e1, v_e2, v_e3, v_e4, v_e5])
bm.to_mesh(emblem.data)
bm.free()
smooth_mesh(emblem)
assign_mat(emblem, MAT_LIGHT_BLUE)

mod_esol = emblem.modifiers.new(name="Solidify", type='SOLIDIFY')
mod_esol.thickness = 0.012
bpy.context.view_layer.objects.active = emblem
bpy.ops.object.modifier_apply(modifier="Solidify")

bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.022, depth=0.014, location=(0.19, -0.33, 0.99), rotation=(math.radians(90), 0, 0))
p_let = bpy.context.active_object
p_let.name = "EMBLEM_P"
p_let.scale = (0.7, 0.8, 1.1)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
smooth_mesh(p_let)
assign_mat(p_let, MAT_WHITE_FEATHER)

bpy.ops.object.select_all(action='DESELECT')
p_let.select_set(True)
emblem.select_set(True)
bpy.context.view_layer.objects.active = emblem
bpy.ops.object.join()
emblem.name = "EMBLEM_Proteo"

# ==========================================
# 2. RIGGING (ARMATURE_Albatros)
# ==========================================
print("-> Configurando Armature funcional...")

arm_data = bpy.data.armatures.new("ARMATURE_Albatros_Data")
arm_obj = bpy.data.objects.new("ARMATURE_Albatros", arm_data)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
arm_data.show_names = True

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

b_root = eb.new("root")
b_root.head = (0, 0, 0)
b_root.tail = (0, 0, 0.2)

b_hips = eb.new("hips")
b_hips.head = (0, 0, 0.52)
b_hips.tail = (0, 0, 0.74)
b_hips.parent = b_root

b_spine = eb.new("spine")
b_spine.head = (0, 0, 0.74)
b_spine.tail = (0, 0, 0.98)
b_spine.parent = b_hips

b_chest = eb.new("chest")
b_chest.head = (0, 0, 0.98)
b_chest.tail = (0, 0, 1.20)
b_chest.parent = b_spine

b_neck = eb.new("neck")
b_neck.head = (0, 0.02, 1.20)
b_neck.tail = (0, 0.00, 1.42)
b_neck.parent = b_chest

b_head = eb.new("head")
b_head.head = (0, 0.00, 1.42)
b_head.tail = (0, 0.02, 1.78)
b_head.parent = b_neck

b_beak_u = eb.new("beak_upper")
b_beak_u.head = (0, -0.14, 1.54)
b_beak_u.tail = (0, -0.55, 1.40)
b_beak_u.parent = b_head

b_beak_l = eb.new("beak_lower")
b_beak_l.head = (0, -0.14, 1.48)
b_beak_l.tail = (0, -0.48, 1.42)
b_beak_l.parent = b_head

b_eye_l = eb.new("eye.L")
b_eye_l.head = ( 0.14, -0.22, 1.62)
b_eye_l.tail = ( 0.14, -0.32, 1.62)
b_eye_l.parent = b_head

b_eye_r = eb.new("eye.R")
b_eye_r.head = (-0.14, -0.22, 1.62)
b_eye_r.tail = (-0.14, -0.32, 1.62)
b_eye_r.parent = b_head

def create_wing_bones(side, sign):
    wu = eb.new(f"wing_upper.{side}")
    wu.head = (sign * 0.32, 0.04, 1.15)
    wu.tail = (sign * 0.39, 0.07, 0.85)
    wu.parent = b_chest
    
    wl = eb.new(f"wing_lower.{side}")
    wl.head = (sign * 0.39, 0.07, 0.85)
    wl.tail = (sign * 0.38, 0.10, 0.55)
    wl.parent = wu
    
    wt = eb.new(f"wing_tip.{side}")
    wt.head = (sign * 0.38, 0.10, 0.55)
    wt.tail = (sign * 0.32, 0.12, 0.25)
    wt.parent = wl

create_wing_bones("L", 1)
create_wing_bones("R", -1)

def create_leg_bones(side, sign):
    thigh = eb.new(f"thigh.{side}")
    thigh.head = (sign * 0.15, 0.02, 0.52)
    thigh.tail = (sign * 0.15, 0.02, 0.34)
    thigh.parent = b_hips
    
    shin = eb.new(f"shin.{side}")
    shin.head = (sign * 0.15, 0.02, 0.34)
    shin.tail = (sign * 0.15, 0.03, 0.08)
    shin.parent = thigh
    
    foot = eb.new(f"foot.{side}")
    foot.head = (sign * 0.15, 0.03, 0.08)
    foot.tail = (sign * 0.15, -0.16, 0.00)
    foot.parent = shin

create_leg_bones("L", 1)
create_leg_bones("R", -1)

b_tail = eb.new("tail")
b_tail.head = (0, 0.24, 0.64)
b_tail.tail = (0, 0.45, 0.42)
b_tail.parent = b_hips

bpy.ops.object.mode_set(mode='OBJECT')

# ==========================================
# 3. SKINNING / WEIGHTING
# ==========================================
print("-> Asignando Pesos de Deformación...")

def skin_object_to_bones(obj, bone_weights, armature=arm_obj):
    mod = obj.modifiers.new(name="Armature", type='ARMATURE')
    mod.object = armature
    obj.parent = armature
    
    mesh = obj.data
    for bone_name, weight in bone_weights.items():
        vg = obj.vertex_groups.new(name=bone_name)
        v_indices = list(range(len(mesh.vertices)))
        vg.add(v_indices, weight, 'REPLACE')

skin_object_to_bones(bpy.data.objects["BODY_Main"], {"chest": 0.4, "spine": 0.35, "hips": 0.25})
skin_object_to_bones(bpy.data.objects["UNIFORM_Body"], {"chest": 0.65, "spine": 0.35})
skin_object_to_bones(bpy.data.objects["UNIFORM_Collar"], {"chest": 0.8, "neck": 0.2})
skin_object_to_bones(bpy.data.objects["UNIFORM_Neckerchief"], {"chest": 0.8, "neck": 0.2})
skin_object_to_bones(bpy.data.objects["EMBLEM_Proteo"], {"chest": 1.0})

skin_object_to_bones(bpy.data.objects["HEAD_Main"], {"head": 0.85, "neck": 0.15})
skin_object_to_bones(bpy.data.objects["BEAK_Upper"], {"beak_upper": 1.0})
skin_object_to_bones(bpy.data.objects["BEAK_Lower"], {"beak_lower": 1.0})

skin_object_to_bones(bpy.data.objects["EYE_L"], {"eye.L": 1.0})
skin_object_to_bones(bpy.data.objects["EYE_R"], {"eye.R": 1.0})
skin_object_to_bones(bpy.data.objects["EYELID_L"], {"head": 1.0})
skin_object_to_bones(bpy.data.objects["EYELID_R"], {"head": 1.0})

skin_object_to_bones(bpy.data.objects["WING_L"], {"wing_upper.L": 0.45, "wing_lower.L": 0.35, "wing_tip.L": 0.2})
skin_object_to_bones(bpy.data.objects["WING_R"], {"wing_upper.R": 0.45, "wing_lower.R": 0.35, "wing_tip.R": 0.2})

skin_object_to_bones(bpy.data.objects["LEG_L"], {"thigh.L": 0.5, "shin.L": 0.5})
skin_object_to_bones(bpy.data.objects["LEG_R"], {"thigh.R": 0.5, "shin.R": 0.5})
skin_object_to_bones(bpy.data.objects["FOOT_L"], {"foot.L": 1.0})
skin_object_to_bones(bpy.data.objects["FOOT_R"], {"foot.R": 1.0})

skin_object_to_bones(bpy.data.objects["TAIL_Main"], {"tail": 1.0})

# ==========================================
# 4. ANIMACIONES (5 ACCIONES)
# ==========================================
print("-> Creando las 5 Animaciones...")

fps = 30
scene.render.fps = fps
arm_obj.animation_data_create()

def reset_pose():
    for pb in arm_obj.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)

def insert_key(bone_name, prop, frame):
    pb = arm_obj.pose.bones[bone_name]
    pb.keyframe_insert(data_path=prop, frame=frame)

# 1. IDLE (120 frames)
reset_pose()
act_idle = bpy.data.actions.new(name="Idle")
act_idle.use_fake_user = True
arm_obj.animation_data.action = act_idle

for frame, z_off, spine_pitch in [(1, 0.0, 0.0), (30, 0.015, 0.025), (60, 0.0, 0.0), (90, 0.015, 0.025), (120, 0.0, 0.0)]:
    pb_chest = arm_obj.pose.bones["chest"]
    pb_chest.location = (0, 0, z_off)
    pb_chest.rotation_mode = 'XYZ'
    pb_chest.rotation_euler = (spine_pitch, 0, 0)
    insert_key("chest", "location", frame)
    insert_key("chest", "rotation_euler", frame)

for frame, roll in [(1, 0.0), (30, 0.025), (60, 0.0), (90, 0.025), (120, 0.0)]:
    for side, sign in [("L", 1), ("R", -1)]:
        bname = f"wing_upper.{side}"
        pb = arm_obj.pose.bones[bname]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, sign * roll, 0)
        insert_key(bname, "rotation_euler", frame)

for frame, yaw, pitch in [(1, 0.0, 0.0), (40, 0.03, -0.015), (80, -0.03, 0.015), (120, 0.0, 0.0)]:
    pb = arm_obj.pose.bones["head"]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (pitch, 0, yaw)
    insert_key("head", "rotation_euler", frame)

# 2. GREETING (60 frames)
reset_pose()
act_greet = bpy.data.actions.new(name="Greeting")
act_greet.use_fake_user = True
arm_obj.animation_data.action = act_greet

for frame in [1, 60]:
    for b in ["wing_upper.R", "wing_lower.R", "head"]:
        pb = arm_obj.pose.bones[b]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        insert_key(b, "rotation_euler", frame)

for frame, roll, yaw in [(15, 0.85, 0.35), (25, 1.15, 0.45), (35, 0.85, 0.35), (45, 1.15, 0.45)]:
    pb_w = arm_obj.pose.bones["wing_upper.R"]
    pb_w.rotation_mode = 'XYZ'
    pb_w.rotation_euler = (0.2, roll, yaw)
    insert_key("wing_upper.R", "rotation_euler", frame)
    pb_wl = arm_obj.pose.bones["wing_lower.R"]
    pb_wl.rotation_mode = 'XYZ'
    pb_wl.rotation_euler = (0.3, 0.4, 0)
    insert_key("wing_lower.R", "rotation_euler", frame)

for frame in [20, 40]:
    pb_h = arm_obj.pose.bones["head"]
    pb_h.rotation_mode = 'XYZ'
    pb_h.rotation_euler = (-0.05, 0.05, -0.08)
    insert_key("head", "rotation_euler", frame)

# 3. THINKING (90 frames)
reset_pose()
act_think = bpy.data.actions.new(name="Thinking")
act_think.use_fake_user = True
arm_obj.animation_data.action = act_think

for frame in [1, 90]:
    for b in ["head", "wing_upper.L", "eye.L", "eye.R"]:
        pb = arm_obj.pose.bones[b]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        insert_key(b, "rotation_euler", frame)

for frame in [30, 60]:
    pb_h = arm_obj.pose.bones["head"]
    pb_h.rotation_mode = 'XYZ'
    pb_h.rotation_euler = (0.12, 0.18, 0.05)
    insert_key("head", "rotation_euler", frame)
    
    pb_w = arm_obj.pose.bones["wing_upper.L"]
    pb_w.rotation_mode = 'XYZ'
    pb_w.rotation_euler = (0.5, -0.6, 0.4)
    insert_key("wing_upper.L", "rotation_euler", frame)
    
    for en in ["eye.L", "eye.R"]:
        pb_e = arm_obj.pose.bones[en]
        pb_e.rotation_mode = 'XYZ'
        pb_e.rotation_euler = (0.22, 0, 0)
        insert_key(en, "rotation_euler", frame)

# 4. SUCCESS (60 frames)
reset_pose()
act_succ = bpy.data.actions.new(name="Success")
act_succ.use_fake_user = True
arm_obj.animation_data.action = act_succ

for frame in [1, 60]:
    for b in ["wing_upper.L", "wing_upper.R", "head", "chest"]:
        pb = arm_obj.pose.bones[b]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        insert_key(b, "rotation_euler", frame)

for frame in [25, 35]:
    pb_wl = arm_obj.pose.bones["wing_upper.L"]
    pb_wl.rotation_mode = 'XYZ'
    pb_wl.rotation_euler = (-0.2, -0.65, 0.3)
    insert_key("wing_upper.L", "rotation_euler", frame)
    
    pb_wr = arm_obj.pose.bones["wing_upper.R"]
    pb_wr.rotation_mode = 'XYZ'
    pb_wr.rotation_euler = (-0.2, 0.65, -0.3)
    insert_key("wing_upper.R", "rotation_euler", frame)
    
    pb_h = arm_obj.pose.bones["head"]
    pb_h.rotation_mode = 'XYZ'
    pb_h.rotation_euler = (-0.15, 0, 0)
    insert_key("head", "rotation_euler", frame)
    
    pb_c = arm_obj.pose.bones["chest"]
    pb_c.rotation_mode = 'XYZ'
    pb_c.rotation_euler = (-0.08, 0, 0)
    insert_key("chest", "rotation_euler", frame)

# 5. ALERT (50 frames)
reset_pose()
act_alert = bpy.data.actions.new(name="Alert")
act_alert.use_fake_user = True
arm_obj.animation_data.action = act_alert

for frame in [1, 50]:
    for b in ["head", "wing_upper.R"]:
        pb = arm_obj.pose.bones[b]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        insert_key(b, "rotation_euler", frame)

for frame in [18, 32]:
    pb_h = arm_obj.pose.bones["head"]
    pb_h.rotation_mode = 'XYZ'
    pb_h.rotation_euler = (-0.08, 0, 0)
    insert_key("head", "rotation_euler", frame)
    pb_w = arm_obj.pose.bones["wing_upper.R"]
    pb_w.rotation_mode = 'XYZ'
    pb_w.rotation_euler = (0.1, 0.35, 0.15)
    insert_key("wing_upper.R", "rotation_euler", frame)

arm_obj.animation_data.action = act_idle
for act in [act_idle, act_greet, act_think, act_succ, act_alert]:
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = f"NLA_{act.name}"
    track.strips.new(act.name, 1, act)

# ==========================================
# 5. ILUMINACIÓN ESTUDIO Y RENDERS
# ==========================================
print("-> Configurando Estudio...")

world = bpy.data.worlds.new("StudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs['Color'].default_value = (0.42, 0.45, 0.49, 1.0)
    bg_node.inputs['Strength'].default_value = 0.85

light_key_data = bpy.data.lights.new(name="LIGHT_Key", type='AREA')
light_key_data.energy = 220
light_key_data.size = 2.5
light_key_data.color = (1.0, 0.98, 0.96)
light_key = bpy.data.objects.new("LIGHT_Key", light_key_data)
light_key.location = (2.2, -3.2, 2.6)
light_key.rotation_euler = (math.radians(52), 0, math.radians(35))
bpy.context.collection.objects.link(light_key)

light_fill_data = bpy.data.lights.new(name="LIGHT_Fill", type='AREA')
light_fill_data.energy = 110
light_fill_data.size = 3.0
light_fill_data.color = (0.94, 0.96, 1.0)
light_fill = bpy.data.objects.new("LIGHT_Fill", light_fill_data)
light_fill.location = (-2.5, -2.8, 1.8)
light_fill.rotation_euler = (math.radians(55), 0, math.radians(-42))
bpy.context.collection.objects.link(light_fill)

light_rim_data = bpy.data.lights.new(name="LIGHT_Rim", type='SPOT')
light_rim_data.energy = 280
light_rim_data.spot_size = math.radians(70)
light_rim_data.color = (1.0, 1.0, 1.0)
light_rim = bpy.data.objects.new("LIGHT_Rim", light_rim_data)
light_rim.location = (0, 3.2, 2.8)
light_rim.rotation_euler = (math.radians(145), 0, 0)
bpy.context.collection.objects.link(light_rim)

bm_f = bmesh.new()
v_f1 = bm_f.verts.new((-8, -8, 0))
v_f2 = bm_f.verts.new(( 8, -8, 0))
v_f3 = bm_f.verts.new(( 8,  2.5, 0))
v_f4 = bm_f.verts.new((-8,  2.5, 0))
bm_f.faces.new([v_f1, v_f2, v_f3, v_f4])
v_f5 = bm_f.verts.new(( 8,  6.0, 6.0))
v_f6 = bm_f.verts.new((-8,  6.0, 6.0))
bm_f.faces.new([v_f4, v_f3, v_f5, v_f6])

floor_mesh = bpy.data.meshes.new("STUDIO_Floor_Mesh")
bm_f.to_mesh(floor_mesh)
bm_f.free()
floor = bpy.data.objects.new("STUDIO_Floor", floor_mesh)
bpy.context.collection.objects.link(floor)
smooth_mesh(floor)
mat_studio = create_material("MAT_StudioFloor", "#CBD5E1", roughness=0.65)
assign_mat(floor, mat_studio)

def setup_camera(name, loc, rot):
    cam_data = bpy.data.cameras.new(name=name)
    cam_data.lens = 72
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = loc
    cam_obj.rotation_euler = rot
    bpy.context.collection.objects.link(cam_obj)
    return cam_obj

cam_front = setup_camera("CAM_Frontal", (0, -4.6, 1.02), (math.radians(89), 0, 0))
cam_3q    = setup_camera("CAM_TresCuartos", (-3.2, -3.4, 1.15), (math.radians(84), 0, math.radians(-42)))
cam_side  = setup_camera("CAM_Lateral", (-4.6, 0, 1.02), (math.radians(89), 0, math.radians(-90)))

def render_view(cam_obj, output_path):
    scene.camera = cam_obj
    scene.render.filepath = output_path
    print(f"-> Renderizando {output_path}...")
    bpy.ops.render.render(write_still=True)

render_view(cam_front, os.path.join(RENDERS_DIR, "albatros_frontal.png"))
render_view(cam_3q,    os.path.join(RENDERS_DIR, "albatros_tres_cuartos.png"))
render_view(cam_side,  os.path.join(RENDERS_DIR, "albatros_lateral.png"))

# ==========================================
# 6. EXPORTACIÓN GLB
# ==========================================
print("-> Guardando .blend y exportando GLB...")
bpy.ops.wm.save_as_mainfile(filepath=BLEND_FILE)
print(f"-> Guardado .blend en: {BLEND_FILE}")

for ob in [floor, light_key, light_fill, light_rim, cam_front, cam_3q, cam_side]:
    bpy.data.objects.remove(ob, do_unlink=True)

bpy.ops.export_scene.gltf(
    filepath=GLB_FILE,
    export_format='GLB',
    use_selection=False,
    export_apply=False,
    export_yup=True,
    export_animations=True,
    export_nla_strips=True,
    export_anim_single_armature=True,
    export_materials='EXPORT'
)

print(f"-> Exportación GLB exitosa en: {GLB_FILE}")
print("=== Proceso finalizado exitosamente ===")
