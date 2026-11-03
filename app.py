import subprocess
import sys
import os
import shutil
import tempfile
import base64
import glob
import json
import streamlit as st

# 1. Install/upgrade yt-dlp, pytubefix (backup engine), and PO-token plugin on startup
@st.cache_resource
def setup_environment():
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--upgrade", "--pre",
                "yt-dlp", "imageio-ffmpeg", "pytubefix", "bgutil-ytdlp-pot-provider"
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

st.set_page_config(
    page_title="YumnaKashif | Universal Media Suite",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

FFMPEG_PATH = setup_environment()

def get_background_base64():
    candidates = ["portrait.jpg", "portrait.png", "IMG_0191.jpg", "IMG_0191.jpeg"]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "rb") as f:
                return base64.b64encode(f.read()).decode()
    all_imgs = glob.glob("*.jpg") + glob.glob("*.jpeg") + glob.glob("*.png")
    if all_imgs:
        with open(all_imgs[0], "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# ----------------- SESSION STATE -----------------
if "history" not in st.session_state:
    st.session_state.history = []
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

# ----------------- LIGHT & DARK THEME STYLING -----------------
theme_text = "#0f172a" if not st.session_state.dark_mode else "#f8fafc"

img_b64 = get_background_base64()
if img_b64:
    overlay = (
        "linear-gradient(135deg, rgba(248, 250, 252, 0.85) 0%, rgba(226, 232, 240, 0.90) 100%)"
        if not st.session_state.dark_mode
        else "linear-gradient(135deg, rgba(10, 15, 30, 0.82) 0%, rgba(30, 20, 60, 0.88) 100%)"
    )
    bg_css = f"""
    .stApp {{
        background: {overlay}, url("data:image/jpeg;base64,{img_b64}");
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}
    """
else:
    grad = (
        "linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #f1f5f9 100%)"
        if not st.session_state.dark_mode
        else "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #020617 100%)"
    )
    bg_css = f"""
    .stApp {{
        background: {grad};
    }}
    """

st.markdown(f"""
<style>
    {bg_css}
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    hr {{
        display: none !important;
    }}
    .stButton>button {{
        width: 100%;
        background: linear-gradient(90deg, #4f46e5 0%, #9333ea 100%);
        color: white !important;
        font-weight: 600;
        border: none;
        padding: 12px 18px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.25);
        transition: all 0.2s ease;
    }}
    .stButton>button:hover {{
        opacity: 0.92;
        transform: translateY(-1px);
    }}
    h1, h2, h3, h4, p, label, .stMarkdown {{
        color: {theme_text} !important;
    }}
</style>
""", unsafe_allow_html=True)


# ----------------- ENGINE 1: PYTUBEFIX (CLOUD-RESILIENT YOUTUBE ENGINE) -----------------
def download_via_pytubefix(url, download_type, quality_choice, temp_dir):
    """
    Uses pytubefix with Android/WEB_EMBED clients as a primary/backup extractor
    specifically for YouTube links when yt-dlp gets 'Requested format is not available'.
    """
    if "youtube.com" not in url and "youtu.be" not in url:
        return None, None, "Not a YouTube URL"

    try:
        from pytubefix import YouTube
    except ImportError:
        return None, None, "pytubefix not installed"

    clients_to_try = ["WEB", "ANDROID_VR", "IOS", "MWEB", "TV_EMBED"]
    last_pt_err = ""

    for client_name in clients_to_try:
        try:
            yt = YouTube(url, client=client_name)
            title = yt.title or "YumnaKashif_Media"
            safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()[:70] or "video"

            if "Audio Only" in download_type:
                stream = yt.streams.get_audio_only()
                if stream:
                    out_file = stream.download(output_path=temp_dir, filename=f"{safe_title}.m4a")
                    return os.path.basename(out_file), {
                        "title": title,
                        "uploader": yt.author,
                        "duration": yt.length,
                        "thumbnail": yt.thumbnail_url,
                        "height": "Audio",
                    }, None
            else:
                # Target resolution cap
                target_res = None
                if "1080p" in quality_choice:
                    target_res = 1080
                elif "720p" in quality_choice:
                    target_res = 720
                elif "480p" in quality_choice:
                    target_res = 480

                # First try progressive (pre-merged video+audio) or adaptive with ffmpeg merge
                prog_streams = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc()
                adap_video = yt.streams.filter(adaptive=True, only_video=True, file_extension="mp4").order_by("resolution").desc()
                adap_audio = yt.streams.get_audio_only()

                chosen_v = None
                if FFMPEG_PATH and adap_video and adap_audio:
                    for s in adap_video:
                        res_num = int(s.resolution.replace("p", "")) if s.resolution and s.resolution.endswith("p") else 0
                        if target_res is None or res_num <= target_res:
                            chosen_v = s
                            break
                    if not chosen_v:
                        chosen_v = adap_video.first()

                # If adaptive chosen and<=720p progressive exists, check if progressive matches target
                if chosen_v and FFMPEG_PATH and adap_audio:
                    v_path = chosen_v.download(output_path=temp_dir, filename="temp_v.mp4")
                    a_path = adap_audio.download(output_path=temp_dir, filename="temp_a.m4a")
                    final_name = f"{safe_title}.mp4"
                    final_path = os.path.join(temp_dir, final_name)
                    subprocess.run(
                        [FFMPEG_PATH, "-y", "-i", v_path, "-i", a_path, "-c:v", "copy", "-c:a", "aac", final_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                        res_str = chosen_v.resolution.replace("p", "") if chosen_v.resolution else "HD"
                        return final_name, {
                            "title": title,
                            "uploader": yt.author,
                            "duration": yt.length,
                            "thumbnail": yt.thumbnail_url,
                            "height": int(res_str) if res_str.isdigit() else res_str,
                        }, None

                # Fallback to direct progressive stream
                if prog_streams:
                    stream = prog_streams.first()
                    out_file = stream.download(output_path=temp_dir, filename=f"{safe_title}.mp4")
                    res_str = stream.resolution.replace("p", "") if stream.resolution else "HD"
                    return os.path.basename(out_file), {
                        "title": title,
                        "uploader": yt.author,
                        "duration": yt.length,
                        "thumbnail": yt.thumbnail_url,
                        "height": int(res_str) if res_str.isdigit() else res_str,
                    }, None
        except Exception as e:
            last_pt_err = str(e)
            continue

    return None, None, last_pt_err


# ----------------- ENGINE 2: YT-DLP SUBPROCESS ENGINE -----------------
def download_via_ytdlp_cli(url, download_type, quality_choice, temp_dir):
    output_template = os.path.join(temp_dir, "%(title).70s.%(ext)s")

    if "Audio Only" in download_type:
        sort_arg = "hasaud,abr,ext:m4a:mp3"
    elif "1080p" in quality_choice:
        sort_arg = "hasvid,res:1080,ext:mp4:m4a"
    elif "720p" in quality_choice:
        sort_arg = "hasvid,res:720,ext:mp4:m4a"
    elif "480p" in quality_choice:
        sort_arg = "hasvid,res:480,ext:mp4:m4a"
    else:
        sort_arg = "hasvid,ext:mp4:m4a"

    base_cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--no-cache-dir",
        "--no-check-certificates",
        "--geo-bypass",
        "--force-ipv4",
        "--socket-timeout", "20",
        "--write-info-json",
        "-S", sort_arg,
        "-o", output_template,
    ]

    if FFMPEG_PATH:
        base_cmd.extend(["--ffmpeg-location", FFMPEG_PATH])
        if "Video" in download_type:
            base_cmd.extend(["--merge-output-format", "mp4"])

    # Notice: NO "-f" flag is passed for video so yt-dlp never fails with "Requested format is not available"
    # It automatically picks the top format sorted by "-S" above.
    if "Audio Only" in download_type:
        base_cmd.extend(["--extract-audio", "--audio-format", "m4a"])

    profiles = [
        # Profile 1: Default client with no restrictions
        [],
        # Profile 2: Android VR + TV Embedded
        ["--extractor-args", "youtube:player_client=android_vr,tv_embedded"],
        # Profile 3: iOS + Mobile Web
        ["--extractor-args", "youtube:player_client=ios,mweb"],
    ]

    # Only try cookies.txt as a FIRST attempt if present, and don't let its failure hide earlier errors
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        cookie_clone = os.path.join(temp_dir, "temp_cookies.txt")
        shutil.copyfile("cookies.txt", cookie_clone)
        profiles.insert(0, ["--cookies", cookie_clone])

    errors_collected = []

    for profile_args in profiles:
        for f in os.listdir(temp_dir):
            if f != "temp_cookies.txt":
                try:
                    os.remove(os.path.join(temp_dir, f))
                except Exception:
                    pass

        cmd = base_cmd + profile_args + [url]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        media_files = [
            f for f in os.listdir(temp_dir)
            if not f.endswith((".json", ".txt", ".part", ".ytdl", ".jpg", ".webp", ".png"))
        ]

        if proc.returncode == 0 and media_files:
            info_data = {}
            json_files = [f for f in os.listdir(temp_dir) if f.endswith(".info.json")]
            if json_files:
                try:
                    with open(os.path.join(temp_dir, json_files[0]), "r", encoding="utf-8") as jf:
                        info_data = json.load(jf)
                except Exception:
                    pass
            return media_files[0], info_data, None
        else:
            err_lines = [line for line in proc.stderr.splitlines() if "ERROR:" in line]
            if err_lines:
                errors_collected.append(err_lines[-1])

    return None, None, " | ".join(dict.fromkeys(errors_collected)) if errors_collected else "Extraction blocked by host IP"


# ----------------- TOP BAR: TITLE & SETTINGS TOGGLE -----------------
top_col1, top_col2 = st.columns([5, 1])
with top_col1:
    st.markdown("<h2 style='margin: 0;'>⚡ YumnaKashif</h2>", unsafe_allow_html=True)
    st.caption("Universal Media Suite • Created by Mohd Kashif")
with top_col2:
    btn_label = "🏠" if st.session_state.show_settings else "⚙️"
    btn_help = "Back to Downloader" if st.session_state.show_settings else "Open Settings"
    if st.button(btn_label, help=btn_help):
        st.session_state.show_settings = not st.session_state.show_settings
        st.rerun()

st.write("")

# ----------------- VIEW A: SETTINGS SCREEN -----------------
if st.session_state.show_settings:
    st.markdown("<h2 style='text-align: center;'>⚙️ Settings & Control Center</h2>", unsafe_allow_html=True)
    st.write("")

    st.subheader("🎨 Theme & Appearance")
    dark_toggle = st.toggle("🌙 Night Mode (Dark Theme)", value=st.session_state.dark_mode)
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()

    st.write("")
    st.subheader("📜 Download History")
    if not st.session_state.history:
        st.info("No videos downloaded in this session yet.")
    else:
        for idx, item in enumerate(st.session_state.history[::-1], 1):
            st.markdown(f"**{idx}. {item['title']}** ({item['type']} • {item['quality']})")
            st.caption(f"Link: {item['url']}")
        if st.button("🗑️ Clear History"):
            st.session_state.history = []
            st.rerun()

    st.write("")
    st.subheader("ℹ️ About & Version")
    st.write("**Application:** YumnaKashif Universal Downloader")
    st.write("**Version:** v11.0 Dual-Engine (pytubefix + yt-dlp)")
    st.markdown("### Made by **Mohd Kashif**")
    st.caption("AI & Full-Stack Developer")

# ----------------- VIEW B: MAIN DOWNLOADER SCREEN -----------------
else:
    st.subheader("📥 Download Ultra-HD Video or Audio")
    url = st.text_input(
        "🔗 Paste YouTube, Instagram, or Social Media Link:",
        placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/..."
    )
    
    download_type = st.radio("Format:", ["Video (MP4)", "Audio Only (MP3/M4A)"], horizontal=True)
    
    if download_type == "Video (MP4)":
        quality_choice = st.selectbox(
            "Select Quality:",
            ["Best Available (1080p/4K)", "1080p Full HD", "720p HD", "480p Fast"]
        )
    else:
        quality_choice = "Best Audio"

    st.write("")
    if st.button("🚀 Fetch & Download Media"):
        if not url.strip():
            st.error("Please paste a valid video link first.")
        else:
            with st.spinner("⚡ YumnaKashif Dual-Engine is extracting your media stream..."):
                temp_dir = tempfile.mkdtemp()
                clean_url = url.strip()

                # Try Engine 1 (pytubefix) first for YouTube URLs, then Engine 2 (yt-dlp CLI)
                filename, info_dict, err1 = download_via_pytubefix(clean_url, download_type, quality_choice, temp_dir)
                
                if not filename:
                    filename, info_dict, err2 = download_via_ytdlp_cli(clean_url, download_type, quality_choice, temp_dir)
                    error_msg = f"{err2} (Fallback: {err1})"
                else:
                    error_msg = None

                if filename:
                    file_path = os.path.join(temp_dir, filename)
                    video_title = info_dict.get("title", filename) if info_dict else filename
                    uploader = info_dict.get("uploader", "Social Media Creator") if info_dict else "Creator"
                    duration = info_dict.get("duration", 0) if info_dict else 0
                    thumbnail = info_dict.get("thumbnail", None) if info_dict else None
                    height = info_dict.get("height", "HD") if info_dict else "HD"

                    mime_type = "audio/mp4" if "Audio" in download_type else "video/mp4"

                    st.session_state.history.append({
                        "title": video_title,
                        "type": download_type,
                        "quality": quality_choice,
                        "url": clean_url
                    })

                    st.success("✅ Media Ready for Download!")
                    col1, col2 = st.columns([1, 2])
                    if thumbnail:
                        col1.image(thumbnail)
                    with col2:
                        st.markdown(f"#### {video_title}")
                        st.write(f"👤 **Creator:** {uploader}")
                        if duration:
                            st.write(f"⏱️ **Duration:** {int(duration) // 60}m {int(duration) % 60}s")
                        if "Video" in download_type:
                            st.write(f"🎯 **Quality:** {quality_choice} ({height}p)" if isinstance(height, int) else f"🎯 **Quality:** {quality_choice}")
                        else:
                            st.write("🎵 **Format:** High-Bitrate Audio")

                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Save {filename} to Device",
                            data=f,
                            file_name=filename,
                            mime=mime_type
                        )
                else:
                    st.error(f"Download Error: {error_msg}")

# END OF FILE
