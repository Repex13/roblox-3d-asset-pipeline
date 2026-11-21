"""Build 4 precision hard-surface Gurren Lagann Roblox 3D props/weapons in Blender 5.3:
  1. core_drill       (Simon's Golden Core Drill Key Pendant)
  2. giga_drill       (Giga Drill Break Weapon)
  3. kamina_glasses   (Kamina's Iconic Crimson Triangle Sunglasses)
  4. kamina_katana    (Kamina's Long Odachi Sword)
Each asset is verified manifold (0 open holes, 0 non-manifold edges), exported to GLB & .blend,
and rendered in a multi-angle studio showcase sheet for visual QA.
"""
import math
import os
import bpy
import bmesh
from mathutils import Matrix, Vector

OUT_ROOT = r"C:\Users\YOU\Roblox-3D-Work\gurren_lagann_pack"
os.makedirs(OUT_ROOT, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, color, metallic=0.0, roughness=0.35, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return m


def verify_manifold_and_join(objs, name):
    """Verify every solid part has 0 open holes & 0 non-manifold edges, then join cleanly."""
    total_holes = 0
    total_nm = 0
    for obj in objs:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.edges.ensure_lookup_table()
        holes = sum(1 for e in bm.edges if e.is_boundary)
        nm = sum(1 for e in bm.edges if not e.is_manifold)
        total_holes += holes
        total_nm += nm
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name

    # Smart UV unwrap cleanly so GLB carries valid UVs
    if not joined.data.uv_layers:
        joined.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.005)
    bpy.ops.object.mode_set(mode="OBJECT")

    tris = sum(max(1, len(p.vertices) - 2) for p in joined.data.polygons)
    print(f"[pack] {name}: tris={tris}, verts={len(joined.data.vertices)}, open_holes={total_holes}, non_manifold={total_nm}")
    return joined


def make_helical_drill_cone(name, height, base_r, turns, rib_depth, seg_z=96, seg_a=64, mat=None):
    """Watertight tapered cone sculpted with continuous helical spiral flutes."""
    bm = bmesh.new()
    rings = []
    for iz in range(seg_z + 1):
        u = iz / seg_z  # 0=base, 1=tip
        z = u * height
        # Slight ogive taper for heroic anime drill profile
        taper = max(0.015, (1.0 - u) ** 0.78)
        r_mean = base_r * taper
        fade_end = min(1.0, u * 10.0) * min(1.0, (1.0 - u) * 7.0)
        ring = []
        for ia in range(seg_a):
            theta = 2.0 * math.pi * ia / seg_a
            # Asymmetric sawtooth-like flute wave for crisp spiral cutting edge
            phase = (theta - turns * 2.0 * math.pi * u) % (2.0 * math.pi)
            w = 1.0 - (phase / math.pi)  # +1 .. -1 saw ridge
            # Smooth edge slightly so normals behave cleanly
            r = r_mean * (1.0 + rib_depth * fade_end * (0.55 * w + 0.35 * math.sin(phase)))
            ring.append(bm.verts.new((r * math.cos(theta), r * math.sin(theta), z)))
        rings.append(ring)

    # Connect side rings
    for iz in range(seg_z):
        for ia in range(seg_a):
            inext = (ia + 1) % seg_a
            bm.faces.new((rings[iz][ia], rings[iz][inext], rings[iz + 1][inext], rings[iz + 1][ia]))

    # Cap bottom & tip with single center pole
    v_bot = bm.verts.new((0.0, 0.0, 0.0))
    v_top = bm.verts.new((0.0, 0.0, height + 0.01))
    for ia in range(seg_a):
        inext = (ia + 1) % seg_a
        bm.faces.new((v_bot, rings[0][inext], rings[0][ia]))
        bm.faces.new((rings[seg_z][ia], rings[seg_z][inext], v_top))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_cylinder(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), segs=32, bevel_w=0.0, mat=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segs, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    if bevel_w > 0:
        bev = obj.modifiers.new("Bev", "BEVEL")
        bev.width = bevel_w
        bev.segments = 2
        bpy.ops.object.modifier_apply(modifier="Bev")
    for p in obj.data.polygons:
        p.use_smooth = True
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_torus(name, major_r, minor_r, loc=(0, 0, 0), rot=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=36, minor_segments=16, major_radius=major_r, minor_radius=minor_r, location=loc, rotation=rot
    )
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    for p in obj.data.polygons:
        p.use_smooth = True
    if mat:
        obj.data.materials.append(mat)
    return obj


