# Digital Library - Teacher's Book Portal

A simple, lightweight, and responsive PDF book hosting portal built using Python and Flask. This portal scans folders dynamically to list available textbooks and hosts them in an inline glassmorphic PDF viewer with simple password protection.

## Setup Instructions

Follow these exact steps to run the website locally:

1. **Install Flask**
   ```bash
   pip install flask
   ```

2. **Add Textbooks**
   Put your PDFs inside the correct subject folder (e.g., `pdfs/class9/maths/`).
   
   The directory structure is organized as:
   - `pdfs/class9/maths/`
   - `pdfs/class9/science/`
   - `pdfs/class9/social/`
   - `pdfs/class10/maths/`
   - `pdfs/class10/science/`
   - `pdfs/class10/social/`

3. **Start the Portal**
   ```bash
   python app.py
   ```

4. **Access in Browser**
   Open your browser at [http://localhost:5000](http://localhost:5000).

5. **Share with Students**
   Share the server's IP address (or `http://localhost:5000` if local) and the password with your students.
   - **Default Portal Password**: `study123` (Configurable in `app.py`)
