# services/advanced_bvh.py
"""
Create a more realistic BVH exporter using a full joint hierarchy.
This script expects a mapping 'skeleton_joints' as list of joints with parent-child structure.
We will write a BVH file with joint offsets and rotation channels.
"""
from pathlib import Path
import math, json

def write_bvh(frames3d, joint_names, parents, out_path, frame_time=1/30.0):
    """
    frames3d: list of dicts each with 'joints': {name:[x,y,z], ...}
    joint_names: ordered list of joint names (root first)
    parents: dict name->parent_name (root parent = None)
    """
    lines = []
    lines.append("HIERARCHY")
    def write_joint(name, indent=0):
        pad = "\t"*indent
        if parents.get(name) is None:
            lines.append(f"{pad}ROOT {name}")
        else:
            lines.append(f"{pad}JOINT {name}")
        lines.append(pad + "{")
        # find offset from parent using first frame
        parent = parents.get(name)
        if parent is None:
            off = frames3d[0]['joints'][name]
            lines.append(pad + f"\tOFFSET {off[0]:.6f} {off[1]:.6f} {off[2]:.6f}")
            lines.append(pad + "\tCHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation")
        else:
            ppos = frames3d[0]['joints'][parent]
            pos = frames3d[0]['joints'][name]
            offset = (pos[0]-ppos[0], pos[1]-ppos[1], pos[2]-ppos[2])
            lines.append(pad + f"\tOFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}")
            lines.append(pad + "\tCHANNELS 3 Zrotation Yrotation Xrotation")
        # children
        children = [j for j,p in parents.items() if p==name]
        if not children:
            lines.append(pad + "\tEnd Site")
            lines.append(pad + "\t{")
            lines.append(pad + "\t\tOFFSET 0.00 0.00 0.00")
            lines.append(pad + "\t}")
        else:
            for c in children:
                write_joint(c, indent+1)
        lines.append(pad + "}")
    # write full hierarchy starting from root(s)
    roots = [n for n in joint_names if parents.get(n) is None]
    for r in roots:
        write_joint(r, 0)
    # Motion
    lines.append("MOTION")
    lines.append(f"Frames: {len(frames3d)}")
    lines.append(f"Frame Time: {frame_time:.6f}")
    # frame data
    for f in frames3d:
        vals = []
        for name in joint_names:
            parent = parents.get(name)
            p = f['joints'][name]
            if parent is None:
                vals += [f"{p[0]:.6f}", f"{p[1]:.6f}", f"{p[2]:.6f}", "0.0","0.0","0.0"]
            else:
                # rotations unknown here; placeholder zeros
                vals += ["0.0","0.0","0.0"]
        lines.append(" ".join(vals))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        fh.write("\n".join(lines))
    return {"ok": True, "out": out_path}
