"""
animar_y_exportar_2d.py
Implementa la Fase 2 del personaje 2D Albatros PROTEO:
1. Configura el rig 2D y el skinning limpio de la marioneta 2D.
2. Crea las 7 acciones de animación requeridas:
   - Idle (120 frames @ 30 FPS)
   - Greeting (60 frames @ 30 FPS)
   - Thinking (90 frames @ 30 FPS)
   - Success (60 frames @ 30 FPS)
   - Alert (50 frames @ 30 FPS)
   - Help (60 frames @ 30 FPS)
   - Talking (90 frames @ 30 FPS)
3. Renderiza las secuencias de fotogramas PNG 512x512 transparentes en sprites/<animacion>/<animacion>_####.png
4. Compila las animaciones WebP optimizadas en exports_2d/albatros_<animacion>.webp usando ffmpeg.
5. Guarda el archivo .blend actualizado.
Uso: blender --background --python scripts/animar_y_exportar_2d.py
"""

import bpy
import math
import os
import subprocess
import shutil

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BLEND_FILE = os.path.join(BASE_DIR, "albatros_proteo_2d.blend")
EXPORT_BLEND = os.path.join(BASE_DIR, "exports_2d", "albatros_proteo_2d.blend")
SPRITES_DIR = os.path.join(BASE_DIR, "sprites")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports_2d")

os.makedirs(SPRITES_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

print(">>> Cargando albatros_proteo_2d.blend...")
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE)

scene = bpy.context.scene
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.file_format = 'PNG'

# Optimizar rendimiento de EEVEE para renders 2D ultrarrápidos
if hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = 1

plane = bpy.data.objects['ALBATROS_ROOT_PLANE']
arm = bpy.data.objects['RIG_AlbatrosProteo_2D']

# 1. Asegurar emisión en material para fidelidad de color
mat = plane.data.materials[0]
bsdf = [n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
tex = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE'][0]
mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
if 'Emission Strength' in bsdf.inputs:
    bsdf.inputs['Emission Strength'].default_value = 1.0

# 2. Subdivisión y pesos de vértices limpios
if len(plane.data.vertices) < 50:
    print("-> Subdividiendo malla para deformación 2D...")
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=40)
    bpy.ops.object.mode_set(mode='OBJECT')

    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    wing_groups = [vg.index for vg in plane.vertex_groups if 'wing' in vg.name]
    body_groups = [vg.index for vg in plane.vertex_groups if vg.name in ['body', 'chest']]
    head_groups = [vg.index for vg in plane.vertex_groups if vg.name in ['head', 'beak_upper', 'beak_lower', 'neck']]
    foot_groups = [vg.index for vg in plane.vertex_groups if 'foot' in vg.name or 'leg' in vg.name]

    for v in plane.data.vertices:
        wz = (plane.matrix_world @ v.co).z
        wx = (plane.matrix_world @ v.co).x
        
        # Pies fijos abajo
        if wz < 0.35:
            for gid in wing_groups:
                plane.vertex_groups[gid].remove([v.index])
            for gid in body_groups:
                plane.vertex_groups[gid].remove([v.index])
            for gid in head_groups:
                plane.vertex_groups[gid].remove([v.index])
        else:
            for gid in foot_groups:
                plane.vertex_groups[gid].remove([v.index])
                
        # Alas aisladas a los costados
        if abs(wx) < 0.23:
            for gid in wing_groups:
                plane.vertex_groups[gid].remove([v.index])
        if abs(wx) >= 0.23 and 0.35 <= wz <= 1.20:
            for gid in body_groups:
                plane.vertex_groups[gid].remove([v.index])
                
        # Cabeza aislada arriba
        if wz < 1.18:
            for gid in head_groups:
                plane.vertex_groups[gid].remove([v.index])
        if wz >= 1.25:
            for gid in body_groups:
                plane.vertex_groups[gid].remove([v.index])

# Helper para resetear pose
def reset_pose():
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)

def insert_pb_keyframe(pb, frame, loc=True, rot=True, scale=True):
    if loc:
        pb.keyframe_insert(data_path="location", frame=frame)
    if rot:
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale:
        pb.keyframe_insert(data_path="scale", frame=frame)

# ==============================================================================
# CREACIÓN DE ACCIONES DE ANIMACIÓN
# ==============================================================================
print("\n>>> Creando las 7 acciones de animación...")

if arm.animation_data is None:
    arm.animation_data_create()

