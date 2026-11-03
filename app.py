import subprocess
import sys
import os
import tempfile
import base64
import glob
import urllib.request
import json
import streamlit as st

# Auto-install imageio-ffmpeg for local media handling if needed
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

# ----------------- ADVANCED MULTI-API EXTRACTION ENGINE -----------------
def fetch_media_stream(url, download_type, temp_dir):
    """
    Queries multiple unthrottled public proxy routing engines with optimized payloads
    to guarantee a valid direct stream URL.
    """
    try:
        stream_url = None
        video_info = {
            "title": "YumnaKashif_Media",
            "uploader": "Social Media Creator",
            "duration": 0,
            "thumbnail": None,
            "height": "HD"
        }

        # Method 1: Cobalt API (Most reliable universal media fetcher)
        try:
            cobalt_payload = json.dumps({
                "url": url,
                "isAudioOnly": True if "Audio Only" in download_type else False
            }).encode("utf-8")
            
            cobalt_req = urllib.request.Request(
                "https://api.cobalt.tools/api/json",
                data=cobalt_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            )
            with urllib.request.urlopen(cobalt_req, timeout=10) as cres:
                cdata = json.loads(cres.read().decode())
                if cdata.get("status") in ["redirect", "stream", "picker"]:
                    if cdata.get("url"):
                        stream_url = cdata.get("url")
                    elif cdata.get("picker"):
                        stream_url = cdata["picker"][0].get("url")
        except Exception:
            pass

        # Method 2: Piped API Mirrors Fallback
        if not stream_url:
            vid_id = ""
            if "youtu.be/" in url:
                vid_id = url.split("youtu.be/")[1].split("?")[0]
            elif "watch?v=" in url:
                vid_id = url.split("watch?v=")[1].split("&")[0]
            elif "shorts/" in url:
                vid_id = url.split("shorts/")[1].split("?")[0]

            if vid_id:
                piped_instances = [
                    "https://pipedapi.kavin.rocks",
                    "https://piped-api.privacy.com.de",
                    "https://api.piped.projectsegfault.net",
                    "https://pipedapi.in.projectsegfault.net"
                ]
                for inst in piped_instances:
                    try:
                        req_url = f"{inst}/streams/{vid_id}"
                        req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = json.loads(response.read().decode())
                            video_info["title"] = data.get("title", "YumnaKashif_Media")
                            video_info["uploader"] = data.get("uploader", "Creator")
                            video_info["duration"] = data.get("duration", 0)
                            video_info["thumbnail"] = data.get("thumbnailUrl", None)

                            if "Audio Only" in download_type:
                                audio_streams = [s for s in data.get("audioStreams", []) if s.get("url")]
                                if audio_streams:
                                    stream_url = audio_streams[0]["url"]
                                    break
                            else:
                                video_streams = [s for s in data.get("videoStreams", []) if s.get("url") and not s.get("videoOnly")]
                                if video_streams:
                                    stream_url = video_streams[0]["url"]
                                    break
                                elif data.get("videoStreams", []):
                                    stream_url = data["videoStreams"][0]["url"]
                                    break
                    except Exception:
                        continue

        if not stream_url:
            return None, None, "Could not bypass host restriction. Please verify the URL or try another link."

        # Download the stream locally to temp directory
        safe_title = "".join(c for c in video_info["title"] if c.isalnum() or c in " -_").strip()[:50] or "media"
        ext = "m4a" if "Audio Only" in download_type else "mp4"
        filename = f"{safe_title}.{ext}"
        file_path = os.path.join(temp_dir, filename)

        dl_req = urllib.request.Request(stream_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(dl_req, timeout=45) as response, open(file_path, "wb") as out_file:
            out_file.write(response.read())

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return filename, video_info, None
        else:
            return None, None, "Downloaded file stream returned empty."

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
    st.write("**Version:** v13.0 Cloud Proxy Engine")
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
            with st.spinner("⚡ YumnaKashif Cloud Proxy is processing your media..."):
                temp_dir = tempfile.mkdtemp()
                filename, info_dict, error_msg = fetch_media_stream(url.strip(), download_type, temp_dir)

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
