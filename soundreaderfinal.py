import argparse
import colored
from colored import stylize
import numpy as np
import onnx
import onnxruntime
from tqdm import tqdm
import subprocess
import yt_dlp
import os
import time  # ✅ Required for measuring execution time
import datetime
import sys
import csv
import re
import gc
import shutil
from typing import List, Optional

sample_rate = 32000

global processing_batch, skipped_videos, existing_files_used, new_videos, videos_inferenced, skip_all, use_existing_all, log_precheck_results  # Ensure we use the global variable

def check_dependencies():
    """Ensures all required dependencies are installed before execution."""
    required_modules = ["numpy", "onnx", "onnxruntime", "yt_dlp", "tqdm", "colored"]
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    # Check if FFmpeg is installed
    if not shutil.which("ffmpeg"):
        missing_modules.append("ffmpeg (system dependency)")

    if missing_modules:
        print("❌ Missing dependencies detected:")
        for mod in missing_modules:
            print(f"   - {mod}")
        
        print("\n💡 To install missing Python modules, run:")
        print("   pip install " + " ".join([m for m in missing_modules if m != "ffmpeg (system dependency)"]))
        print("\n⚠️ If FFmpeg is missing, install it from: https://ffmpeg.org/download.html")
        sys.exit(1)  # Stop execution

#Pre-Check Log Function - Checks if YouTube URLs extracted from Playlist/Channel have already been processed
def precheck_log_for_urls(url_list, log_file="inference_log.csv"):
    """Pre-checks the log file for all extracted YouTube URLs to optimize batch processing."""
    log_results = {}

    if not os.path.exists(log_file):
        print("🟡 Log file not found. No previous processing detected.")
        return log_results  # ✅ No log means no previous processing.

    #print("\n🟢 Debugging Log Pre-Check:")
    #print(f"📜 Extracted Playlist URLs: {len(url_list)}")  
    #print("🔍 Checking log file entries...")  

    with open(log_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] in url_list:  # ✅ Only count videos that exist in the extracted playlist
                video_id = row[0].split("watch?v=")[-1]  # ✅ Extract Video ID
                if video_id not in log_results:
                    log_results[video_id] = {"farts": False, "burps": False}
                if row[1] == "60":
                    log_results[video_id]["farts"] = True
                elif row[1] == "58":
                    log_results[video_id]["burps"] = True

                #print(f"   - ✅ Matched: {video_id} (Present in Playlist & Log)")

    #print(f"🟡 Total Processed Videos Found in Log: {len(log_results)}\n")  
    return log_results

