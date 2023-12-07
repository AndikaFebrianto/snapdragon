from flask import Flask, render_template, jsonify, request, redirect, url_for
app = Flask(__name__)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/Acoount')
def account():
    return render_template('account.html', active_page='account')

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)