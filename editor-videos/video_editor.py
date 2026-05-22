#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║          AUTO VIDEO EDITOR  —  by Senior Dev             ║
║   Edición automatizada de video con acciones CapCut     ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import math
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# ──────────────────────────────────────────────
# COLORES ANSI para terminal
# ──────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BG_DARK= "\033[40m"

def print_banner():
    print(f"""
{C.CYAN}{C.BOLD}
  ╔══════════════════════════════════════════════════════════════╗
  ║   ██╗   ██╗██╗██████╗ ███████╗ ██████╗     ███████╗██████╗  ║
  ║   ██║   ██║██║██╔══██╗██╔════╝██╔═══██╗    ██╔════╝██╔══██╗ ║
  ║   ██║   ██║██║██║  ██║█████╗  ██║   ██║    █████╗  ██║  ██║ ║
  ║   ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║    ██╔══╝  ██║  ██║ ║
  ║    ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝    ███████╗██████╔╝ ║
  ║     ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝     ╚══════╝╚═════╝  ║
  ║                                                              ║
  ║         🎬  Auto Video Editor  —  Senior Dev Edition        ║
  ╚══════════════════════════════════════════════════════════════╝
{C.RESET}""")

def print_section(title: str):
    width = 60
    print(f"\n{C.CYAN}{'─'*width}{C.RESET}")
    print(f"{C.BOLD}{C.YELLOW}  {title}{C.RESET}")
    print(f"{C.CYAN}{'─'*width}{C.RESET}")

def print_ok(msg):    print(f"  {C.GREEN}✔  {C.RESET}{msg}")
def print_info(msg):  print(f"  {C.BLUE}ℹ  {C.RESET}{msg}")
def print_warn(msg):  print(f"  {C.YELLOW}⚠  {C.RESET}{msg}")
def print_err(msg):   print(f"  {C.RED}✘  {C.RESET}{msg}")
def print_step(n,t):  print(f"  {C.MAGENTA}[{n}]{C.RESET} {t}")

def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{C.DIM}{default}{C.RESET}]" if default else ""
    val = input(f"  {C.CYAN}▶{C.RESET} {prompt}{suffix}: ").strip()
    return val if val else default

def ask_yn(prompt: str, default: bool = True) -> bool:
    opts = f"{C.GREEN}S{C.RESET}/{C.RED}n{C.RESET}" if default else f"{C.GREEN}s{C.RESET}/{C.RED}N{C.RESET}"
    val = ask(f"{prompt} ({opts})", "s" if default else "n").lower()
    return val in ("s", "si", "yes", "y", "")

def ask_int(prompt: str, default: int, mn: int = 1, mx: int = 9999) -> int:
    while True:
        val = ask(prompt, str(default))
        try:
            n = int(val)
            if mn <= n <= mx:
                return n
            print_warn(f"Ingresa un número entre {mn} y {mx}")
        except ValueError:
            print_warn("Ingresa un número válido")

def ask_float(prompt: str, default: float, mn: float = 0.1) -> float:
    while True:
        val = ask(prompt, str(default))
        try:
            n = float(val)
            if n >= mn:
                return n
            print_warn(f"Ingresa un valor mayor a {mn}")
        except ValueError:
            print_warn("Ingresa un número válido")

def progress_bar(current: int, total: int, label: str = "", width: int = 40):
    pct = current / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r  {C.CYAN}[{bar}]{C.RESET} {pct*100:5.1f}% {C.DIM}{label}{C.RESET}", end="", flush=True)

