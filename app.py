import os
import cloudinary
import cloudinary.api
import cloudinary.utils
from flask import Flask, render_template, abort, redirect
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


def fetch_from_asset_folder(folder_path):
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

    folders = [(f"{base_folder}/{sf}", sf) for sf in subfolders] if subfolders else [(base_folder, None)]

    for folder_path, group in folders:
        for r in fetch_from_asset_folder(folder_path):
            public_id = r.get('public_id', '')
            asset_id = r.get('asset_id', '')
            display_name = r.get('display_name', public_id)
            secure_url = r.get('secure_url', '')  # Cloudinary gives us the URL directly!
            
            clean_name = '_'.join(display_name.split('_')[:-1]) if '_' in display_name else display_name
            clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
            
            books.append({
                'display_name': clean_name,
                'public_id': public_id,
                'asset_id': asset_id,
                'secure_url': secure_url,  # use this directly
                'group': group
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

    # Find the book from cached list
    book_list = fetch_books(class_id, subject_id)
    book = next((b for b in book_list if b['public_id'] == encoded_id or 
                 (b['group'] and b['group'] + '__' + b['public_id'] == encoded_id)), None)

    if not book:
        abort(404)

    return render_template('viewer.html',
                           class_id=class_id, class_name=CLASS_MAP[class_id],
                           subject_id=subject_id, subject_name=SUBJECT_MAP[subject_id],
                           display_name=book['display_name'],
                           pdf_url=book['secure_url'],
                           download_url=book['secure_url'],
                           group=book.get('group'))


@app.route('/debug')
def debug():
    output = []
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME", "NOT SET")
    output.append(f"<b>Cloud:</b> {cloud}<br><br>")
    try:
        result = cloudinary.api.resources_by_asset_folder("pdfs/class9/maths", max_results=3)
        found = result.get('resources', [])
        output.append(f"<b>pdfs/class9/maths:</b> {len(found)} items<br><br>")
        for r in found:
            output.append(f"<b>Full resource object:</b><br>")
            for k, v in r.items():
                output.append(f"&nbsp;&nbsp;{k} = {v}<br>")
            output.append("<br>")
    except Exception as e:
        output.append(f"<b>Error:</b> {e}<br>")
    return "".join(output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
