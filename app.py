import subprocess
import sys
import os
import shutil
import tempfile
import base64
import glob
import json
import streamlit as st

# 1. Force upgrade yt-dlp and imageio-ffmpeg on container boot
@st.cache_resource
def ensure_latest_binaries():
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--pre", "yt-dlp", "imageio-ffmpeg"],
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

FFMPEG_PATH = ensure_latest_binaries()

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

# ----------------- ISOLATED SUBPROCESS DOWNLOAD ENGINE -----------------
def download_via_cli(url, download_type, quality_choice, temp_dir):
    """
    Runs yt-dlp in a fresh isolated OS process so it always uses the newly upgraded
    binary and never suffers from Python memory/session caching or 403 poisoning.
    """
    output_template = os.path.join(temp_dir, "%(title).80s.%(ext)s")

    # Sort preference instead of rigid format filter so it never fails with 'format not available'
    if "Audio Only" in download_type:
        sort_arg = "abr,ext:m4a:mp3"
    elif "1080p" in quality_choice:
        sort_arg = "res:1080,ext:mp4:m4a"
    elif "720p" in quality_choice:
        sort_arg = "res:720,ext:mp4:m4a"
    elif "480p" in quality_choice:
        sort_arg = "res:480,ext:mp4:m4a"
    else:
        sort_arg = "ext:mp4:m4a"

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

    if "Audio Only" in download_type:
        base_cmd.extend(["-f", "ba/b"])

    # Client profiles ordered by highest success rate against Cloud 403 blocks
    profiles = [
        # Profile 1: Android VR (Does not require PO token or cookies, bypasses 403 on cloud IPs)
        ["--extractor-args", "youtube:player_client=android_vr"],
        # Profile 2: iOS + TV Embedded (Great for Shorts & Reels)
        ["--extractor-args", "youtube:player_client=ios,tv_embedded"],
        # Profile 3: Android Testsuite / MediaConnect
        ["--extractor-args", "youtube:player_client=android_testsuite,mediaconnect"],
        # Profile 4: Mobile Web
        ["--extractor-args", "youtube:player_client=mweb"],
    ]

    # If cookies.txt exists, add a dedicated read-only cookie clone profile for web/tv
    if os.path.exists("cookies.txt") and os.path.getsize("cookies.txt") > 0:
        cookie_clone = os.path.join(temp_dir, "temp_cookies.txt")
        shutil.copyfile("cookies.txt", cookie_clone)
        profiles.append(["--cookies", cookie_clone, "--extractor-args", "youtube:player_client=tv,web"])

    last_err = "Unknown extraction error"

    for profile_args in profiles:
        # Clean temp directory before each attempt (except temp_cookies.txt)
        for f in os.listdir(temp_dir):
            if f != "temp_cookies.txt":
                try:
                    os.remove(os.path.join(temp_dir, f))
                except Exception:
                    pass

        cmd = base_cmd + profile_args + [url]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        # Look for downloaded media file (excluding .info.json and .txt)
        media_files = [
            f for f in os.listdir(temp_dir)
            if not f.endswith(".json") and not f.endswith(".txt") and not f.endswith(".part") and not f.endswith(".ytdl")
        ]

        if proc.returncode == 0 and media_files:
            # Parse metadata from info.json if available
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
                last_err = err_lines[-1]
            elif proc.stderr:
                last_err = proc.stderr.strip()[-300:]

    return None, None, last_err


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
    st.write("**Version:** v10.0.1 Subprocess Anti-403 Engine")
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
            with st.spinner("⚡ YumnaKashif AI is extracting unthrottled media stream..."):
                temp_dir = tempfile.mkdtemp()
                filename, info_dict, error_msg = download_via_cli(url.strip(), download_type, quality_choice, temp_dir)

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
                        "url": url
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
