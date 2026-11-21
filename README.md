# Roblox 3D asset pipeline

How I turn a concept render into a Roblox-ready 3D model on my own PC: a local GPU sculptor (Hunyuan3D-2GP on an RTX 4070 Ti) makes the high-poly mesh, then headless Blender scripts clean it up, cut it to Roblox's triangle budget, bake textures, rig and animate it, and render QA shots.

This repo is the workflow and the scripts only. No models, textures or renders are included.

## The flow

1. **Concept render.** Generate an uncropped, shadowless studio render of the asset on a plain `#E8E8EC` background.
2. **Clean reference.** Flood-fill the background away from the corners and center the cutout on a `1024×1024` RGBA image (`ref_clean_rgba.png`).
3. **Sculpt on the GPU.** Run `sculpt/run_local_3d.py` with the Hunyuan3D-2GP environment, using `--steps 40..45 --octree 384 --profile 2`. It writes a raw high-poly mesh (`*_white_high.glb`) and a textured one (`*_textured.glb`).
4. **Optimize in Blender, headless.** Run the matching script in `blender/`. It:
   - welds vertices until there are 0 holes and 0 non-manifold edges;
   - removes artifacts;
   - decimates to the Roblox triangle budget and scales to studs;
   - Smart-UV-unwraps and bakes `1024×1024` `color.png` and `normal.png`;
   - exports `*_roblox.glb` plus a `*_preview.blend`;
   - renders a Cycles hero shot and a 4-angle EEVEE turnaround for visual QA.
5. **Rig and animate** (characters and bosses). Build an armature, skin it and author clips, for example a 15-bone boss with idle, summon and slash animations.

## Scripts

| Script | Stage |
| --- | --- |
| `sculpt/run_local_3d.py` | Image → high-poly + textured GLB with Hunyuan3D-2GP on a local GPU |
| `blender/optimize_character_pack.py` | Weld, decimate, UV, bake, export and render for GPU-sculpted characters |
| `blender/optimize_kite_weapons.py` | The same pipeline tuned for weapons |
| `blender/build_hard_surface_pack.py` | Procedural hard-surface props built directly in Blender |
| `blender/build_roblox_gurren.py` | Single-model optimizer for a large mech |
| `blender/build_roblox_shadow_boss.py` | Mesh cleanup and texture bake for a boss model |
| `blender/inspect_raw.py`, `blender/inspect_raw_v2.py` | Raw mesh inspection before optimizing |
| `blender/rig_and_animate_boss.py` | 15-bone armature, skinning and three animation clips |

Run the Blender scripts headless:

```bash
"C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" --background --python blender/optimize_character_pack.py
```

**Paths:** the scripts use absolute paths near the top, with `C:/Users/YOU/...` as a placeholder. Point them at your own working folder, Hunyuan3D install and Blender before running.

## Requirements

- An NVIDIA GPU with 12 GB VRAM (built on an RTX 4070 Ti)
- [Hunyuan3D-2GP](https://github.com/deepbeepmeep/Hunyuan3D-2GP) in its own Python virtual environment
- Blender 5.3
- Roblox Studio for importing the exported `*_roblox.glb`

## Results

I built 22 Roblox-ready models with this pipeline. On a topology check of the final exports, every one was watertight, with 0 open edges and 0 non-manifold edges. All were within Roblox's 20,000-triangle limit per mesh (650 to 17,128 triangles).