# Helper para crear acción limpia
def create_action(name):
    if name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[name])
    act = bpy.data.actions.new(name=name)
    act.use_fake_user = True
    arm.animation_data.action = act
    reset_pose()
    return act

# ------------------------------------------------------------------------------
# 1. IDLE (120 frames, loop continuo, respiración armónica, parpadeos, micro-sway)
# ------------------------------------------------------------------------------
print("-> Creando acción Idle (120 frames)...")
act_idle = create_action("Idle")

pb_chest = arm.pose.bones['chest']
pb_body = arm.pose.bones['body']
pb_head = arm.pose.bones['head']
pb_neck = arm.pose.bones['neck']
pb_tie = arm.pose.bones['neckerchief']
pb_eye_l = arm.pose.bones['eye.L']
pb_eye_r = arm.pose.bones['eye.R']
pb_wing_l = arm.pose.bones['wing_upper.L']
pb_wing_r = arm.pose.bones['wing_upper.R']

for f in [1, 120]:
    reset_pose()
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_body, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_neck, f)
    insert_pb_keyframe(pb_tie, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)
    insert_pb_keyframe(pb_wing_l, f)
    insert_pb_keyframe(pb_wing_r, f)

# Respiración (ciclos de 30f: inhalar a 15, 45, 75, 105)
for f in [15, 45, 75, 105]:
    pb_chest.location = (0, 0, 0.012)
    pb_chest.scale = (1.015, 1.0, 1.012)
    pb_body.scale = (1.01, 1.0, 1.008)
    pb_tie.location = (0, 0, -0.006)
    pb_wing_l.rotation_euler = (0, 0, math.radians(-1.5))
    pb_wing_r.rotation_euler = (0, 0, math.radians(1.5))
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_body, f)
    insert_pb_keyframe(pb_tie, f)
    insert_pb_keyframe(pb_wing_l, f)
    insert_pb_keyframe(pb_wing_r, f)

for f in [30, 60, 90]:
    pb_chest.location = (0, 0, 0)
    pb_chest.scale = (1.0, 1.0, 1.0)
    pb_body.scale = (1.0, 1.0, 1.0)
    pb_tie.location = (0, 0, 0)
    pb_wing_l.rotation_euler = (0, 0, 0)
    pb_wing_r.rotation_euler = (0, 0, 0)
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_body, f)
    insert_pb_keyframe(pb_tie, f)
    insert_pb_keyframe(pb_wing_l, f)
    insert_pb_keyframe(pb_wing_r, f)

# Cabeza sutil balanceo
pb_head.rotation_euler = (0, 0, math.radians(2.0))
insert_pb_keyframe(pb_head, 30)
pb_head.rotation_euler = (0, 0, 0)
insert_pb_keyframe(pb_head, 60)
pb_head.rotation_euler = (0, 0, math.radians(-2.0))
insert_pb_keyframe(pb_head, 90)

# Parpadeos naturales (en f=42 y f=88)
for blink_frame in [42, 88]:
    for eye in [pb_eye_l, pb_eye_r]:
        eye.scale = (1.0, 1.0, 1.0)
        insert_pb_keyframe(eye, blink_frame - 2)
        eye.scale = (1.0, 1.0, 0.15)
        insert_pb_keyframe(eye, blink_frame)
        eye.scale = (1.0, 1.0, 1.0)
        insert_pb_keyframe(eye, blink_frame + 2)

# ------------------------------------------------------------------------------
# 2. GREETING (60 frames, levanta ala, 2 saludos suaves, mirada al usuario)
# ------------------------------------------------------------------------------
print("-> Creando acción Greeting (60 frames)...")
act_greet = create_action("Greeting")

pb_w_u = arm.pose.bones['wing_upper.L']
pb_w_l = arm.pose.bones['wing_lower.L']
pb_w_t = arm.pose.bones['wing_tip.L']
pb_head = arm.pose.bones['head']
pb_beak_l = arm.pose.bones['beak_lower']

for f in [1, 60]:
    reset_pose()
    insert_pb_keyframe(pb_w_u, f)
    insert_pb_keyframe(pb_w_l, f)
    insert_pb_keyframe(pb_w_t, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_beak_l, f)

# Inclinación amigable y saludo con el ala
pb_head.rotation_euler = (0, 0, math.radians(-3.0))
pb_beak_l.location = (0, 0, -0.015) # sutil sonrisa abierta
insert_pb_keyframe(pb_head, 15)
insert_pb_keyframe(pb_beak_l, 15)
insert_pb_keyframe(pb_head, 45)
insert_pb_keyframe(pb_beak_l, 45)

