from flask import Flask, render_template, request, jsonify, send_file
from functions import extraxt_id, make_dirs, get_cover_art, get_volumes, get_chapters_images, make_cbr_cbz
import os
from dotenv import load_dotenv
import threading
from threading import Thread
import shutil
from pathlib import Path

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

@app.route('/downloads')
def downloads():
    manga_files = []
    data_dir = Path('data')
    
    if data_dir.exists():
        for manga_dir in data_dir.iterdir():
            if manga_dir.is_dir():
                manga_name = manga_dir.name
                for file in manga_dir.glob('*.cb[rz]'):
                    manga_files.append({
                        'name': manga_name,
                        'file': file.name,
                        'size': f"{file.stat().st_size / (1024*1024):.1f} MB",
                        'type': file.suffix[1:].upper()
                    })
    
    return render_template('downloads.html', manga_files=manga_files)

@app.route('/download/<path:manga_name>/<path:filename>')
def download_file(manga_name, filename):
    file_path = Path(f'data/{manga_name}/{filename}')
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/delete/<path:manga_name>', methods=['POST'])
def delete_manga(manga_name):
    manga_dir = Path(f'data/{manga_name}')
    if manga_dir.exists():
        try:
            shutil.rmtree(manga_dir)
            return jsonify({'message': f'Successfully deleted {manga_name}'})
        except Exception as e:
            return jsonify({'error': f'Failed to delete: {str(e)}'}), 500
    return jsonify({'error': 'Manga directory not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 