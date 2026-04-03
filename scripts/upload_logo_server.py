"""
Simple file upload server to get the LawnOps logo into the static folder.
Run this: python upload_logo_server.py
Then go to http://localhost:8765 in your browser and upload the image.
"""
import http.server
import socketserver
import os
import cgi
from pathlib import Path

PORT = 8765
STATIC_DIR = Path("d:/python-lawn/static")

class UploadHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Upload LawnOps Logo</title>
                <style>
                    body { 
                        font-family: monospace; 
                        background: #000; 
                        color: #7a8d3a; 
                        padding: 40px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                    }
                    .container {
                        border: 2px solid #4a5d4a; 
                        padding: 40px; 
                        max-width: 400px;
                        text-align: center;
                    }
                    h2 { color: #c8d46a; margin-top: 0; }
                    input[type="file"] { 
                        margin: 20px 0; 
                        color: #c8d46a; 
                        padding: 10px;
                        border: 1px solid #4a5d4a;
                        background: #1a2f1a;
                        width: 100%;
                        box-sizing: border-box;
                    }
                    button { 
                        background: transparent; 
                        color: #7a8d3a; 
                        border: 2px solid #7a8d3a;
                        padding: 12px 30px; 
                        cursor: pointer;
                        font-family: monospace;
                        font-size: 14px;
                        letter-spacing: 3px;
                        text-transform: uppercase;
                    }
                    button:hover { 
                        background: #7a8d3a; 
                        color: #000; 
                    }
                    .success { color: #00ff00; margin-top: 20px; }
                    .error { color: #ff4444; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>UPLOAD LAWNOPS LOGO</h2>
                    <p>Select your lawnops_logo.png file</p>
                    <form method="POST" enctype="multipart/form-data">
                        <input type="file" name="file" accept="image/png,image/jpeg,image/jpg" required>
                        <br><br>
                        <button type="submit">UPLOAD</button>
                    </form>
                </div>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/':
            content_type = self.headers.get('Content-Type')
            if content_type and 'multipart/form-data' in content_type:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'}
                )
                
                if 'file' in form:
                    file_item = form['file']
                    if file_item.filename:
                        # Save as lawnops_logo.png
                        filepath = STATIC_DIR / 'lawnops_logo.png'
                        with open(filepath, 'wb') as f:
                            f.write(file_item.file.read())
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        success_html = f'''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Success</title>
                            <style>
                                body {{ 
                                    font-family: monospace; 
                                    background: #000; 
                                    color: #00ff00; 
                                    padding: 40px;
                                    text-align: center;
                                    min-height: 100vh;
                                    display: flex;
                                    flex-direction: column;
                                    justify-content: center;
                                    align-items: center;
                                }}
                                .success {{ 
                                    border: 2px solid #00ff00;
                                    padding: 40px;
                                    background: rgba(0,255,0,0.1);
                                }}
                                h1 {{ margin-top: 0; }}
                                a {{ color: #7a8d3a; text-decoration: none; }}
                                a:hover {{ color: #c8d46a; }}
                            </style>
                        </head>
                        <body>
                            <div class="success">
                                <h1>✓ UPLOAD SUCCESSFUL</h1>
                                <p>Logo saved to: {filepath}</p>
                                <p>File size: {os.path.getsize(filepath)} bytes</p>
                                <br>
                                <a href="/">Upload Another</a> | 
                                <a href="http://localhost:8000/login">Go to Login Page</a>
                            </div>
                        </body>
                        </html>
                        '''
                        self.wfile.write(success_html.encode())
                        print(f"\n✓ Logo uploaded successfully to: {filepath}")
                        print(f"  File size: {os.path.getsize(filepath)} bytes")
                        return
            
            self.send_error(400, "Bad request")

print(f"""
╔══════════════════════════════════════════════════════════╗
║         LAWNOPS LOGO UPLOAD SERVER                       ║
╠══════════════════════════════════════════════════════════╣
║  1. Open your browser                                    ║
║  2. Go to: http://localhost:{PORT}                        ║
║  3. Select your lawnops_logo.png file                    ║
║  4. Click UPLOAD                                         ║
╚══════════════════════════════════════════════════════════╝
""")

with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
