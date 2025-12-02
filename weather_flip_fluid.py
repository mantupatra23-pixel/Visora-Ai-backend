from pathlib import Path
# ensure optimize module path
SCRIPT_DIR = Path(__file__).parent
import sys
sys.path.append(str(SCRIPT_DIR))
# import helper
try:
    from optimize_render import configure_cycles_gpu, set_render_resolution, set_output_format_png
    # quick auto-configure: prefer OptiX -> CUDA -> CPU
    configure_cycles_gpu(device_type='OPTIX', tile_size_gpu=256, use_gpu=True)
    set_render_resolution(1920,1080,100)
    set_output_format_png()
except Exception as e:
    print("Optimize helper not applied:", e)
