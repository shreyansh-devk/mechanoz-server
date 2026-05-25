from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, tempfile, os, base64

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'service': 'MechanzO Compile Server', 'status': 'online', 'version': '1.0.0'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'service': 'MechanzO Compile Server', 'status': 'online'})

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code', '')

    if not code.strip():
        return jsonify({'success': False, 'error': 'No code provided'})

    with tempfile.TemporaryDirectory() as tmpdir:
        sketch_dir = os.path.join(tmpdir, 'sketch')
        os.makedirs(sketch_dir)
        sketch_path = os.path.join(sketch_dir, 'sketch.ino')

        with open(sketch_path, 'w') as f:
            f.write(code)

        result = subprocess.run([
            'arduino-cli', 'compile',
            '--fqbn', 'esp32:esp32:esp32s3',
            '--output-dir', tmpdir,
            sketch_dir
        ], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': result.stderr or result.stdout
            })

        bin_file = None
        for f in os.listdir(tmpdir):
            if f.endswith('.bin') and 'bootloader' not in f and 'partitions' not in f:
                bin_file = os.path.join(tmpdir, f)
                break

        if not bin_file:
            return jsonify({'success': False, 'error': 'Binary not found after compile'})

        with open(bin_file, 'rb') as f:
            binary_data = f.read()

        return jsonify({
            'success': True,
            'binary': base64.b64encode(binary_data).decode('utf-8'),
            'size': len(binary_data)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
