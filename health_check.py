#!/usr/bin/env python3
"""
Простой HTTP сервер для health checks Render
"""
import http.server
import socketserver
import os
import threading
import time

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = """
            <html>
            <head><title>BabyCareBot Health Check</title></head>
            <body>
                <h1>🍼 BabyCareBot</h1>
                <p>Status: ✅ Running</p>
                <p>Time: {}</p>
                <p>Bot is working in background</p>
            </body>
            </html>
            """.format(time.strftime('%Y-%m-%d %H:%M:%S'))
            self.wfile.write(response.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "healthy", "service": "babycare-bot"}'
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server(port=8000):
    """Запуск HTTP сервера для health checks"""
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            print(f"🌐 Health check server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Health check server error: {e}")

def run_health_server():
    """Запуск health сервера в отдельном потоке"""
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    return health_thread

if __name__ == "__main__":
    # Запускаем health сервер
    health_thread = run_health_server()
    
    # Имитируем работу бота (для тестирования)
    try:
        while True:
            print("🤖 Bot is running... (Press Ctrl+C to stop)")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
