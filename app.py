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
import random
import smtplib
from email.message import EmailMessage

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

def send_real_gmail_otp(receiver_email, otp_code):
    # Uses secure server secrets stored in Streamlit Cloud Dashboard -> Settings -> Secrets
    sender_email = st.secrets.get("GMAIL_SENDER", os.environ.get("GMAIL_SENDER", ""))
    app_password = st.secrets.get("GMAIL_APP_PASSWORD", os.environ.get("GMAIL_APP_PASSWORD", ""))
    
    if not sender_email or not app_password:
        raise ValueError("SMTP credentials are not configured in Streamlit Secrets.")

    msg = EmailMessage()
    msg["Subject"] = f"YumnaKashif Verification Code: {otp_code}"
    msg["From"] = f"YumnaKashif Security <{sender_email}>"
    msg["To"] = receiver_email
    msg.set_content(
        f"Hello,\n\n"
        f"Your 6-digit OTP verification code for YumnaKashif Media Suite is: {otp_code}\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"Made by Mohd Kashif"
    )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password.replace(" ", ""))
        server.send_message(msg)

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "email"
if "generated_otp" not in st.session_state:
    st.session_state.generated_otp = None
if "history" not in st.session_state:
    st.session_state.history = []
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "global_quality" not in st.session_state:
    st.session_state.global_quality = "Best Available (1080p/4K)"
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

# ----------------- OTP-ONLY LOGIN GATEWAY -----------------
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; margin-top: 25px; font-size: 2.8rem;'>⚡ YumnaKashif</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {sub_text}; margin-bottom: 25px;'>Secure OTP Verification Portal — Created by Mohd Kashif</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if st.session_state.auth_step == "email":
        st.subheader("✉️ Enter Your Email")
        email_input = st.text_input("Your Email Address:", placeholder="yourname@gmail.com")

        if st.button("📤 Send Verification OTP"):
            clean_email = email_input.strip().lower()
            if not ("@" in clean_email and "." in clean_email and len(clean_email) > 5):
                st.error("⚠️ Please enter a valid email address.")
            else:
                otp_code = str(random.randint(100000, 999999))
                with st.spinner(f"Sending 6-digit OTP to {clean_email}..."):
                    try:
                        send_real_gmail_otp(clean_email, otp_code)
                        st.session_state.generated_otp = otp_code
                        st.session_state.user_email = clean_email
                        st.session_state.auth_step = "otp"
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to dispatch email. Please check server SMTP secrets configuration. Details: {e}")
    else:
        st.subheader("🔐 Enter 6-Digit OTP")
        st.success(f"📩 A verification code has been sent to **{st.session_state.user_email}**. Check your inbox!")
        otp_input = st.text_input("Verification Code:", type="password", max_chars=6, placeholder="••••••")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            if st.button("✔️ Verify & Enter"):
                if st.session_state.generated_otp and otp_input.strip() == st.session_state.generated_otp:
                    st.session_state.logged_in = True
                    st.session_state.generated_otp = None
                    st.rerun()
                else:
                    st.error("❌ Invalid OTP! Access denied. Please enter the exact code received in your email.")
        with col_v2:
            if st.button("⬅️ Resend Code"):
                st.session_state.auth_step = "email"
                st.session_state.generated_otp = None
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ----------------- TOP BAR: TITLE & SETTINGS TOGGLE -----------------
top_col1, top_col2 = st.columns([5, 1])
with top_col1:
    st.markdown("<h2 style='margin: 0;'>⚡ YumnaKashif</h2>", unsafe_allow_html=True)
    st.caption(f"Authenticated as: {st.session_state.user_email} • Created by Mohd Kashif")
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
    st.subheader("👤 Session Profile")
    st.write(f"**Logged-in Email:** `{st.session_state.user_email}`")
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.auth_step = "email"
        st.session_state.show_settings = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🎨 Theme & Download Quality")
    
    dark_toggle = st.toggle("🌙 Night Mode (Dark Theme)", value=st.session_state.dark_mode)
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()

    st.write("")
    quality_options = ["Best Available (1080p/4K)", "720p HD", "480p Fast"]
    selected_q = st.selectbox(
        "📥 Default Download Quality:",
        quality_options,
        index=quality_options.index(st.session_state.global_quality)
    )
    if selected_q != st.session_state.global_quality:
        st.session_state.global_quality = selected_q
        st.success(f"Download quality set to {selected_q}")
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
    st.write("**Version:** v6.1.0 Pro (OTP Secure)")
    st.markdown("---")
    st.markdown("### Made by **Mohd Kashif**")
    st.caption("AI & Full-Stack Developer")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- VIEW B: MAIN DOWNLOADER SCREEN -----------------
else:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📥 Download Ultra-HD Video or Audio")
    url = st.text_input("🔗 Paste YouTube, Instagram, or Social Media Link:", placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/...")
    download_type = st.radio("Format:", ["Video (MP4 - Best Quality)", "Audio Only (MP3/M4A)"], horizontal=True)

    if st.button("🚀 Fetch & Download Best Quality"):
        if not url.strip():
            st.error("Please paste a valid video link first.")
        else:
            with st.spinner("⚡ YumnaKashif AI is fetching the highest resolution video & audio streams..."):
                try:
                    temp_dir = tempfile.mkdtemp()
                    
                    if "Audio Only" in download_type:
                        format_str = "bestaudio[ext=m4a]/bestaudio/best"
                    else:
                        if FFMPEG_PATH:
                            if "720p" in st.session_state.global_quality:
                                format_str = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best"
                            elif "480p" in st.session_state.global_quality:
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
                            "quality": f"{height}p" if isinstance(height, int) else st.session_state.global_quality,
                            "url": url
                        })

                        st.success("✅ Best Quality Media Ready for Download!")
                        col1, col2 = st.columns([1, 2])
                        if thumbnail:
                            col1.image(thumbnail)
                        with col2:
                            st.markdown(f"#### {video_title}")
                            st.write(f"👤 **Creator:** {uploader}")
                            if duration:
                                st.write(f"⏱️ **Duration:** {int(duration) // 60}m {int(duration) % 60}s")
                            st.write(f"🎯 **Resolution Fetched:** {height}p" if isinstance(height, int) else f"🎯 **Quality:** {st.session_state.global_quality}")

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
