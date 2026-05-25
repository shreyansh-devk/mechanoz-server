# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, tempfile, os, glob

app = Flask(__name__)
CORS(app)

@app.route('/flash', methods=['POST'])
def flash():
    data = request.json
    code = data.get('code', '')
    port = data.get('port', 'COM3')  # change to your port

    # Write code to temp sketch
    with tempfile.TemporaryDirectory() as tmpdir:
        sketch_dir = os.path.join(tmpdir, 'sketch')
        os.makedirs(sketch_dir)
        sketch_path = os.path.join(sketch_dir, 'sketch.ino')
        
        with open(sketch_path, 'w') as f:
            f.write(code)

        # Compile
        compile_result = subprocess.run([
            'arduino-cli', 'compile',
            '--fqbn', 'esp32:esp32:esp32s3',
            sketch_dir
        ], capture_output=True, text=True)

        if compile_result.returncode != 0:
            return jsonify({
                'success': False,
                'error': compile_result.stderr
            })

        # Upload
        upload_result = subprocess.run([
            'arduino-cli', 'upload',
            '--fqbn', 'esp32:esp32:esp32s3',
            '--port', port,
            sketch_dir
        ], capture_output=True, text=True)

        if upload_result.returncode != 0:
            return jsonify({
                'success': False,
                'error': upload_result.stderr
            })

        return jsonify({'success': True, 'message': 'Flashed successfully'})

@app.route('/ports', methods=['GET'])
def get_ports():
    result = subprocess.run(
        ['arduino-cli', 'board', 'list'],
        capture_output=True, text=True
    )
    return jsonify({'output': result.stdout})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)