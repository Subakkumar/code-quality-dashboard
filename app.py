import os
import json
import zipfile
import shutil
import tempfile
from flask import Flask, render_template, request, jsonify
from models import db, CodeAnalysis
from code_analyzer import PythonAnalyzer
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///code_quality.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY']                     = 'codequalitysecret'
app.config['MAX_CONTENT_LENGTH']             = 52428800  # 50MB

db.init_app(app)
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

with app.app_context():
    db.create_all()

# ── Helpers ────────────────────────────────────────────
def build_prompt(project_name, metrics, issues, score, source_type='zip'):
    issues_text = '\n'.join(
        f"- [{i['severity'].upper()}] {i['description']}"
        for i in issues
    ) or '- No major issues detected'

    long_funcs = metrics.get('long_functions', [])[:3]
    lf_text    = '\n'.join(
        f"  • {f['function']}() in {os.path.basename(f['file'])} ({f['lines']} lines)"
        for f in long_funcs
    ) or '  • None'

    missing_docs = metrics.get('missing_docstrings', [])[:5]
    md_text = ', '.join(f"{d['function']}()" for d in missing_docs) or 'None'

    return f"""You are a senior Python engineer reviewing a codebase.

Project: {project_name}
Source:  {source_type.upper()} upload

Metrics:
- Files:     {metrics.get('total_files', 0)}
- Lines:     {metrics.get('total_lines', 0):,}
- Functions: {metrics.get('total_functions', 0)}
- Classes:   {metrics.get('total_classes', 0)}

Issues Found:
{issues_text}

Longest functions flagged:
{lf_text}

Functions missing docstrings (first 5): {md_text}

Current Quality Score: {score}/10

Please provide:
1. **Assessment** — 2-3 sentences on the overall code quality
2. **Top 3 Quick Wins** — specific, actionable improvements with estimated score gain
3. **Priority Action** — the single most impactful change to make today
4. **Time Estimate** — realistic hours to reach 9/10

Be specific. Name actual functions and files where possible. Keep it concise."""

def run_groq(prompt: str) -> str:
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=900,
        temperature=0.4
    )
    return response.choices[0].message.content

def save_analysis(project_name, upload_type, source, metrics, issues, score, analysis_text):
    record = CodeAnalysis(
        project_name    = project_name,
        upload_type     = upload_type,
        source          = source,
        total_files     = metrics.get('total_files', 0),
        total_lines     = metrics.get('total_lines', 0),
        total_functions = metrics.get('total_functions', 0),
        metrics_json    = json.dumps(metrics),
        issues_json     = json.dumps(issues),
        quality_score   = score,
        analysis        = analysis_text
    )
    db.session.add(record)
    db.session.commit()
    return record

# ── Routes ─────────────────────────────────────────────
@app.route('/')
def index():
    analyses = CodeAnalysis.query.order_by(
        CodeAnalysis.created_at.desc()).limit(10).all()
    return render_template('index.html', analyses=analyses)

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Please upload a .zip file'}), 400

    temp_dir = None
    try:
        temp_dir    = tempfile.mkdtemp()
        zip_path    = os.path.join(temp_dir, file.filename)
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir)

        file.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        project_name = os.path.splitext(file.filename)[0]
        analyzer     = PythonAnalyzer(extract_dir)
        summary      = analyzer.analyze()

        metrics = summary['metrics']
        issues  = summary['issues']
        score   = summary['score']

        prompt        = build_prompt(project_name, metrics, issues, score, 'zip')
        analysis_text = run_groq(prompt)

        record = save_analysis(project_name, 'zip', file.filename,
                               metrics, issues, score, analysis_text)

        return jsonify({
            'success':         True,
            'analysis_id':     record.id,
            'project_name':    project_name,
            'quality_score':   score,
            'metrics':         metrics,
            'issues':          issues,
            'analysis':        analysis_text
        })

    except zipfile.BadZipFile:
        return jsonify({'error': 'Invalid zip file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/api/github', methods=['POST'])
def analyze_github():
    data    = request.get_json() or {}
    repo_url = data.get('repo_url', '').strip()

    if not repo_url:
        return jsonify({'error': 'No repo URL provided'}), 400
    if 'github.com' not in repo_url:
        return jsonify({'error': 'Please enter a valid GitHub URL'}), 400

    temp_dir = None
    try:
        from git import Repo
        temp_dir = tempfile.mkdtemp()
        repo_dir = os.path.join(temp_dir, 'repo')

        Repo.clone_from(repo_url, repo_dir, depth=1)

        project_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        analyzer     = PythonAnalyzer(repo_dir)
        summary      = analyzer.analyze()

        metrics = summary['metrics']
        issues  = summary['issues']
        score   = summary['score']

        prompt        = build_prompt(project_name, metrics, issues, score, 'github')
        analysis_text = run_groq(prompt)

        record = save_analysis(project_name, 'github', repo_url,
                               metrics, issues, score, analysis_text)

        return jsonify({
            'success':       True,
            'analysis_id':   record.id,
            'project_name':  project_name,
            'quality_score': score,
            'metrics':       metrics,
            'issues':        issues,
            'analysis':      analysis_text
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/api/analysis/<int:analysis_id>')
def get_analysis(analysis_id):
    record = CodeAnalysis.query.get(analysis_id)
    if not record:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(record.to_dict())

@app.route('/api/analyses')
def list_analyses():
    records = CodeAnalysis.query.order_by(
        CodeAnalysis.created_at.desc()).limit(20).all()
    return jsonify([r.to_dict() for r in records])

if __name__ == '__main__':
    app.run(debug=True, port=5008)