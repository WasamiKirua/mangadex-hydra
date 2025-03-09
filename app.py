from flask import Flask, render_template, request, jsonify
from functions import extraxt_id, make_dirs, get_cover_art, get_volumes, get_chapters_images, make_cbr_cbz
import os
from dotenv import load_dotenv
import threading

app = Flask(__name__)
load_dotenv()

# Store download status
download_status = {}

def download_manga(manga_url, format_choice):
    try:
        # Get manga info
        manga_name = manga_url.split("/")[-1]
        manga_id = extraxt_id(manga_url)
        
        download_status[manga_name] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Initializing download...'
        }

        # Create directories
        make_dirs(manga_url)
        download_status[manga_name].update({'status': 'directories_created', 'progress': 10})

        # Get cover art
        get_cover_art(manga_id, manga_name)
        download_status[manga_name].update({'status': 'cover_downloaded', 'progress': 20})

        # Get volumes info
        get_volumes(manga_id, manga_name)
        download_status[manga_name].update({'status': 'volumes_info_downloaded', 'progress': 30})

        # Download chapters
        get_chapters_images(manga_name)
        download_status[manga_name].update({'status': 'chapters_downloaded', 'progress': 80})

        # Create archive
        make_cbr_cbz(manga_name, format_choice)
        download_status[manga_name].update({
            'status': 'completed',
            'progress': 100,
            'message': f'Download completed! Archive created as {manga_name}.{format_choice}'
        })

    except Exception as e:
        download_status[manga_name] = {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        manga_url = request.form.get('manga_url')
        format_choice = request.form.get('format_choice')
        
        # Start download in background
        thread = threading.Thread(
            target=download_manga,
            args=(manga_url, format_choice)
        )
        thread.start()

        manga_name = manga_url.split("/")[-1]
        return render_template('index.html', 
                             download_started=True,
                             manga_name=manga_name)
    return render_template('index.html')

@app.route('/status/<manga_name>')
def check_status(manga_name):
    return jsonify(download_status.get(manga_name, {
        'status': 'not_found',
        'message': 'Download not found'
    }))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 