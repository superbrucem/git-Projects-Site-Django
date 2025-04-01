from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
import os
import yt_dlp
from django.conf import settings
from pathlib import Path

def index(request):
    return render(request, 'polls/index.html')

def process_youtube(request):
    if request.method == 'POST':
        youtube_url = request.POST.get('youtube_url')
        
        try:
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                # Add rate limiting
                'ratelimit': 1000000,  # 1M bytes per second
                # Add progress hooks if needed
                'progress_hooks': [],
                # Add retries
                'retries': 10,
                'fragment_retries': 10,
                'ignoreerrors': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(youtube_url, download=False)
                video_title = info['title']
                
                # Clean the filename to avoid issues
                video_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                # Download the video
                ydl.download([youtube_url])
                
                # Construct the output filename
                output_file = f"downloads/{video_title}.mp3"
                
                # Create a download URL - Fix the URL path to match our URL configuration
                download_url = f"/web/download/?file={video_title}.mp3"
                
                # Verify file exists before sending response
                if not os.path.exists(output_file):
                    raise Exception("Download failed - file not created")
                
                return JsonResponse({
                    'status': 'success',
                    'title': video_title,
                    'download_url': download_url
                })
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=400)
            
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def download_file(request):
    file_name = request.GET.get('file')
    if not file_name:
        return JsonResponse({'error': 'No file specified'}, status=400)
    
    # Use absolute path based on BASE_DIR
    file_path = os.path.join(settings.BASE_DIR, 'downloads', file_name)
    
    # Add debug print
    print(f"Attempting to download file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"File not found at path: {file_path}")
        return JsonResponse({'error': 'File not found'}, status=404)

    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Open file in binary mode
        file_handle = open(file_path, 'rb')
        
        # Create the streaming response
        response = StreamingHttpResponse(
            file_iterator(file_handle),
            content_type='audio/mpeg'
        )
        
        # Add headers
        response['Content-Length'] = file_size
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response['Accept-Ranges'] = 'bytes'
        
        return response
        
    except Exception as e:
        if 'file_handle' in locals():
            file_handle.close()
        print(f"Error during file download: {str(e)}")
        return JsonResponse({
            'error': f'Error during file download: {str(e)}'
        }, status=500)

def file_iterator(file_handle, chunk_size=8192):
    """
    Iterator to stream file in chunks
    """
    try:
        while True:
            chunk = file_handle.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        file_handle.close()
