import os
import requests
from flask import Flask, render_template, abort, redirect
from functools import lru_cache

app = Flask(__name__)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

CLASSES = ['class9', 'class10']
SUBJECTS = ['maths', 'science', 'social']
CLASS_MAP = {'class9': 'Class 9', 'class10': 'Class 10'}
SUBJECT_MAP = {'maths': 'Mathematics', 'science': 'Science', 'social': 'Social Science'}


FOLDER_IDS = {
    'class9': {
        'maths':   '18ZdYAvUKuWVN2xUIBLrPXm8DVT-dZeYF',
        'science': '1sMGU4GD6eFLDGZ1MJ3F6aIGpughETDQU',
        'social':  {'_flat': '1KDf_OmjxOtbBBOHClXvzBK50bLBl3hRA'}
    },
    'class10': {
        'maths':   '1ckVNBd5krPa2VnaQ5kBwzQdM-KKBHgJy',
        'science': '1Nwtn4HaIvNEYnDjzYUvHB7jAGtxSdJ5C',
        'social': {
            'Geography':        '1Jc6xHQwJRGTGT_EutFznkHtZ_BML_NTf',
            'Economics':        '111UBhB9iiU_Ss4x0ButewWbgOCj7L437',
            'History':          '1cHmV87Hns__106GjlBBmhSSoN_2FFTdY',
            'Political Science':'1__ZxSDQ4KmHmLF8-dfU-N7YPC1aFzu30',
        }
    }
}


def list_drive_files(folder_id):
    """List all PDF files in a Google Drive folder."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
        "fields": "files(id, name)",
        "key": GOOGLE_API_KEY,
        "pageSize": 100
    }
    files = []
    while True:
        resp = requests.get(url, params=params)
        data = resp.json()
        files.extend(data.get('files', []))
        page_token = data.get('nextPageToken')
        if not page_token:
            break
        params['pageToken'] = page_token
    return files


def make_pdf_url(file_id):
    """Direct PDF view URL via Google Drive."""
    return f"https://drive.google.com/file/d/{file_id}/preview"


def make_download_url(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"


@lru_cache(maxsize=64)
def fetch_books(class_id, subject_id):
    books = []
    folder_info = FOLDER_IDS[class_id][subject_id]

    if isinstance(folder_info, str):
        # Flat folder
        for f in list_drive_files(folder_info):
            name = f['name']
            clean = name[:-4] if name.lower().endswith('.pdf') else name
            clean = clean.replace('_', ' ').replace('-', ' ').title()
            books.append({
                'display_name': clean,
                'file_id': f['id'],
                'filename': name,
                'group': None
            })
    elif '_flat' in folder_info:
        # Flat social (class9)
        for f in list_drive_files(folder_info['_flat']):
            name = f['name']
            clean = name[:-4] if name.lower().endswith('.pdf') else name
            clean = clean.replace('_', ' ').replace('-', ' ').title()
            books.append({
                'display_name': clean,
                'file_id': f['id'],
                'filename': name,
                'group': None
            })
    else:
        # Subfolders (class10 social)
        for group, folder_id in folder_info.items():
            for f in list_drive_files(folder_id):
                name = f['name']
                clean = name[:-4] if name.lower().endswith('.pdf') else name
                clean = clean.replace('_', ' ').replace('-', ' ').title()
                books.append({
                    'display_name': clean,
                    'file_id': f['id'],
                    'filename': name,
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


@app.route('/view/<class_id>/<subject_id>/<file_id>')
def viewer(class_id, subject_id, file_id):
    if class_id not in CLASSES or subject_id not in SUBJECTS:
        abort(404)

    book_list = fetch_books(class_id, subject_id)
    book = next((b for b in book_list if b['file_id'] == file_id), None)
    if not book:
        abort(404)

    return render_template('viewer.html',
                           class_id=class_id, class_name=CLASS_MAP[class_id],
                           subject_id=subject_id, subject_name=SUBJECT_MAP[subject_id],
                           display_name=book['display_name'],
                           pdf_url=make_pdf_url(file_id),
                           download_url=make_download_url(file_id),
                           group=book.get('group'))


@app.route('/debug')
def debug():
    output = [f"<b>API Key:</b> {'SET' if GOOGLE_API_KEY else 'NOT SET'}<br><br>"]
    try:
        files = list_drive_files('18ZdYAvUKuWVN2xUIBLrPXm8DVT-dZeYF')
        output.append(f"<b>class9/maths:</b> {len(files)} files<br>")
        for f in files[:3]:
            url = make_pdf_url(f['id'])
            output.append(f"&nbsp;&nbsp;→ {f['name']} | <a href='{url}' target='_blank'>Preview</a><br>")
    except Exception as e:
        output.append(f"<b>Error:</b> {e}<br>")
    return "".join(output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
