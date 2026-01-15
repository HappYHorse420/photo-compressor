from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import webbrowser
from threading import Timer

from compressor import compress_image, batch_compress
from video_compressor import compress_video_to_target_mb


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # TODO: move to env var in production


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/compress', methods=['POST'])
def compress():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'})

        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'No file selected or invalid file type'})

        target_size_mb = request.form.get('target_size', default=10, type=int)

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"

        base_dir = os.path.abspath(os.path.dirname(__file__))
        compressed_dir = os.path.join(base_dir, 'static', 'compressed')
        uploads_dir = os.path.join(base_dir, 'static', 'uploads')
        os.makedirs(compressed_dir, exist_ok=True)
        os.makedirs(uploads_dir, exist_ok=True)

        output_path = os.path.join(compressed_dir, unique_filename)
        input_path = os.path.join(uploads_dir, unique_filename)

        file.save(input_path)
        compress_image(input_path, output_path, target_size_mb)

        compressed_size = os.path.getsize(output_path) / (1024 * 1024)
        file_url = url_for('static', filename=f'compressed/{unique_filename}')

        return jsonify({
            'success': True,
            'size': round(compressed_size, 2),
            'output_path': file_url
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    finally:
        if 'input_path' in locals() and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass


@app.route('/video', methods=['GET', 'POST'])
def video():
    if request.method == 'GET':
        return render_template('video.html')

    if 'video' not in request.files:
        flash('No video file part')
        return redirect(url_for('video'))

    file = request.files['video']
    if file.filename == '':
        flash('No video selected')
        return redirect(url_for('video'))

    try:
        target_mb = float(request.form.get('target_mb', '10'))
    except Exception:
        target_mb = 10.0

    base_dir = os.path.abspath(os.path.dirname(__file__))
    uploads_dir = os.path.join(base_dir, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    input_path = os.path.join(uploads_dir, unique_filename)

    file.save(input_path)

    try:
        out_path = compress_video_to_target_mb(input_path, target_mb)
        return send_file(out_path, as_attachment=True, download_name="compressed.mp4")
    except Exception as e:
        flash(f"Video compress failed: {e}")
        return redirect(url_for('video'))
    finally:
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass


def open_browser():
    """Open browser automatically when Flask starts (local dev only)"""
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        Timer(1.5, open_browser).start()
    app.run(debug=True)
