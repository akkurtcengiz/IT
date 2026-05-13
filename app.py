#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading
import os

app = Flask(__name__)

# Ayarlar
LOG_FILE = "/var/log/file-monitor.log"
WATCH_DIR = "/home"  # İzlenecek dizini buraya yazın
PORT = 5000
HOST = "0.0.0.0"

# Global değişkenler
log_entries = []
observer = None
is_monitoring = False

class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        self.log_event("CREATED", event.src_path)
    
    def on_deleted(self, event):
        self.log_event("DELETED", event.src_path)
    
    def on_modified(self, event):
        self.log_event("MODIFIED", event.src_path)
    
    def on_moved(self, event):
        self.log_event("MOVED", f"{event.src_path} -> {event.dest_path}")
    
    def log_event(self, event_type, path):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "type": event_type,
            "path": path
        }
        
        log_entries.append(log_entry)
        
        # Son 1000 girişi koru
        if len(log_entries) > 1000:
            log_entries.pop(0)
        
        # Dosyaya yazma
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{timestamp}] {event_type}: {path}\n")
        except Exception as e:
            print(f"Log yazma hatası: {e}")

def start_monitoring():
    global observer, is_monitoring
    if not is_monitoring:
        observer = Observer()
        event_handler = FileChangeHandler()
        observer.schedule(event_handler, WATCH_DIR, recursive=True)
        observer.start()
        is_monitoring = True
        print(f"✅ İzleme başladı: {WATCH_DIR}")

def stop_monitoring():
    global observer, is_monitoring
    if is_monitoring and observer:
        observer.stop()
        observer.join()
        is_monitoring = False
        print("❌ İzleme durduruldu")

# Web Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    limit = request.args.get('limit', 100, type=int)
    search = request.args.get('search', '', type=str)
    event_type = request.args.get('type', '', type=str)
    
    filtered_logs = log_entries
    
    if search:
        filtered_logs = [l for l in filtered_logs if search.lower() in l['path'].lower()]
    
    if event_type:
        filtered_logs = [l for l in filtered_logs if l['type'] == event_type]
    
    return jsonify(filtered_logs[-limit:])

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "monitoring": is_monitoring,
        "watch_dir": WATCH_DIR,
        "total_logs": len(log_entries),
        "log_file": LOG_FILE
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    start_monitoring()
    return jsonify({"status": "started", "monitoring": is_monitoring})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    stop_monitoring()
    return jsonify({"status": "stopped", "monitoring": is_monitoring})

@app.route('/api/clear', methods=['POST'])
def clear_logs():
    global log_entries
    log_entries = []
    try:
        open(LOG_FILE, 'w').close()
    except:
        pass
    return jsonify({"status": "cleared"})

@app.route('/api/export', methods=['GET'])
def export_logs():
    log_text = "\n".join([f"[{l['timestamp']}] {l['type']}: {l['path']}" for l in log_entries])
    return log_text, 200, {'Content-Type': 'text/plain', 'Content-Disposition': 'attachment; filename=file-monitor-report.txt'}

if __name__ == '__main__':
    # Log dosyasını oluştur
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    open(LOG_FILE, 'a').close()
    
    # İzlemeyi başlat
    start_monitoring()
    
    # Web sunucusunu başlat
    print(f"🌐 Web arayüzü: http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
