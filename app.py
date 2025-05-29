from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime
import pytz

app = Flask(__name__)
DATABASE = 'database/gharik.db'
ADMIN_CODE = "181481"
IST = pytz.timezone('Asia/Kolkata')

# Ensure database directory exists
os.makedirs('database', exist_ok=True)

# Database Setup
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT UNIQUE,
                    name TEXT,
                    password TEXT,
                    balance INTEGER DEFAULT 0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    receiver TEXT,
                    amount INTEGER,
                    timestamp TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    identifier = request.form['identifier']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE identifier=?", (identifier,))
    user = c.fetchone()
    conn.close()
    if user:
        return render_template('login.html', user_exists=True, identifier=identifier)
    else:
        return redirect(url_for('signup', identifier=identifier))

@app.route('/password', methods=['POST'])
def password():
    identifier = request.form['identifier']
    password = request.form['password']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE identifier=? AND password=?", (identifier, password))
    user = c.fetchone()
    conn.close()
    if user:
        return redirect(url_for('dashboard', identifier=identifier))
    else:
        return "Incorrect password. Try again."

@app.route('/signup')
def signup():
    identifier = request.args.get('identifier', '')
    return render_template('signup.html', identifier=identifier)

@app.route('/signup_submit', methods=['POST'])
def signup_submit():
    identifier = request.form['identifier']
    name = request.form['name']
    password = request.form['password']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (identifier, name, password, balance) VALUES (?, ?, ?, ?)",
                  (identifier, name, password, 100000))  # 100,000 Gharik start
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "User already exists."
    conn.close()
    return redirect(url_for('dashboard', identifier=identifier))

@app.route('/dashboard/<identifier>')
def dashboard(identifier):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name, balance FROM users WHERE identifier=?", (identifier,))
    user = c.fetchone()
    conn.close()
    if user:
        return render_template('dashboard.html', identifier=identifier, name=user[0], balance=user[1])
    else:
        return render_template('404.html')

@app.route('/send', methods=['POST'])
def send():
    sender = request.form['sender']
    receiver = request.form['receiver']
    amount = int(request.form['amount'])

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE identifier=?", (sender,))
    sender_data = c.fetchone()

    c.execute("SELECT balance FROM users WHERE identifier=?", (receiver,))
    receiver_data = c.fetchone()

    if not receiver_data:
        conn.close()
        return "Recipient not found."

    if sender_data[0] < amount:
        conn.close()
        return "Insufficient balance."

    new_sender_balance = sender_data[0] - amount
    new_receiver_balance = receiver_data[0] + amount

    c.execute("UPDATE users SET balance=? WHERE identifier=?", (new_sender_balance, sender))
    c.execute("UPDATE users SET balance=? WHERE identifier=?", (new_receiver_balance, receiver))

    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (sender, receiver, amount, timestamp) VALUES (?, ?, ?, ?)",
              (sender, receiver, amount, now))

    conn.commit()
    conn.close()

    return render_template('success.html', sender=sender, receiver=receiver, amount=amount)

@app.route('/convert')
def convert():
    return render_template('conversion.html')

@app.route('/admin_portal', methods=['POST'])
def admin_portal():
    code = request.form['admincode']
    if code == ADMIN_CODE:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        c.execute("SELECT * FROM transactions")
        transactions = c.fetchall()
        conn.close()
        return render_template('admin.html', users=users, transactions=transactions)
    else:
        return render_template('404.html')

@app.route('/admin_transfer', methods=['POST'])
def admin_transfer():
    receiver = request.form['receiver']
    amount = int(request.form['amount'])

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT balance FROM users WHERE identifier=?", (receiver,))
    user = c.fetchone()

    if not user:
        conn.close()
        return "User not found."

    new_balance = user[0] + amount
    c.execute("UPDATE users SET balance=? WHERE identifier=?", (new_balance, receiver))

    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (sender, receiver, amount, timestamp) VALUES (?, ?, ?, ?)",
              ("ADMIN", receiver, amount, now))

    conn.commit()
    conn.close()
    return redirect(url_for('dashboard', identifier=receiver))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