# Onda 1: subir ala
pb_w_u.rotation_euler = (0, 0, math.radians(-35.0))
pb_w_l.rotation_euler = (0, 0, math.radians(15.0))
insert_pb_keyframe(pb_w_u, 18)
insert_pb_keyframe(pb_w_l, 18)

# Onda 1: oscilación
pb_w_u.rotation_euler = (0, 0, math.radians(-20.0))
insert_pb_keyframe(pb_w_u, 26)

# Onda 2: oscilación arriba
pb_w_u.rotation_euler = (0, 0, math.radians(-38.0))
insert_pb_keyframe(pb_w_u, 35)

# Regreso
pb_w_u.rotation_euler = (0, 0, math.radians(-15.0))
insert_pb_keyframe(pb_w_u, 45)

# ------------------------------------------------------------------------------
# 3. THINKING (90 frames, inclina cabeza, mira arriba, ala hacia el pecho, parpadeo)
# ------------------------------------------------------------------------------
print("-> Creando acción Thinking (90 frames)...")
act_think = create_action("Thinking")

pb_head = arm.pose.bones['head']
pb_eye_l = arm.pose.bones['eye.L']
pb_eye_r = arm.pose.bones['eye.R']
pb_brow_l = arm.pose.bones['eyebrow.L']
pb_brow_r = arm.pose.bones['eyebrow.R']
pb_w_u = arm.pose.bones['wing_upper.L']
pb_w_l = arm.pose.bones['wing_lower.L']

for f in [1, 90]:
    reset_pose()
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)
    insert_pb_keyframe(pb_brow_l, f)
    insert_pb_keyframe(pb_brow_r, f)
    insert_pb_keyframe(pb_w_u, f)
    insert_pb_keyframe(pb_w_l, f)

# Inclinación pensativa a f=25 hasta f=65
for f in [25, 65]:
    pb_head.rotation_euler = (0, 0, math.radians(7.0))
    pb_eye_l.location = (0.015, 0, 0.02)
    pb_eye_r.location = (0.015, 0, 0.02)
    pb_brow_l.location = (0, 0, 0.015)
    pb_brow_r.location = (0, 0, 0.01)
    pb_w_u.rotation_euler = (0, 0, math.radians(-18.0))
    pb_w_l.rotation_euler = (0, 0, math.radians(20.0))
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)
    insert_pb_keyframe(pb_brow_l, f)
    insert_pb_keyframe(pb_brow_r, f)
    insert_pb_keyframe(pb_w_u, f)
    insert_pb_keyframe(pb_w_l, f)

# Parpadeo lento reflexivo a f=45
for eye in [pb_eye_l, pb_eye_r]:
    eye.scale = (1.0, 1.0, 0.1)
    insert_pb_keyframe(eye, 45)
    eye.scale = (1.0, 1.0, 1.0)
    insert_pb_keyframe(eye, 50)

# ------------------------------------------------------------------------------
# 4. SUCCESS (60 frames, abre alas parcialmente, eleva cabeza, pequeño rebote)
# ------------------------------------------------------------------------------
print("-> Creando acción Success (60 frames)...")
act_succ = create_action("Success")

pb_chest = arm.pose.bones['chest']
pb_head = arm.pose.bones['head']
pb_w_l = arm.pose.bones['wing_upper.L']
pb_w_r = arm.pose.bones['wing_upper.R']
pb_beak_l = arm.pose.bones['beak_lower']

for f in [1, 60]:
    reset_pose()
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_w_l, f)
    insert_pb_keyframe(pb_w_r, f)
    insert_pb_keyframe(pb_beak_l, f)

# Anticipación f=8
pb_chest.location = (0, 0, -0.015)
insert_pb_keyframe(pb_chest, 8)

# Rebote y celebración f=22
pb_chest.location = (0, 0, 0.035)
pb_chest.scale = (1.02, 1.0, 1.025)
pb_head.location = (0, 0, 0.02)
pb_head.rotation_euler = (0, 0, math.radians(-2.0))
pb_beak_l.location = (0, 0, -0.02)
pb_w_l.rotation_euler = (0, 0, math.radians(-30.0))
pb_w_r.rotation_euler = (0, 0, math.radians(30.0))
insert_pb_keyframe(pb_chest, 22)
insert_pb_keyframe(pb_head, 22)
insert_pb_keyframe(pb_beak_l, 22)
insert_pb_keyframe(pb_w_l, 22)
insert_pb_keyframe(pb_w_r, 22)

