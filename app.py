from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from email.message import EmailMessage
import json, os
import smtplib
import psycopg2

app = Flask(__name__)
app.secret_key = 'prathamssalian146'  # replace with a strong key

PROJECT_FILE = 'data/projects.json'

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("dpg-d2q6mlfdiees73clikgg-a"),
        database=os.getenv("projectbank_db"),
        user=os.getenv("projectbank_db_user"),
        password=os.getenv("ktyUJdPtdgmSsxsm9xhptHu3A2V4070V")
    )

# Load projects
def load_projects():
    with open(PROJECT_FILE) as f:
        return json.load(f)

# Save projects
def save_projects(data):
    with open(PROJECT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home')
def index():
    data = load_projects()
    return render_template('index.html', domains=list(data.keys()))

@app.route('/domain/<domain_name>')
def domain(domain_name):
    data = load_projects()
    return render_template('domain.html', domain=domain_name, projects=data.get(domain_name, []))

@app.route('/domain/<domain_name>/<project_id>')
def project(domain_name, project_id):
    data = load_projects()
    project = next((p for p in data.get(domain_name, []) if p['id'] == project_id), None)
    return render_template('domain.html', domain=domain_name, project=project)

# ----------------- Admin -----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'webadmin' and request.form['password'] == 'admin420':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    data = load_projects()

    # Load contact submissions from JSON (backup storage)
    submissions = []
    contact_file = 'contact_requests.json'
    if os.path.exists(contact_file):
        with open(contact_file, 'r') as f:
            try:
                submissions = json.load(f)
            except json.JSONDecodeError:
                submissions = []

    return render_template('admin_dashboard.html', data=data, submissions=submissions)

@app.route('/admin/add_project', methods=['POST'])
def add_project():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    data = load_projects()
    domain = request.form['domain']
    new_project = {
        "id": request.form['id'],
        "title": request.form['title'],
        "description": request.form['description'],
        "tech_stack": request.form['tech_stack']
    }
    if domain not in data:
        data[domain] = []
    data[domain].append(new_project)
    save_projects(data)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_project/<domain>/<project_id>')
def delete_project(domain, project_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    data = load_projects()
    data[domain] = [p for p in data[domain] if p['id'] != project_id]
    save_projects(data)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('welcome'))

# ----------------- Contact -----------------
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        message = request.form['message']
        email = session.get('email', 'guest@guest.com')  # fallback

        full_message = f"Name: {name}\nPhone: {phone}\nEmail: {email}\n\nMessage:\n{message}"

        # Save to PostgreSQL
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO contacts (name, phone, email, message) VALUES (%s, %s, %s, %s)",
                (name, phone, email, message)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("Message sent successfully!", "success")
        except Exception as e:
            print("DB Error:", e)
            flash("Something went wrong saving to DB!", "error")

        # Optional: Also send email
        try:
            send_email("Contact Form Submission", full_message, email)
        except Exception as e:
            print("Email Error:", e)

        return redirect(url_for('index'))

    return render_template('index.html')

def send_email(subject, body, reply_to):
    sender = 'prathamssalian@gmail.com'
    password = 'ljza jhns bqno hshk'
    receiver = 'prathamssalian@gmail.com'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    msg['Reply-To'] = reply_to
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

# ----------------- Other Pages -----------------
@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# ----------------- Contact Requests (JSON + DB) -----------------
@app.route('/contact_request', methods=['POST'])
def contact_request():
    data = request.get_json()

    required_fields = ['name', 'mobile', 'type', 'project']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400

    # Save to JSON (backup)
    json_path = 'contact_requests.json'
    if os.path.exists(json_path):
        with open(json_path, 'r') as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_data.append(data)
    with open(json_path, 'w') as file:
        json.dump(existing_data, file, indent=2)

    # Save to PostgreSQL
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO contact_requests (name, mobile, type, project)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (data['name'], data['mobile'], data['type'], data['project']))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error saving to PostgreSQL:", e)

    return jsonify({'message': 'We will reach out to you soon!'})

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
