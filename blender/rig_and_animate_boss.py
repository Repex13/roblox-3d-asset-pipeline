"""Rig ShadowFlameBoss with a clean 15-bone humanoid skeleton, auto-skin, author 3 boss animations,
export rigged+animated GLB & .blend, and render preview sheets for visual QA.
"""
import math
import os
import bpy
from mathutils import Euler, Vector

WORK = r"C:\Users\YOU\Roblox-3D-Work\shadow_flame_boss"
SRC_BLEND = rf"{WORK}\shadow_flame_boss_preview.blend"
ANIM_BLEND = rf"{WORK}\shadow_flame_boss_animated.blend"
RIGGED_GLB = rf"{WORK}\shadow_flame_boss_rigged_roblox.glb"
RENDER_DIR = rf"{WORK}\anim_frames"
os.makedirs(RENDER_DIR, exist_ok=True)

FPS = 30

# Probed bone coordinates in Blender world space (+Z up, -Y forward, feet on Z=0)
# Viewer left (-X) = character's Right side; viewer right (+X) = character's Left side.
BONES = [
    # (name, parent, head, tail, use_deform)
    ("Root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 3.60), False),
    ("LowerTorso", "Root", (0.0, -0.08, 3.60), (0.0, -0.10, 4.75), True),
    ("UpperTorso", "LowerTorso", (0.0, -0.10, 4.75), (0.0, -0.20, 6.45), True),
    ("Head", "UpperTorso", (0.0, -0.20, 6.45), (0.0, -0.20, 8.95), True),
    # Character Right Arm (-X)
    ("RightUpperArm", "UpperTorso", (-1.35, 0.02, 5.95), (-2.22, -0.01, 4.80), True),
    ("RightLowerArm", "RightUpperArm", (-2.22, -0.01, 4.80), (-2.30, -0.24, 3.15), True),
    ("RightHand", "RightLowerArm", (-2.30, -0.24, 3.15), (-2.05, -0.40, 2.20), True),
    # Character Left Arm (+X)
    ("LeftUpperArm", "UpperTorso", (1.35, 0.02, 5.95), (2.22, -0.01, 4.80), True),
    ("LeftLowerArm", "LeftUpperArm", (2.22, -0.01, 4.80), (2.30, -0.24, 3.15), True),
    ("LeftHand", "LeftLowerArm", (2.30, -0.24, 3.15), (2.05, -0.40, 2.20), True),
    # Character Right Leg (-X)
    ("RightUpperLeg", "LowerTorso", (-0.75, -0.15, 3.75), (-1.32, -0.22, 2.35), True),
    ("RightLowerLeg", "RightUpperLeg", (-1.32, -0.22, 2.35), (-1.55, 0.05, 0.35), True),
    ("RightFoot", "RightLowerLeg", (-1.55, 0.05, 0.35), (-1.62, -0.70, 0.12), True),
    # Character Left Leg (+X)
    ("LeftUpperLeg", "LowerTorso", (0.75, -0.15, 3.75), (1.32, -0.22, 2.35), True),
    ("LeftLowerLeg", "LeftUpperLeg", (1.32, -0.22, 2.35), (1.55, 0.05, 0.35), True),
    ("LeftFoot", "LeftLowerLeg", (1.55, 0.05, 0.35), (1.62, -0.70, 0.12), True),
]


def build_armature():
    arm_data = bpy.data.armatures.new("BossRigData")
    arm_obj = bpy.data.objects.new("BossRig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    created = {}
    for name, parent, head, tail, deform in BONES:
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_deform = deform
        b.use_connect = False
        if parent:
            b.parent = created[parent]
        created[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def pose_reset(arm_obj):
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def apply_key(arm_obj, action, frame, poses):
    """Apply pose dict {bone_name: {'rot': (rx,ry,rz) deg, 'loc': (lx,ly,lz)}} in local bone Euler space."""
    bpy.context.scene.frame_set(frame)
    pose_reset(arm_obj)
    for pb in arm_obj.pose.bones:
        spec = poses.get(pb.name, {})
        if "loc" in spec:
            pb.location = Vector(spec["loc"])
        if "rot" in spec:
            rx, ry, rz = spec["rot"]
            pb.rotation_euler = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")
        pb.keyframe_insert(data_path="location", frame=frame)
        pb.keyframe_insert(data_path="rotation_euler", frame=frame)


def author_action(arm_obj, name, n_frames, key_list):
    act = bpy.data.actions.new(name)
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = act
    for frame, poses in key_list:
        apply_key(arm_obj, act, frame, poses)
    return act


# Keyframe specs (angles in local bone space; bone +Y points down the bone)
# Using bone-local coordinates checked via first render sheet!
IDLE_KEYS = [
    (0, {
        "LowerTorso": {"loc": (0, 0, -0.05), "rot": (2, 0, 0)},
        "UpperTorso": {"rot": (4, 0, 0)},
        "Head": {"rot": (-6, 0, 0)},
        "RightUpperArm": {"rot": (-8, 0, -4)},
        "RightLowerArm": {"rot": (12, 0, 0)},
        "LeftUpperArm": {"rot": (-8, 0, 4)},
        "LeftLowerArm": {"rot": (12, 0, 0)},
        "RightUpperLeg": {"rot": (-4, 0, 0)},
        "RightLowerLeg": {"rot": (6, 0, 0)},
        "RightFoot": {"rot": (-2, 0, 0)},
        "LeftUpperLeg": {"rot": (-4, 0, 0)},
        "LeftLowerLeg": {"rot": (6, 0, 0)},
        "LeftFoot": {"rot": (-2, 0, 0)},
    }),
    (30, {
        "LowerTorso": {"loc": (0, 0, 0.10), "rot": (-2, 2, 0)},
        "UpperTorso": {"rot": (-5, 3, 2)},
        "Head": {"rot": (4, -4, -3)},
        "RightUpperArm": {"rot": (6, 4, -10)},
        "RightLowerArm": {"rot": (22, 0, 0)},
        "LeftUpperArm": {"rot": (6, -4, 10)},
        "LeftLowerArm": {"rot": (22, 0, 0)},
        "RightUpperLeg": {"rot": (2, 0, 0)},
        "RightLowerLeg": {"rot": (-2, 0, 0)},
        "RightFoot": {"rot": (0, 0, 0)},
        "LeftUpperLeg": {"rot": (2, 0, 0)},
        "LeftLowerLeg": {"rot": (-2, 0, 0)},
        "LeftFoot": {"rot": (0, 0, 0)},
    }),
    (60, {
        "LowerTorso": {"loc": (0, 0, -0.05), "rot": (2, 0, 0)},
        "UpperTorso": {"rot": (4, 0, 0)},
        "Head": {"rot": (-6, 0, 0)},
        "RightUpperArm": {"rot": (-8, 0, -4)},
        "RightLowerArm": {"rot": (12, 0, 0)},
        "LeftUpperArm": {"rot": (-8, 0, 4)},
        "LeftLowerArm": {"rot": (12, 0, 0)},
        "RightUpperLeg": {"rot": (-4, 0, 0)},
        "RightLowerLeg": {"rot": (6, 0, 0)},
        "RightFoot": {"rot": (-2, 0, 0)},
        "LeftUpperLeg": {"rot": (-4, 0, 0)},
        "LeftLowerLeg": {"rot": (6, 0, 0)},
        "LeftFoot": {"rot": (-2, 0, 0)},
    }),
]

ULT_KEYS = [
    (0, {}),
    # Crouch gather
    (16, {
        "LowerTorso": {"loc": (0, -0.25, -0.55), "rot": (14, 0, 0)},
        "UpperTorso": {"rot": (18, 0, 0)},
        "Head": {"rot": (-14, 0, 0)},
        "RightUpperArm": {"rot": (-28, 12, -16)},
        "RightLowerArm": {"rot": (42, 0, 0)},
        "LeftUpperArm": {"rot": (-28, -12, 16)},
        "LeftLowerArm": {"rot": (42, 0, 0)},
        "RightUpperLeg": {"rot": (-22, 0, 0)},
        "RightLowerLeg": {"rot": (34, 0, 0)},
        "RightFoot": {"rot": (-12, 0, 0)},
        "LeftUpperLeg": {"rot": (-22, 0, 0)},
        "LeftLowerLeg": {"rot": (34, 0, 0)},
        "LeftFoot": {"rot": (-12, 0, 0)},
    }),
    # Rise & summon peak (t = 1.13s) - wide roaring Y-pose clear of torso/head
    (34, {
        "LowerTorso": {"loc": (0, 0.15, 0.75), "rot": (-12, 0, 0)},
        "UpperTorso": {"rot": (-18, 0, 0)},
        "Head": {"rot": (-24, 0, 0)},
        "RightUpperArm": {"rot": (-82, 0, -48)},
        "RightLowerArm": {"rot": (12, 0, 0)},
        "LeftUpperArm": {"rot": (-82, 0, 48)},
        "LeftLowerArm": {"rot": (12, 0, 0)},
        "RightUpperLeg": {"rot": (12, 0, 0)},
        "RightLowerLeg": {"rot": (10, 0, 0)},
        "LeftUpperLeg": {"rot": (12, 0, 0)},
        "LeftLowerLeg": {"rot": (10, 0, 0)},
    }),
    # Explosive downward slam impact (t = 1.43s)
    (43, {
        "LowerTorso": {"loc": (0, -0.35, -0.45), "rot": (22, 0, 0)},
        "UpperTorso": {"rot": (28, 0, 0)},
        "Head": {"rot": (-18, 0, 0)},
        "RightUpperArm": {"rot": (-58, 18, 16)},
        "RightLowerArm": {"rot": (22, 0, 0)},
        "LeftUpperArm": {"rot": (-58, -18, -16)},
        "LeftLowerArm": {"rot": (22, 0, 0)},
        "RightUpperLeg": {"rot": (-20, 0, 0)},
        "RightLowerLeg": {"rot": (30, 0, 0)},
        "RightFoot": {"rot": (-10, 0, 0)},
        "LeftUpperLeg": {"rot": (-20, 0, 0)},
        "LeftLowerLeg": {"rot": (30, 0, 0)},
        "LeftFoot": {"rot": (-10, 0, 0)},
    }),
    # Recover back to stance
    (60, {}),
]

SLASH_KEYS = [
    (0, {}),
    # Wind-up twist right
    (7, {
        "LowerTorso": {"loc": (0, 0, -0.15), "rot": (8, -18, 0)},
        "UpperTorso": {"rot": (10, -24, 0)},
        "Head": {"rot": (-8, 28, 0)},
        "RightUpperArm": {"rot": (24, -22, -48)},
        "RightLowerArm": {"rot": (32, 0, 0)},
        "LeftUpperArm": {"rot": (-18, 14, 14)},
        "LeftLowerArm": {"rot": (28, 0, 0)},
        "RightUpperLeg": {"rot": (-12, -10, 0)},
        "RightLowerLeg": {"rot": (18, 0, 0)},
        "LeftUpperLeg": {"rot": (8, 8, 0)},
    }),
    # Fast cross-body claw cleave
    (13, {
        "LowerTorso": {"loc": (0, -0.25, -0.20), "rot": (16, 26, 0)},
        "UpperTorso": {"rot": (20, 32, 0)},
        "Head": {"rot": (-16, -26, 0)},
        "RightUpperArm": {"rot": (-64, 24, 42)},
        "RightLowerArm": {"rot": (18, 0, 0)},
        "RightHand": {"rot": (15, 0, 0)},
        "LeftUpperArm": {"rot": (18, -16, 18)},
        "LeftLowerArm": {"rot": (24, 0, 0)},
        "RightUpperLeg": {"rot": (-16, 12, 0)},
        "RightLowerLeg": {"rot": (24, 0, 0)},
        "LeftUpperLeg": {"rot": (12, -8, 0)},
    }),
    # Follow-through hold + return
    (24, {}),
]


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC_BLEND)
    s = bpy.context.scene
    s.render.fps = FPS

    boss = bpy.data.objects["ShadowFlameBoss"]
    arm = build_armature()

    # Bind ShadowFlameBoss to BossRig with automatic weights
    bpy.ops.object.select_all(action="DESELECT")
    boss.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # Verify skinning coverage
    vgroups = boss.vertex_groups
    unweighted = sum(1 for v in boss.data.vertices if len(v.groups) == 0 or max(g.weight for g in v.groups) < 1e-4)
    print(f"[anim] VertexGroups={len(vgroups)} UnweightedVerts={unweighted}/{len(boss.data.vertices)}")

    # Author all 3 Actions
    specs = [
        ("Boss_Idle", 60, IDLE_KEYS),
        ("Boss_UltSummon", 60, ULT_KEYS),
        ("Boss_ClawSlash", 24, SLASH_KEYS),
    ]
    actions = []
    for name, nframes, keys in specs:
        act = author_action(arm, name, nframes, keys)
        actions.append((name, nframes, act))

    # Push all 3 Actions onto NLA tracks so GLB exports every animation clip
    arm.animation_data.action = None
    for name, nframes, act in actions:
        trk = arm.animation_data.nla_tracks.new()
        trk.name = name
        strip = trk.strips.new(name, 0, act)
        strip.action_frame_start = 0
        strip.action_frame_end = nframes

    # Set up studio world, 3-point lighting & camera (preview.blend has no lights/cam yet)
    if not s.world:
        w = bpy.data.worlds.new("Studio")
        s.world = w
        bg = w.node_tree.nodes["Background"]
    else:
        bg = s.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.24, 0.25, 0.28, 1.0)
    bg.inputs["Strength"].default_value = 0.95

    centre = Vector((0.0, 0.0, 4.5))
    radius = 5.4
    if not any(o.type == "LIGHT" for o in bpy.data.objects):
        for lname, off, en, sz, col in [
            ("Key", Vector((1.2, -1.6, 1.4)), 3.6, 2.2, (1.0, 0.97, 0.94)),
            ("Fill", Vector((-1.4, -1.2, 0.8)), 2.2, 3.0, (0.78, 0.72, 1.0)),
            ("Rim", Vector((0.1, 1.8, 1.3)), 3.6, 2.0, (0.76, 0.52, 1.0)),
        ]:
            bpy.ops.object.light_add(type="AREA", location=centre + off * radius * 2.7)
            lt = bpy.context.view_layer.objects.active
            lt.name = lname
            lt.data.energy = en * (radius * 4.5) ** 2
            lt.data.size = sz * radius
            lt.data.color = col
            lt.rotation_euler = (centre - lt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    cam = s.camera
    if not cam:
        bpy.ops.object.camera_add()
        cam = bpy.context.view_layer.objects.active
        s.camera = cam
    cam.data.type = "PERSP"
    cam.data.lens = 50
    d = Vector((0.48, -0.95, 0.16)).normalized()
    cam.location = centre + d * (radius * 2.45)
    cam.rotation_euler = (centre - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()

    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x = 420
    s.render.resolution_y = 480
    s.render.image_settings.file_format = "PNG"
    s.view_settings.view_transform = "Standard"

    # Temporarily disable NLA during per-action frame render so each Action plays solo
    for trk in arm.animation_data.nla_tracks:
        trk.mute = True

    for name, nframes, act in actions:
        arm.animation_data.action = act
        out_sub = os.path.join(RENDER_DIR, name)
        os.makedirs(out_sub, exist_ok=True)
        for f in range(nframes + 1):
            s.frame_set(f)
            s.render.filepath = os.path.join(out_sub, f"f_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
        print(f"[anim] Rendered {nframes + 1} frames for {name}")

    # Restore NLA tracks for multi-clip GLB export + .blend save
    arm.animation_data.action = actions[0][2]
    for trk in arm.animation_data.nla_tracks:
        trk.mute = False

    bpy.ops.wm.save_as_mainfile(filepath=ANIM_BLEND)
    print(f"[anim] Saved {ANIM_BLEND}")

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    boss.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(
        filepath=RIGGED_GLB,
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_skins=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
    )
    print(f"[anim] Exported {RIGGED_GLB}")


if __name__ == "__main__":
    main()
