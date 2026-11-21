"""Optimize, weld, decimate to high-end Roblox weapon budgets, Smart UV unwrap, bake 1024x1024
Color + Tangent Normal maps, export GLB & .blend, and render turnarounds + 1024x1024 Cycles hero shots
for Kite's Crazy Slots Arsenal (Hunter x Hunter):
  1. crazy_slots_clown   (Sentient Roulette Clown Companion / Summon Head)
  2. slot_2_scythe       (Slot #2: Crazy Slots Death Scythe - Silent Waltz)
  3. slot_3_mace         (Slot #3: Crazy Slots Battle Mace)
  4. slot_4_carbine      (Slot #4: Crazy Slots Precision Carbine Rifle)
"""
import math
import os
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT = r"C:\Users\YOU\Roblox-3D-Work\kite_crazy_slots_pack"
TEX_SIZE = 1024

TARGETS = [
    # (slug, name, target_tris, target_major_studs, rough, metal, axis_mode)
    # axis_mode='Z' scales height (Z) to target_major_studs; axis_mode='MAX' scales longest axis (X/Z).
    ("crazy_slots_clown", "CrazySlotsClown", 15500, 3.2, 0.30, 0.35, "Z"),
    ("slot_2_scythe", "CrazySlots_No2_Scythe", 16000, 7.5, 0.24, 0.65, "Z"),
    ("slot_3_mace", "CrazySlots_No3_Mace", 15500, 4.8, 0.25, 0.62, "Z"),
    ("slot_4_carbine", "CrazySlots_No4_Carbine", 16000, 5.2, 0.28, 0.55, "MAX"),
]


def import_single(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new_objs = [o for o in (set(bpy.data.objects) - before) if o.type == "MESH"]
    if len(new_objs) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in new_objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new_objs[0]
        bpy.ops.object.join()
    obj = new_objs[0]
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def clean_and_weld(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    if boundary_edges:
        bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=0)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.update()

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")

    parts = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if len(parts) > 1:
        parts.sort(key=lambda o: len(o.data.polygons), reverse=True)
        keep_thresh = max(50, int(len(parts[0].data.polygons) * 0.01))
        keepers = [p for p in parts if len(p.data.polygons) >= keep_thresh]
        for p in parts:
            if p not in keepers:
                bpy.data.objects.remove(p, do_unlink=True)
        if len(keepers) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for k in keepers:
                k.select_set(True)
            bpy.context.view_layer.objects.active = keepers[0]
            bpy.ops.object.join()
        obj = keepers[0]
    return obj


def make_emissive_albedo_source(obj):
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        tex_img = None
        for node in nt.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                tex_img = node.image
                break
        if tex_img:
            nt.nodes.clear()
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            em = nt.nodes.new("ShaderNodeEmission")
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = tex_img
            nt.links.new(tex.outputs["Color"], em.inputs["Color"])
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])


