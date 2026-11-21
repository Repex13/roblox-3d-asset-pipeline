"""Headless local 3D generator using Hunyuan3D-2GP (RTX 4070 Ti 12GB + 32GB RAM offloading)."""
import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

import torch
from PIL import Image
from mmgp import offload

from hy3dgen.rembg import BackgroundRemover
from hy3dgen.shapegen import (
    DegenerateFaceRemover,
    FaceReducer,
    FloaterRemover,
    Hunyuan3DDiTFlowMatchingPipeline,
)
from hy3dgen.shapegen.pipelines import export_to_trimesh
from hy3dgen.texgen import Hunyuan3DPaintPipeline


def replace_property_getter(instance, property_name, new_getter):
    original_class = type(instance)
    original_property = getattr(original_class, property_name)
    custom_class = type(f"Custom{original_class.__name__}", (original_class,), {})
    new_property = property(new_getter, original_property.fset)
    setattr(custom_class, property_name, new_property)
    instance.__class__ = custom_class
    return instance


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Input image (RGBA preferred or RGB)")
    ap.add_argument("--outdir", required=True, help="Output folder")
    ap.add_argument("--name", default="model", help="Base filename")
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--octree", type=int, default=384)
    ap.add_argument("--guidance", type=float, default=5.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-faces", type=int, default=45000, help="Faces before texture paint")
    ap.add_argument("--profile", type=int, default=2, help="mmgp profile (2=HighRAM_LowVRAM, 3=LowRAM_HighVRAM)")
    ap.add_argument("--mini", action="store_true", help="Use faster 0.6B mini shape model")
    ap.add_argument("--no-tex", action="store_true", help="Skip texture generation")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    torch.set_default_device("cpu")

    model_path = "tencent/Hunyuan3D-2mini" if args.mini else "tencent/Hunyuan3D-2"
    subfolder = "hunyuan3d-dit-v2-mini" if args.mini else "hunyuan3d-dit-v2-0"

    t0 = time.time()
    print(f"[local3d] Loading shape pipeline: {model_path}/{subfolder}", flush=True)
    i23d_worker = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        model_path,
        subfolder=subfolder,
        use_safetensors=True,
        device="cuda",
    )
    replace_property_getter(i23d_worker, "_execution_device", lambda self: "cuda")

    pipe = offload.extract_models("i23d_worker", i23d_worker)
    texgen_worker = None
    if not args.no_tex:
        print("[local3d] Loading texture pipeline: tencent/Hunyuan3D-2", flush=True)
        texgen_worker = Hunyuan3DPaintPipeline.from_pretrained("tencent/Hunyuan3D-2")
        pipe.update(offload.extract_models("texgen_worker", texgen_worker))
        texgen_worker.models["multiview_model"].pipeline.vae.use_slicing = True

    kwargs = {}
    if args.profile < 5:
        kwargs["pinnedMemory"] = "i23d_worker/model"
    if args.profile not in (1, 3):
        kwargs["budgets"] = {"*": 2200}
    offload.profile(pipe, profile_no=args.profile, verboseLevel=1, **kwargs)

    img = Image.open(args.image)
    if img.mode != "RGBA":
        print("[local3d] Removing background...", flush=True)
        img = BackgroundRemover()(img.convert("RGB"))

    print(f"[local3d] Generating 3D shape (steps={args.steps}, octree={args.octree})...", flush=True)
    gen = torch.Generator().manual_seed(args.seed)
    outputs = i23d_worker(
        image=img,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance,
        generator=gen,
        octree_resolution=args.octree,
        num_chunks=200000,
        output_type="mesh",
    )
    mesh = export_to_trimesh(outputs)[0]
    print(f"[local3d] Raw mesh: {len(mesh.faces)} faces, {len(mesh.vertices)} verts", flush=True)

    mesh = FloaterRemover()(mesh)
    mesh = DegenerateFaceRemover()(mesh)
    white_path = outdir / f"{args.name}_white_high.glb"
    mesh.export(str(white_path))
    print(f"[local3d] Saved {white_path} ({len(mesh.faces)} faces)", flush=True)

    if texgen_worker is not None:
        if len(mesh.faces) > args.max_faces:
            print(f"[local3d] Reducing faces to {args.max_faces} before texture synthesis...", flush=True)
            mesh = FaceReducer()(mesh, max_facenum=args.max_faces)
        torch.cuda.empty_cache()
        print("[local3d] Generating multi-view PBR textures...", flush=True)
        textured = texgen_worker(mesh, img)
        tex_path = outdir / f"{args.name}_textured.glb"
        textured.export(str(tex_path), include_normals=True)
        print(f"[local3d] Saved {tex_path} in {time.time() - t0:.1f}s total", flush=True)


if __name__ == "__main__":
    main()
