import subprocess
import sys

# Auto-install missing packages on Streamlit Cloud if not already present
for package in ["yt-dlp", "imageio-ffmpeg"]:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import streamlit as st
import yt_dlp
import os
import tempfile
import base64
import glob

# Try loading imageio_ffmpeg so 1080p/4K video+audio merging works automatically
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
sub_text = "#475569" if not st.session_state.dark_mode else "#cbd5e1"
card_bg = "rgba(255, 255, 255, 0.88)" if not st.session_state.dark_mode else "rgba(15, 23, 42, 0.82)"
card_border = "rgba(15, 23, 42, 0.12)" if not st.session_state.dark_mode else "rgba(255, 255, 255, 0.16)"

img_b64 = get_background_base64()
if img_b64:
    overlay = (
        "linear-gradient(135deg, rgba(248, 250, 252, 0.82) 0%, rgba(226, 232, 240, 0.88) 100%)"
        if not st.session_state.dark_mode
        else "linear-gradient(135deg, rgba(10, 15, 30, 0.78) 0%, rgba(30, 20, 60, 0.85) 100%)"
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
    [data-testid="stSidebar"] {{
        display: none !important;
    }}
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    .glass-card {{
        background: {card_bg};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid {card_border};
        padding: 28px;
        border-radius: 18px;
        box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.12);
        margin-bottom: 22px;
        color: {theme_text};
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

st.markdown("---")

# ----------------- VIEW A: SETTINGS SCREEN -----------------
if st.session_state.show_settings:
    st.markdown("<h2 style='text-align: center;'>⚙️ Settings & Control Center</h2>", unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🎨 Theme & Appearance")
    dark_toggle = st.toggle("🌙 Night Mode (Dark Theme)", value=st.session_state.dark_mode)
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📜 Download History")
    if not st.session_state.history:
        st.info("No videos downloaded in this session yet.")
    else:
        for idx, item in enumerate(st.session_state.history[::-1], 1):
            st.markdown(f"**{idx}. {item['title']}** ({item['type']} • {item['quality']})")
            st.caption(f"Link: {item['url']}")
            st.markdown("---")
        if st.button("🗑️ Clear History"):
            st.session_state.history = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card" style="text-align: center;">', unsafe_allow_html=True)
    st.subheader("ℹ️ About & Version")
    st.write("**Application:** YumnaKashif Universal Downloader")
    st.write("**Version:** v7.0.0 Public Pro")
    st.markdown("---")
    st.markdown("### Made by **Mohd Kashif**")
    st.caption("AI & Full-Stack Developer")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- VIEW B: MAIN DOWNLOADER SCREEN -----------------
else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📥 Download Ultra-HD Video or Audio")
    url = st.text_input("🔗 Paste YouTube, Instagram, or Social Media Link:", placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/...")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        download_type = st.radio("Format:", ["Video (MP4)", "Audio Only (MP3/M4A)"], horizontal=True)
    with col_opt2:
        quality_choice = st.selectbox(
            "Select Quality:",
            ["Best Available (1080p/4K)", "1080p Full HD", "720p HD", "480p Fast"]
        )

    if st.button("🚀 Fetch & Download Media"):
        if not url.strip():
            st.error("Please paste a valid video link first.")
        else:
            with st.spinner("⚡ YumnaKashif AI is processing video & audio streams..."):
                try:
                    temp_dir = tempfile.mkdtemp()
                    
                    if "Audio Only" in download_type:
                        format_str = "bestaudio[ext=m4a]/bestaudio/best"
                    else:
                        if FFMPEG_PATH:
                            if "1080p" in quality_choice:
                                format_str = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
                            elif "720p" in quality_choice:
                                format_str = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
                            elif "480p" in quality_choice:
                                format_str = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best"
                            else:
                                format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                        else:
                            format_str = "best[ext=mp4]/best"

                    ydl_opts = {
                        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
                        "format": format_str,
                        "merge_output_format": "mp4" if "Video" in download_type else None,
                        "noplaylist": True,
                        "quiet": True,
                        "no_warnings": True,
                        "nocheckcertificate": True,
                    }

                    if FFMPEG_PATH:
                        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info_dict = ydl.extract_info(url, download=True)
                    except Exception:
                        ydl_opts["format"] = "best[ext=mp4]/best"
                        ydl_opts["extractor_args"] = {"youtube": {"player_client": ["ios", "android", "web"]}}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info_dict = ydl.extract_info(url, download=True)

                    video_title = info_dict.get("title", "YumnaKashif_Media")
                    uploader = info_dict.get("uploader", "Social Media Creator")
                    duration = info_dict.get("duration", 0)
                    thumbnail = info_dict.get("thumbnail", None)
                    height = info_dict.get("height", "HD")

                    downloaded_files = os.listdir(temp_dir)
                    if downloaded_files:
                        file_path = os.path.join(temp_dir, downloaded_files[0])
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
                            st.write(f"🎯 **Target Quality:** {quality_choice}")

                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Save {downloaded_files[0]} to Device",
                                data=f,
                                file_name=downloaded_files[0],
                                mime=mime_type
                            )
                    else:
                        st.error("Could not find the downloaded stream file.")
                except Exception as e:
                    st.error(f"Download Error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
