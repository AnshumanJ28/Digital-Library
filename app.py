import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDFS_DIR = os.path.join(BASE_DIR, 'pdfs')

CLASSES = ['class9', 'class10']
SUBJECTS = ['maths', 'science', 'social']

CLASS_MAP = {
    'class9': 'Class 9',
    'class10': 'Class 10'
}

SUBJECT_MAP = {
    'maths': 'Mathematics',
    'science': 'Science',
    'social': 'Social Science'
}

def setup_directories():
    """Create PDF directories if they don't exist."""
    for c in CLASSES:
        for s in SUBJECTS:
            path = os.path.join(PDFS_DIR, c, s)
            os.makedirs(path, exist_ok=True)

# Run directory setup on startup
setup_directories()

# No login or authentication active

def scan_pdfs_recursive(subject_dir):
    """
    Scan a subject directory for PDFs, including inside sub-folders.
    Returns a list of dicts: {filename, subpath, display_name}
    - subpath: relative path from subject_dir (e.g. "Geography/jess101.pdf" or "iemh101.pdf")
    - display_name: human-readable label shown in the UI
    """
    results = []
    if not os.path.exists(subject_dir):
        return results

    entries = sorted(os.listdir(subject_dir))
    for entry in entries:
        entry_path = os.path.join(subject_dir, entry)
        if os.path.isdir(entry_path):
            # It's a sub-folder (e.g. Geography, Economics, History, Political Science)
            sub_entries = sorted(os.listdir(entry_path))
            for fname in sub_entries:
                if fname.lower().endswith('.pdf') and os.path.isfile(os.path.join(entry_path, fname)):
                    results.append({
                        'filename': fname,
                        'subpath': f"{entry}/{fname}",
                        'subfolder': entry,
                        'display_name': fname[:-4].replace('_', ' ').replace('-', ' ').title(),
                        'group': entry   # used for grouping in template
                    })
        elif entry.lower().endswith('.pdf') and os.path.isfile(entry_path):
            results.append({
                'filename': entry,
                'subpath': entry,
                'subfolder': None,
                'display_name': entry[:-4].replace('_', ' ').replace('-', ' ').title(),
                'group': None
            })
    return results


@app.route('/')
def home():
    return render_template('home.html', classes=CLASS_MAP)

@app.route('/class/<class_id>')
def subjects(class_id):
    if class_id not in CLASSES:
        abort(404)
    return render_template(
        'subjects.html',
        class_id=class_id,
        class_name=CLASS_MAP[class_id],
        subjects=SUBJECT_MAP
    )

@app.route('/class/<class_id>/<subject_id>')
def books(class_id, subject_id):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    subject_dir = os.path.join(PDFS_DIR, class_id, subject_id)
    books = scan_pdfs_recursive(subject_dir)

    return render_template(
        'books.html',
        class_id=class_id,
        class_name=CLASS_MAP[class_id],
        subject_id=subject_id,
        subject_name=SUBJECT_MAP[subject_id],
        books=books
    )

@app.route('/view/<class_id>/<subject_id>/<path:subpath>')
def viewer(class_id, subject_id, subpath):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    subject_dir = os.path.join(PDFS_DIR, class_id, subject_id)
    file_path = os.path.join(subject_dir, subpath)

    # Security: make sure resolved path is still inside subject_dir
    file_path = os.path.realpath(file_path)
    subject_dir = os.path.realpath(subject_dir)
    if not file_path.startswith(subject_dir + os.sep) and file_path != subject_dir:
        abort(403)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        abort(404)

    filename = os.path.basename(subpath)
    display_name = filename[:-4].replace('_', ' ').replace('-', ' ').title()

    return render_template(
        'viewer.html',
        class_id=class_id,
        class_name=CLASS_MAP[class_id],
        subject_id=subject_id,
        subject_name=SUBJECT_MAP[subject_id],
        filename=filename,
        subpath=subpath,
        display_name=display_name
    )

@app.route('/pdf/<class_id>/<subject_id>/<path:subpath>')
def serve_pdf(class_id, subject_id, subpath):
    """Securely serve PDF files from designated directories, including sub-folders."""
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    subject_dir = os.path.join(PDFS_DIR, class_id, subject_id)
    file_path = os.path.realpath(os.path.join(subject_dir, subpath))
    subject_dir = os.path.realpath(subject_dir)

    # Security check: ensure file is inside the subject directory
    if not file_path.startswith(subject_dir + os.sep):
        abort(403)

    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    # Running on 0.0.0.0 enables access from other devices in same network if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
