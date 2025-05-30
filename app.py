from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid
import threading
import time
import re

app = Flask(__name__)

# Directory to temporarily store downloaded videos
DOWNLOAD_DIR = 'temp_downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Max file retention time in seconds (e.g., 1 hour)
FILE_RETENTION_SECONDS = 3600

# --- Helper to download video using yt-dlp ---
def download_tiktok_video(tiktok_url, output_path_template):
    """
    Downloads a TikTok video using yt-dlp.
    Attempts to get a no-watermark version.
    """
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Prioritize mp4
        'outtmpl': output_path_template, # Template for output filename
        'noplaylist': True,
        'allow_unplayable_formats': True,
        'extractor_args': {
            'tiktok': ['--no-watermark'] # Instructs yt-dlp to try to find no-watermark versions
        },
        'quiet': True, # Suppress console output from yt-dlp
        'progress': False, # Suppress progress bar
        # Add a user agent to mimic a real browser, useful if TikTok blocks default requests
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extract_info downloads the video if 'download=True'
            info = ydl.extract_info(tiktok_url, download=True)
            # yt-dlp provides the full path of the downloaded file
            return ydl.prepare_filename(info)
    except Exception as e:
        app.logger.error(f"Error downloading TikTok: {e}")
        return None

# --- File Cleanup Thread ---
def cleanup_file(filepath):
    """Deletes a file after a specified delay."""
    time.sleep(FILE_RETENTION_SECONDS)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            app.logger.info(f"Cleaned up: {filepath}")
        except Exception as e:
            app.logger.error(f"Error cleaning up {filepath}: {e}")

# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serves other static files (CSS, JS, images)."""
    return app.send_static_file(path)

@app.route('/download-tiktok', methods=['POST'])
def handle_download_request():
    """Handles the video download request from the frontend."""
    data = request.get_json()
    tiktok_url = data.get('tiktokUrl')

    if not tiktok_url:
        return jsonify({'success': False, 'message': 'TikTok URL is required.'}), 400

    # Basic URL validation regex for TikTok
    # This regex is an improvement but still might not catch all edge cases.
    # A robust solution might involve checking response headers from TikTok directly.
    tiktok_regex = r"^(https?://)?(www\.)?(m\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com|t\.tiktok\.com|douyin\.com)/"
    if not re.match(tiktok_regex, tiktok_url):
        return jsonify({'success': False, 'message': 'Invalid TikTok or Douyin URL provided.'}), 400

    # Generate a unique filename to avoid conflicts and ensure security
    file_id = str(uuid.uuid4())
    # yt-dlp renames files. Use a placeholder in outtmpl and let it do its thing.
    # We will get the *actual* filename it creates from the return value.
    output_path_template = os.path.join(DOWNLOAD_DIR, file_id + '_%(title)s.%(ext)s')


    app.logger.info(f"Received download request for: {tiktok_url}")

    # Download the video
    try:
        actual_filepath = download_tiktok_video(tiktok_url, output_path_template)
    except Exception as e:
        app.logger.error(f"An unexpected error during yt-dlp call: {e}")
        return jsonify({'success': False, 'message': f'Failed to download video: {e}'}), 500


    if actual_filepath and os.path.exists(actual_filepath):
        # Extract just the filename for serving
        served_filename = os.path.basename(actual_filepath)
        
        # Start cleanup in a background thread
        threading.Thread(target=cleanup_file, args=(actual_filepath,)).start()

        app.logger.info(f"Successfully processed and will serve: {served_filename}")
        return jsonify({
            'success': True,
            'message': 'Video processed successfully. Initiating download.',
            'downloadLink': f'/download/{served_filename}' # Frontend will trigger this route
        })
    else:
        app.logger.warning(f"Failed to download/process video for URL: {tiktok_url}")
        return jsonify({'success': False, 'message': 'Could not download or process video. It might be private, removed, geo-restricted, or TikTok changed its format. Please try another URL.'}), 500

@app.route('/download/<filename>')
def serve_download(filename):
    """Serves the downloaded video file to the user."""
    # Ensure the filename is clean to prevent directory traversal attacks
    if not re.match(r"^[a-zA-Z0-9_\-\. ]+$", filename):
        return "Invalid filename", 400

    full_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(full_path):
        app.logger.warning(f"Requested file not found: {full_path}")
        return "File not found", 404
        
    app.logger.info(f"Serving file: {filename}")
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    # When running in development, Flask serves static files automatically.
    # In production, it's recommended to use a dedicated web server (like Nginx or Apache)
    # to serve static files and proxy dynamic requests to Flask (e.g., via Gunicorn/uWSGI).
    app.run(debug=True, port=5000)