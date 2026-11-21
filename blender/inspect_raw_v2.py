import bpy, bmesh, math, os
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
glb_path = r"C:\Users\YOU\Roblox-3D-Work\shadow_flame_boss\local_out_v2\shadow_boss_v2_textured.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print(f"Mesh count: {len(meshes)}")
for obj in meshes:
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    tris = sum(max(1, len(f.verts) - 2) for f in bm.faces)
    open_edges = sum(1 for e in bm.edges if e.is_boundary)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    mat_world = obj.matrix_world
    world_verts = [mat_world @ v.co for v in bm.verts]
    xs = [v.x for v in world_verts]
    ys = [v.y for v in world_verts]
    zs = [v.z for v in world_verts]
    min_z, max_z = min(zs), max(zs)
    print(f"OBJ={obj.name} verts={len(bm.verts)} faces={len(bm.faces)} tris={tris} open_edges={open_edges} non_manifold={non_manifold}")
    print(f"  BBOX X=[{min(xs):.4f}, {max(xs):.4f}] Y=[{min(ys):.4f}, {max(ys):.4f}] Z=[{min_z:.4f}, {max_z:.4f}]")
    # Z-slice histogram near bottom (lowest 15% of height)
    h = max_z - min_z
    for step in range(10):
        z0 = min_z + (step / 10.0) * (h * 0.15)
        z1 = min_z + ((step + 1) / 10.0) * (h * 0.15)
        slice_v = [v for v in world_verts if z0 <= v.z <= z1]
        if slice_v:
            sx = max(v.x for v in slice_v) - min(v.x for v in slice_v)
            sy = max(v.y for v in slice_v) - min(v.y for v in slice_v)
            print(f"  Z[{z0:.4f}..{z1:.4f}]: count={len(slice_v):4d} spanX={sx:.3f} spanY={sy:.3f}")
    # Disconnected components
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    open_after = sum(1 for e in bm.edges if e.is_boundary)
    nm_after = sum(1 for e in bm.edges if not e.is_manifold)
    print(f"  After 1e-5 weld: verts={len(bm.verts)} open_edges={open_after} non_manifold={nm_after}")
    bm.free()

for img in bpy.data.images:
    print(f"IMG={img.name} size={list(img.size)} channels={img.channels}")

# Render quick 6-view sheet with Cycles/EEVEE
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.18, 0.18, 0.22, 1.0)
    bg.inputs[1].default_value = 1.2

# Sun light
ldata = bpy.data.lights.new("Sun", type='SUN')
ldata.energy = 3.0
lobj = bpy.data.objects.new("Sun", ldata)
scene.collection.objects.link(lobj)
lobj.rotation_euler = (math.radians(45), 0, math.radians(35))

# Compute overall center & size
all_pts = []
for obj in meshes:
    for v in obj.data.vertices:
        all_pts.append(obj.matrix_world @ v.co)
cx = 0.5 * (min(p.x for p in all_pts) + max(p.x for p in all_pts))
cy = 0.5 * (min(p.y for p in all_pts) + max(p.y for p in all_pts))
cz = 0.5 * (min(p.z for p in all_pts) + max(p.z for p in all_pts))
span = max(max(p.x for p in all_pts)-min(p.x for p in all_pts),
           max(p.y for p in all_pts)-min(p.y for p in all_pts),
           max(p.z for p in all_pts)-min(p.z for p in all_pts))
center = Vector((cx, cy, cz))

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 50
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

out_dir = r"C:\Users\YOU\Roblox-3D-Work\shadow_flame_boss\inspect_tiles_v2"
os.makedirs(out_dir, exist_ok=True)
views = [
    ("front", (0, -1.8*span, 0)),
    ("back", (0, 1.8*span, 0)),
    ("left", (-1.8*span, 0, 0)),
    ("right", (1.8*span, 0, 0)),
    ("iso", (1.3*span, -1.3*span, 0.7*span)),
    ("top", (0, -0.3*span, 1.8*span)),
]
for idx, (name, off) in enumerate(views):
    cam.location = center + Vector(off)
    direction = (center - cam.location).normalized()
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(out_dir, f"{idx}_{name}.png")
    bpy.ops.render.render(write_still=True)
print("RENDER_DONE")

