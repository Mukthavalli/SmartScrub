import os
import json
import uuid
import io
import pandas as pd
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

from quality_engine.analyzer import load_dataset, analyze_dataset, SUPPORTED_EXTENSIONS
from quality_engine.scorer import compute_score
from quality_engine.fixer import auto_fix
from quality_engine.ai_advisor import generate_suggestions

app = Flask(__name__, static_folder='static', static_url_path='')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

# In-memory session store (for single-server / demo use)
_sessions: dict = {}


from werkzeug.exceptions import HTTPException

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({'error': str(e.description)}), e.code
    return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/report')
def report():
    return app.send_static_file('report.html')


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lower()
    filename = secure_filename(original_filename)
    if not filename:
        filename = 'data_file' + ext

    # We removed the strict extension check to allow ANY file type as requested.
    # The analyzer will attempt to automatically detect and parse the format.

    # Save file
    session_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_FOLDER, session_id + ext)
    file.save(save_path)

    try:
        df, fmt = load_dataset(save_path)
        if df.empty:
            return jsonify({'error': 'Dataset appears to be empty or could not be parsed.'}), 400

        analysis = analyze_dataset(df)
        scores = compute_score(analysis)
        suggestions = generate_suggestions(analysis, scores)

        # Build column heatmap data (missing % per column)
        heatmap = [
            {'column': c['name'], 'missing_pct': c['missing_pct'], 'issue_count': c['issue_count']}
            for c in analysis['columns']
        ]

        # Issue type breakdown for donut chart
        issue_types: dict = {}
        for issue in analysis['all_issues']:
            t = issue['type']
            issue_types[t] = issue_types.get(t, 0) + 1

        # Issues per column (bar chart)
        issues_per_col = [
            {'column': c['name'], 'count': c['issue_count']}
            for c in analysis['columns']
            if c['issue_count'] > 0
        ]
        issues_per_col.sort(key=lambda x: x['count'], reverse=True)

        response = {
            'session_id': session_id,
            'filename': filename,
            'format': fmt,
            'shape': analysis['shape'],
            'scores': scores,
            'analysis': {
                'missing': analysis['missing'],
                'duplicates': analysis['duplicates'],
                'type_issues': analysis['type_issues'],
                'outliers': analysis['outliers'],
                'inconsistencies': analysis['inconsistencies'],
                'empty_columns': analysis['empty_columns'],
                'constant_columns': analysis['constant_columns'],
                'total_issues': len(analysis['all_issues']),
            },
            'columns': analysis['columns'],
            'heatmap': heatmap,
            'issue_types': issue_types,
            'issues_per_col': issues_per_col[:15],  # Top 15
            'all_issues': analysis['all_issues'],
            'suggestions': suggestions,
        }

        # Store df for later download
        _sessions[session_id] = {'df': df, 'analysis': analysis, 'ext': ext, 'filename': filename}

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/api/download-fixed/<session_id>', methods=['GET'])
def download_fixed(session_id):
    sess = _sessions.get(session_id)
    if not sess:
        return jsonify({'error': 'Session not found or expired'}), 404

    mode = request.args.get('mode', 'safe')

    df = sess['df']
    analysis = sess['analysis']
    original_name = os.path.splitext(sess['filename'])[0]
    ext = sess.get('ext', '.csv').lower()

    fixed_df, fixes = auto_fix(df, analysis, mode=mode)

    buf = io.BytesIO()

    if ext in ['.xlsx', '.xls', '.xlsm']:
        fixed_df.to_excel(buf, index=False, engine='openpyxl')
        download_name = f"{original_name}_cleaned{ext}"
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif ext == '.json':
        # to_json returns a string, we need bytes
        json_str = fixed_df.to_json(orient='records')
        buf.write(json_str.encode('utf-8'))
        download_name = f"{original_name}_cleaned.json"
        mimetype = 'application/json'
    elif ext == '.parquet':
        fixed_df.to_parquet(buf, index=False)
        download_name = f"{original_name}_cleaned.parquet"
        mimetype = 'application/octet-stream'
    elif ext == '.tsv':
        str_buf = io.StringIO()
        fixed_df.to_csv(str_buf, index=False, sep='\t')
        buf.write(str_buf.getvalue().encode('utf-8'))
        download_name = f"{original_name}_cleaned.tsv"
        mimetype = 'text/tab-separated-values'
    else:
        # Default to CSV
        str_buf = io.StringIO()
        fixed_df.to_csv(str_buf, index=False)
        buf.write(str_buf.getvalue().encode('utf-8'))
        download_name = f"{original_name}_cleaned.csv"
        mimetype = 'text/csv'

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=download_name, mimetype=mimetype)


@app.route('/api/fixes-preview/<session_id>', methods=['GET'])
def fixes_preview(session_id):
    sess = _sessions.get(session_id)
    if not sess:
        return jsonify({'error': 'Session not found'}), 404
        
    mode = request.args.get('mode', 'safe')
    _, fixes = auto_fix(sess['df'], sess['analysis'], mode=mode)
    return jsonify({'fixes': fixes})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
