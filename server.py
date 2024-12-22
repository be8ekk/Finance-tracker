from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import sqlite3
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse
import uuid

# Создаем базу данных, если ее нет
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Таблица пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Таблица транзакций
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    category TEXT DEFAULT 'Other',
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

# Таблица для сеансов
cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')
conn.commit()
conn.close()

class FinanceTrackerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/transactions':
            self.handle_get_transactions()
        elif self.path == '/api/logout':
            self.handle_logout()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/register':
            self.handle_register()
        elif self.path == '/api/login':
            self.handle_login()
        elif self.path == '/api/add_transaction':
            self.handle_add_transaction()
        else:
            self.send_error(404, "Endpoint not found")

    def parse_cookies(self):
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return {}
        cookies = SimpleCookie(cookie_header)
        return {key: cookies[key].value for key in cookies}

    def get_logged_in_user(self):
        cookies = self.parse_cookies()
        session_id = cookies.get('session_id')
        if not session_id:
            return None

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sessions WHERE session_id = ?', (session_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        return None

    def handle_register(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode('utf-8'))

        username = data.get('username', [''])[0]
        password = data.get('password', [''])[0]

        if not username or not password:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid input')
            return

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.end_headers()
        except sqlite3.IntegrityError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Username already exists')

    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode('utf-8'))

        username = data.get('username', [''])[0]
        password = data.get('password', [''])[0]

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        result = cursor.fetchone()

        if result:
            user_id = result[0]
            session_id = str(uuid.uuid4())

            cursor.execute('INSERT INTO sessions (session_id, user_id) VALUES (?, ?)', (session_id, user_id))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header('Set-Cookie', f'session_id={session_id}; HttpOnly')
            self.end_headers()
        else:
            conn.close()
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Invalid credentials')

    def handle_logout(self):
        cookies = self.parse_cookies()
        session_id = cookies.get('session_id')

        if session_id:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()

        self.send_response(200)
        self.end_headers()

    def handle_get_transactions(self):
        user_id = self.get_logged_in_user()
        if not user_id:
            self.send_response(401)
            self.end_headers()
            return

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE user_id = ?', (user_id,))
        transactions = cursor.fetchall()
        conn.close()

        response = [
            {
                'id': row[0],
                'description': row[2],
                'amount': row[3],
                'date': row[4],
                'category': row[5]
            }
            for row in transactions
        ]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def handle_add_transaction(self):
        user_id = self.get_logged_in_user()
        if not user_id:
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode('utf-8'))

        description = data.get('description', [''])[0]
        amount = float(data.get('amount', ['0'])[0])
        date = data.get('date', [''])[0]
        category = data.get('category', ['Other'])[0]

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO transactions (user_id, description, amount, date, category) VALUES (?, ?, ?, ?, ?)',
            (user_id, description, amount, date, category)
        )
        conn.commit()
        conn.close()

        self.send_response(200)
        self.end_headers()

# Запуск сервера
server = HTTPServer(('localhost', 8000), FinanceTrackerHandler)
print("Server running on http://localhost:8000")
server.serve_forever()
