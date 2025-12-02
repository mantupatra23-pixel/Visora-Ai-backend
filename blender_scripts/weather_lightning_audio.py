# blender_scripts/weather_lightning_audio.py
import bpy, sys, json, os, random
from pathlib import Path
import wave, struct, math

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_job(path): return json.loads(Path(path).read_text())

def create_lightning_frames(job, outdir):
    cfg = job.get("config",{})
    flashes = cfg.get("lightning_flashes", 4)
    frames = job.get("frames", 240)
    frames_list = []
    for i in range(flashes):
        f = random.randint(5, frames-5)
        frames_list.append(f)
        # create point light and key energy
        light_data = bpy.data.lights.new(name=f"Lightning_{i}", type='POINT')
        light_obj = bpy.data.objects.new(name=f"Lightning_{i}", object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = (random.uniform(-10,10), random.uniform(-10,10), random.uniform(8,18))
        light_data.energy = 0
        light_obj.keyframe_insert(data_path="data.energy", frame=f-1)
        light_data.energy = cfg.get("light_energy",2000)
        light_obj.keyframe_insert(data_path="data.energy", frame=f)
        light_data.energy = 0
        light_obj.keyframe_insert(data_path="data.energy", frame=f+3)
    # write manifest
    mfile = Path(outdir)/f"{job['job_id']}_lightning_frames.json"
    mfile.write_text(json.dumps({"frames": frames_list}))
    return frames_list

def synth_thunder(frames_list, fps=24, out_wav=None):
    # Very simple synthetic thunder: low-frequency rumble timed after lightning with delay
    # We'll produce a mono WAV with a short low-frequency noise burst after each lightning
    if not out_wav: out_wav = "thunder_"+str(random.randint(1000,9999))+".wav"
    sample_rate = 22050
    duration = max(frames_list)/fps + 2.0
    n_samples = int(sample_rate * duration)
    data = []
    import random, math
    for i in range(n_samples):
        t = i / sample_rate
        val = 0.0
        # add bursts
        for f in frames_list:
            t_light = f / fps
            if 0 <= (t - t_light) < 1.0:
                # decaying noise weighted to low freq
                val += (1.0 - (t - t_light)) * (random.uniform(-1,1)) * 0.4 * math.exp(-2*(t - t_light))
        # mild lowpass by averaging
        data.append(max(-1.0, min(1.0, val)))
    # write wav
    wav_path = Path(out_wav).resolve()
    with wave.open(str(wav_path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for v in data:
            wf.writeframes(struct.pack('<h', int(v * 32767)))
    return str(wav_path)

def main(jobfile, outdir):
    job = load_job(jobfile)
    frames = create_lightning_frames(job, outdir)
    wav = synth_thunder(frames, fps=job.get("fps",24), out_wav=str(Path(outdir)/f"{job['job_id']}_thunder.wav"))
    print("thunder created:", wav)
    # write audio manifest for mux
    Path(outdir).joinpath(f"{job['job_id']}_audio_manifest.json").write_text(json.dumps({"thunder": wav}))
    return {"ok": True, "frames": frames, "thunder": wav}

if __name__=="__main__":
    argv = _args()
    if len(argv)<2:
        print("usage: blender --background --python weather_lightning_audio.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    res = main(jobfile, outdir)
    print(res)
