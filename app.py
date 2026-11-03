import subprocess
import sys
import os
import tempfile
import base64
import glob
import json
import streamlit as st

# Ensure imageio-ffmpeg is present
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

st.set_page_config(
    page_title="YumnaKashif | Universal Media Suite",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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

# ----------------- ROBUST DUAL-HANDLER EXTRACTION ENGINE -----------------
def fetch_media_stream(url, download_type, temp_dir):
    try:
        output_template = os.path.join(temp_dir, "%(title).50s.%(ext)s")
        is_youtube = "youtube.com" in url or "youtu.be" in url

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist",
            "--no-cache-dir",
            "--no-check-certificates",
            "--geo-bypass",
            "--force-ipv4",
            "--socket-timeout", "25",
            "--write-info-json",
            "-o", output_template,
        ]

        if FFMPEG_PATH:
            cmd.extend(["--ffmpeg-location", FFMPEG_PATH])

        # Handle YouTube specifically with single-stream combined format ('b' or 'ba/b') to prevent cloud 403 & format errors
        if is_youtube:
            if "Audio Only" in download_type:
                cmd.extend(["-f", "ba/b"])
            else:
                # Force combined best single format for YouTube on cloud hosting
                cmd.extend(["-f", "b"])
            
            # Use Android / MWeb client signature which bypasses YouTube's cloud datacenter block
            cmd.extend(["--extractor-args", "youtube:player_client=android"])
        else:
            # Instagram & other platforms standard logic
            if FFMPEG_PATH and "Video" in download_type:
                cmd.extend(["--merge-output-format", "mp4"])
            if "Audio Only" in download_type:
                cmd.extend(["--extract-audio", "--audio-format", "m4a"])

        cmd.append(url)

        proc = subprocess.run(cmd, capture_output=True, text=True)

        media_files = [
            f for f in os.listdir(temp_dir)
            if not f.endswith((".json", ".txt", ".part", ".ytdl"))
        ]

        if proc.returncode == 0 and media_files:
            filename = media_files[0]
            video_info = {
                "title": "YumnaKashif_Media",
                "uploader": "Social Media Creator",
                "duration": 0,
                "thumbnail": None,
                "height": "HD"
            }
            json_files = [f for f in os.listdir(temp_dir) if f.endswith(".info.json")]
            if json_files:
                try:
                    with open(os.path.join(temp_dir, json_files[0]), "r", encoding="utf-8") as jf:
                        jdata = json.load(jf)
                        video_info["title"] = jdata.get("title", "Media_File")
                        video_info["uploader"] = jdata.get("uploader", "Creator")
                        video_info["thumbnail"] = jdata.get("thumbnail", None)
                        video_info["duration"] = jdata.get("duration", 0)
                except Exception:
                    pass
            return filename, video_info, None
        else:
            err_msg = "Unknown download failure."
            for line in proc.stderr.splitlines():
                if "ERROR:" in line:
                    err_msg = line
                    break
            return None, None, err_msg

    except Exception as e:
        return None, None, str(e)


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
    st.write("**Version:** v15.0 Cloud-Optimized Engine")
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
    
    # Quality selector box hides completely when Audio is selected
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
            with st.spinner("⚡ YumnaKashif Engine is processing your media..."):
                temp_dir = tempfile.mkdtemp()
                filename, info_dict, error_msg = fetch_media_stream(url.strip(), download_type, temp_dir, quality_choice if 'quality_choice' in locals() else "Best")

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
                        "url": url.strip()
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
                        st.write(f"🎯 **Format:** {download_type}")

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