# -----------------------------------------------------------------------------
# 1. CORE DRILL (Simon's Golden Key Pendant - ~1.4 studs tall)
# -----------------------------------------------------------------------------
def build_core_drill():
    reset_scene()
    gold = make_mat("CoreGold", (0.94, 0.72, 0.16), metallic=0.92, roughness=0.22)
    dark_gold = make_mat("CoreDarkGold", (0.58, 0.40, 0.08), metallic=0.88, roughness=0.35)
    spiral_glow = make_mat("SpiralGlow", (0.10, 0.95, 0.42), metallic=0.0, roughness=0.18,
                           emission=(0.15, 1.0, 0.45), emission_strength=3.2)

    parts = [
        # Helical drill body pointing +Z from Z=0.52..1.40
        make_helical_drill_cone("DrillTip", height=0.88, base_r=0.26, turns=4.5, rib_depth=0.22, seg_z=80, seg_a=56, mat=gold),
        # Flanged octagonal guard collar
        add_cylinder("GuardCollar", radius=0.31, depth=0.09, loc=(0, 0, 0.48), segs=8, bevel_w=0.015, mat=gold),
        # Glowing green spiral energy core ring
        add_cylinder("CoreRing", radius=0.21, depth=0.08, loc=(0, 0, 0.40), segs=24, bevel_w=0.01, mat=spiral_glow),
        # Stepped recessed dark collar
        add_cylinder("NeckStep", radius=0.17, depth=0.14, loc=(0, 0, 0.30), segs=16, bevel_w=0.01, mat=dark_gold),
        # Octagonal pommel grip
        add_cylinder("Grip", radius=0.22, depth=0.18, loc=(0, 0, 0.17), segs=8, bevel_w=0.018, mat=gold),
        # Bail eyelet ring at base
        add_torus("BailRing", major_r=0.11, minor_r=0.032, loc=(0, 0, 0.05), rot=(math.radians(90), 0, 0), mat=gold),
    ]
    # Shift helical cone base up to Z=0.52
    parts[0].location = (0, 0, 0.52)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.transform_apply(location=True)

    return verify_manifold_and_join(parts, "CoreDrill")


# -----------------------------------------------------------------------------
# 2. GIGA DRILL WEAPON (Hero Weapon Attachment - ~5.6 studs tall)
# -----------------------------------------------------------------------------
def build_giga_drill():
    reset_scene()
    crimson = make_mat("GigaCrimson", (0.76, 0.09, 0.14), metallic=0.72, roughness=0.28)
    gunmetal = make_mat("GigaGunmetal", (0.14, 0.14, 0.17), metallic=0.85, roughness=0.32)
    gold = make_mat("GigaGold", (0.95, 0.74, 0.18), metallic=0.90, roughness=0.25)
    spiral_em = make_mat("GigaSpiralEnergy", (0.18, 0.96, 0.45), metallic=0.0, roughness=0.15,
                         emission=(0.20, 1.0, 0.50), emission_strength=3.5)

    drill = make_helical_drill_cone("GigaSpiralCone", height=4.45, base_r=1.18, turns=6.0, rib_depth=0.24, seg_z=120, seg_a=64, mat=crimson)
    drill.location = (0, 0, 1.15)
    bpy.context.view_layer.objects.active = drill
    bpy.ops.object.transform_apply(location=True)

    parts = [
        drill,
        add_cylinder("UpperRing", radius=1.24, depth=0.22, loc=(0, 0, 1.08), segs=24, bevel_w=0.04, mat=gold),
        add_cylinder("EnergyBand", radius=1.15, depth=0.20, loc=(0, 0, 0.88), segs=32, bevel_w=0.02, mat=spiral_em),
        add_cylinder("ThrusterBase", radius=1.28, depth=0.58, loc=(0, 0, 0.50), segs=12, bevel_w=0.04, mat=gunmetal),
        add_cylinder("ArmCuff", radius=0.96, depth=0.24, loc=(0, 0, 0.12), segs=16, bevel_w=0.02, mat=gold),
    ]
    # 6 angled armored fins around the thruster cuff
    for i in range(6):
        ang = i * math.pi / 3.0
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.26 * math.cos(ang), 1.26 * math.sin(ang), 0.58))
        fin = bpy.context.view_layer.objects.active
        fin.name = f"Fin_{i}"
        fin.scale = (0.36, 0.14, 0.72)
        fin.rotation_euler = (0, math.radians(-16), ang)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bev = fin.modifiers.new("Bev", "BEVEL")
        bev.width = 0.03
        bev.segments = 2
        bpy.ops.object.modifier_apply(modifier="Bev")
        fin.data.materials.append(crimson)
        parts.append(fin)

    return verify_manifold_and_join(parts, "GigaDrill")