# Hold de triunfo f=34
pb_chest.location = (0, 0, 0.02)
insert_pb_keyframe(pb_chest, 34)
insert_pb_keyframe(pb_head, 34)
insert_pb_keyframe(pb_beak_l, 34)
insert_pb_keyframe(pb_w_l, 34)
insert_pb_keyframe(pb_w_r, 34)

# ------------------------------------------------------------------------------
# 5. ALERT (50 frames, cuerpo erguido, mirada y cejas atentas, postura alerta)
# ------------------------------------------------------------------------------
print("-> Creando acción Alert (50 frames)...")
act_alert = create_action("Alert")

pb_chest = arm.pose.bones['chest']
pb_head = arm.pose.bones['head']
pb_brow_l = arm.pose.bones['eyebrow.L']
pb_brow_r = arm.pose.bones['eyebrow.R']
pb_eye_l = arm.pose.bones['eye.L']
pb_eye_r = arm.pose.bones['eye.R']
pb_w_l = arm.pose.bones['wing_upper.L']

for f in [1, 50]:
    reset_pose()
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_brow_l, f)
    insert_pb_keyframe(pb_brow_r, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)
    insert_pb_keyframe(pb_w_l, f)

# Estiramiento súbito alerta f=12 a f=32
for f in [12, 32]:
    pb_chest.location = (0, 0, 0.028)
    pb_chest.scale = (0.99, 1.0, 1.03)
    pb_head.location = (0, 0, 0.02)
    pb_brow_l.location = (0, 0, 0.02)
    pb_brow_r.location = (0, 0, 0.02)
    pb_eye_l.scale = (1.08, 1.0, 1.08)
    pb_eye_r.scale = (1.08, 1.0, 1.08)
    pb_w_l.rotation_euler = (0, 0, math.radians(-12.0))
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_brow_l, f)
    insert_pb_keyframe(pb_brow_r, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)
    insert_pb_keyframe(pb_w_l, f)

# ------------------------------------------------------------------------------
# 6. HELP (60 frames, extiende ala hacia el costado señalando interfaz, mirada cordial)
# ------------------------------------------------------------------------------
print("-> Creando acción Help (60 frames)...")
act_help = create_action("Help")

pb_w_l = arm.pose.bones['wing_upper.L']
pb_w_low = arm.pose.bones['wing_lower.L']
pb_w_tip = arm.pose.bones['wing_tip.L']
pb_head = arm.pose.bones['head']
pb_chest = arm.pose.bones['chest']

for f in [1, 60]:
    reset_pose()
    insert_pb_keyframe(pb_w_l, f)
    insert_pb_keyframe(pb_w_low, f)
    insert_pb_keyframe(pb_w_tip, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_chest, f)

# Extender ala lateralmente indicando interfaz f=20 a f=42
for f in [20, 42]:
    pb_w_l.rotation_euler = (0, 0, math.radians(-32.0))
    pb_w_low.rotation_euler = (0, 0, math.radians(-12.0))
    pb_w_tip.rotation_euler = (0, 0, math.radians(-8.0))
    pb_head.rotation_euler = (0, 0, math.radians(-4.0))
    pb_chest.location = (0, 0, 0.01)
    insert_pb_keyframe(pb_w_l, f)
    insert_pb_keyframe(pb_w_low, f)
    insert_pb_keyframe(pb_w_tip, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_chest, f)

# ------------------------------------------------------------------------------
# 7. TALKING (90 frames, modulación fonética pico, cabeceo natural, parpadeo, loopable)
# ------------------------------------------------------------------------------
print("-> Creando acción Talking (90 frames)...")
act_talk = create_action("Talking")

pb_beak_l = arm.pose.bones['beak_lower']
pb_head = arm.pose.bones['head']
pb_chest = arm.pose.bones['chest']
pb_eye_l = arm.pose.bones['eye.L']
pb_eye_r = arm.pose.bones['eye.R']

for f in [1, 90]:
    reset_pose()
    insert_pb_keyframe(pb_beak_l, f)
    insert_pb_keyframe(pb_head, f)
    insert_pb_keyframe(pb_chest, f)
    insert_pb_keyframe(pb_eye_l, f)
    insert_pb_keyframe(pb_eye_r, f)

# Fonética y apertura rítmica del pico
cadence_open = [10, 22, 34, 48, 62, 74]
cadence_close = [16, 28, 40, 54, 68, 82]