#Check Log Function - Checks if a YouTube URL has already been downloaded+inferenced or not
def check_log(youtube_url, log_file="inference_log.csv"):
    """Checks if the YouTube URL exists in the log and returns which focus_idx values were processed."""
    if not os.path.exists(log_file):
        return False, False  # ✅ No log means no previous processing.

    processed_farts = False
    processed_burps = False

    with open(log_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
                                              
        for row in reader:
            if row and row[0] == youtube_url:  # ✅ First column contains URL
                if row[1] == "60":
                    processed_farts = True
                elif row[1] == "58":
                    processed_burps = True

    return processed_farts, processed_burps

#Pre-Check Files based on Video IDs - When processing URL batch, it pre-check if files exist
def precheck_files_for_urls(url_list):
    """Pre-checks if audio files for extracted YouTube URLs already exist."""
    file_results = {}
    possible_extensions = ['.opus', '.m4a', '.mp3', '.mp4']
    
    for url in url_list:
        video_id = url.split("watch?v=")[-1]  # ✅ Extract video ID correctly

        for ext in possible_extensions:
            for file in os.listdir("."):
                if video_id in file and file.endswith(ext):  # ✅ Match video ID with filename
                    file_results[video_id] = file
                    break  # ✅ Stop searching once found
            if video_id in file_results:  
                break  # ✅ Move to the next URL if a match was found
    return file_results

def log_inference(youtube_url, focus_idx, video_title, log_file="inference_log.csv"):
    """Logs the YouTube URL, focus_idx, timestamp, and video title after inference."""
    if not youtube_url.startswith("http") or "tiktok.com" in youtube_url:  # ✅ Skip logging if it's a local file
        return  

    timestamp = datetime.datetime.now().strftime("%d/%m/%Y_%H:%M:%S")

    # ✅ Append the entry to the CSV file
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([youtube_url, focus_idx, timestamp, video_title])

def extract_playlist_urls(playlist_url, cookies=None):
    """Extracts all video URLs from a YouTube playlist."""
    print(f"📜 Extracting video URLs from playlist: {playlist_url}...")
    
    options = {
        'quiet': True,
        'extract_flat': True,  # ✅ Extracts video URLs without downloading
        'force_generic_extractor': True
    }

    if cookies:
        options['cookiefile'] = os.path.abspath(cookies)

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(playlist_url, download=False)
            urls = [entry['url'] for entry in info_dict.get('entries', []) if 'url' in entry]
            print(f"✅ Extracted {len(urls)} video URLs from playlist.")
            return urls
        except Exception as e:
            print(f"❌ Failed to extract playlist URLs: {e}")
            return []

def extract_channel_videos(channel_url, cookies=None):
    """Extracts video URLs from a YouTube channel's 'Videos' tab."""
    print(f"📜 Extracting video URLs from channel: {channel_url}...")

    options = {
        'quiet': True,
        'extract_flat': True,  # ✅ Prevents downloading, only extracts URLs
        'cookiefile': os.path.abspath(cookies) if cookies else None,
        'force_generic_extractor': False  # ✅ yt-dlp now automatically selects best extractor
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(channel_url, download=False)
            urls = [
                entry["url"].replace("/shorts/", "/watch?v=")  # ✅ Ensure Shorts URLs are converted
                for entry in info_dict.get("entries", []) if "url" in entry
            ]

            if not urls:
                print("⚠️ No video URLs found in this channel.")
                return []

            print(f"✅ Extracted {len(urls)} video URLs from channel.")
            return urls

        except Exception as e:
            print(f"❌ Error extracting channel videos: {e}")
            return []

def extract_tiktok_videos(account_url, cookies=None):
    """Extracts video URLs from a TikTok user's page and saves them to a file."""
    print(f"📜 Extracting video URLs from TikTok account: {account_url}...")

    # ✅ Extract the account name (e.g., @vitinlove)
    match = re.search(r"tiktok\.com/@([^/?]+)", account_url)
    account_name = match.group(1) if match else "Unknown"

    output_file = f"TikTokURLs - @{account_name}.txt"  # ✅ Updated filename format

    options = {
        'quiet': True,
        'extract_flat': True,
        'cookiefile': os.path.abspath(cookies) if cookies else None
    }

    urls = []

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(account_url, download=False)
            urls = [entry["url"] for entry in info_dict.get("entries", []) if "url" in entry]

            if urls:
                print(f"✅ Extracted {len(urls)} videos from TikTok account.")
                # 🔹 Save to file with account name
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(urls))
                print(f"💾 URLs saved to {output_file}")
                return urls
            else:
                print("⚠️ No video URLs extracted, attempting direct download.")

        except yt_dlp.utils.DownloadError as e:
            print(f"⚠️ Metadata extraction failed ({e}), proceeding with direct download.")
        except Exception as e:
            print(f"❌ Unexpected error while extracting TikTok videos: {e}, but continuing.")

    return []
use_existing_all = False  # ✅ Track if user wants to always use existing files

# 🔹 YouTube Audio Download Function
def download_audio(youtube_url, cookies=None, auto_redownload=False):
    """
    Downloads audio from YouTube using yt-dlp with --extract-audio.
    First, it checks if an audio file already exists (using the video title).
    If the file exists, it checks the log (using the YouTube URL) and, if logged,
    asks the user whether to run inference again.
    If no file exists (or if the user opts to re-download), it proceeds to download.
    """
    
    print(f"🎵 Checking if audio already exists for: {youtube_url}")
    global existing_files_used, new_videos, skip_all, use_existing_all, log_precheck_results
    possible_extensions = ['.opus', '.m4a', '.mp3', '.mp4']
    
    # ✅ Ensure cookies are passed in both metadata extraction and downloading
    metadata_options = {
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': True,
        'noplaylist': True  # ✅ Prevent playlist issues if a single URL is passed
    }

    if cookies:
        metadata_options['cookiefile'] = os.path.abspath(cookies)  # ✅ Use cookies when extracting metadata

    # 🔹 Fetch metadata using yt-dlp
    with yt_dlp.YoutubeDL(metadata_options) as ydl:
        try:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_title = info_dict.get("title", None)
            video_id = info_dict.get("id", None)  # ✅ Extract YouTube Video ID
        except Exception as e:
            print(f"❌ Failed to retrieve video metadata. Error: {e}")
            return None, None  # ✅ Exit gracefully instead of crashing

    # ✅ Ensure cookies are passed to the actual download step
    download_options = {
        'format': 'bestaudio[ext=m4a]/bestaudio',        'outtmpl': '%(title)s [%(id)s].%(ext)s',        'quiet': False,
        'concurrent_fragment_downloads': 20,
        'n_threads': 16,                      
        'throttled_rate': 'inf',
        'http_chunk_size': 10485760            
    }

    if cookies:
        download_options['cookiefile'] = os.path.abspath(cookies)  # ✅ Use cookies when downloading

    # ✅ Step 1: Check log file BEFORE looking for the audio file.
    if processing_batch:
        processed_farts, processed_burps = log_precheck_results.get(video_id, {"farts": False, "burps": False}).values()
    else:
        processed_farts, processed_burps = check_log(youtube_url)  # ✅ Restore check for single URLs

    # ✅ Step 2: Check if the file exists based on video ID, not title.
    if processing_batch:
        existing_file = file_precheck_results.get(video_id)
        if existing_file:
            print(f"✅ Found existing audio file: {existing_file}")
    else:
        existing_file = None
        if video_id:
            for ext in possible_extensions:
                for file in os.listdir("."):
                    if video_id in file and file.endswith(ext):
                        existing_file = file
                        print(f"✅ Found existing audio file: {existing_file}")
                        break
                if existing_file:
                    break  # ✅ Exit loop once a match is found

    # ✅ Step 2.1: Handle potential duplicate file (exists but not logged)
    if existing_file and not (processed_farts or processed_burps):  # ✅ File exists but wasn't logged
        if use_existing_all:
            print("🔹 Using existing file due to 'Use All' selection.")
            existing_files_used += 1
            return existing_file, video_title

        print(f"⚠️ A file for this video already exists: {existing_file}")
        user_input = input("Do you want to use the existing file? (Y/N/A for Apply 'Y' to All): ").strip().lower()

        if user_input == 'a':  # ✅ Apply "Use Existing" to all
            use_existing_all = True
            print("🔹 Using existing file for all remaining videos.")
            existing_files_used += 1  # ✅ Count videos where existing file was used
            return existing_file, video_title

        elif user_input == 'y':  # ✅ Use existing file for this one
            print("🔹 Using existing file.")
            existing_files_used += 1  # ✅ Count videos where existing file was used
            return existing_file, video_title

        elif user_input == 'n':  # ✅ Re-download file
            print("🔄 Re-downloading audio...")
            os.remove(existing_file)  # ✅ Delete old file before downloading
            existing_file = None  # ✅ Ensure the script knows it must download a new file

    # ✅ Step 3: If file exists AND inference is logged, generate warning message dynamically.
    if existing_file:
        if processed_farts or processed_burps:
            focus_message = []
            if processed_farts:
                focus_message.append("farts")
            if processed_burps:
                focus_message.append("burps")
            focus_text = " and ".join(focus_message)
        
            # ✅ If "Skip All" was selected earlier, automatically skip
            if skip_all:
                print("⏭️ Skipping this video due to 'Skip All' selection.")
                #skipped_videos += 1  # ✅ Count videos skipped due to user choice
                return None, None
            
            # ✅ Ensure `user_input` is always defined to prevent reference errors
            user_input = None
            
            # ✅ Ask user if they want to re-run inference
            if processing_batch and args.files == urls:
                print("🔄 Skipping redundant warnings since batch re-run was selected.")
            else:
                warning_message = f"⚠️ This video has already been processed for {focus_text}.\n"
                if processing_batch:
                    user_input = input(warning_message + "Do you want to run inference again? (Y/N/A for Apply 'N' to All): ").strip().lower()
                else:
                    user_input = input(warning_message + "Do you want to run inference again? (Y/N): ").strip().lower()

            if user_input == 'a':  # ✅ Skip all remaining videos
                skip_all = True
                print("⏭️ Skipping all remaining videos in this batch.")
                return None, None  

            elif user_input == 'n':  # ✅ Skip only this video
                print("⏭️ Skipping this video.")
                #skipped_videos += 1  # ✅ Count videos skipped due to user choice
                return None, None    

        return existing_file, video_title  # ✅ Returns both the filename and video title

    # If no file exists but the log indicates previous processing, ask if re-download is desired.
    if processed_farts or processed_burps:
        focus_message = []
        if processed_farts:
            focus_message.append("farts")
        if processed_burps:
            focus_message.append("burps")
        focus_text = " and ".join(focus_message)
        if auto_redownload:
            print("🔄 Automatically re-downloading missing file (selected 'A' for all).")
        else:            
            user_input = input(
                f"⚠️ This video has already been processed for {focus_text}, but the audio file is missing.\n"
                "Do you want to re-download it? (Y/N): "
            ).strip().lower()
            if user_input != 'y':
                print(f"⏭️ Skipping this video. processing_batch={processing_batch}")
                if processing_batch:
                    print("✅ Continuing to next video in batch.")
                    return None, None
                else:
                    print("❌ Exiting script for single video.")
                    sys.exit(1)

    # Proceed to download if we get here.
    options = {
        'format': 'bestaudio[ext=m4a]/bestaudio',        'outtmpl': '%(title)s [%(id)s].%(ext)s',        'quiet': False,
        'concurrent_fragment_downloads': 20,
        'n_threads': 16,                      
        'throttled_rate': 'inf',
        'http_chunk_size': 10485760               
    }
    if cookies:
        options['cookiefile'] = os.path.abspath(cookies)
    
    with yt_dlp.YoutubeDL(options) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        file_name = ydl.prepare_filename(info_dict)
        # ✅ Extract base filename correctly (remove only the last extension)
        base_name = os.path.splitext(file_name)[0]  # Removes the last extension (e.g., ".webm", ".m4a")

        # ✅ Check for expected file extensions
        for ext in possible_extensions:
            expected_file = f"{base_name}{ext}"  # Append extension correctly
            if os.path.exists(expected_file):
                print(f"✅ Audio downloaded & converted: {expected_file}")
                new_videos += 1  # ✅ Count newly downloaded and processed videos
                return expected_file, video_title

        raise RuntimeError("❌ Failed to find the downloaded audio file.")

def download_tiktok(tiktok_url, cookies=None):
    """Downloads TikTok video and extracts audio for inference."""
    print(f"🎵 Checking if TikTok video already exists: {tiktok_url}")

    possible_extensions = ['.mp4', '.opus', '.m4a', '.mp3']

    metadata_options = {
        'quiet': True,
        'skip_download': True
    }

    if cookies:
        metadata_options['cookiefile'] = os.path.abspath(cookies) # ✅ Use cookies when extracting metadata

    with yt_dlp.YoutubeDL(metadata_options) as ydl:
        try:
            info_dict = ydl.extract_info(tiktok_url, download=False)
            video_title = info_dict.get("title", "Unknown TikTok Video")
            video_id = info_dict.get("id", None)
        except Exception as e:
            print(f"❌ Video data could not be extracted for {tiktok_url}. Logging URL and moving to the next video.")
            
            # ✅ Log failed URL
            log_failed_tiktok(tiktok_url)
            print("⏭️ Skipping video due to failed extraction.") # ✅ Explicitly indicate skipping
            return None, None  # ✅ Skip this video and continue

    # Check if file already exists
    existing_file = None
    for ext in possible_extensions:
        for file in os.listdir("."):
            if video_id in file and file.endswith(ext):
                existing_file = file
                print(f"✅ Found existing TikTok file: {existing_file}")
                break
        if existing_file:
            break

    if existing_file:
        return existing_file, video_title  # Use existing file without re-downloading

    # Download TikTok video
    download_options = {
        'format': 'mp4/bestaudio/best',
        'outtmpl': f"%(title)s [%(id)s].mp4",
        'quiet': False
    }

    if cookies:
        download_options['cookiefile'] = os.path.abspath(cookies)  # ✅ Use cookies when downloading
        
    with yt_dlp.YoutubeDL(download_options) as ydl:
        try:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            file_name = ydl.prepare_filename(info_dict)
            return file_name, video_title
        except Exception as e:
            print(f"❌ Failed to download TikTok video. Error: {e}")
            return None, None

def log_failed_tiktok(tiktok_url):
    """Logs failed TikTok URLs to a file for retrying later."""
    match = re.search(r"tiktok\.com/@([^/?]+)", tiktok_url)
    account_name = match.group(1) if match else "Unknown"
    failed_log_file = f"TikTokFailedURLs - @{account_name}.txt"

    with open(failed_log_file, "a", encoding="utf-8") as f:
        f.write(f"{tiktok_url}\n")
    
    print(f"💾 Logged failed URL to {failed_log_file}")

def download_twitch(twitch_url, cookies=None):
    """Downloads Twitch VOD or clip and extracts audio for inference."""
    print(f"🎵 Checking if Twitch video already exists: {twitch_url}")

    possible_extensions = ['.opus', '.m4a', '.mp3', '.mp4']

    metadata_options = {
        'quiet': True,
        'skip_download': True
    }

    if cookies:
        metadata_options['cookiefile'] = os.path.abspath(cookies)

    with yt_dlp.YoutubeDL(metadata_options) as ydl:
        try:
            info_dict = ydl.extract_info(twitch_url, download=False)
            video_title = info_dict.get("title", "Unknown Twitch Video")
            video_id = info_dict.get("id", None)
        except Exception as e:
            print(f"❌ Failed to retrieve Twitch video info: {e}")
            return None, None

    # Verifica se o arquivo já existe
    existing_file = None
    for ext in possible_extensions:
        for file in os.listdir("."):
            if video_id in file and file.endswith(ext):
                existing_file = file
                print(f"✅ Found existing Twitch file: {existing_file}")
                break
        if existing_file:
            break

    if existing_file:
        return existing_file, video_title

    # Opções de download com conversão para .opus
    options = {
        'format': 'bestaudio[ext=m4a]/bestaudio',        'outtmpl': '%(title)s [%(id)s].%(ext)s',  # 🛠️ deixa o yt-dlp decidir a extensão        'quiet': False,
        'concurrent_fragment_downloads': 20,
        'n_threads': 16,                      
        'throttled_rate': 'inf',
        'http_chunk_size': 10485760           
    }

    if cookies:
        options['cookiefile'] = os.path.abspath(cookies)

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(twitch_url, download=True)
    # Tenta encontrar o .opus real usando o ID
            output_id = info_dict.get("id")
            expected_file = None

            for ext in possible_extensions:
                for file in os.listdir("."):
                    if output_id in file and file.endswith(ext):
                        expected_file = file
                        break
                if expected_file:
                     break

            if expected_file:
                print(f"✅ Audio downloaded & converted: {expected_file}")
                return expected_file, video_title
            else:
                raise RuntimeError("❌ Failed to locate downloaded Twitch audio file.")


        except Exception as e:
            print(f"❌ Error during Twitch video download: {e}")
            return None, None
        
def download_soop(soop_url, cookies=None):
    """Downloads Soop.live (AfreecaTV) VOD and extracts audio for inference."""
    print(f"🎵 Checking if Soop/Afreeca video already exists: {soop_url}")

    possible_extensions = ['.opus', '.m4a', '.mp3', '.mp4']

    metadata_options = {
        'quiet': True,
        'skip_download': True
    }

    if cookies:
        metadata_options['cookiefile'] = os.path.abspath(cookies)

    with yt_dlp.YoutubeDL(metadata_options) as ydl:
        try:
            info_dict = ydl.extract_info(soop_url, download=False)
            video_title = info_dict.get("title", "Unknown Soop Video")
            video_id = info_dict.get("id", None)
        except Exception as e:
            print(f"❌ Failed to retrieve Soop video info: {e}")
            return None, None

    # Verifica se o arquivo já existe
    existing_file = None
    for ext in possible_extensions:
        for file in os.listdir("."):
            if video_id in file and file.endswith(ext):
                existing_file = file
                print(f"✅ Found existing Soop file: {existing_file}")
                return existing_file, video_title

    # Opções para baixar e converter áudio
    options = {
        'format': 'bestaudio[ext=m4a]/bestaudio',        'outtmpl': '%(title)s [%(id)s].%(ext)s',        'quiet': False,
        'concurrent_fragment_downloads': 20,
        'n_threads': 16,                      
        'throttled_rate': 'inf',
        'http_chunk_size': 10485760   
    }

    if cookies:
        options['cookiefile'] = os.path.abspath(cookies)

    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            info_dict = ydl.extract_info(soop_url, download=True)
            if 'entries' in info_dict:
                info_dict = info_dict['entries'][0]  # 🔹 SoopLive entrega playlists às vezes, pega só o primeiro item
            file_name = ydl.prepare_filename(info_dict)
            base_name = os.path.splitext(file_name)[0]

            for ext in possible_extensions:
                expected_file = f"{base_name}.{ext}"
                if os.path.exists(expected_file):
                    print(f"✅ Audio downloaded & converted: {expected_file}")
                    return expected_file, video_title

            raise RuntimeError("❌ Failed to locate downloaded Soop audio file.")

        except Exception as e:
            print(f"❌ Error during Soop video download: {e}")
            return None, None
    
def chunker(seq: np.ndarray, size: int):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

# 🔹 Audio Processing Function (FFmpeg + Chunk Processing)
def load_audio(file: str, sr: int, chunk_size: int = 960000):
    """Loads an audio file using FFmpeg and processes it in chunks to avoid MemoryError."""
    cmd = [
        'ffmpeg', '-i', file, '-f', 's16le', '-ac', '1', '-acodec',
        'pcm_s16le', '-ar', str(sr), '-'
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=chunk_size)
        buffer = []
        while True:
            chunk = process.stdout.read(chunk_size * 2)  # Read in small chunks
            if not chunk:
                break

            audio_chunk = np.frombuffer(chunk, np.int16).astype(np.float32) / (2.0**15)
            buffer.append(audio_chunk)

        process.stdout.close()
        process.wait()

        # 🔴 Adicione este check aqui:
        if not buffer:
            raise RuntimeError(f"⚠️ No audio could be extracted from the file: {file}")

    except subprocess.SubprocessError as e:
        raise RuntimeError(f"❌ Failed to load audio: {str(e)}")

    return np.concatenate(buffer)

def seconds_to_hms(seconds):
    """Converts seconds into HH:MM:SS format."""
    hours, remainder = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def subsample(frame: np.ndarray, scale_factor: int) -> np.ndarray:
    """Reduces frame data to improve efficiency by downsampling."""
    subframe = frame[:len(frame) - (len(frame) % scale_factor)].reshape(-1, scale_factor)
    subframe_mean = subframe.max(axis=1)

    subsample = subframe_mean

    if len(frame) % scale_factor != 0:
        residual_frame = frame[len(frame) - (len(frame) % scale_factor):]
        residual_mean = residual_frame.max()
        subsample = np.append(subsample, residual_mean)

    return subsample

def print_results(scores: np.ndarray, precision: int, offset: int, top: np.ndarray, threshold: int):
    """Prints detected sounds in HH:MM:SS + confidence percentage format."""
    for i in top:
        score = int(scores[i] * 100)
        
        if score >= threshold:
            tqdm.write(
                seconds_to_hms(i * precision / 100 + offset) + ' ' +
                f'{score}%')
        else:
            break

def print_timestamps(framewise_output: np.ndarray, precision: int, threshold: int, focus_idx: int, offset: int):
    """Extracts and formats timestamps for detected sounds."""
    focus = framewise_output[:, focus_idx]
    subsampled_scores = subsample(focus, precision)
    top_indices = np.argpartition(subsampled_scores, -len(subsampled_scores))[-len(subsampled_scores):]
    sorted_confidence = np.sort(top_indices)

    # ✅ Fix: Ensure threshold is applied correctly
    actual_threshold = threshold / 100  # Convert user threshold to match score format
    filtered_indices = [i for i in sorted_confidence if subsampled_scores[i] >= actual_threshold]

    # ✅ Ensure at least one valid result exists
    if not filtered_indices:
        return  # If no timestamps pass the threshold, don't print anything
    
    print_results(subsampled_scores, precision, offset, filtered_indices, threshold)

check_dependencies()  # ✅ Ensure all dependencies are available before execution

rerun_main = True  # Control variable to restart main loop if needed

while rerun_main:
    rerun_main = False  # Reset flag before each run

    #🔹 Argument Parsing
    if __name__ == '__main__':
        parser = argparse.ArgumentParser(prog='bdetector', description='Scans audio files for sounds')
        parser.add_argument('files', metavar='f', nargs='+', type=str, help='Files to be processed (or YouTube link or .txt file)')
        parser.add_argument('--precision', metavar='p', nargs='?', type=int, default=1 * 100, help='Precision in ms')
        parser.add_argument('--threshold', metavar='t', nargs='?', type=int, default=20, help='Confidence threshold')
        parser.add_argument('--batch_size', metavar='b', nargs='?', type=int, default=960000, help='Batch size')

        focus_group = parser.add_mutually_exclusive_group()
        focus_group.add_argument('--focus_idx', metavar='i', type=int, help='Manually specify focus_idx')
        focus_group.add_argument('-F', action='store_const', const=60, dest='focus_idx', help='Set focus_idx to 60 (FARTS)')
        focus_group.add_argument('-B', action='store_const', const=58, dest='focus_idx', help='Set focus_idx to 58 (BURPS)')

        parser.add_argument('--model', metavar='m', type=str, help='Path to ONNX model', default="bdetectionmodel_05_01_23.onnx")
        parser.add_argument('--cookies', metavar='c', type=str, help='Path to cookies file (for age-restricted videos)', default=None)

        args = parser.parse_args()

        model = onnx.load(args.model)
        sess_options = onnxruntime.SessionOptions()
        sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.optimized_model_filepath = args.model

        ort_session = onnxruntime.InferenceSession(
            args.model,
            sess_options,
            providers=onnxruntime.get_available_providers()
        )

        # ✅ Initialize summary counters
        total_videos = 0
        skipped_videos = 0
        new_videos = 0
        existing_files_used = 0
        videos_inferenced = 0  # ✅ Track videos that ran inference

        first_file = args.files[0]
        
        # Detect platform type
        is_youtube = "youtube.com" in first_file or "youtu.be" in first_file
        is_tiktok_video = "tiktok.com" in first_file and "/video/" in first_file
        is_tiktok_channel = "tiktok.com/@" in first_file
        is_twitch_video = "twitch.tv/videos/" in first_file
        is_twitch_clip = "clips.twitch.tv/" in first_file
        is_soop = "soop.live" in first_file or "afreecatv.com" in first_file

        if is_tiktok_video:
            print("📜 Detected TikTok video. Processing as a single TikTok video...")
        elif is_tiktok_channel:
            print(f"📜 Detected TikTok account: {first_file}. Checking for existing TikTok URLs file...")

            match = re.search(r"tiktok\.com/@([^/?]+)", first_file)
            account_name = match.group(1) if match else "Unknown"
            tiktok_urls_file = f"TikTokURLs - @{account_name}.txt"

            if os.path.exists(tiktok_urls_file):
                print(f"💾 Found existing TikTok URLs file: {tiktok_urls_file}. Using saved URLs instead of extracting.")
                with open(tiktok_urls_file, "r", encoding="utf-8") as f:
                    extracted_urls = [line.strip() for line in f.readlines() if line.strip()]
            else:
                print("📜 Extracting TikTok URLs from account...")
                extracted_urls = extract_tiktok_videos(first_file, args.cookies)

            if extracted_urls:
                args.files = extracted_urls
            else:
                print("❌ No videos found in this TikTok account.")
                sys.exit(1)
        # ✅ Extract URLs in .txt file and Pre-Check Log
        elif first_file.endswith('.txt'):
            print(f"📜 Detected .txt file: {first_file}. Extracting YouTube URLs...")
            process_logged_missing = None  # ✅ Ensure it’s always defined
            with open(first_file, "r", encoding="utf-8") as f:
                urls = [
                    line.strip().replace("/shorts/", "/watch?v=")
                    for line in f.readlines()
                    if "youtube.com/watch?" in line or "youtu.be/" in line or "youtube.com/shorts/" in line
                ]

            if not urls:
                print("❌ No valid YouTube URLs found in the text file. Exiting.")
                sys.exit(1)

            # ✅ Pre-check log for these URLs
            log_precheck_results = precheck_log_for_urls(urls)
            
            # ✅ Pre-check file existence
            file_precheck_results = precheck_files_for_urls(urls)

            # ✅ Step 3: Show Pre-Processing Summary BEFORE processing
            # ✅ Find IDs that are in log but missing from file checks
            logged_but_missing_files = sum(1 for vid in log_precheck_results if vid not in file_precheck_results)
            # ✅ Find IDs that exist as files but have no corresponding log entry
            existing_but_not_logged = sum(1 for vid in file_precheck_results if vid not in log_precheck_results)
            videos_to_process = max(len(urls) - len(log_precheck_results), 0)  # Ensure non-negative

            # ✅ Filter URLs to process only required videos
            urls_to_process = []

            print("\n📊 Summary Before Processing:")
            print(f"   🎥 Total videos extracted: {len(urls)}")
            print(f"   🔍 Videos already processed (found in log): {len(log_precheck_results)}")
            print(f"   ✅ Existing files found: {len(file_precheck_results)}")
            print(f"   🔴 Logged videos with missing files: {logged_but_missing_files}")  # NEW
            print(f"   🟡 Existing files not found in log: {existing_but_not_logged}")  # NEW
            print(f"   🔄 Videos requiring download & processing: {videos_to_process}")

            # ✅ If ALL videos are logged AND ALL files exist, prompt for re-inference instead of re-processing
            if len(log_precheck_results) == len(urls) and len(file_precheck_results) == len(urls):
                print("✅ No new videos require downloading, but all extracted videos are fully processed and still exist.")
                
                user_input = input("Do you want to re-run inference for all videos? (Y/N): ").strip().lower()
                
                if user_input == 'y':  # ✅ Re-run all videos
                    print("🔄 Re-running inference for all extracted videos.")
                    urls_to_process = urls  # ✅ Reset file list to process all
                else:  # ✅ Exit normally
                    print("⏹️ Process terminated by user.")
                    sys.exit(0)

            # ✅ Ask user if they want to continue if mismatches exist
            elif len(log_precheck_results) > 0 and (logged_but_missing_files > 0 or existing_but_not_logged > 0 or videos_to_process != len(urls)):
                print("\n⚠️ Warning: There are inconsistencies between the log and existing files.")
                user_decision = input("Would you like to:\n"
                                      "(Y) Re-download only missing files (Logged videos with missing files)\n"
                                      "(N) Skip missing files that have been inferenced and process only new ones (Videos requiring download & processing) \n"
                                      "(A) Process all videos (Total videos extracted)\n"
                                      "(E) Exit script\n"
                                      "Enter choice (Y/N/A/E): ").strip().lower()

                if user_decision == 'n':
                    print("⏭️ Skipping re-downloading missing files and only processing new videos.")
                    process_logged_missing = False
                    
                    # ✅ Check if there are actually any new videos to process; exit if none exist
                    if videos_to_process == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'y':
                    print("🔄 Re-downloading only missing files.")
                    process_logged_missing = True
                    
                    # ✅ If no videos are logged, exit!
                    if len(log_precheck_results) == 0 or logged_but_missing_files == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'a':
                    print("🔄 Processing all extracted videos (new + missing + existing).")
                    process_logged_missing = "all"
                elif user_decision == 'e':
                    print("⏹️ Process terminated by user.")
                    exit()
                else:
                    print("⚠️ Invalid input. Defaulting to skipping re-download.")
                    process_logged_missing = False
                    
            for url in urls:
                video_id = url.split("watch?v=")[-1]
                log_entry_exists = video_id in log_precheck_results
                file_exists = video_id in file_precheck_results

                # ✅ If 'A' (All) was chosen, process all videos
                if process_logged_missing == "all":
                    urls_to_process.append(url)

                # ✅ If 'Y' (Re-download missing files), process only logged but missing files
                elif process_logged_missing == True and log_entry_exists and not file_exists and logged_but_missing_files > 0:
                    urls_to_process.append(url)

                # ✅ If 'N' (Skip missing files), process only new unlogged videos
                elif not process_logged_missing and not log_entry_exists:
                    urls_to_process.append(url)

                # ✅ If files exist but aren't logged, ask user (Handled later in existing checks)
                elif not log_entry_exists and file_exists:
                    urls_to_process.append(url)
            
            print(f"\n🎯 Filtered videos to process: {len(urls_to_process)} out of {len(urls)}")
            args.files = urls_to_process  # ✅ Update file list to process only necessary videos

            print(f"📜 Processing {len(urls_to_process)} videos from batch file...")

        elif "youtube.com/playlist?" in first_file or "&list=" in first_file:
            print(f"📜 Detected YouTube playlist: {first_file}. Extracting video URLs...")
            urls = extract_playlist_urls(first_file, args.cookies)
            # ✅ Convert Shorts URLs in extracted playlist videos
            urls = [
                url.replace("/shorts/", "/watch?v=") if "youtube.com/shorts/" in url else url
                for url in urls
            ]
            process_logged_missing = None  # ✅ Ensure it’s always defined

            if not urls:
                print("❌ No videos found in the playlist. Exiting.")
                sys.exit(1)

            # ✅ Pre-check log for these URLs
            log_precheck_results = precheck_log_for_urls(urls)
            
            # ✅ Pre-check file existence
            file_precheck_results = precheck_files_for_urls(urls)

            # ✅ Step 3: Show Pre-Processing Summary BEFORE processing
            # ✅ Find IDs that are in log but missing from file checks
            logged_but_missing_files = sum(1 for vid in log_precheck_results if vid not in file_precheck_results)
            # ✅ Find IDs that exist as files but have no corresponding log entry
            existing_but_not_logged = sum(1 for vid in file_precheck_results if vid not in log_precheck_results)
            videos_to_process = max(len(urls) - len(log_precheck_results), 0)  # Ensure non-negative
            
            # ✅ Filter URLs to process only required videos
            urls_to_process = []
            
            print("\n📊 Summary Before Processing:")
            print(f"   🎥 Total videos extracted: {len(urls)}")
            print(f"   🔍 Videos already processed (found in log): {len(log_precheck_results)}")
            print(f"   ✅ Existing files found: {len(file_precheck_results)}")
            print(f"   🔴 Logged videos with missing files: {logged_but_missing_files}")  # NEW
            print(f"   🟡 Existing files not found in log: {existing_but_not_logged}")  # NEW
            print(f"   🔄 Videos requiring download & processing: {videos_to_process}")
            
            #print("\n🟢 Debugging Summary Calculation:")
            #print(f"🔍 Total Extracted Videos: {len(urls)}")
            #print(f"📜 Video IDs in Playlist: {[url.split('watch?v=')[-1] for url in urls]}")  

            #print(f"\n🟢 Comparing Log Entries to Extracted Playlist:")
            #for vid in log_precheck_results:
                #if vid not in [url.split("watch?v=")[-1] for url in urls]:
                    #print(f"❌ Log Entry {vid} is NOT in extracted playlist!")

            #print(f"\n🟢 Comparing Extracted Playlist to Log Entries:")
            #for url in urls:
                #vid = url.split("watch?v=")[-1]
                #if vid not in log_precheck_results:
                    #print(f"❌ Extracted Video {vid} is NOT in Log!")                                          

            # ✅ If ALL videos are logged AND ALL files exist, prompt for re-inference instead of re-processing
            if len(log_precheck_results) == len(urls) and len(file_precheck_results) == len(urls):
                print("✅ No new videos require downloading, but all extracted videos are fully processed and still exist.")
                
                user_input = input("Do you want to re-run inference for all videos? (Y/N): ").strip().lower()
                
                if user_input == 'y':  # ✅ Re-run all videos
                    print("🔄 Re-running inference for all extracted videos.")
                    urls_to_process = urls  # ✅ Reset file list to process all
                else:  # ✅ Exit normally
                    print("⏹️ Process terminated by user.")
                    sys.exit(0)

            # ✅ Ask user if they want to continue if mismatches exist
            elif len(log_precheck_results) > 0 and (logged_but_missing_files > 0 or existing_but_not_logged > 0 or videos_to_process != len(urls)):
                print("\n⚠️ Warning: There are inconsistencies between the log and existing files.")
                user_decision = input("Would you like to:\n"
                                      "(Y) Re-download only missing files (Logged videos with missing files)\n"
                                      "(N) Skip missing files that have been inferenced and process only new ones (Videos requiring download & processing) \n"
                                      "(A) Process all videos (Total videos extracted)\n"
                                      "(E) Exit script\n"
                                      "Enter choice (Y/N/A/E): ").strip().lower()

                if user_decision == 'n':
                    print("⏭️ Skipping re-downloading missing files and only processing new videos.")
                    process_logged_missing = False
                    
                    # ✅ Check if there are actually any new videos to process; exit if none exist
                    if videos_to_process == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'y':
                    print("🔄 Re-downloading only missing files.")
                    process_logged_missing = True
                    
                    # ✅ If no videos are logged, exit!
                    if len(log_precheck_results) == 0 or logged_but_missing_files == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'a':
                    print("🔄 Processing all extracted videos (new + missing + existing).")
                    process_logged_missing = "all"
                elif user_decision == 'e':
                    print("⏹️ Process terminated by user.")
                    exit()
                else:
                    print("⚠️ Invalid input. Defaulting to skipping re-download.")
                    process_logged_missing = False

            for url in urls:
                video_id = url.split("watch?v=")[-1]
                log_entry_exists = video_id in log_precheck_results
                file_exists = video_id in file_precheck_results

                # ✅ If 'A' (All) was chosen, process all videos
                if process_logged_missing == "all":
                    urls_to_process.append(url)

                # ✅ If 'Y' (Re-download missing files), process only logged but missing files
                elif process_logged_missing == True and log_entry_exists and not file_exists and logged_but_missing_files > 0:
                    urls_to_process.append(url)

                # ✅ If 'N' (Skip missing files), process only new unlogged videos
                elif not process_logged_missing and not log_entry_exists:
                    urls_to_process.append(url)

                # ✅ If files exist but aren't logged, ask user (Handled later in existing checks)
                elif not log_entry_exists and file_exists:
                    urls_to_process.append(url)
            
            print(f"\n🎯 Filtered videos to process: {len(urls_to_process)} out of {len(urls)}")
            args.files = urls_to_process  # ✅ Update file list to process only necessary videos

            print(f"📜 Processing {len(urls_to_process)} videos from playlist...")

        elif "youtube.com/@".lower() in first_file or "youtube.com/c/".lower() in first_file or \
            "youtube.com/user/".lower() in first_file or "youtube.com/channel/".lower() in first_file:

            print(f"📜 Detected YouTube channel: {first_file}. Extracting video URLs...")
            urls = extract_channel_videos(first_file, args.cookies)
            # ✅ Convert Shorts URLs in extracted playlist videos
            urls = [
                url.replace("/shorts/", "/watch?v=") if "youtube.com/shorts/" in url else url
                for url in urls
            ]
            process_logged_missing = None  # ✅ Ensure it’s always defined

            if not urls:
                print("❌ No videos found in the channel. Exiting.")
                sys.exit(1)

            # ✅ Step 1: Pre-check log for these URLs
            log_precheck_results = precheck_log_for_urls(urls)
            
            # ✅ Step 2: Pre-check file existence
            file_precheck_results = precheck_files_for_urls(urls)
          
            # ✅ Step 3: Show Pre-Processing Summary BEFORE processing
            # ✅ Find IDs that are in log but missing from file checks
            logged_but_missing_files = sum(1 for vid in log_precheck_results if vid not in file_precheck_results)
            # ✅ Find IDs that exist as files but have no corresponding log entry
            existing_but_not_logged = sum(1 for vid in file_precheck_results if vid not in log_precheck_results)
            videos_to_process = max(len(urls) - len(log_precheck_results), 0)  # Ensure non-negative

            # ✅ Filter URLs to process only required videos
            urls_to_process = []

            print("\n📊 Summary Before Processing:")
            print(f"   🎥 Total videos extracted: {len(urls)}")
            print(f"   🔍 Videos already processed (found in log): {len(log_precheck_results)}")
            print(f"   ✅ Existing files found: {len(file_precheck_results)}")
            print(f"   🔴 Logged videos with missing files: {logged_but_missing_files}")  # NEW
            print(f"   🟡 Existing files not found in log: {existing_but_not_logged}")  # NEW
            print(f"   🔄 Videos requiring download & processing: {videos_to_process}")

            # ✅ If ALL videos are logged AND ALL files exist, prompt for re-inference instead of re-processing
            if len(log_precheck_results) == len(urls) and len(file_precheck_results) == len(urls):
                print("✅ No new videos require downloading, but all extracted videos are fully processed and still exist.")
                
                user_input = input("Do you want to re-run inference for all videos? (Y/N): ").strip().lower()
                
                if user_input == 'y':  # ✅ Re-run all videos
                    print("🔄 Re-running inference for all extracted videos.")
                    urls_to_process = urls  # ✅ Reset file list to process all
                else:  # ✅ Exit normally
                    print("⏹️ Process terminated by user.")
                    sys.exit(0)

            # ✅ Ask user if they want to continue if mismatches exist
            elif len(log_precheck_results) > 0 and (logged_but_missing_files > 0 or existing_but_not_logged > 0 or videos_to_process != len(urls)):
                print("\n⚠️ Warning: There are inconsistencies between the log and existing files.")
                user_decision = input("Would you like to:\n"
                                      "(Y) Re-download only missing files (Logged videos with missing files)\n"
                                      "(N) Skip missing files that have been inferenced and process only new ones (Videos requiring download & processing) \n"
                                      "(A) Process all videos (Total videos extracted)\n"
                                      "(E) Exit script\n"
                                      "Enter choice (Y/N/A/E): ").strip().lower()

                if user_decision == 'n':
                    print("⏭️ Skipping re-downloading missing files and only processing new videos.")
                    process_logged_missing = False
                    
                    # ✅ Check if there are actually any new videos to process; exit if none exist
                    if videos_to_process == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'y':
                    print("🔄 Re-downloading only missing files.")
                    process_logged_missing = True
                    
                    # ✅ If no videos are logged, exit!
                    if len(log_precheck_results) == 0 or logged_but_missing_files == 0:
                        print("✅ No new videos requiring download. Exiting script.")
                        sys.exit(0)  # ✅ Prevents unnecessary processing
                elif user_decision == 'a':
                    print("🔄 Processing all extracted videos (new + missing + existing).")
                    process_logged_missing = "all"
                elif user_decision == 'e':
                    print("⏹️ Process terminated by user.")
                    exit()
                else:
                    print("⚠️ Invalid input. Defaulting to skipping re-download.")
                    process_logged_missing = False

            for url in urls:
                video_id = url.split("watch?v=")[-1]
                log_entry_exists = video_id in log_precheck_results
                file_exists = video_id in file_precheck_results

                # ✅ If 'A' (All) was chosen, process all videos
                if process_logged_missing == "all":
                    urls_to_process.append(url)

                # ✅ If 'Y' (Re-download missing files), process only logged but missing files
                elif process_logged_missing == True and log_entry_exists and not file_exists and logged_but_missing_files > 0:
                    urls_to_process.append(url)

                # ✅ If 'N' (Skip missing files), process only new unlogged videos
                elif not process_logged_missing and not log_entry_exists:
                    urls_to_process.append(url)

                # ✅ If files exist but aren't logged, ask user (Handled later in existing checks)
                elif not log_entry_exists and file_exists:
                    urls_to_process.append(url)
            
            print(f"\n🎯 Filtered videos to process: {len(urls_to_process)} out of {len(urls)}")
            args.files = urls_to_process  # ✅ Update file list to process only necessary videos

            print(f"📜 Processing {len(urls_to_process)} videos from Channel...")

        # ✅ Detect if processing a batch (.txt, Playlist, YouTube Channel or TikTok Account)
        processing_batch = (
            first_file.endswith(".txt") or 
            "youtube.com/playlist" in first_file or 
            "youtube.com/@".lower() in first_file or 
            "youtube.com/c/".lower() in first_file or 
            "youtube.com/user/".lower() in first_file or 
            "youtube.com/channel/".lower() in first_file or
            ("tiktok.com/@" in first_file and "/video/" not in first_file)  # ✅ Ensure only TikTok channels
        )
        
        skip_all = False  # ✅ Track if user chose to skip all remaining videos

        # ✅ Process each URL one by one
        for i, file in enumerate(args.files):
            print(f"\n📌 Processing video {i + 1} out of {len(args.files)} in list to be processed")  # NEW MESSAGE
            
            total_videos += 1  # ✅ Count every video processed (regardless of result)
            original_youtube_url = file.replace("/shorts/", "/watch?v=")
            video_id = original_youtube_url.split("watch?v=")[-1]

            auto_redownload = (process_logged_missing == "all") if 'process_logged_missing' in locals() else False
            if "youtube.com" in file or "youtu.be" in file:
                file, video_title = download_audio(file, args.cookies, auto_redownload)

                # ✅ If user chose to skip, move to the next video
                if file is None:
                    skipped_videos += 1  # ✅ Count videos skipped due to user choice
                    continue
            elif "tiktok.com" in file and "/video/" in file:
                file, video_title = download_tiktok(file, args.cookies)

            elif "twitch.tv/videos/" in file or "clips.twitch.tv/" in file:
                file, video_title = download_twitch(file, args.cookies)

            elif "soop.live" in file or "vod.sooplive.co.kr" in file:
                file, video_title = download_soop(file, args.cookies)

                # ✅ If download failed, skip to the next video
                if file is None:
                    skipped_videos += 1  # ✅ Count videos skipped due to download failure
                    continue             
            else:
                video_title = file  # ✅ Use the filename as the title for local files

                # ✅ Skip only if processing a batch, otherwise exit normally
                if file is None:
                    if processing_batch:
                        continue  # ✅ Move to the next video in batch
                    else:
                        skipped_videos += 1
                        sys.exit(1)  # ✅ Exit for single URL or filename

            print(f"🎥 Video Title: {video_title}")
            print(f"🔍 Starting inference for: {file}")
            print("🔹 Loading audio...")
            audio = load_audio(file, sr=sample_rate)
            print("✅ Audio loaded successfully!")
            
            total_chunks = len(audio) // args.batch_size  # Standard batch calculation

            # ✅ Only add an extra batch if the remaining audio is at least 1 full sample frame
            remaining_audio = len(audio) % args.batch_size
            if remaining_audio > 0 and remaining_audio >= sample_rate:
                total_chunks += 1

            if not hasattr(args, 'focus_idx') or args.focus_idx is None:
                focus_idx_values = [60, 58]
            else:
                focus_idx_values = [int(args.focus_idx)]
                print(f"🔍 User-specified focus_idx: {args.focus_idx}")

            for focus_idx in focus_idx_values:
                offset = 0
                header = "🟣 FARTS" if focus_idx == 60 else "🟢 BURPS"
                print("\n" + stylize(header, colored.attr('bold')))
                
                for idx, chunk in enumerate(tqdm(chunker(audio, args.batch_size), total=total_chunks, leave=False)):
                    if idx >= total_chunks:
                        break  # ✅ Forcefully stop at total_chunks
                    chunk = chunk.reshape(1, -1)
                    ort_inputs = {'input': chunk}
                    framewise_output = ort_session.run(['output'], ort_inputs)[0]
                    print_timestamps(framewise_output[0], args.precision, args.threshold, focus_idx, offset)
                    offset += len(chunk[0]) / sample_rate
                    
                    del chunk

                log_inference(original_youtube_url, focus_idx, video_title)
            del audio
            videos_inferenced += 1  # ✅ Count videos where inference was run
            gc.collect()  # ✅ Force Python to free up unused memory
            print("✅ Inference completed for this file!")

        if processing_batch:
            print("\n📊 Summary Report:")
            print(f"   🎥 Total videos processed: {total_videos}")
            print(f"   🧠 Videos inferenced: {videos_inferenced}")  # ✅ New inference count
            print(f"   ✅ Previously existing files used: {existing_files_used}") #This counter only refers to videos that were not downloaded during the script run
            print(f"   🔄 Newly downloaded videos: {new_videos}")
            # ✅ Check for failed TikTok URLs
            if "tiktok.com/@" in first_file and not "/video/" in first_file:
                match = re.search(r"tiktok\.com/@([^/?]+)", first_file)
                account_name = match.group(1) if match else "Unknown"
                failed_log_file = f"TikTokFailedURLs - @{account_name}.txt"
                urls_file = f"TikTokURLs - @{account_name}.txt"

                if os.path.exists(failed_log_file):
                    with open(failed_log_file, "r", encoding="utf-8") as f:
                        failed_urls = f.readlines()

                    print(f"❌ Skipped videos: {len(failed_urls)}")
                    for url in failed_urls:
                        print(f"   - {url.strip()}")

                    retry = input("🔄 Retry failed downloads? (Y/N): ").strip().lower()
                    if retry == 'y':
                        print("♻️ Replacing URL list with failed URLs and restarting...")
                        with open(urls_file, "w", encoding="utf-8") as f:
                            f.writelines(url.strip() + "\n" for url in failed_urls)
                            rerun_main = True  # Set flag to rerun the loop
                        os.remove(failed_log_file)
                    else:
                        print("⏭️ Skipping retry.")
            else:
                print(f"   ⏭️ Skipped videos: {skipped_videos}")
