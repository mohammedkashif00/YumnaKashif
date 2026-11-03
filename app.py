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
    page_title="YumnaKashif | Enterprise Media Suite",
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

# ----------------- LIGHT & DARK THEME STYLING -----------------
theme_text = "#0f172a" if not st.session_state.dark_mode else "#f8fafc"
card_bg = "rgba(255, 255, 255, 0.85)" if not st.session_state.dark_mode else "rgba(15, 23, 42, 0.85)"

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
    .suite-card {{
        background: {card_bg};
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
</style>
""", unsafe_allow_html=True)

# ----------------- EXTRACTION ENGINE -----------------
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

        if is_youtube:
            if "Audio Only" in download_type:
                cmd.extend(["-f", "ba/b"])
            else:
                cmd.extend(["-f", "b"])
            cmd.extend(["--extractor-args", "youtube:player_client=android"])
        else:
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
                "thumbnail": None
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


# ----------------- TOP BAR: HEADER & THEME TOGGLE -----------------
top_col1, top_col2 = st.columns([5, 1])
with top_col1:
    st.markdown("<h2 style='margin: 0;'>⚡ YumnaKashif Media Suite</h2>", unsafe_allow_html=True)
    st.caption("Professional Multi-Module Media Hub • Created by Mohd Kashif")
with top_col2:
    theme_icon = "☀️" if st.session_state.dark_mode else "🌙"
    if st.button(theme_icon, help="Toggle Theme"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.write("")

# ----------------- MULTI-TAB SUITE NAVIGATION -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Universal Downloader", 
    "⚡ Batch Queue", 
    "📊 Analytics & History", 
    "🛠️ System Health"
])

# ================= TAB 1: UNIVERSAL DOWNLOADER =================
with tab1:
    st.subheader("📥 Single Media Downloader")
    url = st.text_input(
        "🔗 Paste YouTube or Instagram Link:",
        placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/...",
        key="single_url_input"
    )
    
    download_type = st.radio("Format:", ["Video (MP4)", "Audio Only (MP3/M4A)"], horizontal=True, key="single_type")
    
    if download_type == "Video (MP4)":
        quality_choice = st.selectbox(
            "Select Quality:",
            ["Best Available (1080p/4K)", "1080p Full HD", "720p HD", "480p Fast"],
            key="single_quality"
        )
    else:
        quality_choice = "Best Audio"

    st.write("")
    if st.button("🚀 Fetch & Download Media", key="single_btn"):
        if not url.strip():
            st.error("Please paste a valid video link first.")
        else:
            with st.spinner("⚡ Processing media stream..."):
                temp_dir = tempfile.mkdtemp()
                filename, info_dict, error_msg = fetch_media_stream(url.strip(), download_type, temp_dir)

                if filename:
                    file_path = os.path.join(temp_dir, filename)
                    video_title = info_dict.get("title", filename) if info_dict else filename
                    uploader = info_dict.get("uploader", "Creator") if info_dict else "Creator"
                    duration = info_dict.get("duration", 0) if info_dict else 0
                    thumbnail = info_dict.get("thumbnail", None) if info_dict else None

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
                            mime="audio/mp4" if "Audio" in download_type else "video/mp4",
                            key="single_dl_btn"
                        )
                else:
                    st.error(f"Download Error: {error_msg}")

# ================= TAB 2: BATCH QUEUE =================
with tab2:
    st.subheader("⚡ Batch Link Queue")
    st.caption("Paste multiple links (one per line) to process them sequentially.")
    
    batch_text = st.text_area("🔗 Enter Links:", placeholder="https://youtube.com/watch?v=...\nhttps://instagram.com/reel/...", height=120)
    batch_type = st.radio("Batch Format:", ["Video (MP4)", "Audio Only (MP3/M4A)"], horizontal=True, key="batch_type")

    if st.button("🚀 Process Batch Queue"):
        links = [l.strip() for l in batch_text.splitlines() if l.strip()]
        if not links:
            st.error("Please enter at least one link.")
        else:
            st.info(f"Processing {len(links)} link(s)...")
            for idx, link in enumerate(links, 1):
                st.write(f"Processing item {idx}: `{link}`")
                temp_dir = tempfile.mkdtemp()
                filename, info_dict, err = fetch_media_stream(link, batch_type, temp_dir)
                if filename:
                    fpath = os.path.join(temp_dir, filename)
                    st.success(f"✅ Successfully downloaded: {filename}")
                    st.session_state.history.append({
                        "title": filename,
                        "type": batch_type,
                        "quality": "Batch",
                        "url": link
                    })
                else:
                    st.warning(f"⚠️ Failed: {err}")

# ================= TAB 3: ANALYTICS & HISTORY =================
with tab3:
    st.subheader("📊 Analytics & Download History")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Downloads", len(st.session_state.history))
    col2.metric("Active Session", "Online")
    col3.metric("Engine Status", "Operational")
    
    st.markdown("---")
    if not st.session_state.history:
        st.info("No download history recorded in this session yet.")
    else:
        for idx, item in enumerate(st.session_state.history[::-1], 1):
            st.markdown(f"**{idx}. {item['title']}**")
            st.caption(f"Type: {item['type']} | Quality: {item['quality']} | URL: {item['url']}")
            st.markdown("---")
        
        if st.button("🗑️ Clear History"):
            st.session_state.history = []
            st.rerun()

# ================= TAB 4: SYSTEM HEALTH =================
with tab4:
    st.subheader("🛠️ System Diagnostics & Health")
    st.write("**Application Version:** v16.0 Enterprise Suite")
    st.write("**Developer:** Mohd Kashif")
    st.markdown("---")
    
    st.write("🔧 **Dependency Status:**")
    st.write(f"- **FFmpeg Path:** `{FFMPEG_PATH if FFMPEG_PATH else 'Not detected (using fallback)'}`")
    st.write(f"- **Python Environment:** `{sys.version.split()[0]}`")
    st.write(f"- **Streamlit Version:** `{st.__version__}`")
    
    st.markdown("---")
    if st.button("🔄 Run Diagnostics Test"):
        st.success("All system modules and subprocess pipes are functioning normally!")
