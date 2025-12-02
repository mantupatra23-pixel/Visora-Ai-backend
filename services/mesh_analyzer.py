# services/mesh_analyzer.py
import numpy as np
import os, json
from pathlib import Path
import trimesh  # pip install trimesh

ROOT = Path(".").resolve()
TMP = ROOT / "tmp" ; TMP.mkdir(exist_ok=True)

def estimate_handle_point(mesh_path: str, sample_points:int=2000):
    """
    Loads mesh (fbx/glb/obj) via trimesh, samples points, computes PCA to find principal axis and
    returns centroid of highest-density cross-section as likely handle.
    """
    mesh = trimesh.load(mesh_path, force='mesh')
    if mesh.is_empty:
        return {"ok": False, "error": "empty_mesh"}
    pts = mesh.sample(sample_points)
    # PCA via covariance
    C = np.cov(pts.T)
    eigvals, eigvecs = np.linalg.eig(C)
    # principal axis vector
    principal = eigvecs[:, np.argmax(eigvals)]
    # project points onto principal axis -> select median slice
    proj = pts.dot(principal)
    mid = np.median(proj)
    mask = np.abs(proj - mid) < (np.ptp(proj) * 0.05)  # 5% width
    slice_pts = pts[mask]
    if len(slice_pts)==0:
        centroid = pts.mean(axis=0).tolist()
    else:
        centroid = slice_pts.mean(axis=0).tolist()
    return {"ok": True, "centroid": centroid, "principal_axis": principal.tolist()}

def save_handle_json(mesh_path: str, out_json: str = None):
    r = estimate_handle_point(mesh_path)
    if not out_json:
        out_json = str(TMP / (Path(mesh_path).stem + "_handle.json"))
    Path(out_json).write_text(json.dumps(r, indent=2))
    return out_json
