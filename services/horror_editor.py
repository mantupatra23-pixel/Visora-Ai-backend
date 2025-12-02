# services/horror_editor.py
def schedule_jumps(timeline, level):
    # heuristics to add quick cuts for high tension
    out = []
    for item in timeline:
        dur = item['frames']
        if level=="high" and item['shot']=="jump_close":
            # break into micro cuts
            micro = max(3, int(dur/3))
            start = item['start']
            for i in range(3):
                out.append({"shot": item['shot'], "start": start, "frames": micro})
                start += micro
        else:
            out.append(item)
    return out

def build_edl_from_timeline(timeline):
    edl = []
    for idx,item in enumerate(timeline, start=1):
        edl.append({"event":idx, "shot":item['shot'], "start": item['start'], "frames": item['frames']})
    return edl