# ──────────────────────────────────────────────
# FFMPEG HELPERS
# ──────────────────────────────────────────────
def ffprobe(path: str) -> dict:
    """Obtiene metadata del video."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        info = {"path": path, "duration": 0, "width": 0, "height": 0,
                "fps": 30, "has_audio": False, "size_mb": 0}
        fmt = data.get("format", {})
        info["duration"] = float(fmt.get("duration", 0))
        info["size_mb"] = int(fmt.get("size", 0)) / 1024 / 1024
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                info["width"] = s.get("width", 0)
                info["height"] = s.get("height", 0)
                fps_str = s.get("r_frame_rate", "30/1")
                try:
                    n, d = fps_str.split("/")
                    info["fps"] = round(float(n) / float(d), 2)
                except Exception:
                    info["fps"] = 30
            elif s.get("codec_type") == "audio":
                info["has_audio"] = True
        return info
    except Exception as e:
        raise RuntimeError(f"Error leyendo {path}: {e}")

def run_ffmpeg(args: list, desc: str = "") -> bool:
    """Ejecuta ffmpeg con barra de progreso simulada."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    if desc:
        print_info(f"Procesando: {C.DIM}{desc}{C.RESET}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            print_err(f"ffmpeg error: {proc.stderr[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print_err("Timeout: el proceso tardó demasiado")
        return False
    except Exception as e:
        print_err(f"Error ejecutando ffmpeg: {e}")
        return False

def ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path

def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def fmt_dur(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

# ──────────────────────────────────────────────
# TRANSICIONES
# ──────────────────────────────────────────────
TRANSITIONS = {
    "1": ("fade",       "Fade (fundido a negro)",    0.5),
    "2": ("crossfade",  "Crossfade (disolvencia)",   0.5),
    "3": ("slide_left", "Slide Left (deslizar izq)", 0.4),
    "4": ("slide_right","Slide Right (deslizar der)",0.4),
    "5": ("zoom",       "Zoom In",                   0.4),
    "6": ("none",       "Sin transición",            0.0),
}

def apply_transition(in_file: str, out_file: str, trans_type: str, duration: float = 0.5) -> bool:
    """Aplica transición al inicio de un clip."""
    if trans_type == "none":
        return run_ffmpeg(["-i", in_file, "-c", "copy", out_file], "Sin transición")

    if trans_type == "fade":
        dur = duration
        filter_v = f"fade=t=in:st=0:d={dur}"
        filter_a = f"afade=t=in:st=0:d={dur}" 
        cmd = ["-i", in_file, "-vf", filter_v, "-af", filter_a,
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "aac", out_file]
        return run_ffmpeg(cmd, f"Fade in {dur}s")

    elif trans_type == "crossfade":
        # Crossfade simple con fade
        dur = duration
        filter_v = f"fade=t=in:st=0:d={dur},fade=t=out:st=0:d={dur}"
        cmd = ["-i", in_file, "-vf", filter_v,
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "copy", out_file]
        return run_ffmpeg(cmd, "Crossfade")

    elif trans_type in ("slide_left", "slide_right"):
        w = 1920
        direction = -1 if trans_type == "slide_left" else 1
        dur = duration
        filter_v = (
            f"[0:v]split[bg][fg];"
            f"[bg]scale={w}:-1[bg_s];"
            f"[fg]scale={w}:-1,crop={w}:ih:0:0[fg_c];"
            f"[bg_s][fg_c]overlay=x='if(lt(t,{dur}),{direction}*{w}*(1-t/{dur}),0)':y=0[v]"
        )
        cmd = ["-i", in_file, "-filter_complex", filter_v, "-map", "[v]",
               "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "copy", out_file]
        return run_ffmpeg(cmd, f"Slide {trans_type}")

    elif trans_type == "zoom":
        dur = duration
        filter_v = f"zoompan=z='if(lt(it,{dur*25}),1+0.5*it/({dur*25}),1)':d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1280x720"
        cmd = ["-i", in_file, "-vf", filter_v,
               "-c:v", "libx264", "-preset", "fast", "-crf", "23",
               "-c:a", "copy", out_file]
        return run_ffmpeg(cmd, "Zoom in")

    return run_ffmpeg(["-i", in_file, "-c", "copy", out_file], "Copia directa")

# ──────────────────────────────────────────────
# SUBTÍTULOS
# ──────────────────────────────────────────────
def generate_subtitles(video_path: str, srt_path: str, text: str = None, 
                        auto_lines: bool = False, duration: float = 0):
    """Genera un archivo SRT básico."""
    if text:
        # Subtítulo manual
        words = text.split()
        lines = []
        chunk = 8
        t = 0
        step = max(duration / max(len(words)//chunk, 1), 2) if duration > 0 else 3
        for i in range(0, len(words), chunk):
            line_text = " ".join(words[i:i+chunk])
            t_end = t + step
            start = fmt_srt_time(t)
            end = fmt_srt_time(t_end)
            lines.append(f"{len(lines)+1}\n{start} --> {end}\n{line_text}\n")
            t = t_end
    else:
        # Subtítulo placeholder
        lines = [f"1\n00:00:00,000 --> {fmt_srt_time(duration or 5)}\n[Subtítulo automático]\n"]

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print_ok(f"SRT generado: {Path(srt_path).name}")

def fmt_srt_time(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def burn_subtitles(in_file: str, srt_file: str, out_file: str,
                   font_size: int = 24, color: str = "white",
                   position: str = "bottom") -> bool:
    """Quema subtítulos en el video."""
    y_pos = "h-th-40" if position == "bottom" else "40"
    # Escape path para ffmpeg
    srt_escaped = srt_file.replace("\\", "/").replace(":", "\\:")
    filter_v = (
        f"subtitles='{srt_escaped}'"
        f":force_style='FontSize={font_size},PrimaryColour=&H00{color_to_hex(color)}&,"
        f"Outline=2,Shadow=1,Alignment=2'"
    )
    cmd = ["-i", in_file, "-vf", filter_v,
           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
           "-c:a", "copy", out_file]
    return run_ffmpeg(cmd, "Quemando subtítulos")

def color_to_hex(color: str) -> str:
    colors = {"white":"FFFFFF","yellow":"00FFFF","red":"0000FF",
               "blue":"FF0000","green":"00FF00","black":"000000"}
    return colors.get(color.lower(), "FFFFFF")

# ──────────────────────────────────────────────
# ACCIONES CAPCUT
# ──────────────────────────────────────────────
CAPCUT_ACTIONS = {
    "1":  ("speed_up",    "Acelerar video (0.5x – 4x)"),
    "2":  ("slow_mo",     "Cámara lenta (0.25x – 0.9x)"),
    "3":  ("brightness",  "Ajustar brillo"),
    "4":  ("contrast",    "Ajustar contraste"),
    "5":  ("saturation",  "Ajustar saturación"),
    "6":  ("crop",        "Recortar / cambiar aspecto (16:9, 9:16, 1:1)"),
    "7":  ("rotate",      "Rotar video (90°, 180°, 270°)"),
    "8":  ("flip",        "Voltear video (H / V)"),
    "9":  ("blur_bg",     "Blur de fondo (para 9:16 con barras)"),
    "10": ("text_overlay","Agregar texto sobre video"),
    "11": ("music",       "Agregar música de fondo (fade in/out)"),
    "12": ("volume",      "Ajustar volumen de audio"),
    "13": ("mute",        "Silenciar audio"),
    "14": ("vignette",    "Efecto viñeta"),
    "15": ("sharpen",     "Afilar imagen"),
    "16": ("denoise",     "Reducir ruido"),
    "17": ("stabilize",   "Estabilización básica"),
    "18": ("color_grade", "Color grading (cinematico/frio/calido/byn)"),
    "19": ("reverse",     "Invertir video (rebobinar)"),
    "20": ("none",        "Sin acciones adicionales"),
}

def apply_capcut_action(in_file: str, out_file: str, action: str, params: dict) -> bool:
    """Aplica acción estilo CapCut al video."""

    if action == "speed_up" or action == "slow_mo":
        speed = params.get("speed", 2.0)
        vf = f"setpts={1/speed:.4f}*PTS"
        af = f"atempo={min(max(speed, 0.5), 100.0):.2f}" if 0.5 <= speed <= 2.0 else ""
        # Para velocidades extremas encadenar atempo
        if speed > 2.0:
            steps = []
            s = speed
            while s > 2.0:
                steps.append("atempo=2.0")
                s /= 2.0
            steps.append(f"atempo={s:.2f}")
            af = ",".join(steps)
        elif speed < 0.5:
            steps = []
            s = speed
            while s < 0.5:
                steps.append("atempo=0.5")
                s /= 0.5
            steps.append(f"atempo={s:.2f}")
            af = ",".join(steps)
        cmd = ["-i", in_file, "-vf", vf]
        if af:
            cmd += ["-af", af]
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", out_file]
        return run_ffmpeg(cmd, f"Velocidad {speed}x")

    elif action in ("brightness", "contrast", "saturation"):
        b = params.get("brightness", 0)
        c = params.get("contrast", 1)
        s = params.get("saturation", 1)
        vf = f"eq=brightness={b}:contrast={c}:saturation={s}"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], f"Ajuste {action}")

    elif action == "crop":
        ratio = params.get("ratio", "16:9")
        ratios = {
            "16:9": "iw:iw*9/16",
            "9:16": "ih*9/16:ih",
            "1:1":  "min(iw\\,ih):min(iw\\,ih)",
            "4:3":  "iw:iw*3/4",
        }
        crop = ratios.get(ratio, ratios["16:9"])
        vf = f"crop={crop},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], f"Crop {ratio}")

    elif action == "rotate":
        deg = params.get("degrees", 90)
        transpose_map = {90: "transpose=1", 180: "transpose=2,transpose=2", 270: "transpose=2"}
        vf = transpose_map.get(deg, "transpose=1")
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], f"Rotar {deg}°")

    elif action == "flip":
        direction = params.get("direction", "h")
        vf = "hflip" if direction == "h" else "vflip"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], f"Flip {direction}")

    elif action == "blur_bg":
        # Para formato 9:16 con fondo blureado
        vf = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:5[bg];"
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        return run_ffmpeg(["-i", in_file, "-filter_complex", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], "Blur background 9:16")

    elif action == "text_overlay":
        text = params.get("text", "Mi Video")
        x = params.get("x", "(w-text_w)/2")
        y = params.get("y", "h-th-40")
        fs = params.get("fontsize", 48)
        color = params.get("color", "white")
        vf = (f"drawtext=text='{text}':fontsize={fs}:fontcolor={color}:"
              f"x={x}:y={y}:box=1:boxcolor=black@0.5:boxborderw=5")
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], "Texto superpuesto")

    elif action == "music":
        music_file = params.get("music_file", "")
        if not os.path.exists(music_file):
            print_warn("Archivo de música no encontrado, copiando sin cambios")
            return run_ffmpeg(["-i", in_file, "-c", "copy", out_file], "Sin música")
        vol = params.get("volume", 0.3)
        fade_dur = params.get("fade", 2.0)
        # Obtener duración del video
        info = ffprobe(in_file)
        dur = info["duration"]
        af = (f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2,"
              f"afade=t=in:st=0:d={fade_dur},afade=t=out:st={dur-fade_dur}:d={fade_dur}")
        return run_ffmpeg(["-i", in_file, "-stream_loop", "-1", "-i", music_file,
                           "-filter_complex", af,
                           "-c:v", "copy", "-c:a", "aac", "-shortest", out_file], "Música de fondo")

    elif action == "volume":
        vol = params.get("volume", 1.5)
        return run_ffmpeg(["-i", in_file, "-af", f"volume={vol}",
                           "-c:v", "copy", "-c:a", "aac", out_file], f"Volumen {vol}x")

    elif action == "mute":
        return run_ffmpeg(["-i", in_file, "-an", "-c:v", "copy", out_file], "Silenciar")

    elif action == "vignette":
        vf = "vignette=PI/4"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], "Viñeta")

    elif action == "sharpen":
        vf = "unsharp=5:5:1.0:5:5:0.0"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], "Sharpening")

    elif action == "denoise":
        vf = "hqdn3d=4:3:6:4.5"
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], "Reducción ruido")

    elif action == "stabilize":
        # Estabilización en 2 pasadas
        vectors = out_file.replace(".mp4", "_vectors.trf")
        ok1 = run_ffmpeg(["-i", in_file, "-vf", f"vidstabdetect=result={vectors}",
                          "-f", "null", "-"], "Detectando movimiento")
        if not ok1:
            return run_ffmpeg(["-i", in_file, "-c", "copy", out_file], "Copia")
        ok2 = run_ffmpeg(["-i", in_file, "-vf", f"vidstabtransform=input={vectors},unsharp=5:5:0.8",
                          "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                          "-c:a", "copy", out_file], "Estabilizando")
        if os.path.exists(vectors):
            os.remove(vectors)
        return ok2

    elif action == "color_grade":
        grade = params.get("grade", "cinematico")
        grades = {
            "cinematico": "curves=r='0 0 0.5 0.4 1 0.9':g='0 0 0.5 0.48 1 0.95':b='0 0.05 0.5 0.5 1 1'",
            "frio":       "colorbalance=rs=-0.1:gs=-0.05:bs=0.2",
            "calido":     "colorbalance=rs=0.2:gs=0.05:bs=-0.1",
            "byn":        "hue=s=0",
            "vintage":    "curves=r='0 0.1 0.5 0.55 1 0.9':g='0 0 0.5 0.5 1 0.9':b='0 0.05 0.5 0.45 1 0.85'",
        }
        vf = grades.get(grade, grades["cinematico"])
        return run_ffmpeg(["-i", in_file, "-vf", vf,
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "copy", out_file], f"Color grade: {grade}")

    elif action == "reverse":
        return run_ffmpeg(["-i", in_file, "-vf", "reverse", "-af", "areverse",
                           "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                           "-c:a", "aac", out_file], "Invertir video")

    else:  # none
        return run_ffmpeg(["-i", in_file, "-c", "copy", out_file], "Copia directa")

# ──────────────────────────────────────────────
# ESTIMADOR DE TIEMPO
# ──────────────────────────────────────────────
def estimate_time(config: dict) -> float:
    """Estima tiempo total de procesamiento en segundos."""
    base = 0
    total_dur = config.get("total_source_duration", 0)
    n_clips = config.get("n_clips", 1)
    has_transitions = config.get("has_transitions", False)
    has_subtitles = config.get("has_subtitles", False)
    n_actions = config.get("n_actions", 0)
    mode = config.get("mode", "split")

    # Base: ~0.3s de proceso por segundo de video (máquina media)
    factor = 0.3
    base = total_dur * factor

    if has_transitions:
        base += n_clips * 8   # ~8s por transición
    if has_subtitles:
        base += n_clips * 15  # ~15s por clip con subtítulos quemados
    base += n_clips * n_actions * 10  # ~10s por acción por clip
    if mode == "merge":
        base += 5  # concat rápido

    return max(base, 5)

def print_estimate(config: dict):
    est = estimate_time(config)
    print_section("⏱  ESTIMADO DE TIEMPO")
    print_info(f"Clips a procesar    : {C.BOLD}{config.get('n_clips', 1)}{C.RESET}")
    print_info(f"Duración fuente     : {C.BOLD}{fmt_dur(config.get('total_source_duration',0))}{C.RESET}")
    print_info(f"Transiciones        : {C.BOLD}{'Sí' if config.get('has_transitions') else 'No'}{C.RESET}")
    print_info(f"Subtítulos          : {C.BOLD}{'Sí' if config.get('has_subtitles') else 'No'}{C.RESET}")
    print_info(f"Acciones CapCut     : {C.BOLD}{config.get('n_actions', 0)} por clip{C.RESET}")
    print()
    if est < 30:
        lvl = f"{C.GREEN}Rápido"
    elif est < 120:
        lvl = f"{C.YELLOW}Moderado"
    else:
        lvl = f"{C.RED}Largo"
    print(f"  {C.BOLD}Tiempo estimado:{C.RESET} {lvl} — ~{fmt_dur(est)}{C.RESET}")
    print()

# ──────────────────────────────────────────────
# MÓDULO 1: DIVIDIR VIDEO LARGO EN CLIPS
# ──────────────────────────────────────────────
def module_split_video(output_dir: str):
    print_section("🎬  DIVIDIR VIDEO EN CLIPS")

    # 1. Seleccionar video fuente
    src = ask("Ruta del video fuente").strip('"').strip("'")
    if not os.path.exists(src):
        print_err(f"Archivo no encontrado: {src}")
        return

    info = ffprobe(src)
    print_ok(f"Video: {Path(src).name}")
    print_info(f"Duración: {fmt_dur(info['duration'])} | "
               f"Resolución: {info['width']}x{info['height']} | "
               f"FPS: {info['fps']} | Audio: {'Sí' if info['has_audio'] else 'No'}")

    # 2. ¿Cuántos clips y de qué duración?
    print_section("📐  CONFIGURACIÓN DE CLIPS")
    mode = ask("Modo: (1) cantidad de clips  (2) duración fija por clip", "1")
    if mode == "1":
        n_clips = ask_int("¿Cuántos clips?", default=5, mn=1, mx=500)
        clip_dur = info["duration"] / n_clips
        print_info(f"Duración por clip: ~{fmt_dur(clip_dur)}")
    else:
        clip_dur = ask_float("Duración de cada clip (segundos)", default=30.0)
        n_clips = max(1, int(info["duration"] / clip_dur))
        print_info(f"Se generarán ~{n_clips} clips de {fmt_dur(clip_dur)} c/u")

    # 3. Sondeo por clip
    global_transition = None
    global_subtitles  = None
    global_actions    = []
    use_global = ask_yn("¿Usar misma configuración para todos los clips?", True)

    if use_global:
        global_transition, global_subtitles, global_actions = sondeo_clip_config(info["has_audio"])

    # 4. Estimado
    cfg = {
        "n_clips": n_clips,
        "total_source_duration": info["duration"],
        "has_transitions": bool(global_transition and global_transition != "none"),
        "has_subtitles": bool(global_subtitles),
        "n_actions": len(global_actions),
        "mode": "split",
    }
    print_estimate(cfg)
    if not ask_yn("¿Continuar con el procesamiento?", True):
        print_info("Operación cancelada")
        return

    # 5. Procesar clips
    out_folder = ensure_dir(os.path.join(output_dir, f"clips_{datetime.now().strftime('%H%M%S')}"))
    print_section("⚙️   PROCESANDO CLIPS")
    start_t = time.time()
    success = 0

    for i in range(n_clips):
        t_start = i * clip_dur
        t_dur   = min(clip_dur, info["duration"] - t_start)
        if t_dur <= 0:
            break

        clip_name = f"clip_{i+1:03d}.mp4"
        tmp_clip  = os.path.join(out_folder, f"_tmp_{clip_name}")
        fin_clip  = os.path.join(out_folder, clip_name)

        print(f"\n{C.BOLD}  ── Clip {i+1}/{n_clips} ──{C.RESET}  {C.DIM}desde {fmt_time(t_start)} dur {fmt_dur(t_dur)}{C.RESET}")

        # Config individual o global
        if not use_global:
            print_info(f"Configuración para clip {i+1}:")
            trans, subs, actions = sondeo_clip_config(info["has_audio"])
        else:
            trans, subs, actions = global_transition, global_subtitles, global_actions

        # Extraer clip base
        ok = run_ffmpeg([
            "-ss", str(t_start), "-i", src,
            "-t", str(t_dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", tmp_clip
        ], f"Extrayendo clip {i+1}")

        if not ok:
            print_err(f"Error extrayendo clip {i+1}")
            continue

        current = tmp_clip
        step = 0

        # Aplicar acciones CapCut
        for action_cfg in actions:
            step += 1
            action_name = action_cfg["action"]
            action_params = action_cfg.get("params", {})
            next_file = os.path.join(out_folder, f"_tmp_{i}_{step}_{action_name}.mp4")
            ok = apply_capcut_action(current, next_file, action_name, action_params)
            if ok and os.path.exists(next_file):
                if current != tmp_clip and os.path.exists(current):
                    os.remove(current)
                current = next_file
            else:
                print_warn(f"Acción {action_name} falló, continuando...")

        # Aplicar transición
        if trans and trans != "none":
            step += 1
            trans_file = os.path.join(out_folder, f"_tmp_{i}_{step}_trans.mp4")
            apply_transition(current, trans_file, trans)
            if os.path.exists(trans_file):
                if current != tmp_clip and os.path.exists(current):
                    os.remove(current)
                current = trans_file

        # Aplicar subtítulos
        if subs:
            step += 1
            srt_path = os.path.join(out_folder, f"_sub_{i+1}.srt")
            sub_params = subs if isinstance(subs, dict) else {}
            generate_subtitles(
                current, srt_path,
                text=sub_params.get("text"),
                duration=t_dur
            )
            sub_file = os.path.join(out_folder, f"_tmp_{i}_{step}_sub.mp4")
            ok = burn_subtitles(current, srt_path, sub_file,
                                font_size=sub_params.get("fontsize", 28),
                                color=sub_params.get("color", "white"),
                                position=sub_params.get("position", "bottom"))
            if ok and os.path.exists(sub_file):
                if current != tmp_clip and os.path.exists(current):
                    os.remove(current)
                current = sub_file

        # Mover al nombre final
        shutil.move(current, fin_clip)
        # Limpiar temporal base
        if os.path.exists(tmp_clip):
            os.remove(tmp_clip)

        elapsed = time.time() - start_t
        avg = elapsed / (i + 1)
        remaining = avg * (n_clips - i - 1)
        print_ok(f"Clip {i+1} guardado → {clip_name}  "
                 f"{C.DIM}(restante ~{fmt_dur(remaining)}){C.RESET}")
        success += 1

    # Limpiar temporales sobrantes
    for f in Path(out_folder).glob("_tmp_*"):
        f.unlink(missing_ok=True)

    total_t = time.time() - start_t
    print_section("✅  RESUMEN SPLIT")
    print_ok(f"Clips generados: {success}/{n_clips}")
    print_ok(f"Carpeta: {out_folder}")
    print_ok(f"Tiempo total: {fmt_dur(total_t)}")

# ──────────────────────────────────────────────
# MÓDULO 2: UNIR CLIPS EN VIDEO LARGO
# ──────────────────────────────────────────────
def module_merge_videos(output_dir: str):
    print_section("🔗  UNIR VIDEOS EN UNO LARGO")

    # 1. Recolectar videos
    videos = collect_videos("fuente para unir")
    if not videos:
        return

    total_dur = sum(ffprobe(v)["duration"] for v in videos if os.path.exists(v))
    print_info(f"Videos a unir: {len(videos)} | Duración total: ~{fmt_dur(total_dur)}")

    # 2. Orden
    if len(videos) > 1:
        if ask_yn("¿Cambiar el orden de los videos?", False):
            videos = reorder_list(videos)

    # 3. Sondeo de transiciones entre clips
    add_trans = ask_yn("¿Agregar transiciones entre clips?", False)
    trans_type = "none"
    if add_trans:
        print_transitions_menu()
        trans_key = ask("Tipo de transición para todas las uniones", "1")
        trans_type = TRANSITIONS.get(trans_key, TRANSITIONS["6"])[0]

    # 4. Subtítulos
    add_subs = ask_yn("¿Agregar subtítulos al video final?", False)
    subs_cfg = {}
    if add_subs:
        subs_cfg = ask_subtitle_config()

    # 5. Acciones CapCut para el video final
    add_actions = ask_yn("¿Aplicar acciones CapCut al video final?", False)
    actions = []
    if add_actions:
        actions = ask_capcut_actions()

    # 6. Normalizar videos (mismo codec, resolución)
    normalize = ask_yn("¿Normalizar resolución de todos los videos? (recomendado)", True)

    # 7. Nombre de salida
    out_name = ask("Nombre del archivo de salida (sin extensión)", "video_unido")
    out_file  = os.path.join(output_dir, f"{out_name}.mp4")

    # 8. Estimado
    cfg = {
        "n_clips": len(videos),
        "total_source_duration": total_dur,
        "has_transitions": add_trans,
        "has_subtitles": add_subs,
        "n_actions": len(actions),
        "mode": "merge",
    }
    print_estimate(cfg)
    if not ask_yn("¿Iniciar el procesamiento?", True):
        print_info("Cancelado")
        return

    print_section("⚙️   PROCESANDO")
    tmp_dir = ensure_dir(os.path.join(output_dir, "_tmp_merge"))
    start_t = time.time()
    processed = []

    for i, vid in enumerate(videos):
        print(f"\n  {C.BOLD}── Video {i+1}/{len(videos)}: {Path(vid).name} ──{C.RESET}")
        tmp_vid = os.path.join(tmp_dir, f"v{i:03d}_norm.mp4")

        if normalize:
            ok = run_ffmpeg([
                "-i", vid,
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                       "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", "-ar", "44100", "-ac", "2",
                tmp_vid
            ], f"Normalizando {Path(vid).name}")
        else:
            ok = run_ffmpeg(["-i", vid, "-c", "copy", tmp_vid], "Copiando")

        if ok:
            processed.append(tmp_vid)
            print_ok(f"Listo: {Path(vid).name}")
        else:
            print_warn(f"Omitiendo {Path(vid).name}")

    if not processed:
        print_err("No se pudo procesar ningún video")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    # Concat
    print_info("Uniendo videos...")
    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")

    merged_tmp = os.path.join(tmp_dir, "merged_raw.mp4")
    ok = run_ffmpeg(["-f", "concat", "-safe", "0",
                     "-i", concat_list,
                     "-c", "copy", merged_tmp], "Concatenando")

    if not ok:
        print_err("Error al unir videos")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    current = merged_tmp

    # Aplicar acciones al video unido
    for j, ac in enumerate(actions):
        next_f = os.path.join(tmp_dir, f"merged_{j}_{ac['action']}.mp4")
        ok = apply_capcut_action(current, next_f, ac["action"], ac.get("params", {}))
        if ok and os.path.exists(next_f):
            current = next_f

    # Subtítulos finales
    if add_subs:
        info_merged = ffprobe(current)
        srt_path = os.path.join(tmp_dir, "final.srt")
        generate_subtitles(current, srt_path,
                           text=subs_cfg.get("text"),
                           duration=info_merged["duration"])
        sub_out = os.path.join(tmp_dir, "merged_sub.mp4")
        ok = burn_subtitles(current, srt_path, sub_out,
                            font_size=subs_cfg.get("fontsize", 28),
                            color=subs_cfg.get("color", "white"))
        if ok:
            current = sub_out

    shutil.move(current, out_file)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    total_t = time.time() - start_t
    print_section("✅  RESUMEN MERGE")
    print_ok(f"Videos unidos: {len(processed)}")
    print_ok(f"Archivo final: {out_file}")
    print_ok(f"Tiempo total: {fmt_dur(total_t)}")

# ──────────────────────────────────────────────
# MÓDULO 3: GENERAR CLIPS DE MÚLTIPLES VIDEOS
# ──────────────────────────────────────────────
def module_multi_clips(output_dir: str):
    print_section("🎞️   GENERAR CLIPS DE MÚLTIPLES VIDEOS")

    videos = collect_videos("para extraer clips")
    if not videos:
        return

    print_section("📐  CONFIGURACIÓN GLOBAL")
    n_clips_total = ask_int("¿Cuántos clips en total quieres generar?", 10)
    clip_dur = ask_float("Duración de cada clip (segundos)", 30.0)

    # Distribuir clips entre videos
    clips_per_video = max(1, n_clips_total // len(videos))
    remainder = n_clips_total - clips_per_video * len(videos)

    use_global = ask_yn("¿Misma config (transición/subtítulos/acciones) para todos?", True)
    global_trans = global_subs = None
    global_actions = []
    if use_global:
        print_info("Configurando para TODOS los clips:")
        # Info de primer video para audio
        info0 = ffprobe(videos[0])
        global_trans, global_subs, global_actions = sondeo_clip_config(info0["has_audio"])

    total_dur = sum(ffprobe(v)["duration"] for v in videos if os.path.exists(v))
    cfg = {
        "n_clips": n_clips_total,
        "total_source_duration": total_dur,
        "has_transitions": bool(global_trans and global_trans != "none"),
        "has_subtitles": bool(global_subs),
        "n_actions": len(global_actions),
        "mode": "split",
    }
    print_estimate(cfg)
    if not ask_yn("¿Continuar?", True):
        return

    out_folder = ensure_dir(os.path.join(output_dir, f"multi_clips_{datetime.now().strftime('%H%M%S')}"))
    print_section("⚙️   PROCESANDO")
    start_t = time.time()
    clip_count = 0

    for vi, vid in enumerate(videos):
        n = clips_per_video + (1 if vi < remainder else 0)
        info = ffprobe(vid)
        vid_dur = info["duration"]
        actual_n = min(n, int(vid_dur / clip_dur))
        if actual_n < 1:
            actual_n = 1

        print(f"\n  {C.BOLD}📹 Video {vi+1}/{len(videos)}: {Path(vid).name}{C.RESET}"
              f"  {C.DIM}→ {actual_n} clips{C.RESET}")

        for ci in range(actual_n):
            t_start = ci * clip_dur
            t_dur   = min(clip_dur, vid_dur - t_start)
            if t_dur < 1:
                break

            clip_count += 1
            clip_name = f"clip_v{vi+1:02d}_{ci+1:03d}.mp4"
            tmp_clip  = os.path.join(out_folder, f"_tmp_{clip_name}")
            fin_clip  = os.path.join(out_folder, clip_name)

            print(f"    {C.DIM}[{clip_count}] desde {fmt_time(t_start)} dur {fmt_dur(t_dur)}{C.RESET}")

            ok = run_ffmpeg([
                "-ss", str(t_start), "-i", vid,
                "-t", str(t_dur),
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", tmp_clip
            ], f"Clip {clip_count}")

            if not ok:
                continue

            current = tmp_clip
            step = 0

            if use_global:
                trans, subs, actions = global_trans, global_subs, global_actions
            else:
                trans, subs, actions = sondeo_clip_config(info["has_audio"])

            for action_cfg in actions:
                step += 1
                nf = os.path.join(out_folder, f"_tmp_{clip_count}_{step}.mp4")
                ok2 = apply_capcut_action(current, nf, action_cfg["action"], action_cfg.get("params", {}))
                if ok2 and os.path.exists(nf):
                    if current != tmp_clip and os.path.exists(current):
                        os.remove(current)
                    current = nf

            if trans and trans != "none":
                step += 1
                tf = os.path.join(out_folder, f"_tmp_{clip_count}_{step}_t.mp4")
                apply_transition(current, tf, trans)
                if os.path.exists(tf):
                    if current != tmp_clip and os.path.exists(current):
                        os.remove(current)
                    current = tf

            if subs:
                step += 1
                srt_p = os.path.join(out_folder, f"_sub_{clip_count}.srt")
                sp = subs if isinstance(subs, dict) else {}
                generate_subtitles(current, srt_p, text=sp.get("text"), duration=t_dur)
                sf = os.path.join(out_folder, f"_tmp_{clip_count}_{step}_s.mp4")
                ok3 = burn_subtitles(current, srt_p, sf,
                                     font_size=sp.get("fontsize", 28),
                                     color=sp.get("color", "white"))
                if ok3 and os.path.exists(sf):
                    if current != tmp_clip and os.path.exists(current):
                        os.remove(current)
                    current = sf

            shutil.move(current, fin_clip)
            if os.path.exists(tmp_clip):
                os.remove(tmp_clip)
            print_ok(f"Guardado: {clip_name}")

    for f in Path(out_folder).glob("_tmp_*"):
        f.unlink(missing_ok=True)

    total_t = time.time() - start_t
    print_section("✅  RESUMEN MULTI-CLIPS")
    print_ok(f"Clips generados: {clip_count}")
    print_ok(f"Carpeta: {out_folder}")
    print_ok(f"Tiempo total: {fmt_dur(total_t)}")

# ──────────────────────────────────────────────
# MÓDULO 4: EDITAR VIDEO INDIVIDUAL
# ──────────────────────────────────────────────
def module_edit_single(output_dir: str):
    print_section("✂️   EDITAR VIDEO INDIVIDUAL")

    src = ask("Ruta del video").strip('"').strip("'")
    if not os.path.exists(src):
        print_err("Archivo no encontrado")
        return

    info = ffprobe(src)
    print_ok(f"Video: {Path(src).name} | {fmt_dur(info['duration'])} | "
             f"{info['width']}x{info['height']}")

    actions = ask_capcut_actions()
    if not actions:
        print_info("Sin acciones seleccionadas")
        return

    out_name = ask("Nombre de salida (sin extensión)", Path(src).stem + "_editado")
    out_file = os.path.join(output_dir, f"{out_name}.mp4")

    cfg = {
        "n_clips": 1,
        "total_source_duration": info["duration"],
        "has_transitions": False,
        "has_subtitles": False,
        "n_actions": len(actions),
        "mode": "edit",
    }
    print_estimate(cfg)
    if not ask_yn("¿Continuar?", True):
        return

    current = src
    tmp_dir = ensure_dir(os.path.join(output_dir, "_tmp_edit"))
    start_t = time.time()

    for j, ac in enumerate(actions):
        next_f = os.path.join(tmp_dir, f"edit_{j}_{ac['action']}.mp4")
        ok = apply_capcut_action(current, next_f, ac["action"], ac.get("params", {}))
        if ok and os.path.exists(next_f):
            if current != src and os.path.exists(current) and "_tmp_" in current:
                os.remove(current)
            current = next_f
        else:
            print_warn(f"Acción {ac['action']} omitida")

    shutil.move(current, out_file)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    total_t = time.time() - start_t
    print_ok(f"Video editado guardado: {out_file}")
    print_ok(f"Tiempo: {fmt_dur(total_t)}")

# ──────────────────────────────────────────────
# HELPERS DE SONDEO
# ──────────────────────────────────────────────
def sondeo_clip_config(has_audio: bool = True):
    """Sondea transición, subtítulos y acciones para un clip."""
    # Transición
    trans = "none"
    if ask_yn("¿Agregar transición?", False):
        print_transitions_menu()
        key = ask("Elige transición", "1")
        trans = TRANSITIONS.get(key, TRANSITIONS["6"])[0]

    # Subtítulos
    subs = None
    if ask_yn("¿Agregar subtítulos?", False):
        subs = ask_subtitle_config()

    # Acciones CapCut
    actions = []
    if ask_yn("¿Aplicar acciones CapCut?", False):
        actions = ask_capcut_actions()

    return trans, subs, actions

def print_transitions_menu():
    print(f"\n  {C.BOLD}Transiciones disponibles:{C.RESET}")
    for k, (t, label, _) in TRANSITIONS.items():
        print(f"    {C.CYAN}[{k}]{C.RESET} {label}")

def ask_subtitle_config() -> dict:
    cfg = {}
    add_text = ask_yn("¿Ingresar texto manual para subtítulos?", False)
    if add_text:
        cfg["text"] = ask("Texto del subtítulo")
    cfg["fontsize"] = ask_int("Tamaño de fuente", 28, 10, 120)
    print(f"  Colores: {C.WHITE}white{C.RESET} | {C.YELLOW}yellow{C.RESET} | red | blue | green | black")
    cfg["color"] = ask("Color del texto", "white")
    pos = ask("Posición: (1) abajo  (2) arriba", "1")
    cfg["position"] = "bottom" if pos == "1" else "top"
    return cfg

def ask_capcut_actions() -> list:
    actions = []
    print(f"\n  {C.BOLD}Acciones CapCut disponibles:{C.RESET}")
    for k, (action, label) in CAPCUT_ACTIONS.items():
        print(f"    {C.CYAN}[{k:>2}]{C.RESET} {label}")
    print()
    selection = ask("Elige acciones (ej: 1,3,18 o 20 para ninguna)", "20")
    if "20" in selection.split(","):
        return []
    for key in selection.split(","):
        key = key.strip()
        if key in CAPCUT_ACTIONS:
            action_id, label = CAPCUT_ACTIONS[key]
            params = ask_action_params(action_id, label)
            actions.append({"action": action_id, "params": params})
    return actions

def ask_action_params(action: str, label: str) -> dict:
    params = {}
    print_info(f"Configurando: {label}")
    if action == "speed_up":
        params["speed"] = ask_float("Velocidad (ej: 2.0 = doble)", 2.0, 0.01)
    elif action == "slow_mo":
        params["speed"] = ask_float("Velocidad lenta (ej: 0.5 = mitad)", 0.5, 0.01)
    elif action == "brightness":
        params["brightness"] = ask_float("Brillo (-1.0 a 1.0)", 0.1, -1.0)
        params["contrast"]   = ask_float("Contraste (0.1 a 3.0)", 1.0, 0.1)
        params["saturation"] = ask_float("Saturación (0 a 3.0)", 1.0, 0.0)
    elif action == "contrast":
        params["contrast"] = ask_float("Contraste (0.1 a 3.0)", 1.5, 0.1)
    elif action == "saturation":
        params["saturation"] = ask_float("Saturación (0 a 3.0)", 1.5, 0.0)
    elif action == "crop":
        print("  Ratios: 16:9 | 9:16 | 1:1 | 4:3")
        params["ratio"] = ask("Ratio de aspecto", "16:9")
    elif action == "rotate":
        deg = ask_int("Grados (90/180/270)", 90)
        params["degrees"] = deg if deg in (90, 180, 270) else 90
    elif action == "flip":
        d = ask("Dirección: (h) horizontal  (v) vertical", "h")
        params["direction"] = "h" if d.lower() == "h" else "v"
    elif action == "text_overlay":
        params["text"]     = ask("Texto a mostrar", "Mi Video")
        params["fontsize"] = ask_int("Tamaño de fuente", 48, 8, 200)
        params["color"]    = ask("Color (white/yellow/red/blue)", "white")
        pos = ask("Posición: (1) abajo  (2) arriba  (3) centro", "1")
        if pos == "1":
            params["x"] = "(w-text_w)/2"
            params["y"] = "h-th-40"
        elif pos == "2":
            params["x"] = "(w-text_w)/2"
            params["y"] = "40"
        else:
            params["x"] = "(w-text_w)/2"
            params["y"] = "(h-text_h)/2"
    elif action == "music":
        params["music_file"] = ask("Ruta del archivo de música").strip('"')
        params["volume"]     = ask_float("Volumen de música (0.1-1.0)", 0.3, 0.0)
        params["fade"]       = ask_float("Duración fade in/out (seg)", 2.0, 0)
    elif action == "volume":
        params["volume"] = ask_float("Multiplicador de volumen (ej: 1.5)", 1.5, 0.0)
    elif action == "color_grade":
        print("  Estilos: cinematico | frio | calido | byn | vintage")
        params["grade"] = ask("Estilo de color", "cinematico")
    return params

def collect_videos(label: str = "") -> list:
    """Recolecta múltiples rutas de video del usuario."""
    videos = []
    print_info(f"Ingresa los videos {label} (uno por línea, Enter vacío para terminar):")
    while True:
        path = ask(f"Video {len(videos)+1} (o Enter para terminar)", "").strip('"').strip("'")
        if not path:
            if videos:
                break
            print_warn("Debes ingresar al menos 1 video")
            continue
        if os.path.exists(path):
            try:
                info = ffprobe(path)
                print_ok(f"  {Path(path).name} ({fmt_dur(info['duration'])}, {info['width']}x{info['height']})")
                videos.append(path)
            except Exception as e:
                print_err(f"  Error leyendo video: {e}")
        else:
            print_err(f"  Archivo no encontrado: {path}")
    return videos

def reorder_list(lst: list) -> list:
    """Permite reordenar una lista."""
    print("\n  Orden actual:")
    for i, item in enumerate(lst):
        print(f"    {C.CYAN}[{i+1}]{C.RESET} {Path(item).name}")
    order_str = ask(f"Nuevo orden (ej: 3,1,2)", ",".join(str(i+1) for i in range(len(lst))))
    try:
        indices = [int(x.strip())-1 for x in order_str.split(",")]
        return [lst[i] for i in indices if 0 <= i < len(lst)]
    except Exception:
        print_warn("Orden inválido, manteniendo el original")
        return lst

# ──────────────────────────────────────────────
# MENÚ PRINCIPAL
# ──────────────────────────────────────────────
def main():
    print_banner()

    # Directorio de salida
    output_dir = ask("Directorio de salida", os.path.expanduser("~/Videos/AutoEditor"))
    ensure_dir(output_dir)
    print_ok(f"Salida en: {output_dir}")

    while True:
        print_section("🏠  MENÚ PRINCIPAL")
        print(f"""
  {C.CYAN}[1]{C.RESET}  🎬  Dividir video largo en clips
  {C.CYAN}[2]{C.RESET}  🔗  Unir múltiples videos en uno largo
  {C.CYAN}[3]{C.RESET}  🎞️   Generar clips de múltiples videos
  {C.CYAN}[4]{C.RESET}  ✂️   Editar video individual (acciones CapCut)
  {C.CYAN}[5]{C.RESET}  📁  Cambiar directorio de salida
  {C.CYAN}[0]{C.RESET}  ❌  Salir
""")
        opt = ask("Elige una opción", "1")

        if opt == "1":
            module_split_video(output_dir)
        elif opt == "2":
            module_merge_videos(output_dir)
        elif opt == "3":
            module_multi_clips(output_dir)
        elif opt == "4":
            module_edit_single(output_dir)
        elif opt == "5":
            output_dir = ask("Nuevo directorio de salida", output_dir)
            ensure_dir(output_dir)
            print_ok(f"Directorio actualizado: {output_dir}")
        elif opt == "0":
            print(f"\n  {C.CYAN}¡Hasta pronto! 🎬{C.RESET}\n")
            break
        else:
            print_warn("Opción inválida")

        print()
        if not ask_yn("¿Realizar otra operación?", True):
            print(f"\n  {C.CYAN}¡Hasta pronto! 🎬{C.RESET}\n")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}Interrumpido por el usuario{C.RESET}\n")
        sys.exit(0)
