import streamlit as st
from phi.agent import Agent
from phi.model.google import Gemini
from phi.tools.duckduckgo import DuckDuckGo
from google.generativeai import upload_file, get_file
import google.generativeai as genai

import time
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import os

# Ensure ffmpeg path is in PATH for yt_dlp
ffmpeg_path = r"C:\Users\Akram PC\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-full_build\bin"
if ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + ffmpeg_path

from yt_dlp import YoutubeDL

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

# Streamlit page configuration
st.set_page_config(
    page_title="Agentic AI Video & YouTube Summarizer 🚀🎥",
    page_icon="🚀",
    layout="wide"
)

# Stylish custom CSS
st.markdown("""
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .center {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Header Section
st.markdown('<div class="center big-font">🚀 Agentic AI Video & YouTube Summarizer 🎥</div>', unsafe_allow_html=True)
st.markdown('<div class="center">Summarize any video with multimodal AI | Created by Akram Mohammad</div>', unsafe_allow_html=True)
st.markdown("---")

# About Section
with st.expander("ℹ️ About this App", expanded=True):
    st.write("""
    This app allows you to **summarize any uploaded video or YouTube link** using advanced multimodal AI (Gemini via Phi) with optional web augmentation.
    
    **Features:**
    - 🎥 Upload `.mp4`, `.mov`, `.avi` files or paste YouTube links.
    - 🤖 AI-powered deep summarization and insight extraction.
    - 🔍 Supplementary web search using DuckDuckGo for additional context.
    - 📋 Clean, actionable summaries ready for notes or reports.
    
    **Usage:**
    1. Upload a video file or paste a YouTube link.
    2. Enter your query (e.g., "Summarize key points" or "List action items").
    3. Click **Analyze Video** and let the AI generate your summary.
    """)

@st.cache_resource
def initialize_agent():
    return Agent(
        name="Video AI Summarizer",
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[DuckDuckGo()],
        markdown=True,
    )

multimodal_Agent = initialize_agent()

# Upload or YouTube Link
st.subheader("📥 Upload a Video File or Provide a YouTube Link")

col1, col2 = st.columns(2)

with col1:
    video_file = st.file_uploader(
        "Upload Video",
        type=['mp4', 'mov', 'avi'],
        help="Upload a local video for summarization."
    )

with col2:
    youtube_url = st.text_input(
        "YouTube Video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste a YouTube link to process and summarize."
    )

video_path = None

if youtube_url.strip():
    with st.spinner("📥 Downloading YouTube video..."):
        try:
            ydl_opts = {
                'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'merge_output_format': 'mp4',
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                video_path = downloaded_file
            st.success("✅ YouTube video downloaded successfully.")
            st.video(video_path)
        except Exception as e:
            st.error(f"❌ Failed to download YouTube video: {e}")

elif video_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
        temp_video.write(video_file.read())
        video_path = temp_video.name
    st.success("✅ Video uploaded successfully.")
    st.video(video_path, format="video/mp4", start_time=0)

if video_path:
    user_query = st.text_area(
        "💡 What insights are you seeking?",
        placeholder="Example: Summarize the key points or extract important events from the video.",
        help="Provide a clear question or instruction for what you want the AI to extract."
    )

    if st.button("🚀 Analyze Video"):
        if not user_query.strip():
            st.warning("⚠️ Please enter a query before analyzing the video.")
        else:
            try:
                with st.spinner("🤖 Uploading and analyzing your video..."):
                    processed_video = upload_file(video_path)
                    while processed_video.state.name == "PROCESSING":
                        time.sleep(1)
                        processed_video = get_file(processed_video.name)

                    analysis_prompt = (
                        f"""
                        Analyze the uploaded video for content and context.
                        Respond to the following user query using video insights and relevant supplementary context:
                        {user_query}

                        Provide a detailed, user-friendly, and actionable summary.
                        """
                    )

                    response = multimodal_Agent.run(analysis_prompt, videos=[processed_video])

                st.subheader("📋 Your AI Summary:")
                st.markdown(response.content)

            except Exception as error:
                st.error(f"❌ An error occurred during analysis: {error}")
            finally:
                try:
                    Path(video_path).unlink(missing_ok=True)
                except Exception:
                    pass
else:
    st.info("⬆️ Please upload a video file or provide a YouTube link to begin analysis.")

import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

def save_to_google_drive(content, file_name):
    """
    This function takes your AI text and saves it as a Google Doc.
    """
    # 1. Access the "Key" (either from a file or Streamlit Secrets)
    # If using Streamlit Secrets, you'd use st.secrets["GCP_SERVICE_ACCOUNT"]
    try:
        # For testing locally, just use the file
        creds_info = json.load(open("service_account.json"))
        creds = service_account.Credentials.from_service_account_info(
            creds_info, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)

        # 2. File Settings
        folder_id = "PASTE_YOUR_CLIENTS_FOLDER_ID_HERE" # The ID is the long string at the end of the Folder URL
        file_metadata = {
            'name': file_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.document' 
        }

        # 3. Perform the Upload
        fh = io.BytesIO(content.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        return f"Success! File created with ID: {file.get('id')}"
    
    except Exception as e:
        return f"Error: {str(e)}"

# --- BUTTON IN YOUR UI ---
if st.button("🚀 Deliver to Client's Google Drive"):
    # ai_final_post is the text from your LinkedIn logic
    result = save_to_google_drive(ai_final_post, "LinkedIn_Draft_Today")
    st.success(result)

# Footer
st.markdown("---")
st.markdown('<div class="center">Made with ❤️ by Korewole Onire</div>', unsafe_allow_html=True)
