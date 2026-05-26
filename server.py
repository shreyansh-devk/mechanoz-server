from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, uuid, time, os

app = Flask(__name__)
CORS(app)

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO')  # format: username/mechanzo-server

@app.route('/', methods=['GET'])
def index():
    return jsonify({'service': 'MechanzO Compile Server', 'status': 'online'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'service': 'MechanzO Compile Server', 'status': 'online'})

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.json
    code = data.get('code', '')

    if not code.strip():
        return jsonify({'success': False, 'error': 'No code provided'})

    job_id = str(uuid.uuid4())[:8]

    # Trigger GitHub Actions workflow
    trigger_res = requests.post(
        f'https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/compile.yml/dispatches',
        headers={
            'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json'
        },
        json={
            'ref': 'main',
            'inputs': {
                'code': code,
                'callback_id': job_id
            }
        }
    )

    if trigger_res.status_code != 204:
        return jsonify({'success': False, 'error': f'Failed to trigger workflow: {trigger_res.text}'})

    # Wait for workflow to complete and find our run
    time.sleep(5)
    run_id = None

    for attempt in range(20):
        runs_res = requests.get(
            f'https://api.github.com/repos/{GITHUB_REPO}/actions/runs?event=workflow_dispatch&per_page=5',
            headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
        )
        runs = runs_res.json().get('workflow_runs', [])
        
        for run in runs:
            if run.get('status') in ('in_progress', 'completed') and \
               run.get('name') == 'Compile Arduino Sketch':
                run_id = run['id']
                break
        
        if run_id:
            break
        time.sleep(3)

    if not run_id:
        return jsonify({'success': False, 'error': 'Workflow did not start'})

    # Wait for completion
    for attempt in range(40):
        run_res = requests.get(
            f'https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}',
            headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
        )
        run_data = run_res.json()
        
        if run_data['status'] == 'completed':
            if run_data['conclusion'] != 'success':
                return jsonify({'success': False, 'error': 'Compilation failed. Check your code.'})
            break
        time.sleep(5)

    # Download artifact
    artifacts_res = requests.get(
        f'https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}/artifacts',
        headers={'Authorization': f'Bearer {GITHUB_TOKEN}'}
    )
    
    artifacts = artifacts_res.json().get('artifacts', [])
    target = next((a for a in artifacts if job_id in a['name']), None)

    if not target:
        return jsonify({'success': False, 'error': 'Binary artifact not found'})

    # Download binary
    dl_res = requests.get(
        target['archive_download_url'],
        headers={'Authorization': f'Bearer {GITHUB_TOKEN}'},
        allow_redirects=True
    )

    import zipfile, io, base64
    z = zipfile.ZipFile(io.BytesIO(dl_res.content))
    bin_file = next((n for n in z.namelist() if n.endswith('.bin') and 'bootloader' not in n and 'partitions' not in n), None)

    if not bin_file:
        return jsonify({'success': False, 'error': 'Binary not found in artifact'})

    binary_data = z.read(bin_file)

    return jsonify({
        'success': True,
        'binary': base64.b64encode(binary_data).decode('utf-8'),
        'size': len(binary_data)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)