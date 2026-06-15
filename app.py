import os
import cloudinary
import cloudinary.api
from flask import Flask, render_template, abort, redirect
from functools import lru_cache

app = Flask(__name__)

# Cloudinary config — set these as environment variables on Render
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

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

# Class 10 social has subfolders; class 9 social is flat
SOCIAL_SUBFOLDERS = {
    'class10': ['Economics', 'Geography', 'History', 'Political Science'],
    'class9': []
}


def get_cloudinary_url(public_id, resource_type="raw"):
    """Build a direct file URL from public_id."""
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dr3tph8sg")
    return f"https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{public_id}"


def fetch_from_cloudinary(folder_path):
    """
    Try fetching PDFs from a folder, checking both 'raw' and 'image' resource types.
    Returns list of dicts with resource info.
    """
    resources = []
    for resource_type in ["raw", "image"]:
        try:
            result = cloudinary.api.resources(
                type="upload",
                resource_type=resource_type,
                prefix=folder_path + "/",
                max_results=100
            )
            found = result.get('resources', [])
            if found:
                print(f"Found {len(found)} files in {folder_path} as resource_type={resource_type}")
                for r in found:
                    r['_resource_type'] = resource_type
                resources.extend(found)
                break  # found with this type, no need to try the other
        except Exception as e:
            print(f"Cloudinary error [{resource_type}] for {folder_path}: {e}")
    return resources


@lru_cache(maxsize=64)
def fetch_books(class_id, subject_id):
    """
    Fetch PDF list from Cloudinary for a given class/subject.
    Returns list of dicts: {display_name, public_id, url, group}
    Results are cached so we don't hit the API on every page load.
    """
    base_folder = f"pdfs/{class_id}/{subject_id}"
    books = []

    subfolders = SOCIAL_SUBFOLDERS.get(class_id, []) if subject_id == 'social' else []

    if subfolders:
        for subfolder in subfolders:
            folder_path = f"{base_folder}/{subfolder}"
            for r in fetch_from_cloudinary(folder_path):
                public_id = r['public_id']
                filename = public_id.split('/')[-1]
                if not filename.lower().endswith('.pdf'):
                    continue
                resource_type = r.get('_resource_type', 'raw')
                display_name = filename[:-4].replace('_', ' ').replace('-', ' ').title()
                books.append({
                    'display_name': display_name,
                    'filename': filename,
                    'public_id': public_id,
                    'url': get_cloudinary_url(public_id, resource_type),
                    'group': subfolder
                })
    else:
        for r in fetch_from_cloudinary(base_folder):
            public_id = r['public_id']
            filename = public_id.split('/')[-1]
            if not filename.lower().endswith('.pdf'):
                continue
            resource_type = r.get('_resource_type', 'raw')
            display_name = filename[:-4].replace('_', ' ').replace('-', ' ').title()
            books.append({
                'display_name': display_name,
                'filename': filename,
                'public_id': public_id,
                'url': get_cloudinary_url(public_id, resource_type),
                'group': None
            })

    # Sort: by group then filename
    books.sort(key=lambda x: (x['group'] or '', x['filename']))
    return books


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

    book_list = fetch_books(class_id, subject_id)

    return render_template(
        'books.html',
        class_id=class_id,
        class_name=CLASS_MAP[class_id],
        subject_id=subject_id,
        subject_name=SUBJECT_MAP[subject_id],
        books=book_list
    )


@app.route('/view/<class_id>/<subject_id>/<path:public_id_suffix>')
def viewer(class_id, subject_id, public_id_suffix):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    public_id = f"pdfs/{class_id}/{subject_id}/{public_id_suffix}"
    filename = public_id_suffix.split('/')[-1]
    group = public_id_suffix.split('/')[0] if '/' in public_id_suffix else None
    display_name = filename[:-4].replace('_', ' ').replace('-', ' ').title() if filename.endswith('.pdf') else filename
    pdf_url = get_cloudinary_url(public_id)

    return render_template(
        'viewer.html',
        class_id=class_id,
        class_name=CLASS_MAP[class_id],
        subject_id=subject_id,
        subject_name=SUBJECT_MAP[subject_id],
        filename=filename,
        display_name=display_name,
        pdf_url=pdf_url,
        group=group
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
