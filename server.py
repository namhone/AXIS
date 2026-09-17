from flask import Flask, request, jsonify, send_file, send_from_directory
from pathlib import Path
import json
import datetime

app = Flask(__name__)
PROJECT_ROOT = Path(__file__).parent
DATA_FILE = Path(__file__).parent / 'data' / 'submissions.json'
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# Simple CORS for local testing
@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp

@app.route('/submit', methods=['POST', 'OPTIONS'])
def submit():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json() or {}
    entry = {
        'email': data.get('email'),
        'phone': data.get('phone'),
        'message': data.get('message', ''),
        'received_at': datetime.datetime.utcnow().isoformat() + 'Z'
    }
    # append to JSON file
    arr = []
    if DATA_FILE.exists():
        try:
            arr = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except Exception:
            arr = []
    arr.append(entry)
    DATA_FILE.write_text(json.dumps(arr, indent=2, ensure_ascii=False), encoding='utf-8')
    return jsonify({'status': 'ok', 'saved': entry})

@app.route('/list', methods=['GET'])
def list_entries():
    arr = []
    if DATA_FILE.exists():
        try:
            arr = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except Exception:
            arr = []
    return jsonify(arr)


# Small static proxy routes keep the standalone editor usable with
# `python server.py` as well as with a plain static server.
@app.route('/cv-builder/editor', methods=['GET'])
@app.route('/cv-builder/editor/', methods=['GET'])
def cv_builder_editor():
    return send_file(PROJECT_ROOT / 'pages' / 'cv-builder-editor.html')


@app.route('/', methods=['GET'])
def home():
    return send_file(PROJECT_ROOT / 'index.html')


@app.route('/css/<path:filename>', methods=['GET'])
def css_asset(filename):
    return send_from_directory(PROJECT_ROOT / 'css', filename)


@app.route('/js/<path:filename>', methods=['GET'])
def js_asset(filename):
    return send_from_directory(PROJECT_ROOT / 'js', filename)


@app.route('/components/<path:filename>', methods=['GET'])
def component_asset(filename):
    return send_from_directory(PROJECT_ROOT / 'components', filename)


@app.route('/assets/<path:filename>', methods=['GET'])
def image_asset(filename):
    return send_from_directory(PROJECT_ROOT / 'assets', filename)


@app.route('/pages/<path:filename>', methods=['GET'])
def page_asset(filename):
    return send_from_directory(PROJECT_ROOT / 'pages', filename)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