for f in cadence_open:
    pb_beak_l.location = (0, 0, -0.022)
    insert_pb_keyframe(pb_beak_l, f)

for f in cadence_close:
    pb_beak_l.location = (0, 0, -0.004)
    insert_pb_keyframe(pb_beak_l, f)

# Micro-cabeceo expresivo
pb_head.rotation_euler = (0, 0, math.radians(2.5))
insert_pb_keyframe(pb_head, 24)
pb_head.rotation_euler = (0, 0, math.radians(-2.5))
insert_pb_keyframe(pb_head, 56)

# Parpadeo natural conversacional f=46
for eye in [pb_eye_l, pb_eye_r]:
    eye.scale = (1.0, 1.0, 0.15)
    insert_pb_keyframe(eye, 46)
    eye.scale = (1.0, 1.0, 1.0)
    insert_pb_keyframe(eye, 49)

# Respiración de apoyo
pb_chest.location = (0, 0, 0.01)
insert_pb_keyframe(pb_chest, 45)

reset_pose()
print(">>> Las 7 acciones de animación fueron creadas exitosamente.")

# Guardar .blend con todas las acciones
bpy.ops.wm.save_as_mainfile(filepath=BLEND_FILE)
print(f"-> Guardado .blend principal en: {BLEND_FILE}")
bpy.ops.wm.save_as_mainfile(filepath=EXPORT_BLEND)
print(f"-> Guardado .blend export en: {EXPORT_BLEND}")

# ==============================================================================
# RENDERIZADO DE SECUENCIAS PNG (512x512) Y GENERACIÓN DE WEBP
# ==============================================================================
ANIMACIONES = [
    {"name": "idle", "action": "Idle", "frames": 120, "step": 2, "fps": 15},
    {"name": "greeting", "action": "Greeting", "frames": 60, "step": 2, "fps": 15},
    {"name": "thinking", "action": "Thinking", "frames": 90, "step": 2, "fps": 15},
    {"name": "success", "action": "Success", "frames": 60, "step": 2, "fps": 15},
    {"name": "alert", "action": "Alert", "frames": 50, "step": 2, "fps": 15},
    {"name": "help", "action": "Help", "frames": 60, "step": 2, "fps": 15},
    {"name": "talking", "action": "Talking", "frames": 90, "step": 2, "fps": 15},
]

print("\n=======================================================")
print("INICIANDO RENDERIZADO DE SPRITES Y EXPORTACIÓN WEBP")
print("=======================================================\n")

for anim in ANIMACIONES:
    anim_name = anim["name"]
    action_name = anim["action"]
    total_frames = anim["frames"]
    step = anim["step"]
    fps = anim["fps"]

    out_folder = os.path.join(SPRITES_DIR, anim_name)
    os.makedirs(out_folder, exist_ok=True)

    print(f"\n--- Renderizando '{anim_name}' ({action_name}): {total_frames} frames (tasa optimizada {fps} FPS)... ---")
    arm.animation_data.action = bpy.data.actions[action_name]

    frame_indices = list(range(1, total_frames + 1, step))
    output_idx = 0

    for f in frame_indices:
        scene.frame_set(f)
        out_filename = f"{anim_name}_{output_idx:04d}.png"
        out_filepath = os.path.join(out_folder, out_filename)
        scene.render.filepath = out_filepath
        bpy.ops.render.render(write_still=True)
        output_idx += 1

    print(f"-> Generados {output_idx} sprites PNG en: {out_folder}")

    # Compilar animación WebP con ffmpeg
    webp_path = os.path.join(EXPORTS_DIR, f"albatros_{anim_name}.webp")
    input_pattern = os.path.join(out_folder, f"{anim_name}_%04d.png")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", input_pattern,
        "-vcodec", "libwebp_anim",
        "-loop", "0",
        "-lossless", "0",
        "-compression_level", "4",
        "-q:v", "80",
        webp_path
    ]

    print(f"-> Compilando WebP animado: {webp_path}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and os.path.isfile(webp_path):
        size_kb = os.path.getsize(webp_path) / 1024
        print(f"[OK] {os.path.basename(webp_path)} generado exitosamente ({size_kb:.1f} KB)")
    else:
        print(f"[ERROR] Error compilando WebP para {anim_name}:\n{res.stderr[-400:]}")

print("\n=== Todas las animaciones 2D y WebP fueron generadas exitosamente ===")