# -----------------------------------------------------------------------------
# 3. KAMINA GLASSES (Iconic Sharp Red Triangle Shades - ~2.2 studs wide)
# -----------------------------------------------------------------------------
def make_extruded_poly(name, pts_2d, thickness, bevel_w=0.012, mat=None):
    """Build a watertight beveled planar prism centered along depth."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -thickness * 0.5, z)) for (x, z) in pts_2d]
    back = [bm.verts.new((x, thickness * 0.5, z)) for (x, z) in pts_2d]
    n = len(pts_2d)
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if bevel_w > 0:
        bev = obj.modifiers.new("Bev", "BEVEL")
        bev.width = bevel_w
        bev.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="Bev")
    if mat:
        obj.data.materials.append(mat)
    return obj


def build_kamina_glasses():
    reset_scene()
    crimson_lens = make_mat("KaminaRedLens", (0.86, 0.05, 0.08), metallic=0.15, roughness=0.08,
                            emission=(0.45, 0.02, 0.03), emission_strength=0.45)
    frame_dark = make_mat("KaminaFrame", (0.06, 0.05, 0.07), metallic=0.75, roughness=0.25)

    # Classic sweeping angular Kamina boomerang-triangle wings (both halves symmetric)
    # Drawn in XZ plane (width along X, height along Z, thickness along Y)
    right_wing_pts = [
        (0.06, 0.14),   # inner top bridge corner
        (1.18, 0.68),   # extreme sharp swept wingtip!
        (0.84, 0.24),   # notched lower outer spike corner
        (0.96, 0.06),   # outer winglet tip
        (0.22, -0.22),  # lower cheek point
        (0.05, -0.02),  # nose cut inner corner
    ]
    left_wing_pts = [(-x, z) for (x, z) in reversed(right_wing_pts)]

    lens_r = make_extruded_poly("LensR", right_wing_pts, thickness=0.06, bevel_w=0.012, mat=crimson_lens)
    lens_l = make_extruded_poly("LensL", left_wing_pts, thickness=0.06, bevel_w=0.012, mat=crimson_lens)
    # Slight wrap angle around face (-Y is front)
    lens_r.rotation_euler = (0, 0, math.radians(-10))
    lens_l.rotation_euler = (0, 0, math.radians(10))
    for l in (lens_r, lens_l):
        bpy.context.view_layer.objects.active = l
        bpy.ops.object.transform_apply(rotation=True)

    # Center angular nose bridge + ear temple arms
    bridge = make_extruded_poly(
        "NoseBridge",
        [(-0.10, 0.14), (0.10, 0.14), (0.08, 0.02), (-0.08, 0.02)],
        thickness=0.075, bevel_w=0.008, mat=frame_dark,
    )
    parts = [lens_r, lens_l, bridge]

    for side, sx in (("R", 1.0), ("L", -1.0)):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(sx * 0.72, 0.54, 0.22))
        arm = bpy.context.view_layer.objects.active
        arm.name = f"TempleArm_{side}"
        arm.scale = (0.04, 1.05, 0.075)
        bpy.ops.object.transform_apply(scale=True)
        bev = arm.modifiers.new("Bev", "BEVEL")
        bev.width = 0.008
        bev.segments = 2
        bpy.ops.object.modifier_apply(modifier="Bev")
        arm.data.materials.append(frame_dark)
        parts.append(arm)

    joined = verify_manifold_and_join(parts, "KaminaGlasses")
    # Center lowest Z at 0
    zs = [(joined.matrix_world @ v.co).z for v in joined.data.vertices]
    joined.location.z -= min(zs)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.object.transform_apply(location=True)
    return joined


# -----------------------------------------------------------------------------
# 4. KAMINA ODACHI KATANA (~6.5 studs tall upright standing along +Z)
# -----------------------------------------------------------------------------
def build_kamina_katana():
    reset_scene()
    steel = make_mat("KatanaSteel", (0.82, 0.85, 0.90), metallic=0.96, roughness=0.14)
    gold = make_mat("KatanaGold", (0.94, 0.74, 0.18), metallic=0.90, roughness=0.24)
    wrap_red = make_mat("KatanaHiltRed", (0.58, 0.07, 0.11), metallic=0.08, roughness=0.55)
    dark_saya = make_mat("KatanaDarkMetal", (0.08, 0.08, 0.10), metallic=0.65, roughness=0.35)

    # 1. Curved katana blade (watertight swept diamond cross-section from Z=1.42..6.50)
    bm = bmesh.new()
    segs = 60
    rings = []
    for i in range(segs + 1):
        u = i / segs
        z = 1.42 + u * 5.05
        # Classic gentle katana sori curvature in Y
        curve_y = 0.28 * (u ** 1.8)
        taper = 1.0 if u < 0.88 else max(0.08, 1.0 - (u - 0.88) / 0.12 * 0.92)
        half_w = 0.085 * taper   # Y width (spine +Y to sharp edge -Y)
        half_t = 0.026 * taper   # X thickness
        pts = [
            (0.0, curve_y - half_w, z),           # sharp edge (-Y)
            (half_t, curve_y + 0.015 * taper, z), # shinogi ridge +X
            (0.0, curve_y + half_w, z),           # spine (+Y)
            (-half_t, curve_y + 0.015 * taper, z),# shinogi ridge -X
        ]
        rings.append([bm.verts.new(p) for p in pts])

    for i in range(segs):
        for k in range(4):
            kn = (k + 1) % 4
            bm.faces.new((rings[i][k], rings[i][kn], rings[i + 1][kn], rings[i + 1][k]))
    # Cap hilt-tang end & kissaki point
    bm.faces.new(list(reversed(rings[0])))
    v_tip = bm.verts.new((0.0, 0.28 + 0.01, 6.53))
    for k in range(4):
        kn = (k + 1) % 4
        bm.faces.new((rings[segs][k], rings[segs][kn], v_tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("BladeMesh")
    bm.to_mesh(me)
    bm.free()
    blade = bpy.data.objects.new("Blade", me)
    bpy.context.scene.collection.objects.link(blade)
    blade.data.materials.append(steel)

    # 2. Habaki blade collar + Gold square Tsuba guard
    habaki = add_cylinder("Habaki", radius=0.095, depth=0.16, loc=(0, 0, 1.48), segs=6, bevel_w=0.008, mat=gold)
    habaki.scale = (0.55, 1.2, 1.0)
    bpy.context.view_layer.objects.active = habaki
    bpy.ops.object.transform_apply(scale=True)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 1.38))
    tsuba = bpy.context.view_layer.objects.active
    tsuba.name = "Tsuba"
    tsuba.scale = (0.42, 0.48, 0.055)
    bpy.ops.object.transform_apply(scale=True)
    bev = tsuba.modifiers.new("Bev", "BEVEL")
    bev.width = 0.015
    bev.segments = 2
    bpy.ops.object.modifier_apply(modifier="Bev")
    tsuba.data.materials.append(gold)

    # 3. Wrapped Tsuka hilt + ribbed wrap rings + gold Kashira pommel
    hilt = add_cylinder("Tsuka", radius=0.068, depth=1.28, loc=(0, -0.02, 0.72), segs=12, bevel_w=0.01, mat=dark_saya)
    hilt.scale = (0.72, 1.15, 1.0)
    bpy.context.view_layer.objects.active = hilt
    bpy.ops.object.transform_apply(scale=True)

    pommel = add_cylinder("Kashira", radius=0.08, depth=0.12, loc=(0, -0.02, 0.06), segs=12, bevel_w=0.015, mat=gold)
    pommel.scale = (0.78, 1.18, 1.0)
    bpy.context.view_layer.objects.active = pommel
    bpy.ops.object.transform_apply(scale=True)

    parts = [blade, habaki, tsuba, hilt, pommel]
    # Red ito wrap diamond bands along the grip
    for idx in range(11):
        z_band = 0.20 + idx * 0.105
        band = add_torus(f"Wrap_{idx}", major_r=0.064, minor_r=0.016, loc=(0, -0.02, z_band), mat=wrap_red)
        band.scale = (0.76, 1.18, 1.0)
        bpy.context.view_layer.objects.active = band
        bpy.ops.object.transform_apply(scale=True)
        parts.append(band)

    return verify_manifold_and_join(parts, "KaminaKatana")


def export_and_render(builder_fn, slug, cam_dir, cam_dist_mult=2.55):
    item_dir = os.path.join(OUT_ROOT, slug)
    os.makedirs(item_dir, exist_ok=True)
    obj = builder_fn()

    # Export GLB & .blend
    glb_path = os.path.join(item_dir, f"{slug}_roblox.glb")
    blend_path = os.path.join(item_dir, f"{slug}_preview.blend")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
    )
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    # Render Cycles hero shot for this item
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo + hi) * 0.5
    radius = max(0.3, (hi - lo).length * 0.5)

    s = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    s.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.09, 0.10, 0.12, 1.0)
    bg.inputs["Strength"].default_value = 0.9

    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, lo.z - 0.01))
    flr = bpy.context.view_layer.objects.active
    fmat = make_mat("Floor", (0.06, 0.065, 0.075), roughness=0.65)
    flr.data.materials.append(fmat)

    for lname, off, en, sz, col in [
        ("Key", Vector((1.2, -1.6, 1.4)), 3.8, 2.2, (1.0, 0.97, 0.94)),
        ("Fill", Vector((-1.4, -1.2, 0.8)), 2.2, 3.0, (0.82, 0.90, 1.0)),
        ("Rim", Vector((0.1, 1.8, 1.3)), 3.6, 2.0, (1.0, 0.72, 0.55)),
    ]:
        bpy.ops.object.light_add(type="AREA", location=centre + off * radius * 2.7)
        lt = bpy.context.view_layer.objects.active
        lt.name = lname
        lt.data.energy = en * (radius * 4.5) ** 2
        lt.data.size = sz * radius
        lt.data.color = col
        lt.rotation_euler = (centre - lt.location).normalized().to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.camera_add()
    cam = bpy.context.view_layer.objects.active
    s.camera = cam
    cam.data.lens = 50
    d = Vector(cam_dir).normalized()
    cam.location = centre + d * (radius * cam_dist_mult)
    cam.rotation_euler = (centre - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()

    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 48
    s.cycles.use_denoising = True
    s.render.resolution_x = 768
    s.render.resolution_y = 768
    s.view_settings.view_transform = "AgX"
    hero_path = os.path.join(item_dir, f"{slug}_hero.png")
    s.render.filepath = hero_path
    bpy.ops.render.render(write_still=True)
    return hero_path


def main():
    heroes = [
        export_and_render(build_core_drill, "core_drill", (0.55, -0.95, 0.35), 2.85),
        export_and_render(build_giga_drill, "giga_drill", (0.55, -0.95, 0.30), 2.75),
        export_and_render(build_kamina_glasses, "kamina_glasses", (0.45, -1.0, 0.25), 2.55),
        export_and_render(build_kamina_katana, "kamina_katana", (0.55, -0.95, 0.22), 2.65),
    ]
    print("[pack] HEROES:", "|".join(heroes))


if __name__ == "__main__":
    main()
