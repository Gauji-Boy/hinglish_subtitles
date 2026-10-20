"""
app.py - Streamlit Web UI for Hinglish Subtitle Generator with GPU Acceleration.
Allows users to upload video, choose language mode, Whisper model, and compute device (CUDA GPU / CPU),
transcribe speech at high speed, preview synchronized subtitles, and download SRT files.
"""

import os
import tempfile
import streamlit as st
from hinglish_engine import generate_subtitles, get_hardware_info

st.set_page_config(
    page_title="Hinglish Subtitle Generator (GPU Accelerated)",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Detect Hardware
hw_info = get_hardware_info()

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #1E293B;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .hw-badge-gpu {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .hw-badge-cpu {
        background-color: #64748B;
        color: white;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
    .stat-pill {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Hinglish Subtitle Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Transcribe videos and automatically convert Hindi & Code-Mixed speech into natural Latin-script Hinglish subtitles.</div>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚡ Hardware & Settings")
    
    # Hardware Status Badge
    if hw_info["cuda_available"]:
        st.markdown(f'<div class="hw-badge-gpu">🚀 GPU: {hw_info["device_name"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hw-badge-cpu">💻 Hardware: CPU (Standard)</div>', unsafe_allow_html=True)

    device_selection = st.selectbox(
        "Acceleration Device",
        options=["auto", "cuda", "cpu"] if hw_info["cuda_available"] else ["cpu"],
        format_func=lambda x: {
            "auto": f"Auto (Recommended: {hw_info['recommended_device'].upper()})",
            "cuda": f"NVIDIA GPU (CUDA - {hw_info['device_name']})",
            "cpu": "CPU (Safe Mode)"
        }[x],
        index=0,
        help="CUDA leverages your RTX GPU Tensor Cores for 10x-25x faster processing."
    )

    model_size = st.selectbox(
        "Whisper Model Size",
        options=["small", "medium", "large-v3-turbo", "large-v3", "tiny"],
        index=1,
        help="'small' is fast with low RAM. 'medium' and 'large-v3-turbo' offer studio-grade accuracy for rapid or accented speech."
    )

    st.markdown("---")
    st.header("🌐 Audio Language")

    language_mode = st.selectbox(
        "Spoken Language Mode",
        options=["mixed", "hi", "en", "auto"],
        format_func=lambda x: {
            "mixed": "Mixed (Hindi + English) [Recommended]",
            "hi": "Hindi (Pure Devanagari)",
            "en": "English",
            "auto": "Auto-Detect Language"
        }[x],
        index=0,
        help="Select the speech style in your video."
    )

    st.markdown("---")
    st.markdown("""
    **💡 Tips:**
    - **RTX 4050 GPU**: Transcribes in `float16` at blistering speed.
    - **Large-v3**: Best for noisy backgrounds or fast code-mixed dialogue.
    - **Hinglish Normalizer**: Automatically handles English loanwords (`subscribe`, `video`, etc.) and natural grammar.
    """)

# Main Content
col_upload, col_preview = st.columns([1, 1], gap="medium")

with col_upload:
    st.subheader("1. Upload Media")
    uploaded_file = st.file_uploader(
        "Choose a video or audio file",
        type=["mp4", "mov", "mkv", "avi", "webm", "mp3", "wav", "m4a", "aac", "flac", "ogg"],
        help="Supported formats: MP4, MOV, MKV, AVI, WEBM, MP3, WAV, M4A, AAC, FLAC, OGG"
    )

    if uploaded_file is not None:
        ext = uploaded_file.name.split('.')[-1].lower()
        if ext in ["mp3", "wav", "m4a", "aac", "flac", "ogg"]:
            st.audio(uploaded_file)
        else:
            st.video(uploaded_file)
        file_details = f"**File:** `{uploaded_file.name}` | **Size:** `{uploaded_file.size / (1024*1024):.2f} MB`"
        st.markdown(file_details)

with col_preview:
    st.subheader("2. Generate Subtitles")
    if uploaded_file is None:
        st.info("👈 Upload a video on the left to begin.")
    else:
        generate_btn = st.button("🚀 Generate Hinglish Subtitles", type="primary", use_container_width=True)

        if generate_btn:
            # Save uploaded video to temporary file
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_video:
                tmp_video.write(uploaded_file.read())
                temp_video_path = tmp_video.name

            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress(pct: float, message: str):
                progress_bar.progress(pct)
                status_text.text(f"⏳ {message}")

            try:
                results = generate_subtitles(
                    video_path=temp_video_path,
                    language_choice=language_mode,
                    model_size=model_size,
                    device=device_selection,
                    progress_callback=update_progress
                )

                st.session_state["sub_results"] = results
                st.session_state["video_name"] = os.path.splitext(uploaded_file.name)[0]
                status_text.success(f"✅ Generated in {results['elapsed_time']:.1f}s ({results['speed_factor']:.1f}x real-time) on {results['active_device'].upper()}!")

            except Exception as e:
                st.error(f"Error during subtitle generation: {str(e)}")
            finally:
                if os.path.exists(temp_video_path):
                    try:
                        os.remove(temp_video_path)
                    except Exception:
                        pass

# Display Results if available
if "sub_results" in st.session_state:
    st.markdown("---")
    st.subheader("3. Subtitle Results & Downloads")

    results = st.session_state["sub_results"]
    base_name = st.session_state.get("video_name", "subtitles")

    # Performance Stats Banner
    st.markdown(f"""
    <span class="stat-pill">⚡ Device: {results['active_device'].upper()} ({results['active_compute']})</span>
    <span class="stat-pill">⏱ Duration: {results['duration']:.1f}s</span>
    <span class="stat-pill">⚡ Processing Time: {results['elapsed_time']:.1f}s</span>
    <span class="stat-pill">🚀 Speed: {results['speed_factor']:.1f}x real-time</span>
    """, unsafe_allow_html=True)
    st.markdown("")

    # Download Buttons Row
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
    with btn_col1:
        st.download_button(
            label="📥 Download Hinglish SRT (.srt)",
            data=results["srt_hinglish"],
            file_name=f"{base_name}_hinglish.srt",
            mime="text/plain",
            use_container_width=True,
            type="primary"
        )
    with btn_col2:
        st.download_button(
            label="📄 Download Original SRT (.srt)",
            data=results["srt_original"],
            file_name=f"{base_name}_original.srt",
            mime="text/plain",
            use_container_width=True
        )
    with btn_col3:
        st.download_button(
            label="📝 Download Plain Text (.txt)",
            data=results["full_text"],
            file_name=f"{base_name}_hinglish.txt",
            mime="text/plain",
            use_container_width=True
        )

    # Subtitle View Tabs
    tab_hinglish, tab_comparison, tab_table = st.tabs([
        "Hinglish Subtitles (SRT)",
        "Comparison (Original vs Hinglish)",
        "Segment Inspector"
    ])

    with tab_hinglish:
        st.text_area(
            "Hinglish Subtitles (Ready for YouTube / Premiere)",
            value=results["srt_hinglish"],
            height=350
        )

    with tab_comparison:
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            st.markdown("**Original Whisper Transcription (Devanagari / English)**")
            st.text_area("Original SRT", value=results["srt_original"], height=320, key="orig_srt_area")
        with comp_col2:
            st.markdown("**Converted Hinglish (Latin Script)**")
            st.text_area("Hinglish SRT", value=results["srt_hinglish"], height=320, key="hing_srt_area")

    with tab_table:
        if results.get("segments"):
            st.dataframe(
                results["segments"],
                column_config={
                    "index": "Segment #",
                    "start_str": "Start",
                    "end_str": "End",
                    "original_text": "Original Text",
                    "hinglish_text": "Hinglish Subtitle"
                },
                hide_index=True,
                use_container_width=True
            )
