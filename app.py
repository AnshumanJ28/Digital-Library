import os
import cloudinary
import cloudinary.api
from flask import Flask, render_template, abort
from functools import lru_cache

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

CLASSES = ['class9', 'class10']
SUBJECTS = ['maths', 'science', 'social']
CLASS_MAP = {'class9': 'Class 9', 'class10': 'Class 10'}
SUBJECT_MAP = {'maths': 'Mathematics', 'science': 'Science', 'social': 'Social Science'}
SOCIAL_SUBFOLDERS = {
    'class10': ['Economics', 'Geography', 'History', 'Political Science'],
    'class9': []
}


def get_pdf_url(public_id):
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg")
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.pdf"


def fetch_from_asset_folder(folder_path):
    """Fetch all assets from a Cloudinary asset folder (new ML folder mode)."""
    resources = []
    try:
        next_cursor = None
        while True:
            kwargs = {"max_results": 500}
            if next_cursor:
                kwargs["next_cursor"] = next_cursor
            result = cloudinary.api.resources_by_asset_folder(folder_path, **kwargs)
            resources.extend(result.get('resources', []))
            next_cursor = result.get('next_cursor')
            if not next_cursor:
                break
    except Exception as e:
        print(f"Error fetching {folder_path}: {e}")
    return resources


@lru_cache(maxsize=64)
def fetch_books(class_id, subject_id):
    base_folder = f"pdfs/{class_id}/{subject_id}"
    books = []
    subfolders = SOCIAL_SUBFOLDERS.get(class_id, []) if subject_id == 'social' else []

    if subfolders:
        for subfolder in subfolders:
            for r in fetch_from_asset_folder(f"{base_folder}/{subfolder}"):
                display_name = r.get('display_name', '') or r.get('public_id', '').split('/')[-1]
                display_name = display_name.replace('_', ' ').replace('-', ' ').title()
                public_id = r.get('public_id', '')
                books.append({
                    'display_name': display_name,
                    'filename': display_name,
                    'public_id': public_id,
                    'group': subfolder
                })
    else:
        for r in fetch_from_asset_folder(base_folder):
            display_name = r.get('display_name', '') or r.get('public_id', '').split('/')[-1]
            display_name = display_name.replace('_', ' ').replace('-', ' ').title()
            public_id = r.get('public_id', '')
            books.append({
                'display_name': display_name,
                'filename': display_name,
                'public_id': public_id,
                'group': None
            })

    books.sort(key=lambda x: (x['group'] or '', x['filename']))
    return books


@app.route('/')
def home():
    return render_template('home.html', classes=CLASS_MAP)


@app.route('/class/<class_id>')
def subjects(class_id):
    if class_id not in CLASSES:
        abort(404)
    return render_template('subjects.html', class_id=class_id,
                           class_name=CLASS_MAP[class_id], subjects=SUBJECT_MAP)


@app.route('/class/<class_id>/<subject_id>')
def books(class_id, subject_id):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)
    book_list = fetch_books(class_id, subject_id)
    return render_template('books.html', class_id=class_id,
                           class_name=CLASS_MAP[class_id],
                           subject_id=subject_id,
                           subject_name=SUBJECT_MAP[subject_id],
                           books=book_list)


@app.route('/view/<class_id>/<subject_id>/<path:public_id_suffix>')
def viewer(class_id, subject_id, public_id_suffix):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)
    public_id = f"pdfs/{class_id}/{subject_id}/{public_id_suffix}"
    filename = public_id_suffix.split('/')[-1]
    group = public_id_suffix.split('/')[0] if '/' in public_id_suffix else None
    display_name = filename.replace('_', ' ').replace('-', ' ').title()
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg")
    pdf_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.pdf"
    download_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/fl_attachment/{public_id}.pdf"

    return render_template('viewer.html', class_id=class_id,
                           class_name=CLASS_MAP[class_id],
                           subject_id=subject_id,
                           subject_name=SUBJECT_MAP[subject_id],
                           filename=filename,
                           display_name=display_name,
                           pdf_url=pdf_url,
                           download_url=download_url,
                           group=group)


@app.route('/debug')
def debug():
    output = []
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME", "NOT SET")
    key = "SET" if os.environ.get("CLOUDINARY_API_KEY") else "NOT SET"
    secret = "SET" if os.environ.get("CLOUDINARY_API_SECRET") else "NOT SET"
    output.append(f"<b>Cloud:</b> {cloud} | <b>Key:</b> {key} | <b>Secret:</b> {secret}<br><br>")

    # Test asset folder API
    try:
        result = cloudinary.api.resources_by_asset_folder("pdfs/class9/maths", max_results=5)
        found = result.get('resources', [])
        output.append(f"<b>pdfs/class9/maths:</b> {len(found)} items<br>")
        for r in found:
            output.append(f"&nbsp;&nbsp;→ public_id={r.get('public_id')} | display_name={r.get('display_name')} | format={r.get('format')} | asset_folder={r.get('asset_folder')}<br>")
    except Exception as e:
        output.append(f"<b>asset_folder error:</b> {e}<br>")

    return "".join(output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