def process_one(slug, display_name, target_tris, target_studs, rough, metal, axis_mode):
    work = os.path.join(ROOT, slug)
    tex_glb = os.path.join(work, "local_out", f"{slug}_textured.glb")
    high_glb = os.path.join(work, "local_out", f"{slug}_white_high.glb")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    tex_src = clean_and_weld(import_single(tex_glb, "TexSource"))
    make_emissive_albedo_source(tex_src)
    high_src = clean_and_weld(import_single(high_glb, "HighSource"))

    bpy.ops.object.select_all(action="DESELECT")
    tex_src.select_set(True)
    bpy.context.view_layer.objects.active = tex_src
    bpy.ops.object.duplicate()
    low = bpy.context.view_layer.objects.active
    low.name = display_name

    dec = low.modifiers.new("Decimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = min(1.0, target_tris / max(1, len(low.data.polygons)))
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="Decimate")

    bm = bmesh.new()
    bm.from_mesh(low.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.edges.ensure_lookup_table()
    open_holes = sum(1 for e in bm.edges if e.is_boundary)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(low.data)
    bm.free()
    low.data.update()

    # Scale cleanly and seat bottom on Z=0
    pts = [low.matrix_world @ v.co for v in low.data.vertices]
    lo_v = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi_v = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    span = hi_v.z - lo_v.z if axis_mode == "Z" else max(hi_v.x - lo_v.x, hi_v.y - lo_v.y, hi_v.z - lo_v.z)
    scale = target_studs / max(1e-6, span)
    cx = (lo_v.x + hi_v.x) * 0.5
    cy = (lo_v.y + hi_v.y) * 0.5
    offset = Vector((-cx * scale, -cy * scale, -lo_v.z * scale))
    for o in (low, tex_src, high_src):
        o.scale = (scale, scale, scale)
        o.location = offset
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)

    while len(low.data.uv_layers) > 0:
        low.data.uv_layers.remove(low.data.uv_layers[0])
    low.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")

    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 16
    s.cycles.use_denoising = False

    bake_mat = bpy.data.materials.new("BakeTarget")
    bake_mat.use_nodes = True
    low.data.materials.clear()
    low.data.materials.append(bake_mat)
    nt = bake_mat.node_tree

    col_img = bpy.data.images.new("ColorBake", TEX_SIZE, TEX_SIZE, alpha=False)
    col_node = nt.nodes.new("ShaderNodeTexImage")
    col_node.image = col_img
    nt.nodes.active = col_node
    high_src.hide_render = True
    tex_src.hide_render = False
    low.hide_render = False

    cage = 0.045 * (target_studs / 4.5)
    bpy.ops.object.select_all(action="DESELECT")
    tex_src.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    s.cycles.bake_type = "EMIT"
    s.render.bake.use_selected_to_active = True
    s.render.bake.cage_extrusion = cage
    s.render.bake.max_ray_distance = cage * 2.2
    s.render.bake.margin = 16
    bpy.ops.object.bake(type="EMIT")
    col_path = os.path.join(work, "color.png")
    col_img.filepath_raw = col_path
    col_img.file_format = "PNG"
    col_img.save()

    nrm_img = bpy.data.images.new("NormalBake", TEX_SIZE, TEX_SIZE, alpha=False)
    nrm_img.colorspace_settings.name = "Non-Color"
    nrm_node = nt.nodes.new("ShaderNodeTexImage")
    nrm_node.image = nrm_img
    nt.nodes.active = nrm_node
    tex_src.hide_render = True
    high_src.hide_render = False
    for p in low.data.polygons:
        p.use_smooth = True

    bpy.ops.object.select_all(action="DESELECT")
    high_src.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    s.cycles.bake_type = "NORMAL"
    s.render.bake.normal_space = "TANGENT"
    s.render.bake.use_selected_to_active = True
    s.render.bake.cage_extrusion = cage
    s.render.bake.max_ray_distance = cage * 2.2
    s.render.bake.margin = 16
    bpy.ops.object.bake(type="NORMAL")
    nrm_path = os.path.join(work, "normal.png")
    nrm_img.filepath_raw = nrm_path
    nrm_img.file_format = "PNG"
    nrm_img.save()

    bpy.data.objects.remove(tex_src, do_unlink=True)
    bpy.data.objects.remove(high_src, do_unlink=True)

    final_mat = bpy.data.materials.new(f"{display_name}Mat")
    final_mat.use_nodes = True
    fnt = final_mat.node_tree
    fn, fl = fnt.nodes, fnt.links
    fbsdf = fn.get("Principled BSDF")
    fbsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in fbsdf.inputs:
        fbsdf.inputs["Metallic"].default_value = metal

    tc = fn.new("ShaderNodeTexImage")
    tc.image = bpy.data.images.load(col_path)
    fl.new(tc.outputs["Color"], fbsdf.inputs["Base Color"])

    tn = fn.new("ShaderNodeTexImage")
    tn.image = bpy.data.images.load(nrm_path)
    tn.image.colorspace_settings.name = "Non-Color"
    nmap = fn.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.85
    fl.new(tn.outputs["Color"], nmap.inputs["Color"])
    fl.new(nmap.outputs["Normal"], fbsdf.inputs["Normal"])

    low.data.materials.clear()
    low.data.materials.append(final_mat)

    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    glb_out = os.path.join(work, f"{slug}_roblox.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb_out,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
    )
    blend_out = os.path.join(work, f"{slug}_preview.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)

    # Render 4-angle EEVEE turnaround + 1024x1024 Cycles beauty shot
    pts = [low.matrix_world @ v.co for v in low.data.vertices]
    lo_v = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi_v = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo_v + hi_v) * 0.5
    radius = (hi_v - lo_v).length * 0.5
    dims = (hi_v.x - lo_v.x, hi_v.y - lo_v.y, hi_v.z - lo_v.z)
    print(f"[kite_pack] {slug}: tris={len(low.data.polygons)} verts={len(low.data.vertices)} "
          f"open_holes={open_holes} non_manifold={non_man} dims={dims[0]:.2f}x{dims[1]:.2f}x{dims[2]:.2f}")

    w = bpy.data.worlds.new("Studio")
    s.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]

    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.005))
    floor = bpy.context.view_layer.objects.active
    fmat = bpy.data.materials.new("Floor")
    fmat.use_nodes = True
    fbs = fmat.node_tree.nodes.get("Principled BSDF")
    fbs.inputs["Base Color"].default_value = (0.06, 0.055, 0.08, 1.0)
    fbs.inputs["Roughness"].default_value = 0.60
    floor.data.materials.append(fmat)

    for lname, off, en, sz, col in [
        ("Key", Vector((1.2, -1.6, 1.4)), 3.8, 2.2, (1.0, 0.97, 0.94)),
        ("Fill", Vector((-1.4, -1.2, 0.8)), 2.4, 3.0, (0.86, 0.82, 1.0)),
        ("Rim", Vector((0.1, 1.8, 1.3)), 3.6, 2.0, (1.0, 0.72, 0.58)),
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

    # 4-angle EEVEE turnaround
    s.render.engine = "BLENDER_EEVEE"
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(dims) * 1.22
    s.render.resolution_x = 384
    s.render.resolution_y = 480
    s.view_settings.view_transform = "Standard"
    floor.hide_render = True
    bg.inputs["Color"].default_value = (0.28, 0.29, 0.32, 1.0)
    bg.inputs["Strength"].default_value = 0.95
    for i, yaw_deg in enumerate((-90, 0, 90, 180)):
        yaw = math.radians(yaw_deg)
        elev = math.radians(8)
        d = Vector((math.cos(yaw) * math.cos(elev), math.sin(yaw) * math.cos(elev), math.sin(elev)))
        cam.location = centre + d * (radius * 4.0)
        cam.rotation_euler = (centre - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
        s.render.filepath = os.path.join(work, f"_turn_{i}.png")
        bpy.ops.render.render(write_still=True)

    # Cycles 1024x1024 Hero beauty render
    floor.hide_render = False
    bg.inputs["Color"].default_value = (0.08, 0.075, 0.11, 1.0)
    bg.inputs["Strength"].default_value = 0.85
    s.render.engine = "CYCLES"
    s.cycles.samples = 64
    s.cycles.use_denoising = True
    cam.data.type = "PERSP"
    cam.data.lens = 52
    d = Vector((0.48, -0.95, 0.22)).normalized()
    cam.location = centre + d * (radius * 2.75)
    cam.rotation_euler = (centre - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    s.render.resolution_x = 1024
    s.render.resolution_y = 1024
    s.view_settings.view_transform = "AgX"
    s.render.filepath = os.path.join(work, f"{slug}_hero.png")
    bpy.ops.render.render(write_still=True)


def main():
    only = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else None
    for args in TARGETS:
        if only and args[0] not in only:
            continue
        process_one(*args)
    print("[kite_pack] ALL_DONE")


if __name__ == "__main__":
    main()
