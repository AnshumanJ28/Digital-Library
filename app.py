import os
import cloudinary
import cloudinary.api
from flask import Flask, render_template, abort, redirect
from functools import lru_cache
import urllib.parse

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


def build_pdf_url(public_id, asset_folder):
    """
    In Cloudinary's new ML folder mode:
    - public_id is just the filename (e.g. Chapter_8_wkkxv4)
    - asset_folder is the folder path (e.g. pdfs/class9/maths)
    - URL format: /image/upload/<asset_folder>/<public_id>.pdf
    """
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg")
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{asset_folder}/{public_id}.pdf"


def fetch_from_asset_folder(folder_path):
    """Fetch all assets from a Cloudinary asset folder."""
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
            folder_path = f"{base_folder}/{subfolder}"
            for r in fetch_from_asset_folder(folder_path):
                public_id = r.get('public_id', '')
                asset_folder = r.get('asset_folder', folder_path)
                display_name = r.get('display_name', public_id)
                # Clean up display name (remove random suffix like _wkkxv4)
                clean_name = '_'.join(display_name.split('_')[:-1]) if '_' in display_name else display_name
                clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
                books.append({
                    'display_name': clean_name,
                    'public_id': public_id,
                    'asset_folder': asset_folder,
                    'pdf_url': build_pdf_url(public_id, asset_folder),
                    'group': subfolder
                })
    else:
        for r in fetch_from_asset_folder(base_folder):
            public_id = r.get('public_id', '')
            asset_folder = r.get('asset_folder', base_folder)
            display_name = r.get('display_name', public_id)
            clean_name = '_'.join(display_name.split('_')[:-1]) if '_' in display_name else display_name
            clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
            books.append({
                'display_name': clean_name,
                'public_id': public_id,
                'asset_folder': asset_folder,
                'pdf_url': build_pdf_url(public_id, asset_folder),
                'group': None
            })

    books.sort(key=lambda x: (x['group'] or '', x['display_name']))
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


@app.route('/view/<class_id>/<subject_id>/<path:encoded_id>')
def viewer(class_id, subject_id, encoded_id):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    # encoded_id format: group__public_id OR public_id (for flat)
    if '__' in encoded_id:
        group, public_id = encoded_id.split('__', 1)
        asset_folder = f"pdfs/{class_id}/{subject_id}/{group}"
    else:
        group = None
        public_id = encoded_id
        asset_folder = f"pdfs/{class_id}/{subject_id}"

    display_name = '_'.join(public_id.split('_')[:-1]) if '_' in public_id else public_id
    display_name = display_name.replace('_', ' ').replace('-', ' ').title()

    pdf_url = build_pdf_url(public_id, asset_folder)
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg")
    download_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/fl_attachment/{asset_folder}/{public_id}.pdf"

    return render_template('viewer.html',
                           class_id=class_id, class_name=CLASS_MAP[class_id],
                           subject_id=subject_id, subject_name=SUBJECT_MAP[subject_id],
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
    try:
        result = cloudinary.api.resources_by_asset_folder("pdfs/class9/maths", max_results=3)
        found = result.get('resources', [])
        output.append(f"<b>pdfs/class9/maths:</b> {len(found)} items<br>")
        for r in found:
            pid = r.get('public_id')
            af = r.get('asset_folder')
            url = build_pdf_url(pid, af)
            output.append(f"&nbsp;&nbsp;→ {pid} | folder={af}<br>")
            output.append(f"&nbsp;&nbsp;&nbsp;&nbsp;URL: <a href='{url}' target='_blank'>{url}</a><br>")
    except Exception as e:
        output.append(f"<b>Error:</b> {e}<br>")
    return "".join(output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
