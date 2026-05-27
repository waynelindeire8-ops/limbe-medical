from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
import datetime
import math
import os
import re
from werkzeug.utils import secure_filename
from functools import wraps
from dataclasses import asdict
from main import HospitalManagementSystem
from models import Patient, Appointment, Doctor, Message, Bill, Prescription, MedicalRecord, QueueItem, InventoryItem, User, LabResult

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for flashing messages
hms = HospitalManagementSystem()

# Providers List for Billing and Inventory
PROVIDERS = [
    "Cash",
    "Medical Aid Society of Malawi (MASM)",
    "Central Health Medical Aid",
    "Umoyo Health Care Insurance Company",
    "Wella Medical Aid Society Limited",
    "Precious Medical International",
    "NABMAS (National Bank Medical Aid Scheme)",
    "MedPlus Medical Solutions",
    "Bakresa Medical Centre",
    "MedHealth Malawi",
    "Cura Health Management",
    "Medlife Services Limited",
    "Lifeline Malawi",
    "Malmed Healthcare Services",
    "Adventist Health Services Malawi",
    "Partners In Health Malawi",
    "Liberty Life Malawi",
    "Old Mutual Malawi",
    "NICO Life Insurance Company",
    "NICO General Insurance",
    "Alliance Insurance Company Malawi",
    "General Alliance Insurance Malawi",
    "Reunion Insurance Company Malawi",
    "Hollard Insurance Malawi",
    "Sanlam Malawi",
    "Britam Insurance Malawi",
    "Madison Life Insurance Malawi",
    "Bupa Global",
    "Cigna Global",
    "Allianz Care",
    "AXA Global Healthcare",
    "Aetna International",
    "William Russell International",
    "Airtel Money Thanzi Medical Aid",
    "Inclusivity Health Platform",
    "Airtel Insurance Health Cover",
    "Mwaiwathu Private Hospital",
    "Blantyre Adventist Hospital",
    "Beit CURE International Hospital Malawi",
    "MedPlus Clinics",
    "Bakresa Health Services"
]

# Notifications helper
def notify(subject: str, content: str, recipient_id: str = 'all'):
    if not hms.settings.get('notifications', True):
        return
    msg = Message(
        message_id=hms.generate_id('msg_'),
        sender_id='system',
        sender_name='System',
        recipient_id=recipient_id,
        subject=subject,
        content=content,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_read=False,
        is_archived=False
    )
    hms.messages.append(msg)
    hms.save_data()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role', '').strip().lower() not in ['admin', 'admin doctor', 'admin_doctor']:
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Seed Users
def seed_users():
    users = [
        ('admin', 'admin123', 'admin'),
        ('receptionist', 'rec123', 'receptionist'),
        ('cashier', 'cash123', 'cashier'),
        ('nurse', 'nurse123', 'nurse'),
        ('lab', 'lab123', 'lab_assistant'),
        ('doctor', 'doc123', 'doctor'),
        ('locum', 'locum123', 'doctor')
    ]
    # Check if users exist, if not create them
    # We need to temporarily mock an admin actor for the first user creation if strict checks are in place
    # But register_user allows creation if actor_role is admin or if checks are bypassed.
    # Let's check main.py logic again. 
    # register_user(username, password, role, actor_role)
    # It checks: if role is admin, actor must be admin OR no admins exist yet.
    
    for username, password, role in users:
        if not any(u.username == username for u in hms.users):
            # For the first admin, it should work if no admins exist.
            # For subsequent users, we pass actor_role='admin'
            hms.register_user(username, password, role, actor_role='admin')

seed_users()

def paginate_list(items, page, per_page=20):
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.context_processor
def inject_user():
    username = session.get('username')
    role = session.get('role')
    unread = 0
    if username:
        unread = hms.get_unread_count(username, role)
    return dict(current_user=username, current_role=role, unread_messages_count=unread, hms=hms)

@app.route('/analytics')
def analytics():
    # Use optimized database aggregation
    stats = hms.get_stats()
    
    # Revenue by Month (Last 6 months) - This part still needs some Python logic for month keys
    revenue_data = {}
    today = datetime.date.today()
    for i in range(5, -1, -1):
        month_date = today - datetime.timedelta(days=i*30)
        month_key = month_date.strftime("%B")
        revenue_data[month_key] = 0
        
    # We can still optimize this with a custom SQL query if needed
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT created_date, SUM(amount) FROM bills 
        WHERE status = 'Paid' AND created_date >= date('now', '-180 days')
        GROUP BY created_date
    """)
    for row in cursor.fetchall():
        try:
            bill_date = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
            month_key = bill_date.strftime("%B")
            if month_key in revenue_data:
                revenue_data[month_key] += float(row[1])
        except:
            pass
    conn.close()

    # Top Doctors by Appointments - Optimized with SQL
    top_doctors = []
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.last_name, COUNT(a.appointment_id) as count 
        FROM doctors d
        LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
        GROUP BY d.doctor_id
        ORDER BY count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        top_doctors.append({'name': f"Dr. {row[0]}", 'count': row[1]})
    conn.close()

    status_counts = stats['appointment_statuses']

    return render_template('analytics.html', 
                           total_patients=stats['total_patients'],
                           total_appointments=stats['total_appointments'],
                           total_revenue=stats['total_revenue'],
                           status_labels=list(status_counts.keys()),
                           status_data=list(status_counts.values()),
                           revenue_labels=list(revenue_data.keys()),
                           revenue_data=list(revenue_data.values()),
                           top_doctors_labels=[d['name'] for d in top_doctors],
                           top_doctors_data=[d['count'] for d in top_doctors],
                           active_page='analytics')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = hms.authenticate(username, password)
        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if hms.register_user(username, password, role='user'):
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    try:
        days = 90
        stats = hms.get_dashboard_stats(days)
        total_patients = hms.get_patients_count()
        
        # Charts
        base = datetime.date.today()
        chart_labels = [(base - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days-1, -1, -1)]
        
        reg_map = stats['registration_map']
        appt_map = stats['appointment_map']
        
        chart_patient_reg = [reg_map.get(d, 0) for d in chart_labels]
        chart_appointments = [appt_map.get(d, 0) for d in chart_labels]
        
        # Get notifications
        username = session.get('username')
        role = session.get('role')
        system_notifications = hms.get_recent_notifications(username, role)

        return render_template('dashboard.html', 
                            total_patients=total_patients,
                            stats=stats,
                            active_doctors=stats['active_doctors'],
                            todays_appointments=stats['todays_appointments'],
                            pending_appointments=stats['pending_appointments'],
                            completed_appointments=stats['completed_appointments'],
                            recent_appointments=hms.get_recent_appointments(),
                            queue=hms.get_active_queue(),
                            chart_labels=chart_labels,
                            chart_patient_reg=chart_patient_reg,
                            chart_appointments=chart_appointments,
                            system_notifications=system_notifications,
                            active_page='dashboard')
    except Exception as e:
        print(f"[CRITICAL ERROR] Dashboard route failed: {e}")
        import traceback
        traceback.print_exc()
        return f"Internal Server Error: {e}", 500

@app.route('/queue/add/<patient_id>')
def add_to_queue(patient_id):
    patient = hms.get_patient(patient_id)
    if patient:
        # Check if already in queue (only block if they are currently waiting or being seen)
        if not any(q.patient_id == patient_id and (q.status or "").strip() not in ['Completed', 'No-show', 'Cancelled'] for q in hms.queue):
            new_item = QueueItem(
                queue_id=hms.generate_id('Q'),
                patient_id=patient.patient_id,
                patient_name=f"{patient.last_name}, {patient.first_name}",
                doctor_id="Unassigned",
                status="Waiting",
                priority="Routine",
                arrival_time=datetime.datetime.now().strftime("%H:%M"),
                estimated_wait=hms.estimate_wait_time(''),
                department='',
                visit_reason='',
                special_category='',
                check_in_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                date_added=datetime.datetime.now().strftime("%Y-%m-%d"),
                assigned_doctor_id='',
                triage_level='3',
                vitals={}
            )
            hms.add_to_queue(new_item)
            flash(f'{patient.first_name} added to queue.', 'success')
            notify('Queue update', f"{patient.last_name}, {patient.first_name} added to queue", 'receptionist')
        else:
            flash('Patient is already in the active queue.', 'warning')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/queue/update/<queue_id>/<status>')
def update_queue_status(queue_id, status):
    if hms.update_queue_status(queue_id, status):
        flash(f'Queue status updated to {status}.', 'success')
        notify('Queue status', f"{queue_id} -> {status}", 'receptionist')
    return redirect(url_for('dashboard'))

@app.route('/queue/remove/<queue_id>')
def remove_from_queue(queue_id):
    if hms.remove_from_queue(queue_id):
        flash('Patient removed from queue.', 'success')
        notify('Queue update', f"Removed from queue: {queue_id}", 'receptionist')
    return redirect(url_for('dashboard'))

@app.route('/queue/checkin', methods=['GET','POST'])
def queue_checkin():
    patients = hms.patients
    departments = hms.departments or ['General']
    doctors = hms.doctors
    urgencies = ['Emergency','Urgent','Routine']
    specials = ['None','Elderly','Pregnant','Disabled']
    if request.method == 'POST':
        pid = request.form.get('patient_id')
        dept = request.form.get('department') or ''
        reason = request.form.get('reason') or ''
        urgency = request.form.get('urgency') or 'Routine'
        special = request.form.get('special') or 'None'
        doc_id = request.form.get('doctor_id') or 'Unassigned'
        triage = request.form.get('triage_level') or '3'
        bp = request.form.get('bp') or ''
        temp = request.form.get('temp') or ''
        weight = request.form.get('weight') or ''
        p = hms.get_patient(pid)
        if p:
            # Check if already in queue (only block if they are currently waiting or being seen)
            if any(q.patient_id == pid and (q.status or "").strip() not in ['Completed', 'No-show', 'Cancelled'] for q in hms.queue):
                flash('Patient is already in the active queue.', 'warning')
                return redirect(url_for('queue_dashboard'))

            new_item = QueueItem(
                queue_id=hms.generate_id('Q'),
                patient_id=p.patient_id,
                patient_name=f"{p.last_name}, {p.first_name}",
                doctor_id=doc_id,
                status="Waiting",
                priority=urgency,
                arrival_time=datetime.datetime.now().strftime("%H:%M"),
                date_added=datetime.datetime.now().strftime("%Y-%m-%d"),
                estimated_wait=hms.estimate_wait_time(dept),
                department=dept,
                visit_reason=reason,
                special_category=special,
                check_in_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                assigned_doctor_id=doc_id,
                triage_level=triage,
                vitals={'bp': bp, 'temp': temp, 'weight': weight}
            )
            hms.add_to_queue(new_item)
            flash('Patient checked in.', 'success')
            notify('Queue check-in', f"{new_item.patient_name} for {dept}", 'receptionist')
            if doc_id and doc_id != 'Unassigned':
                notify('Queue assigned', f"{new_item.patient_name} -> {doc_id}", 'doctor')
            return redirect(url_for('queue_dashboard'))
        flash('Invalid patient.', 'error')
    return render_template('queue/checkin.html', patients=patients, departments=departments, doctors=doctors, urgencies=urgencies, specials=specials, active_page='queue')

@app.route('/queue/dashboard')
def queue_dashboard():
    # Exclude completed and no-show items from active dashboard
    active_items = [q for q in hms.queue if (q.status or '').strip() not in ['Completed', 'No-show']]
    queues_by_dept = {}
    for q in active_items:
        d = q.department or 'General'
        queues_by_dept.setdefault(d, []).append(q)
    for d in queues_by_dept:
        queues_by_dept[d] = sorted(queues_by_dept[d], key=lambda x: (x.priority or 'Routine', x.arrival_time or ''))
    return render_template('queue/dashboard.html', queues_by_dept=queues_by_dept, doctors=hms.doctors, departments=hms.departments or ['General'], active_page='queue')

@app.route('/queue/call/<queue_id>')
def queue_call(queue_id):
    if hms.call_patient(queue_id):
        flash('Patient called.', 'success')
        notify('Queue call', queue_id, 'receptionist')
    return redirect(url_for('queue_dashboard'))

@app.route('/queue/transfer/<queue_id>', methods=['POST'])
def queue_transfer(queue_id):
    dept = request.form.get('department') or ''
    doc_id = request.form.get('doctor_id') or ''
    if hms.transfer_patient(queue_id, dept, doc_id):
        flash('Patient transferred.', 'success')
        notify('Queue transfer', f"{queue_id} -> {dept}", 'receptionist')
    return redirect(url_for('queue_dashboard'))

@app.route('/queue/requeue/<queue_id>')
def queue_requeue(queue_id):
    if hms.requeue_patient(queue_id):
        flash('Patient re-queued.', 'success')
        notify('Queue requeue', queue_id, 'receptionist')
    return redirect(url_for('queue_dashboard'))

@app.route('/queue/complete/<queue_id>')
def queue_complete(queue_id):
    if hms.update_queue_status(queue_id, 'Completed'):
        flash('Consultation completed.', 'success')
        notify('Consultation completed', queue_id, 'cashier')
    return redirect(url_for('queue_dashboard'))

@app.route('/queue/noshow/<queue_id>')
def queue_noshow(queue_id):
    if hms.update_queue_status(queue_id, 'No-show'):
        flash('Marked as no-show.', 'success')
        notify('No-show', queue_id, 'receptionist')
    return redirect(url_for('queue_dashboard'))

@app.route('/queue/clear_all')
def queue_clear_all():
    try:
        hms.queue = []
        hms.save_data()
        flash('Cleared all items from the queue.', 'success')
        notify('Queue cleared', 'All items cleared', 'receptionist')
    except Exception as e:
        flash(f'Error clearing queue: {e}', 'error')
    return redirect(url_for('queue_dashboard'))

@app.route('/patient/<patient_id>')
def patient_details(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))
    
    # Sync with Supabase to discover legacy or remote files
    hms.sync_patient_attachments(patient_id)
    
    files = hms.patient_files.get(patient_id, [])
    appointments = hms.get_patient_appointments(patient_id)
    medical_records = hms.get_patient_medical_records(patient_id)
    bills = hms.get_patient_bills(patient_id)
    lab_results = [lr for lr in hms.lab_results if lr.patient_id == patient_id]
    queue_item = next((q for q in hms.queue if q.patient_id == patient_id and q.status != 'Completed'), None)
    
    return render_template('patient_details.html', 
                           patient=patient, 
                           files=files, 
                           appointments=appointments, 
                           medical_records=medical_records,
                           bills=bills,
                           lab_results=lab_results,
                           queue_item=queue_item,
                           active_page='patients')

@app.route('/patient/<patient_id>/send_to_lab')
def send_to_lab(patient_id):
    queue_item = next((q for q in hms.queue if q.patient_id == patient_id and q.status != 'Completed'), None)
    if queue_item:
        queue_item.status = "In Lab"
        hms.save_data()
        notify('Lab Request', f"{patient_id} sent to lab", 'lab_assistant')
        flash('Patient sent to lab.', 'success')
    else:
        # Patient not in queue, maybe check them in first?
        # For simplicity, we'll just say they aren't in the active queue.
        flash('Patient is not currently in the active queue.', 'error')
    return redirect(url_for('patient_details', patient_id=patient_id))

@app.route('/patient/<patient_id>/upload_file', methods=['POST'])
def upload_patient_file(patient_id):
    redirect_url = request.form.get('redirect_url') or url_for('patient_details', patient_id=patient_id)
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(redirect_url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(redirect_url)
    
    if file:
        filename = secure_filename(file.filename)
        # Create a temporary path to save the uploaded file before passing to HMS
        # HMS expects file paths to copy from
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        temp_path = os.path.join(upload_folder, filename)
        file.save(temp_path)
        
        try:
            hms.add_patient_files(patient_id, [temp_path])
            flash('File uploaded successfully!', 'success')
        except Exception as e:
            flash(f'Error uploading file: {e}', 'error')
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return redirect(redirect_url)

@app.route('/patient/<patient_id>/delete_file')
def delete_patient_file(patient_id):
    rel_path = request.args.get('path')
    redirect_url = request.args.get('redirect_url') or url_for('patient_details', patient_id=patient_id)
    if hms.delete_patient_file(patient_id, rel_path):
        flash('File deleted successfully!', 'success')
    else:
        flash('Error deleting file!', 'error')
    return redirect(redirect_url)

@app.route('/download_file')
def download_file():
    path = request.args.get('path')
    if not path:
        return "File not found", 404
        
    # Security check: ensure path is within attachments
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    abs_path = os.path.join(base_dir, path)
    
    if not os.path.exists(abs_path):
        # Check if we have a Supabase URL for this file
        from supabase_data_manager import get_supabase_file_url
        sup_url = get_supabase_file_url(path)
        if sup_url:
            return redirect(sup_url)
        return "File not found", 404
        
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/serve_file')
def serve_file():
    path = request.args.get('path')
    if not path:
        return "File not found", 404
        
    # Security check: ensure path is within attachments
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    abs_path = os.path.join(base_dir, path)
    
    if not os.path.exists(abs_path):
        # Check if we have a Supabase URL for this file
        from supabase_data_manager import get_supabase_file_url
        sup_url = get_supabase_file_url(path)
        if sup_url:
            return redirect(sup_url)
        return "File not found", 404
        
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename)
# ADD this at the top of app.py with the other imports
import sqlite3

@app.route('/patients')
def patients():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 10

    conn = hms.db.get_connection()
    cursor = conn.cursor()

    if search_term:
        search_value = f"%{search_term}%"
        
        query_params = (search_value, search_value, search_value, search_value, search_value, search_value)
        
        cursor.execute("""
            SELECT * FROM patients
            WHERE is_deleted = 0 AND (
                patient_id LIKE ?
                OR first_name LIKE ?
                OR last_name LIKE ?
                OR (first_name || ' ' || last_name) LIKE ?
                OR (last_name || ' ' || first_name) LIKE ?
                OR phone LIKE ?
            )
            ORDER BY rowid DESC
            LIMIT ? OFFSET ?
        """, (*query_params, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) FROM patients
            WHERE is_deleted = 0 AND (
                patient_id LIKE ?
                OR first_name LIKE ?
                OR last_name LIKE ?
                OR (first_name || ' ' || last_name) LIKE ?
                OR (last_name || ' ' || first_name) LIKE ?
                OR phone LIKE ?
            )
        """, query_params)
        
        total_count = cursor.fetchone()[0]

    else:
        cursor.execute("""
            SELECT * FROM patients WHERE is_deleted = 0
            ORDER BY rowid DESC
            LIMIT ? OFFSET ?
        """, (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM patients WHERE is_deleted = 0")
        total_count = cursor.fetchone()[0]

    conn.close()

    # ✅ Convert to Patient objects so template can use patient.patient_id etc.
    patients = [hms.db._row_to_obj(Patient, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1

    return render_template(
        'patients.html',
        patients=patients,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        search_term=search_term
    )
@app.route('/deleted_patients')
def deleted_patients():
    patients = hms.get_deleted_patients()
    return render_template('deleted_patients.html', patients=patients, active_page='patients')

@app.route('/recover_patient/<patient_id>')
def recover_patient(patient_id):
    if hms.recover_patient(patient_id):
        flash('Patient recovered successfully!', 'success')
        notify('Patient recovered', patient_id, 'admin')
    else:
        flash('Error recovering patient.', 'error')
    return redirect(url_for('deleted_patients'))

@app.route('/permanent_delete_patient/<patient_id>')
def permanent_delete_patient(patient_id):
    if hms.delete_patient(patient_id, permanent=True):
        flash('Patient permanently deleted.', 'success')
        notify('Patient permanently deleted', patient_id, 'admin')
    else:
        flash('Error deleting patient.', 'error')
    return redirect(url_for('deleted_patients'))

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            
            if not patient_id:
                flash('Patient ID is required!', 'error')
                return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)
            
            # Check for existing patient ID
            if hms.get_patient(patient_id):
                flash(f'Patient ID "{patient_id}" already exists. Please use a unique ID.', 'error')
                return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)

            new_patient = Patient(
                patient_id=patient_id,
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                date_of_birth=request.form.get('dob',''),
                gender=request.form.get('gender',''),
                phone=request.form.get('phone',''),
                email=request.form.get('email',''),
                address=request.form.get('address',''),
                emergency_contact=request.form.get('emergency_contact',''),
                blood_group=request.form.get('blood_group',''),
                medical_history=request.form.get('medical_history',''),
                created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                scheme_provider=request.form.get('scheme_provider',''),
                scheme_type=request.form.get('scheme_type','')
            )
            hms.add_patient(new_patient)
            flash('Patient added successfully!', 'success')
            notify('Patient added', f"{new_patient.last_name}, {new_patient.first_name} ({new_patient.patient_id})", 'admin')
            notify('Patient added', f"{new_patient.last_name}, {new_patient.first_name}", 'receptionist')
            return redirect(url_for('patients'))
        except Exception as e:
            flash(f'Error adding patient: {e}', 'error')
    
    return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)

@app.route('/edit_patient/<patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))

    if request.method == 'POST':
        try:
            # Get original patient object for validation
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('patients'))

            new_id = (request.form.get('patient_id', '') or patient_id).strip()
            
            # Prepare update data
            update_data = {
                'patient_id': new_id,
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'date_of_birth': request.form.get('dob',''),
                'gender': request.form.get('gender',''),
                'phone': request.form.get('phone',''),
                'email': request.form.get('email',''),
                'address': request.form.get('address',''),
                'emergency_contact': request.form.get('emergency_contact',''),
                'blood_group': request.form.get('blood_group',''),
                'medical_history': request.form.get('medical_history',''),
                'scheme_provider': request.form.get('scheme_provider',''),
                'scheme_type': request.form.get('scheme_type','')
            }
            
            # Filter out None values to avoid overwriting with empty
            # Actually, we want to allow empty strings, just not None
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            # Explicitly pass original_id to avoid conflict with patient_id in update_data
            success = hms.update_patient(original_id=patient_id, **update_data)
            print(f"[DEBUG] edit_patient: update_patient success={success}")
            if success:
                flash('Patient updated successfully!', 'success')
                notify('Patient updated', new_id or patient_id, 'admin')
                return redirect(url_for('patients'))
            else:
                print(f"[ERROR] edit_patient: update_patient failed for {patient_id}")
                flash('Error updating patient: ID might already be in use.', 'error')
        except Exception as e:
            print(f"[ERROR] edit_patient exception: {e}")
            flash(f'Error updating patient: {e}', 'error')

    return render_template('edit_patient.html', patient=patient, active_page='patients', providers=PROVIDERS)


@app.route('/delete_patient/<patient_id>')
def delete_patient(patient_id):
    if hms.delete_patient(patient_id):
        flash('Patient deleted successfully! You can recover it from the recovery system.', 'success')
        notify('Patient soft-deleted', patient_id, 'admin')
    else:
        flash('Error deleting patient!', 'error')
    return redirect(url_for('patients'))

@app.route('/doctors')
def doctors():
    search_term = request.args.get('search', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if search_term:
        all_results = hms.search_doctors(search_term)
        total_count = len(all_results)
        doctors_slice, total_pages = paginate_list(all_results, page, per_page)
    else:
        # Scalable query
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM doctors")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM doctors LIMIT ? OFFSET ?", (per_page, (page-1)*per_page))
        rows = cursor.fetchall()
        doctors_slice = [hms.db._row_to_obj(Doctor, row) for row in rows]
        conn.close()
        total_pages = math.ceil(total_count / per_page)
        
    return render_template('doctors.html', 
                           doctors=doctors_slice, 
                           active_page='doctors',
                           search_term=search_term,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count)

@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        try:
            new_doctor = Doctor(
                doctor_id=hms.generate_id("D"),
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                specialty=request.form['specialty'],
                phone=request.form['phone'],
                email=request.form['email'],
                status=request.form['status'],
                is_locum=1 if 'is_locum' in request.form else 0,
                locum_name=request.form.get('locum_name', '')
            )
            hms.add_doctor(new_doctor)
            flash('Doctor added successfully!', 'success')
            notify('Doctor added', f"{new_doctor.first_name} {new_doctor.last_name} ({new_doctor.doctor_id})", 'admin')
            return redirect(url_for('doctors'))
        except Exception as e:
            flash(f'Error adding doctor: {e}', 'error')
    
    return render_template('add_doctor.html', active_page='doctors')

@app.route('/edit_doctor/<doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    doctor = hms.get_doctor(doctor_id)
    if not doctor:
        flash('Doctor not found!', 'error')
        return redirect(url_for('doctors'))

    if request.method == 'POST':
        try:
            hms.update_doctor(
                doctor_id,
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                specialty=request.form['specialty'],
                phone=request.form['phone'],
                email=request.form['email'],
                status=request.form['status'],
                is_locum=1 if 'is_locum' in request.form else 0,
                locum_name=request.form.get('locum_name', '')
            )
            flash('Doctor updated successfully!', 'success')
            notify('Doctor updated', doctor_id, 'admin')
            return redirect(url_for('doctors'))
        except Exception as e:
            flash(f'Error updating doctor: {e}', 'error')

    return render_template('edit_doctor.html', doctor=doctor, active_page='doctors')

@app.route('/delete_doctor/<doctor_id>')
def delete_doctor(doctor_id):
    if hms.delete_doctor(doctor_id):
        flash('Doctor deleted successfully!', 'success')
        notify('Doctor deleted', doctor_id, 'admin')
    else:
        flash('Error deleting doctor!', 'error')
    return redirect(url_for('doctors'))

@app.route('/create_medical_record', methods=['GET', 'POST'])
def create_medical_record():
    patient_id = request.args.get('patient_id')
    patients = hms.patients
    doctors = hms.doctors

    if request.method == 'POST':
        try:
            new_record = MedicalRecord(
                record_id=hms.generate_id("MR"),
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                date=request.form.get('visit_date', request.form.get('date', '')),
                consult_reason=request.form.get('consult_reason', 'General Consultation'),
                diagnosis=request.form['diagnosis'],
                treatment=request.form['treatment'],
                prescriptions=request.form.get('prescriptions', request.form.get('prescription', '')),
                notes=request.form.get('notes', '')
            )
            if hms.add_medical_record(new_record):
                flash('Medical record created successfully!', 'success')
                return redirect(url_for('patient_details', patient_id=new_record.patient_id))
            else:
                flash('Failed to create medical record in database.', 'error')
        except Exception as e:
            flash(f'Error creating medical record: {e}', 'error')

    return render_template('create_medical_record.html', patients=patients, doctors=doctors, patient_id=patient_id, active_page='patients')

@app.route('/patients/<patient_id>/records')
def view_medical_records(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))

    records = hms.get_patient_medical_records(patient_id)
    files = hms.patient_files.get(patient_id, [])
    return render_template('view_medical_records.html', patient=patient, records=records, files=files, active_page='patients', hms=hms)

@app.route('/schedule_appointment', methods=['GET', 'POST'])
def schedule_appointment():
    doctors = hms.get_available_doctors()
    patients = hms.patients
    
    if request.method == 'POST':
        try:
            new_appointment = Appointment(
                appointment_id=hms.generate_id("A"),
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                appointment_date=request.form['date'],
                appointment_time=request.form['time'],
                reason=request.form['reason'],
                status="Scheduled",
                notes=""
            )
            hms.schedule_appointment(new_appointment)
            flash('Appointment scheduled successfully!', 'success')
            notify('Appointment scheduled', f"{new_appointment.patient_id} -> {new_appointment.doctor_id} {new_appointment.appointment_date} {new_appointment.appointment_time}", 'receptionist')
            notify('Appointment scheduled', new_appointment.doctor_id, 'doctor')
            return redirect(url_for('view_schedule'))
        except Exception as e:
            flash(f'Error scheduling appointment: {e}', 'error')

    return render_template('schedule_appointment.html', doctors=doctors, patients=patients, active_page='schedule')

@app.route('/edit_appointment/<appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    appointment = hms.get_appointment(appointment_id)
    if not appointment:
        flash('Appointment not found!', 'error')
        return redirect(url_for('view_schedule'))

    doctors = hms.doctors
    patients = hms.patients
    
    # Get current patient details and files
    current_patient = hms.get_patient(appointment.patient_id)
    patient_files = hms.patient_files.get(appointment.patient_id, []) if current_patient else []

    if request.method == 'POST':
        try:
            hms.update_appointment(
                appointment_id,
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                appointment_date=request.form['date'],
                appointment_time=request.form['time'],
                reason=request.form['reason'],
                status=request.form['status']
            )
            flash('Appointment updated successfully!', 'success')
            notify('Appointment updated', appointment_id, 'receptionist')
            return redirect(url_for('view_schedule'))
        except Exception as e:
            flash(f'Error updating appointment: {e}', 'error')

    return render_template('edit_appointment.html', 
                           appointment=appointment, 
                           doctors=doctors, 
                           patients=patients, 
                           current_patient=current_patient,
                           patient_files=patient_files,
                           active_page='schedule')

@app.route('/delete_appointment/<appointment_id>')
def delete_appointment(appointment_id):
    if hms.delete_appointment(appointment_id):
        flash('Appointment deleted successfully!', 'success')
        notify('Appointment deleted', appointment_id, 'receptionist')
    else:
        flash('Error deleting appointment!', 'error')
    return redirect(url_for('view_schedule'))

@app.route('/departments')
def departments():
    # Group doctors by specialty
    departments_map = {}
    
    # 1. Add explicit departments first (initially empty doctor list)
    for dept in hms.departments:
        departments_map[dept] = []
        
    # 2. Add doctors to departments (and create derived ones)
    for doctor in hms.doctors:
        # Check for both specialty and specialization just in case
        spec = getattr(doctor, 'specialty', getattr(doctor, 'specialization', 'General'))
        if not spec:
            spec = 'General'
        if spec not in departments_map:
            departments_map[spec] = []
        departments_map[spec].append(doctor)
        
    return render_template('departments.html', departments=departments_map, active_page='departments')

@app.route('/add_department', methods=['POST'])
def add_department():
    dept_name = request.form.get('department_name')
    if dept_name:
        if dept_name not in hms.departments:
            hms.departments.append(dept_name)
            hms.save_data()
            flash(f'Department "{dept_name}" added successfully!', 'success')
            notify('Department added', dept_name, 'admin')
        else:
            flash(f'Department "{dept_name}" already exists.', 'warning')
    return redirect(url_for('departments'))

@app.route('/messages')
def messages():
    # Get current user details from session
    current_username = session.get('username')
    current_role = session.get('role')
    
    # Use optimized database query
    user_messages = hms.get_messages_for_user(current_username, current_role)
    
    # Format for display
    display_messages = []
    for msg in user_messages:
        display_messages.append({
            'id': msg.message_id,
            'sender': msg.sender_name,
            'sender_id': msg.sender_id,
            'role': 'User', # Could look up sender role
            'time': msg.timestamp,
            'preview': msg.subject,
            'content': msg.content,
            'active': False,
            'is_read': msg.is_read,
            'is_outgoing': (msg.sender_id == current_username)
        })
        
    if display_messages:
        display_messages[0]['active'] = True
    
    # Mark as read using SQL for scalability
    conn = hms.db.get_connection()
    conn.execute("""
        UPDATE messages SET is_read = 1 
        WHERE is_read = 0 AND (recipient_id = ? OR recipient_id = ? OR recipient_id = 'all')
    """, (current_username, current_role))
    conn.commit()
    conn.close()
        
    # Get list of potential recipients
    recipients = []
    roles = ['admin', 'doctor', 'nurse', 'receptionist', 'cashier', 'lab_assistant']
    for r in roles:
        if r != current_role:
            recipients.append({'id': r, 'name': f"All {r.title()}s", 'type': 'role'})
            
    # Add individual users (limited to 50 for performance)
    for user in hms.db.get_all(User, 'users', limit=50):
        if user.username != current_username:
            recipients.append({'id': user.username, 'name': user.username, 'type': 'user'})

    return render_template('messages.html', 
                           active_page='messages', 
                           messages=display_messages,
                           recipients=recipients)

@app.route('/messages/send', methods=['POST'])
def send_message():
    content = request.form.get('message')
    recipient_id = request.form.get('recipient')
    subject = request.form.get('subject', 'No Subject')
    
    current_username = session.get('username')
    
    if content and recipient_id:
        new_msg = Message(
            message_id=hms.generate_id('msg_'),
            sender_id=current_username,
            sender_name=current_username, # Ideally fetch full name
            recipient_id=recipient_id,
            subject=subject,
            content=content,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            is_read=False,
            is_archived=False
        )
        hms.add_message(new_msg) # I should add this method to HMS
        flash('Message sent successfully!', 'success')
    else:
        flash('Message cannot be empty.', 'error')
        
    return redirect(url_for('messages'))

@app.route('/view_lab_results')
def view_lab_results():
    # Use optimized database query
    lab_records = hms.get_lab_records()
    return render_template('view_lab_results.html', medical_records=lab_records, active_page='lab_results')

@app.route('/general_reports')
def general_reports():
    # Use optimized database aggregation
    stats = hms.get_report_stats()
    
    total_patients = stats['total_patients']
    total_doctors = stats['total_doctors']
    total_appointments = stats['total_appointments']
    revenue = stats['revenue']
    department_counts = stats['department_counts']

    # Demographics
    gender_counts = stats['gender_counts']
    male_patients = gender_counts.get('Male', 0) + gender_counts.get('male', 0)
    female_patients = gender_counts.get('Female', 0) + gender_counts.get('female', 0)
    
    if total_patients > 0:
        male_pct = int((male_patients / total_patients) * 100)
        female_pct = int((female_patients / total_patients) * 100)
    else:
        male_pct = 0
        female_pct = 0

    # Appointment Status
    status_counts = stats['status_counts']
    completed_appt = status_counts.get('Completed', 0)
    cancelled_appt = status_counts.get('Cancelled', 0)
    no_show_appt = status_counts.get('No-show', 0)
    
    if total_appointments > 0:
        completed_pct = int((completed_appt / total_appointments) * 100)
        cancelled_pct = int((cancelled_appt / total_appointments) * 100)
        no_show_pct = int((no_show_appt / total_appointments) * 100)
    else:
        completed_pct = 0
        cancelled_pct = 0
        no_show_pct = 0

    return render_template('general_reports.html', 
                           active_page='reports',
                           today=datetime.datetime.now().strftime("%Y-%m-%d"),
                           total_patients=total_patients,
                           total_doctors=total_doctors,
                           total_appointments=total_appointments,
                           revenue=revenue,
                           department_counts=department_counts,
                           male_pct=male_pct,
                           female_pct=female_pct,
                           completed_pct=completed_pct,
                           cancelled_pct=cancelled_pct,
                           no_show_pct=no_show_pct)

@app.route('/view_schedule')
def view_schedule():
    search_term = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if search_term:
        all_results = hms.search_appointments(search_term)
        total_count = len(all_results)
        appointments_slice, total_pages = paginate_list(all_results, page, per_page)
    else:
        # Scale by querying only what we need
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM appointments ORDER BY appointment_date DESC, appointment_time DESC LIMIT ? OFFSET ?", 
                      (per_page, (page-1)*per_page))
        rows = cursor.fetchall()
        appointments_slice = [hms.db._row_to_obj(Appointment, row) for row in rows]
        conn.close()
        total_pages = math.ceil(total_count / per_page)
        
    return render_template('view_schedule.html', 
                           appointments=appointments_slice, 
                           active_page='schedule', 
                           search_term=search_term,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count)

@app.route('/billing')
def billing_dashboard():
    # Filter for search if needed
    search_term = request.args.get('search', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    search_parts = search_term.split()
    
    # Sort bills by timestamp descending (newest first), falling back to date if timestamp missing
    all_bills = sorted(hms.bills, key=lambda x: (getattr(x, 'created_at', '') or getattr(x, 'created_date', '') or ''), reverse=True)
    
    # Resolve patient names for display
    filtered_bills = []
    for bill in all_bills:
        patient = hms.get_patient(bill.patient_id)
        p_name = f"{patient.last_name}, {patient.first_name}" if patient else "Unknown"
        
        # Search filter
        p_first = patient.first_name.lower() if patient else ""
        p_last = patient.last_name.lower() if patient else ""
        
        bill_text = (
            bill.bill_id.lower() + " " +
            p_first + " " +
            p_last + " " +
            bill.status.lower()
        )
        
        if search_term and not all(part in bill_text for part in search_parts):
            continue
            
        filtered_bills.append({
            'bill_id': bill.bill_id,
            'date': bill.created_date,
            'patient_name': p_name,
            'amount': bill.amount,
            'status': bill.status,
            'services': bill.services
        })

    bills_slice, total_pages = paginate_list(filtered_bills, page)

    # Calculate stats
    total_revenue = sum(b.amount for b in hms.bills if b.status.lower() == 'paid')
    pending_amount = sum(b.amount for b in hms.bills if b.status.lower() == 'pending')
    total_bills = len(hms.bills)
    
    return render_template('billing_dashboard.html', 
                           bills=bills_slice, 
                           patients=hms.patients,
                           inventory=hms.inventory,
                           total_revenue=total_revenue,
                           pending_amount=pending_amount,
                           total_bills=total_bills,
                           today_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                           active_page='billing',
                           hms_providers=PROVIDERS,
                           page=page,
                           total_pages=total_pages,
                           total_count=len(filtered_bills),
                           search_term=search_term)

@app.route('/billing/create', methods=['GET', 'POST'])
def create_bill():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            
            # Check if it's the dashboard's "Create Bill" tab fields
            if request.form.getlist('item_date[]'):
                dates = request.form.getlist('item_date[]')
                id_nos = request.form.getlist('item_id_no[]')
                cons = request.form.getlist('item_con[]')
                drugs = request.form.getlist('item_drug[]')
                labs = request.form.getlist('item_lab[]')
                amounts = request.form.getlist('item_amount[]')
                
                invoice_items = []
                total_amount = 0
                services_summary = []
                
                for i in range(len(dates)):
                    if not dates[i]: continue
                    
                    amt = float(amounts[i])
                    total_amount += amt
                    
                    item = {
                        'date': dates[i],
                        'id_no': id_nos[i],
                        'con': float(cons[i]),
                        'drug': float(drugs[i]),
                        'lab': float(labs[i]),
                        'amount': amt
                    }
                    invoice_items.append(item)
                    services_summary.append(f"Services on {dates[i]} (${amt})")
                
                if not invoice_items:
                    flash('No items added to invoice', 'error')
                    return redirect(url_for('billing_dashboard'))
                
                new_bill = Bill(
                    bill_id=hms.generate_id("INV"),
                    patient_id=patient_id,
                    appointment_id="",
                    amount=total_amount,
                    services=", ".join(services_summary),
                    status="Pending",
                    created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    items=invoice_items,
                    created_at=datetime.datetime.now().isoformat()
                )
            else:
                # Old style / legacy form support
                items = request.form.getlist('items[]')
                costs = request.form.getlist('costs[]')
                provider = request.form.get('provider') or 'Cash'
                bill_items = []
                total_amount = 0
                for i in range(len(items)):
                    if items[i] and costs[i]:
                        cost = float(costs[i])
                        bill_items.append({"name": items[i], "cost": cost, "provider": provider})
                        total_amount += cost

                new_bill = Bill(
                    bill_id=hms.generate_id("INV"),
                    patient_id=patient_id,
                    appointment_id="", 
                    amount=total_amount,
                    services=", ".join(items),
                    items=bill_items,
                    status="Pending",
                    created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                    created_at=datetime.datetime.now().isoformat()
                )
            
            hms.create_bill(new_bill)
            flash('Bill created successfully!', 'success')
            notify('Bill created', new_bill.bill_id, 'cashier')
            return redirect(url_for('billing_dashboard'))
        except Exception as e:
            flash(f'Error creating bill: {e}', 'error')
    
    return render_template('billing/create_bill.html', patients=hms.patients, inventory=hms.inventory, providers=PROVIDERS, active_page='billing')

@app.route('/invoice', methods=['POST'])
def handle_invoice():
    try:
        provider = request.form.get('provider')
        invoice_date = request.form.get('invoice_date')
        
        dates = request.form.getlist('item_date[]')
        patient_ids = request.form.getlist('item_patient_id[]')
        id_nos = request.form.getlist('item_id_no[]')
        cons = request.form.getlist('item_con[]')
        drugs = request.form.getlist('item_drug[]')
        drug_ids_grouped = request.form.getlist('item_drug_ids[]')
        drug_qtys_grouped = request.form.getlist('item_drug_qtys[]')
        drug_prices_grouped = request.form.getlist('item_drug_prices[]')
        
        labs = request.form.getlist('item_lab[]')
        lab_ids_grouped = request.form.getlist('item_lab_ids[]')
        lab_qtys_grouped = request.form.getlist('item_lab_qtys[]')
        lab_prices_grouped = request.form.getlist('item_lab_prices[]')
        
        amounts = request.form.getlist('item_amount[]')

        invoice_items = []
        total_invoice_amount = 0
        
        for i in range(len(patient_ids)):
            if not patient_ids[i]: continue
            
            item_amount = float(amounts[i])
            total_invoice_amount += item_amount
            
            # Reconstruct mini drugs
            row_drugs = []
            if i < len(drug_ids_grouped) and drug_ids_grouped[i]:
                ids = drug_ids_grouped[i].split(',')
                qtys = drug_qtys_grouped[i].split(',')
                prices = drug_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_drugs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            # Reconstruct mini labs
            row_labs = []
            if i < len(lab_ids_grouped) and lab_ids_grouped[i]:
                ids = lab_ids_grouped[i].split(',')
                qtys = lab_qtys_grouped[i].split(',')
                prices = lab_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_labs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            invoice_items.append({
                'date': dates[i],
                'patient_id': patient_ids[i],
                'id_no': id_nos[i],
                'con': float(cons[i]),
                'drug': float(drugs[i]),
                'drugs': row_drugs,
                'lab': float(labs[i]),
                'labs': row_labs,
                'amount': item_amount
            })

        if not invoice_items:
            flash('No items added to invoice', 'error')
            return redirect(url_for('billing_dashboard'))

        primary_patient_id = patient_ids[0]
        
        new_bill = Bill(
            bill_id=hms.generate_id("INV"),
            patient_id=primary_patient_id,
            appointment_id="",
            amount=total_invoice_amount,
            services=f"Bulk Invoice for {provider}",
            status="Pending",
            created_date=invoice_date,
            provider=provider,
            items=invoice_items,
            created_at=datetime.datetime.now().isoformat()
        )
        
        hms.create_bill(new_bill)
        flash('Invoice saved successfully!', 'success')
        notify('Invoice created', new_bill.bill_id, 'cashier')
        
    except Exception as e:
        flash(f'Error saving invoice: {e}', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/invoice/individual', methods=['POST'])
def handle_individual_invoice():
    try:
        patient_id = request.form.get('patient_id')
        invoice_date = request.form.get('invoice_date')
        
        dates = request.form.getlist('ind_date[]')
        id_nos = request.form.getlist('ind_id_no[]')
        cons = request.form.getlist('ind_con[]')
        drugs = request.form.getlist('ind_drug[]')
        drug_ids_grouped = request.form.getlist('ind_drug_ids[]')
        drug_qtys_grouped = request.form.getlist('ind_drug_qtys[]')
        drug_prices_grouped = request.form.getlist('ind_drug_prices[]')
        
        labs = request.form.getlist('ind_lab[]')
        lab_ids_grouped = request.form.getlist('ind_lab_ids[]')
        lab_qtys_grouped = request.form.getlist('ind_lab_qtys[]')
        lab_prices_grouped = request.form.getlist('ind_lab_prices[]')
        
        amounts = request.form.getlist('ind_amount[]')

        invoice_items = []
        total_amount = 0
        services_summary = []
        
        for i in range(len(dates)):
            if not dates[i]: continue
            
            amt = float(amounts[i])
            total_amount += amt
            
            # Reconstruct mini drugs
            row_drugs = []
            if i < len(drug_ids_grouped) and drug_ids_grouped[i]:
                ids = drug_ids_grouped[i].split(',')
                qtys = drug_qtys_grouped[i].split(',')
                prices = drug_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_drugs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            # Reconstruct mini labs
            row_labs = []
            if i < len(lab_ids_grouped) and lab_ids_grouped[i]:
                ids = lab_ids_grouped[i].split(',')
                qtys = lab_qtys_grouped[i].split(',')
                prices = lab_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_labs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            item = {
                'date': dates[i],
                'id_no': id_nos[i],
                'con': float(cons[i]),
                'drug': float(drugs[i]),
                'drugs': row_drugs,
                'lab': float(labs[i]),
                'labs': row_labs,
                'amount': amt
            }
            invoice_items.append(item)
            services_summary.append(f"Individual services on {dates[i]} (${amt})")

        if not invoice_items:
            flash('No items added to invoice', 'error')
            return redirect(url_for('billing_dashboard'))

        new_bill = Bill(
            bill_id=hms.generate_id("INV"),
            patient_id=patient_id,
            appointment_id="",
            amount=total_amount,
            services=", ".join(services_summary),
            status="Pending",
            created_date=invoice_date,
            items=invoice_items,
            created_at=datetime.datetime.now().isoformat()
        )
        
        hms.create_bill(new_bill)
        flash('Individual Invoice saved successfully!', 'success')
        notify('Individual Invoice created', new_bill.bill_id, 'cashier')
        
    except Exception as e:
        flash(f'Error saving individual invoice: {e}', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/invoice/individual/update/<bill_id>', methods=['POST'])
def update_individual_invoice(bill_id):
    try:
        bill = hms.get_bill(bill_id)
        if not bill:
            flash('Bill not found', 'error')
            return redirect(url_for('billing_dashboard'))

        patient_id = request.form.get('patient_id')
        invoice_date = request.form.get('invoice_date')
        
        dates = request.form.getlist('ind_date[]')
        id_nos = request.form.getlist('ind_id_no[]')
        cons = request.form.getlist('ind_con[]')
        drugs = request.form.getlist('ind_drug[]')
        drug_ids_grouped = request.form.getlist('ind_drug_ids[]')
        drug_qtys_grouped = request.form.getlist('ind_drug_qtys[]')
        drug_prices_grouped = request.form.getlist('ind_drug_prices[]')
        
        labs = request.form.getlist('ind_lab[]')
        lab_ids_grouped = request.form.getlist('ind_lab_ids[]')
        lab_qtys_grouped = request.form.getlist('ind_lab_qtys[]')
        lab_prices_grouped = request.form.getlist('ind_lab_prices[]')
        
        amounts = request.form.getlist('ind_amount[]')

        invoice_items = []
        total_amount = 0
        services_summary = []
        
        for i in range(len(dates)):
            if not dates[i]: continue
            
            amt = float(amounts[i])
            total_amount += amt
            
            # Reconstruct mini drugs
            row_drugs = []
            if i < len(drug_ids_grouped) and drug_ids_grouped[i]:
                ids = drug_ids_grouped[i].split(',')
                qtys = drug_qtys_grouped[i].split(',')
                prices = drug_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_drugs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            # Reconstruct mini labs
            row_labs = []
            if i < len(lab_ids_grouped) and lab_ids_grouped[i]:
                ids = lab_ids_grouped[i].split(',')
                qtys = lab_qtys_grouped[i].split(',')
                prices = lab_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_labs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            item = {
                'date': dates[i],
                'id_no': id_nos[i],
                'con': float(cons[i]),
                'drug': float(drugs[i]),
                'drugs': row_drugs,
                'lab': float(labs[i]),
                'labs': row_labs,
                'amount': amt
            }
            invoice_items.append(item)
            services_summary.append(f"Individual services on {dates[i]} (${amt})")

        if not invoice_items:
            flash('No items added to invoice', 'error')
            return redirect(url_for('billing_dashboard'))

        bill.patient_id = patient_id
        bill.created_date = invoice_date
        bill.amount = total_amount
        bill.items = invoice_items
        bill.services = ", ".join(services_summary)
        
        hms.save_data()
        flash('Individual Invoice updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating individual invoice: {e}', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/api/bill/<bill_id>')
def get_bill_json(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    return jsonify(asdict(bill))

@app.route('/invoice/update/<bill_id>', methods=['POST'])
def update_invoice(bill_id):
    try:
        bill = hms.get_bill(bill_id)
        if not bill:
            flash('Bill not found', 'error')
            return redirect(url_for('billing_dashboard'))

        provider = request.form.get('provider')
        invoice_date = request.form.get('invoice_date')
        
        dates = request.form.getlist('item_date[]')
        patient_ids = request.form.getlist('item_patient_id[]')
        id_nos = request.form.getlist('item_id_no[]')
        cons = request.form.getlist('item_con[]')
        drugs = request.form.getlist('item_drug[]')
        drug_ids_grouped = request.form.getlist('item_drug_ids[]')
        drug_qtys_grouped = request.form.getlist('item_drug_qtys[]')
        drug_prices_grouped = request.form.getlist('item_drug_prices[]')
        
        labs = request.form.getlist('item_lab[]')
        lab_ids_grouped = request.form.getlist('item_lab_ids[]')
        lab_qtys_grouped = request.form.getlist('item_lab_qtys[]')
        lab_prices_grouped = request.form.getlist('item_lab_prices[]')
        
        amounts = request.form.getlist('item_amount[]')

        invoice_items = []
        total_invoice_amount = 0
        
        for i in range(len(patient_ids)):
            if not patient_ids[i]: continue
            
            item_amount = float(amounts[i])
            total_invoice_amount += item_amount
            
            # Reconstruct mini drugs
            row_drugs = []
            if i < len(drug_ids_grouped) and drug_ids_grouped[i]:
                ids = drug_ids_grouped[i].split(',')
                qtys = drug_qtys_grouped[i].split(',')
                prices = drug_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_drugs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            # Reconstruct mini labs
            row_labs = []
            if i < len(lab_ids_grouped) and lab_ids_grouped[i]:
                ids = lab_ids_grouped[i].split(',')
                qtys = lab_qtys_grouped[i].split(',')
                prices = lab_prices_grouped[i].split(',')
                for j in range(len(ids)):
                    row_labs.append({
                        'id': ids[j],
                        'qty': float(qtys[j]),
                        'price': float(prices[j])
                    })

            invoice_items.append({
                'date': dates[i],
                'patient_id': patient_ids[i],
                'id_no': id_nos[i],
                'con': float(cons[i]),
                'drug': float(drugs[i]),
                'drugs': row_drugs,
                'lab': float(labs[i]),
                'labs': row_labs,
                'amount': item_amount
            })

        if not invoice_items:
            flash('No items added to invoice', 'error')
            return redirect(url_for('billing_dashboard'))

        bill.provider = provider
        bill.created_date = invoice_date
        bill.amount = total_invoice_amount
        bill.items = invoice_items
        bill.services = f"Bulk Invoice for {provider} (Updated)"
        
        hms.save_data()
        flash('Invoice updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating invoice: {e}', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/api/billing/autosave', methods=['POST'])
def billing_autosave():
    try:
        data = request.json
        # Store drafts in a simple file or in hms
        if not hasattr(hms, 'billing_drafts'):
            hms.billing_drafts = {}
        
        user_id = session.get('user_id', 'default')
        tab = data.get('tab', 'general')
        hms.billing_drafts[f"{user_id}_{tab}"] = {
            'data': data.get('form_data'),
            'timestamp': datetime.datetime.now().isoformat()
        }
        # We don't necessarily need to hms.save_data() for every autosave 
        # to avoid disk I/O overhead, but we could.
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/billing/draft/<tab>')
def get_billing_draft(tab):
    user_id = session.get('user_id', 'default')
    draft = getattr(hms, 'billing_drafts', {}).get(f"{user_id}_{tab}")
    if draft:
        return jsonify(draft)
    return jsonify({'error': 'No draft found'}), 404

@app.route('/billing/delete/<bill_id>')
def delete_bill(bill_id):
    if hms.delete_bill(bill_id):
        flash('Bill deleted successfully!', 'success')
        notify('Bill deleted', bill_id, 'admin')
    else:
        flash('Error deleting bill!', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/billing/payment', methods=['POST'])
def process_payment():
    try:
        bill_id = request.form.get('bill_id')
        payment_method = request.form.get('payment_method')
        
        # Find bill and update status
        for bill in hms.bills:
            if bill.bill_id == bill_id:
                bill.status = "Paid"
                # Could add payment method to bill model if needed
                hms.save_data()
                flash(f'Payment processed for Bill {bill_id}', 'success')
                notify('Payment processed', bill_id, 'cashier')
                notify('Payment processed', bill_id, 'admin')
                break
    except Exception as e:
        flash(f'Error processing payment: {e}', 'error')
    return redirect(url_for('billing_dashboard'))

@app.route('/billing/view/<bill_id>')
def view_bill(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        flash('Bill not found', 'error')
        return redirect(url_for('billing_dashboard'))
        
    patient = hms.get_patient(bill.patient_id)
    return render_template('billing/view_bill.html', bill=bill, patient=patient, active_page='billing')

@app.route('/billing/pay/<bill_id>', methods=['POST'])
def pay_bill(bill_id):
    if hms.update_bill_status(bill_id, "Paid"):
        flash('Payment processed successfully!', 'success')
        notify('Payment processed', bill_id, 'cashier')
        notify('Payment processed', bill_id, 'admin')
    else:
        flash('Error processing payment', 'error')
    return redirect(url_for('view_bill', bill_id=bill_id))

@app.route('/billing/edit/<bill_id>', methods=['GET', 'POST'])
def edit_bill(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        flash('Bill not found', 'error')
        return redirect(url_for('billing_dashboard'))
    
    if request.method == 'POST':
        try:
            services = request.form.get('services')
            amount = float(request.form.get('amount'))
            status = request.form.get('status')
            
            bill.services = services
            bill.amount = amount
            bill.status = status
            hms.save_data()
            
            flash('Bill updated successfully!', 'success')
            return redirect(url_for('view_bill', bill_id=bill_id))
        except Exception as e:
            flash(f'Error updating bill: {e}', 'error')
            
    patient = hms.get_patient(bill.patient_id)
    return render_template('billing/edit_bill.html', bill=bill, patient=patient, active_page='billing')

@app.route('/billing/print/<bill_id>')
def print_invoice(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        return "Bill not found", 404
    
    # If this is a structured invoice (bulk or individual)
    if hasattr(bill, 'items') and bill.items:
        if getattr(bill, 'provider', None):
            # Bulk Invoice
            resolved_items = []
            for item in bill.items:
                p = hms.get_patient(item['patient_id'])
                item_copy = dict(item)
                item_copy['patient_name'] = f"{p.last_name}, {p.first_name}" if p else "Unknown"
                item_copy['scheme_type'] = getattr(p, 'scheme_type', '-') if p else "-"
                resolved_items.append(item_copy)
            
            return render_template('billing/invoice.html',
                                   bill=bill,
                                   items=resolved_items,
                                   is_bulk=True)
        else:
            # Individual Invoice with items
            patient = hms.get_patient(bill.patient_id)
            return render_template('billing/invoice.html',
                                   bill=bill,
                                   patient=patient,
                                   items=bill.items,
                                   is_bulk=False,
                                   is_structured_individual=True)
    
    # Fallback for old simple bills or non-structured individual bills
    patient = hms.get_patient(bill.patient_id)
    scheme = hms.get_patient_scheme(bill.patient_id) if hasattr(hms, 'get_patient_scheme') else {}
    try:
        dt = datetime.datetime.strptime(bill.created_date, "%Y-%m-%d")
        yr, mh, day = dt.year, dt.month, dt.day
    except Exception:
        yr, mh, day = "", "", ""
    items = []
    for raw in (bill.services or "").split(", "):
        desc = raw
        amt = 0.0
        if "($" in raw:
            try:
                desc = raw.split(" ($")[0]
                amt = float(raw.split(" ($")[1].rstrip(")").strip())
            except Exception:
                pass
        items.append({
            'code': 'SRV',
            'description': desc,
            'qty': 1,
            'yr': yr,
            'mh': mh,
            'day': day,
            'fee': amt if amt > 0 else float(bill.amount) if len(items) == 0 else 0.0,
            'award': 0.0
        })
    coverage_percent = scheme.get('coverage_percent') or scheme.get('coverage') or 0
    try:
        coverage_percent = float(coverage_percent)
    except Exception:
        coverage_percent = 0.0
    total_amount = float(bill.amount)
    covered_amount = total_amount * (coverage_percent / 100.0)
    shortfall_amount = max(total_amount - covered_amount, 0.0)
    received_amount = total_amount if (bill.status or '').lower() == 'paid' else 0.0
    balance_amount = max(total_amount - received_amount, 0.0)
    # populate award per row proportionally
    for r in items:
        if r['fee'] > 0:
            r['award'] = r['fee'] * (coverage_percent / 100.0)
    return render_template('billing/invoice.html',
                           bill=bill,
                           patient=patient,
                           scheme=scheme,
                           coverage_percent=int(coverage_percent),
                           items=items,
                           total_amount=total_amount,
                           covered_amount=covered_amount,
                           shortfall_amount=shortfall_amount,
                           received_amount=received_amount,
                           balance_amount=balance_amount,
                           is_bulk=False)

@app.route('/billing/receipt/<bill_id>')
def print_receipt(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        return "Bill not found", 404
    patient = hms.get_patient(bill.patient_id)
    return render_template('billing/receipt.html', bill=bill, patient=patient)

@app.route('/billing/invoice/export/<bill_id>')
def export_invoice_csv(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        return "Bill not found", 404
    
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    
    # Check if bulk or individual
    if hasattr(bill, 'items') and bill.items and getattr(bill, 'provider', None):
        # Bulk Invoice Export
        writer.writerow(['LIMBE MEDICAL CLINIC'])
        writer.writerow(['BULK MEDICAL BILL EXPORT'])
        writer.writerow(['PROVIDER', bill.provider])
        writer.writerow(['DATE', bill.created_date])
        writer.writerow([])
        writer.writerow(['INV NO', 'DATE', 'NAME OF PATIENT', 'SCHEME NO', 'SCHEME TYPE', 'CON', 'DRUG', 'LAB', 'TOTAL AMOUNT'])
        
        for item in bill.items:
            p = hms.get_patient(item['patient_id'])
            p_name = f"{p.last_name}, {p.first_name}" if p else "Unknown"
            s_type = getattr(p, 'scheme_type', '-') if p else "-"
            writer.writerow([
                bill.bill_id,
                item.get('date', bill.created_date),
                p_name,
                item.get('id_no', '-'),
                s_type,
                item.get('con', 0),
                item.get('drug', 0),
                item.get('lab', 0),
                item.get('amount', 0)
            ])
        writer.writerow([])
        writer.writerow(['', '', '', '', '', '', '', 'GRAND TOTAL', bill.amount])
        
    else:
        # Individual Invoice Export
        patient = hms.get_patient(bill.patient_id)
        p_name = f"{patient.last_name}, {patient.first_name}" if patient else "Unknown"
        
        writer.writerow(['LIMBE MEDICAL CLINIC'])
        writer.writerow(['STATEMENT OF ACCOUNT'])
        writer.writerow(['PATIENT', p_name])
        writer.writerow(['DATE', bill.created_date])
        writer.writerow([])
        writer.writerow(['DATE', 'INVOICE NO', 'DESCRIPTION', 'AMOUNT', 'BALANCE'])
        
        if hasattr(bill, 'items') and bill.items:
            for item in bill.items:
                writer.writerow([
                    bill.created_date,
                    bill.bill_id,
                    item.get('description', '-'),
                    item.get('amount', 0),
                    ''
                ])
        else:
            writer.writerow([
                bill.created_date,
                bill.bill_id,
                bill.services,
                bill.amount,
                bill.amount if bill.status != 'Paid' else 0
            ])
            
        writer.writerow([])
        writer.writerow(['', '', 'TOTAL', bill.amount, ''])

    resp = app.response_class(buf.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = f'attachment; filename=invoice_{bill.bill_id}.csv'
    return resp

@app.route('/billing/invoice/update/<bill_id>', methods=['POST'])
def update_invoice_scheme(bill_id):
    bill = hms.get_bill(bill_id)
    if not bill:
        return "Bill not found", 404
    scheme = hms.get_patient_scheme(bill.patient_id) if hasattr(hms, 'get_patient_scheme') else {}
    scheme = dict(scheme or {})
    scheme['provider'] = request.form.get('provider', '')
    scheme['type'] = request.form.get('type', '')
    scheme['membership_number'] = request.form.get('membership_number', '')
    scheme['policy_number'] = request.form.get('policy_number', '')
    scheme['form_number'] = request.form.get('form_number', '')
    cp = request.form.get('coverage_percent', '0')
    try:
        scheme['coverage_percent'] = float(cp)
    except Exception:
        scheme['coverage_percent'] = cp
    hms.update_patient_scheme(bill.patient_id, scheme)
    flash('Invoice details updated.', 'success')
    return redirect(url_for('print_invoice', bill_id=bill_id))

@app.route('/billing/reports')
def billing_reports():
    # Simple reports logic
    # Revenue by month
    revenue_by_month = {}
    for bill in hms.bills:
        if bill.status.lower() == 'paid':
            month = bill.created_date[:7] # YYYY-MM
            revenue_by_month[month] = revenue_by_month.get(month, 0) + bill.amount
            
    # Sort by month
    sorted_revenue = dict(sorted(revenue_by_month.items()))
    
    return render_template('billing/reports.html', revenue_data=sorted_revenue, active_page='billing')

@app.route('/prescriptions')
def prescriptions():
    search_term = request.args.get('search', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    search_parts = search_term.split()
    all_rx = sorted(hms.prescriptions, key=lambda x: (x.date or ''), reverse=True)
    
    def map_display(rx):
        patient = hms.get_patient(rx.patient_id)
        doctor = hms.get_doctor(rx.doctor_id)
        p_name = f"{patient.last_name}, {patient.first_name}" if patient else 'Unknown'
        p_reverse = f"{patient.first_name} {patient.last_name}" if patient else 'Unknown'
        d_name = f"Dr. {doctor.last_name}" if doctor else 'Unknown'
        d_full = f"{doctor.first_name} {doctor.last_name}" if doctor else 'Unknown'
        d_reverse = f"{doctor.last_name} {doctor.first_name}" if doctor else 'Unknown'
        
        return {
            'prescription_id': rx.prescription_id,
            'date': rx.date,
            'patient_name': p_name,
            'patient_reverse': p_reverse,
            'doctor_name': d_name,
            'doctor_full': d_full,
            'doctor_reverse': d_reverse,
            'medication': rx.medication,
            'status': rx.status
        }
    
    filtered_list = []
    if search_term:
        # We still need to map all for search unfortunately, unless we optimize search
        # But let's at least paginate the result
        full_list = [map_display(rx) for rx in all_rx]
        filtered_list = [d for d in full_list if all(part in (
            d['prescription_id'].lower() + " " +
            d['patient_name'].lower() + " " +
            d['patient_reverse'].lower() + " " +
            d['doctor_name'].lower() + " " +
            d['doctor_full'].lower() + " " +
            d['doctor_reverse'].lower() + " " +
            d['medication'].lower()
        ) for part in search_parts)]
    else:
        # If no search, we only need to map the slice! This is a big optimization.
        filtered_list = all_rx # Just a list of objects for now
    
    display_slice, total_pages = paginate_list(filtered_list, page)
    
    # If it wasn't searched, it's still raw objects, so map them now
    if not search_term:
        display_slice = [map_display(rx) for rx in display_slice]
        
    return render_template('prescriptions.html', 
                           prescriptions=display_slice, 
                           active_page='prescriptions', 
                           search_term=search_term,
                           page=page,
                           total_pages=total_pages,
                           total_count=len(filtered_list))

@app.route('/prescriptions/add', methods=['GET', 'POST'])
def add_prescription():
    patients = hms.patients
    doctors = hms.doctors
    if request.method == 'POST':
        try:
            medications = request.form.getlist('medication[]')
            medication_str = ", ".join(medications)
            new_rx = Prescription(
                prescription_id=hms.generate_id('RX'),
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                date=request.form['date'],
                medication=medication_str,
                duration=request.form['duration'],
                notes=request.form.get('notes',''),
                status=request.form.get('status','Active')
            )
            hms.add_prescription(new_rx)
            flash('Prescription added successfully!', 'success')
            notify('Prescription added', new_rx.prescription_id, 'doctor')
            return redirect(url_for('prescriptions'))
        except Exception as e:
            flash(f'Error adding prescription: {e}', 'error')
    return render_template('add_prescription.html', patients=patients, doctors=doctors, active_page='prescriptions')

@app.route('/prescriptions/edit/<prescription_id>', methods=['GET', 'POST'])
def edit_prescription(prescription_id):
    rx = hms.get_prescription(prescription_id)
    if not rx:
        flash('Prescription not found', 'error')
        return redirect(url_for('prescriptions'))
    patients = hms.patients
    doctors = hms.doctors
    if request.method == 'POST':
        try:
            medications = request.form.getlist('medication[]')
            medication_str = ", ".join(medications)
            updated = Prescription(
                prescription_id=rx.prescription_id,
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                date=request.form['date'],
                medication=medication_str,
                duration=request.form['duration'],
                notes=request.form.get('notes',''),
                status=request.form.get('status','Active')
            )
            hms.update_prescription(updated)
            flash('Prescription updated successfully!', 'success')
            notify('Prescription updated', prescription_id, 'doctor')
            return redirect(url_for('prescriptions'))
        except Exception as e:
            flash(f'Error updating prescription: {e}', 'error')
    return render_template('edit_prescription.html', rx=rx, patients=patients, doctors=doctors, active_page='prescriptions')

@app.route('/prescriptions/delete/<prescription_id>')
def delete_prescription(prescription_id):
    if hms.delete_prescription(prescription_id):
        flash('Prescription deleted successfully!', 'success')
        notify('Prescription deleted', prescription_id, 'doctor')
    else:
        flash('Error deleting prescription', 'error')
    return redirect(url_for('prescriptions'))

@app.route('/prescriptions/view/<prescription_id>')
def view_prescription(prescription_id):
    rx = hms.get_prescription(prescription_id)
    if not rx:
        flash('Prescription not found', 'error')
        return redirect(url_for('prescriptions'))
    patient = hms.get_patient(rx.patient_id)
    doctor = hms.get_doctor(rx.doctor_id)
    return render_template('view_prescription.html', rx=rx, patient=patient, doctor=doctor, active_page='prescriptions')

@app.route('/prescriptions/print/<prescription_id>')
def print_prescription(prescription_id):
    rx = hms.get_prescription(prescription_id)
    if not rx:
        return 'Prescription not found', 404
    patient = hms.get_patient(rx.patient_id)
    doctor = hms.get_doctor(rx.doctor_id)
    return render_template('prescriptions/print.html', rx=rx, patient=patient, doctor=doctor)

@app.route('/medical_records')
def medical_records():
    search_term = request.args.get('search', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Use a faster query that joins tables
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    
    where_clauses = ["1=1"]
    params = []
    
    if search_term:
        search_parts = search_term.split()
        for part in search_parts:
            where_clauses.append("(mr.record_id LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR d.last_name LIKE ? OR mr.diagnosis LIKE ?)")
            p_val = f"%{part}%"
            params.extend([p_val, p_val, p_val, p_val, p_val])
            
    where_sql = " AND ".join(where_clauses)
    
    # Get total count for pagination
    count_query = f"""
        SELECT COUNT(*) 
        FROM medical_records mr
        LEFT JOIN patients p ON mr.patient_id = p.patient_id
        LEFT JOIN doctors d ON mr.doctor_id = d.doctor_id
        WHERE {where_sql}
    """
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page
    
    # Get paginated results
    query = f"""
        SELECT 
            mr.record_id, mr.date, mr.diagnosis, mr.consult_reason,
            p.first_name as p_first, p.last_name as p_last,
            d.last_name as d_last
        FROM medical_records mr
        LEFT JOIN patients p ON mr.patient_id = p.patient_id
        LEFT JOIN doctors d ON mr.doctor_id = d.doctor_id
        WHERE {where_sql}
        ORDER BY mr.date DESC, mr.rowid DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [per_page, (page - 1) * per_page])
    rows = cursor.fetchall()
    conn.close()
    
    display_list = []
    for row in rows:
        display_list.append({
            'record_id': row['record_id'],
            'date': row['date'],
            'patient_name': f"{row['p_last']}, {row['p_first']}" if row['p_last'] else 'Unknown',
            'doctor_name': f"Dr. {row['d_last']}" if row['d_last'] else 'Unknown',
            'diagnosis': row['diagnosis'],
            'consult_reason': row['consult_reason']
        })
            
    return render_template('medical_records.html', 
                           records=display_list, 
                           active_page='medical_records', 
                           search_term=search_term,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count)

@app.route('/medical_records/add', methods=['GET', 'POST'])
def add_medical_record():
    patient_id = request.args.get('patient_id')
    if request.method == 'POST':
        try:
            details = {
                # Consultation & Exam
                'main_symptoms': request.form.get('main_symptoms'),
                'symptoms_duration': request.form.get('symptoms_duration'),
                'pain_level': request.form.get('pain_level'),
                'blood_pressure': request.form.get('blood_pressure'),
                'temperature': request.form.get('temperature'),
                'heart_rate': request.form.get('heart_rate'),
                'weight': request.form.get('weight'),
                'preliminary_diagnosis': request.form.get('preliminary_diagnosis'),
                
                # Patient Info & History
                'problem_start_date': request.form.get('problem_start_date'),
                'problem_description': request.form.get('problem_description'),
                'cause_accident': 'cause_accident' in request.form,
                'cause_work': 'cause_work' in request.form,
                'cause_gradual': 'cause_gradual' in request.form,
                'cause_other': 'cause_other' in request.form,
                'surgery_required': request.form.get('surgery_required'),
                'surgery_date': request.form.get('surgery_date'),
                'hospitalizations': request.form.get('hospitalizations'),
                'medications_history': request.form.get('medications_history'),
                'allergy_latex': 'allergy_latex' in request.form,
                'allergy_iodine': 'allergy_iodine' in request.form,
                'allergy_bromine': 'allergy_bromine' in request.form,
                'allergy_other': request.form.get('allergy_other'),
                'cultural_impact': request.form.get('cultural_impact'),
                'additional_comments': request.form.get('additional_comments'),
                'soap_subjective': request.form.get('soap_subjective'),
                
                # History Checkboxes
                'hist_breathing': 'hist_breathing' in request.form,
                'hist_pregnant': 'hist_pregnant' in request.form,
                'hist_heart': 'hist_heart' in request.form,
                'hist_skin': 'hist_skin' in request.form,
                'hist_pacemaker': 'hist_pacemaker' in request.form,
                'hist_cancer': 'hist_cancer' in request.form,
                'hist_diabetes': 'hist_diabetes' in request.form,
                'hist_stroke': 'hist_stroke' in request.form,
                'hist_bone': 'hist_bone' in request.form,
                'hist_kidney': 'hist_kidney' in request.form,
                'hist_liver': 'hist_liver' in request.form,
                'hist_implants': 'hist_implants' in request.form,
                'hist_anxiety': 'hist_anxiety' in request.form,
                'hist_sleep': 'hist_sleep' in request.form,
                'hist_depression': 'hist_depression' in request.form,
                'hist_bowel': 'hist_bowel' in request.form,
                'hist_alcohol': 'hist_alcohol' in request.form,
                'hist_drug': 'hist_drug' in request.form,
                'hist_smoking': 'hist_smoking' in request.form,
                'hist_headaches': 'hist_headaches' in request.form,

                # Personal Info
                'personal_full_name': request.form.get('personal_full_name'),
                'place_of_birth': request.form.get('place_of_birth'),
                'personal_address': request.form.get('personal_address'),
                'personal_phone': request.form.get('personal_phone'),
                'personal_email': request.form.get('personal_email'),
                'id_number': request.form.get('id_number'),
                'ssn': request.form.get('ssn'),
                'personal_status': request.form.get('personal_status'),
                'occupation': request.form.get('occupation'),
                'retiree': 'retiree' in request.form,
                'personal_note': request.form.get('personal_note'),

                # Emergency Contact
                'emergency_contact_name': request.form.get('emergency_contact_name'),
                'emergency_relationship': request.form.get('emergency_relationship'),
                'emergency_home_phone': request.form.get('emergency_home_phone'),
                'emergency_mobile_phone': request.form.get('emergency_mobile_phone'),

                # Office Use
                'membership_type': request.form.get('membership_type'),
                'membership_number': request.form.get('membership_number'),
                'payment_type': request.form.get('payment_type'),
                'staff_name': request.form.get('staff_name'),
                'staff_signature': request.form.get('staff_signature'),

                # Authorization Release
                'requestor_name': request.form.get('requestor_name'),
                'requestor_address': request.form.get('requestor_address'),
                'requestor_city': request.form.get('requestor_city'),
                'requestor_state': request.form.get('requestor_state'),
                'requestor_zip': request.form.get('requestor_zip'),
                'requestor_country': request.form.get('requestor_country'),
                'requestor_phone': request.form.get('requestor_phone'),
                'requestor_fax': request.form.get('requestor_fax'),
                'auth_access_records': 'auth_access_records' in request.form,
                'auth_replace_existing': 'auth_replace_existing' in request.form,
                'auth_remove_provider': 'auth_remove_provider' in request.form,
                'disclosure_purpose': request.form.get('disclosure_purpose'),
                'date_range_from': request.form.get('date_range_from'),
                'date_range_to': request.form.get('date_range_to'),
                
                # Release Info Checkboxes
                'release_discharge': 'release_discharge' in request.form,
                'release_operative': 'release_operative' in request.form,
                'release_consultation': 'release_consultation' in request.form,
                'release_tissue': 'release_tissue' in request.form,
                'release_nuclear': 'release_nuclear' in request.form,
                'release_radiology': 'release_radiology' in request.form,
                'release_lab': 'release_lab' in request.form,
                'release_history': 'release_history' in request.form,
                'release_outpatient': 'release_outpatient' in request.form,
                'release_pulmonary': 'release_pulmonary' in request.form,
                'release_nuclear_reports': 'release_nuclear_reports' in request.form,
                'release_heart': 'release_heart' in request.form,
                'release_radiology_cd': 'release_radiology_cd' in request.form,
                'notes': request.form.get('notes')
            }
            
            new_record = MedicalRecord(
                record_id=hms.generate_id("MR"),
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                date=request.form['date'],
                consult_reason=request.form['consult_reason'],
                diagnosis=request.form['diagnosis'],
                treatment=request.form['treatment'],
                prescriptions=request.form.get('prescriptions', ''),
                notes=request.form.get('notes', ''),
                details=details
            )
            if hms.add_medical_record(new_record):
                flash('Medical record added successfully!', 'success')
                notify('Medical record added', new_record.record_id, 'doctor')
                
                # Check if doctor wants to send patient to lab
                if request.form.get('action') == 'send_to_lab':
                    # Find patient in queue and update status
                    queue_item = next((q for q in hms.queue if q.patient_id == new_record.patient_id and q.status != 'Completed'), None)
                    if queue_item:
                        queue_item.status = "In Lab"
                        hms.save_data()
                        notify('Lab Request', f"{new_record.patient_id} sent to lab", 'lab_assistant')
                        flash('Patient sent to lab.', 'info')
                    else:
                        flash('Patient not found in active queue, but record saved.', 'warning')
                
                return redirect(url_for('medical_records'))
            else:
                flash('Failed to add medical record to database.', 'error')
        except Exception as e:
            flash(f'Error adding medical record: {e}', 'error')
            
    patients = hms.patients
    doctors = hms.doctors
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return render_template('add_medical_record.html', patients=patients, doctors=doctors, today=today, patient_id=patient_id, active_page='medical_records')

@app.route('/medical_records/edit/<record_id>', methods=['GET', 'POST'])
def edit_medical_record(record_id):
    record = next((r for r in hms.medical_records if r.record_id == record_id), None)
    if not record:
        flash('Medical record not found!', 'error')
        return redirect(url_for('medical_records'))
        
    if request.method == 'POST':
        try:
            record.patient_id = request.form['patient_id']
            record.doctor_id = request.form['doctor_id']
            record.date = request.form['date']
            record.consult_reason = request.form['consult_reason']
            record.diagnosis = request.form['diagnosis']
            record.treatment = request.form['treatment']
            record.prescriptions = request.form.get('prescriptions', '')
            record.notes = request.form.get('notes', '')
            
            # Update only fields present in form
            for key in [
                'main_symptoms', 'symptoms_duration', 'pain_level', 'blood_pressure',
                'temperature', 'heart_rate', 'weight', 'preliminary_diagnosis',
                'personal_info', 'emergency_contact', 'office_use', 'authorization_release'
            ]:
                if key in request.form:
                    record.details[key] = request.form[key]
            
            if 'notes' in request.form:
                record.details['notes'] = request.form['notes']
            
            hms.update_medical_record(record)
            flash('Medical record updated successfully!', 'success')
            notify('Medical record updated', record_id, 'doctor')
            
            # Check if doctor wants to send patient to lab
            if request.form.get('action') == 'send_to_lab':
                # Find patient in queue and update status
                queue_item = next((q for q in hms.queue if q.patient_id == record.patient_id and q.status != 'Completed'), None)
                if queue_item:
                    queue_item.status = "In Lab"
                    hms.save_data()
                    notify('Lab Request', f"{record.patient_id} sent to lab", 'lab_assistant')
                    flash('Patient sent to lab.', 'info')
                else:
                    flash('Patient not found in active queue, but record updated.', 'warning')
            
            return redirect(url_for('medical_records'))
        except Exception as e:
            flash(f'Error updating medical record: {e}', 'error')
            
    patients = hms.patients
    doctors = hms.doctors
    return render_template('edit_medical_record.html', record=record, patients=patients, doctors=doctors, active_page='medical_records')

@app.route('/medical_records/view/<record_id>')
def view_medical_record(record_id):
    record = next((r for r in hms.medical_records if r.record_id == record_id), None)
    if not record:
        flash('Medical record not found!', 'error')
        return redirect(url_for('medical_records'))
        
    patient = hms.get_patient(record.patient_id)
    doctor = hms.get_doctor(record.doctor_id)
    return render_template('view_medical_record.html', record=record, patient=patient, doctor=doctor, active_page='medical_records')

@app.route('/medical_records/print/<record_id>')
def print_medical_record(record_id):
    record = next((r for r in hms.medical_records if r.record_id == record_id), None)
    if not record:
        return "Medical record not found", 404
        
    patient = hms.get_patient(record.patient_id)
    doctor = hms.get_doctor(record.doctor_id)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('print_medical_record.html', record=record, patient=patient, doctor=doctor, now=now)

@app.route('/medical_records/export/<record_id>')
def export_medical_record_csv(record_id):
    record = next((r for r in hms.medical_records if r.record_id == record_id), None)
    if not record:
        return "Medical record not found", 404
    
    patient = hms.get_patient(record.patient_id)
    doctor = hms.get_doctor(record.doctor_id)
    
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    
    writer.writerow(['LIMBE MEDICAL CLINIC'])
    writer.writerow(['MEDICAL RECORD EXPORT'])
    writer.writerow([])
    writer.writerow(['RECORD ID', record.record_id])
    writer.writerow(['DATE', record.date])
    writer.writerow(['PATIENT', f"{patient.first_name} {patient.last_name}" if patient else 'Unknown'])
    writer.writerow(['DOCTOR', f"Dr. {doctor.last_name}" if doctor else 'Unknown'])
    writer.writerow([])
    writer.writerow(['SECTION', 'DETAILS'])
    writer.writerow(['Consultation Reason', record.consult_reason])
    writer.writerow(['Diagnosis', record.diagnosis])
    writer.writerow(['Treatment', record.treatment])
    writer.writerow(['Prescriptions', record.prescriptions])
    writer.writerow(['Notes', record.notes])
    writer.writerow([])
    writer.writerow(['DETAILED INFORMATION'])
    for key, val in record.details.items():
        writer.writerow([key.replace('_', ' ').title(), val])
        
    resp = app.response_class(buf.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = f'attachment; filename=medical_record_{record.record_id}.csv'
    return resp

@app.route('/medical_records/delete/<record_id>')
def delete_medical_record(record_id):
    if hms.delete_medical_record(record_id):
        flash('Medical record deleted successfully!', 'success')
        notify('Medical record deleted', record_id, 'doctor')
    else:
        flash('Error deleting medical record!', 'error')
    return redirect(url_for('medical_records'))

# ==================================
# 🧪 LAB RESULTS
# ==================================

@app.route('/lab_results')
def lab_results():
    search_term = request.args.get('search', '').lower().strip()
    page = request.args.get('page', 1, type=int)
    
    all_results = sorted(hms.lab_results, key=lambda x: (getattr(x, 'test_date', '') or ''), reverse=True)
    
    if search_term:
        search_parts = search_term.split()
        filtered_results = [r for r in all_results if all(part in (
            (getattr(r, 'result_id', '') or '').lower() + " " +
            (getattr(r, 'test_name', '') or '').lower() + " " +
            (getattr(r, 'patient_id', '') or '').lower()
        ) for part in search_parts)]
    else:
        filtered_results = all_results
        
    results_slice, total_pages = paginate_list(filtered_results, page)
    
    return render_template('lab_results.html', 
                           lab_results=results_slice, 
                           active_page='lab_results', 
                           hms=hms,
                           search_term=search_term,
                           page=page,
                           total_pages=total_pages,
                           total_count=len(filtered_results))

@app.route('/lab_results/add', methods=['GET', 'POST'])
def add_lab_result():
    patient_id = request.args.get('patient_id')
    if request.method == 'POST':
        try:
            new_result = LabResult(
                result_id=hms.generate_id("LR"),
                patient_id=request.form['patient_id'],
                doctor_id=request.form['doctor_id'],
                test_name=request.form['test_name'],
                test_date=request.form['test_date'],
                result_value=request.form.get('result_value'),
                units=request.form.get('units'),
                reference_range=request.form.get('reference_range'),
                status=request.form.get('status', 'Pending'),
                notes=request.form.get('notes')
            )
            hms.add_lab_result(new_result)
            flash('Lab result added successfully!', 'success')
            return redirect(url_for('lab_results'))
        except Exception as e:
            flash(f'Error adding lab result: {e}', 'error')
    patients = hms.patients
    doctors = hms.doctors
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return render_template('add_lab_result.html', patients=patients, doctors=doctors, patient_id=patient_id, today=today, active_page='lab_results')

@app.route('/lab_results/edit/<result_id>', methods=['GET', 'POST'])
def edit_lab_result(result_id):
    result = hms.get_lab_result(result_id)
    if not result:
        flash('Lab result not found!', 'error')
        return redirect(url_for('lab_results'))
    if request.method == 'POST':
        try:
            result.patient_id = request.form['patient_id']
            result.doctor_id = request.form['doctor_id']
            result.test_name = request.form['test_name']
            result.test_date = request.form['test_date']
            result.result_value = request.form.get('result_value')
            result.units = request.form.get('units')
            result.reference_range = request.form.get('reference_range')
            result.status = request.form.get('status')
            result.notes = request.form.get('notes')
            hms.update_lab_result(result)
            flash('Lab result updated successfully!', 'success')
            
            # If status is Completed, notify doctor and potentially update queue
            if result.status == 'Completed':
                notify('Lab Results Ready', f"Results for {result.patient_id} are ready", result.doctor_id)
                queue_item = next((q for q in hms.queue if q.patient_id == result.patient_id and q.status == 'In Lab'), None)
                if queue_item:
                    queue_item.status = "Ready for Review"
                    hms.save_data()
                    flash('Patient status updated to Ready for Review.', 'info')

            return redirect(url_for('lab_results'))
        except Exception as e:
            flash(f'Error updating lab result: {e}', 'error')
    patients = hms.patients
    doctors = hms.doctors
    return render_template('edit_lab_result.html', result=result, patients=patients, doctors=doctors, active_page='lab_results')

@app.route('/lab_results/view/<result_id>')
def view_lab_result(result_id):
    result = hms.get_lab_result(result_id)
    if not result:
        flash('Lab result not found!', 'error')
        return redirect(url_for('lab_results'))
    return render_template('view_lab_result.html', result=result, active_page='lab_results', hms=hms)

@app.route('/lab_results/print/<result_id>')
def print_lab_result(result_id):
    result = hms.get_lab_result(result_id)
    if not result:
        return "Lab result not found", 404
    return render_template('print_lab_result.html', result=result, hms=hms)



@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            hms.settings['theme'] = request.form.get('theme')
            hms.settings['notifications'] = 'notifications' in request.form
            hms.settings['auto_backup'] = 'auto_backup' in request.form
            hms.settings['language'] = request.form.get('language')
            hms.settings['date_format'] = request.form.get('date_format')
            hms.settings['server_url'] = request.form.get('server_url')
            hms.settings['supabase_url'] = request.form.get('supabase_url')
            hms.settings['supabase_project_id'] = request.form.get('supabase_project_id')
            hms.settings['supabase_api_key'] = request.form.get('supabase_api_key')
            hms.settings['supabase_service_role'] = request.form.get('supabase_service_role')
            
            hms.save_data()
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating settings: {e}', 'error')
            
    return render_template('settings.html', settings=hms.settings, active_page='settings')

@app.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin_users.html', users=hms.users, active_page='admin_users')

@app.route('/admin/update_role', methods=['POST'])
@admin_required
def update_user_role():
    target_username = request.form.get('username')
    new_role = request.form.get('role')
    actor_username = session.get('username')
    
    if hms.update_user_role(target_username, new_role, actor_username):
        flash(f'Role for {target_username} updated to {new_role}!', 'success')
    else:
        flash(f'Error updating role for {target_username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/activate/<username>')
@admin_required
def activate_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_status(username, True, actor_username):
        flash(f'User {username} activated!', 'success')
    else:
        flash(f'Error activating user {username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/deactivate/<username>')
@admin_required
def deactivate_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_status(username, False, actor_username):
        flash(f'User {username} deactivated!', 'success')
    else:
        flash(f'Error deactivating user {username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/verify/<username>')
@admin_required
def verify_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_verification(username, True, actor_username):
        flash(f'User {username} verified!', 'success')
    else:
        flash(f'Error verifying user {username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/unverify/<username>')
@admin_required
def unverify_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_verification(username, False, actor_username):
        flash(f'User {username} unverified!', 'success')
    else:
        flash(f'Error unverifying user {username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/enable_2fa/<username>')
@admin_required
def enable_user_2fa(username):
    actor_username = session.get('username')
    if hms.toggle_user_2fa(username, True, actor_username):
        flash(f'2FA enabled for {username}!', 'success')
    else:
        flash(f'Error enabling 2FA for {username}!', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/disable_2fa/<username>')
@admin_required
def disable_user_2fa(username):
    actor_username = session.get('username')
    if hms.toggle_user_2fa(username, False, actor_username):
        flash(f'2FA disabled for {username}!', 'success')
    else:
        flash(f'Error disabling 2FA for {username}!', 'error')
    return redirect(url_for('admin_users'))

# ==================================
# 📦 INVENTORY
# ==================================

@app.route('/inventory')
def inventory():
    search_term = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if search_term:
        all_results = hms.search_inventory(search_term)
        total_count = len(all_results)
        items_slice, total_pages = paginate_list(all_results, page, per_page)
    else:
        # Scalable query
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM inventory")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM inventory LIMIT ? OFFSET ?", (per_page, (page-1)*per_page))
        rows = cursor.fetchall()
        items_slice = [hms.db._row_to_obj(InventoryItem, row) for row in rows]
        conn.close()
        total_pages = math.ceil(total_count / per_page)
    
    return render_template('inventory.html', 
                           inventory=items_slice, 
                           active_page='inventory', 
                           search_term=search_term, 
                           providers=PROVIDERS,
                           page=page,
                           total_pages=total_pages,
                           total_count=total_count)

@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory_item():
    if request.method == 'POST':
        try:
            billing_codes = {}
            providers = request.form.getlist('provider[]')
            codes = request.form.getlist('code[]')
            for i in range(len(providers)):
                if providers[i] and codes[i]:
                    billing_codes[providers[i]] = codes[i]

            new_item = InventoryItem(
                item_id=hms.generate_id("ITEM"),
                name=request.form.get('name', 'Unknown Item'),
                category=request.form.get('category', ''),
                quantity=int(request.form.get('quantity') or 0),
                unit_price=float(request.form.get('unit_price') or 0.0),
                supplier=request.form.get('supplier', ''),
                expiry_date=request.form.get('expiry_date', ''),
                min_quantity=int(request.form.get('min_quantity') or 0),
                is_medicine='is_medicine' in request.form,
                billing_codes=billing_codes
            )
            print(f"DEBUG: Adding inventory item: {new_item}") # Debug print
            if hms.add_inventory_item(new_item):
                flash('Inventory item added successfully!', 'success')
            else:
                flash('Failed to add inventory item to system.', 'error')
            return redirect(url_for('inventory'))
        except Exception as e:
            print(f"DEBUG: Error adding item: {e}") # Debug print
            flash(f'Error adding item: {e}', 'error')
    return render_template('add_inventory_item.html', active_page='inventory', providers=PROVIDERS)

@app.route('/inventory/import', methods=['GET', 'POST'])
def inventory_import():
    if request.method == 'POST':
        provider = request.form.get('provider', '').strip()
        items_text = request.form.get('items_text', '').strip()
        mark_medicine = True  # default to medicines
        if not provider:
            flash('Please select a scheme provider.', 'error')
            return redirect(url_for('inventory_import'))
        if not items_text:
            flash('Please paste items to import.', 'error')
            return redirect(url_for('inventory_import'))
        # Improved pattern: Handles optional repeated code and various price formats
        # Matches: [CODE] [OPTIONAL_CODE] ITEM_NAME PRICE
        # Example: 33157 33157 LONART TABLETS 12S Tablets 500
        # Example: 32100 ACYCLOVR Cream 15mg 2990
        pattern = re.compile(r'^\s*(\d{4,6})(?:\s+\d{4,6})?\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s*$', re.IGNORECASE)
        added = 0
        for raw in items_text.splitlines():
            line = raw.strip()
            if not line:
                continue
            
            m = pattern.match(line)
            if m:
                code, item_name, price_str = m.group(1), m.group(2), m.group(3)
                # Clean price string (remove commas)
                price = float(price_str.replace(',', ''))
            else:
                # Try alternative: split by tabs or multiple spaces
                parts = re.split(r'\t+|\s{2,}', line)
                if len(parts) >= 3:
                    code = parts[0].strip()
                    item_name = parts[1].strip()
                    price_str = parts[2].strip()
                    try:
                        price = float(price_str.replace(',', '').replace('$', ''))
                    except:
                        continue
                else:
                    # Final fallback: last word is price, first word is code
                    parts = line.split()
                    if len(parts) >= 3:
                        code = parts[0]
                        price_str = parts[-1]
                        item_name = " ".join(parts[1:-1])
                        # If second part is also a code, skip it
                        if item_name.split()[0].isdigit():
                            item_name = " ".join(item_name.split()[1:])
                        try:
                            price = float(price_str.replace(',', '').replace('$', ''))
                        except:
                            continue
                    else:
                        continue
            
            try:
                new_item = InventoryItem(
                    item_id=hms.generate_id("ITEM"),
                    name=item_name,
                    category='Medicine',
                    quantity=0,
                    unit_price=price,
                    supplier='',
                    expiry_date='',
                    min_quantity=0,
                    is_medicine=mark_medicine,
                    billing_codes={provider: code}
                )
                hms.patients # Just to trigger some activity if needed? No.
                # Use a more direct append to avoid repeated save_data in loop if possible
                # but hms.add_inventory_item is the standard way.
                hms.inventory.append(new_item)
                added += 1
            except Exception as e:
                print(f"[WARN] Failed to import line '{line}': {e}")
        
        if added > 0:
            hms.save_data()
            flash(f'Imported {added} item(s) for {provider}.', 'success')
        else:
            flash('No items were imported. Please check the format.', 'error')
        return redirect(url_for('inventory'))
    return render_template('inventory_import.html', active_page='inventory', providers=PROVIDERS)

@app.route('/inventory/edit/<item_id>', methods=['GET', 'POST'])
def edit_inventory_item(item_id):
    item = hms.get_inventory_item(item_id)
    if not item:
        flash('Inventory item not found!', 'error')
        return redirect(url_for('inventory'))

    if request.method == 'POST':
        try:
            billing_codes = {}
            providers = request.form.getlist('provider[]')
            codes = request.form.getlist('code[]')
            for i in range(len(providers)):
                if providers[i] and codes[i]:
                    billing_codes[providers[i]] = codes[i]

            item.name = request.form.get('name', 'Unknown Item')
            item.category = request.form.get('category', '')
            item.quantity = int(request.form.get('quantity') or 0)
            item.unit_price = float(request.form.get('unit_price') or 0.0)
            item.supplier = request.form.get('supplier', '')
            item.expiry_date = request.form.get('expiry_date', '')
            item.min_quantity = int(request.form.get('min_quantity') or 0)
            item.is_medicine = 'is_medicine' in request.form
            item.billing_codes = billing_codes
            
            if hms.update_inventory_item(item):
                flash('Inventory item updated successfully!', 'success')
            else:
                flash('Failed to update inventory item in system.', 'error')
            return redirect(url_for('inventory'))
        except Exception as e:
            flash(f'Error updating item: {e}', 'error')

    return render_template('edit_inventory_item.html', item=item, active_page='inventory', providers=PROVIDERS)

@app.route('/inventory/delete/<item_id>')
def delete_inventory_item(item_id):
    if hms.delete_inventory_item(item_id):
        flash('Inventory item deleted successfully!', 'success')
    else:
        flash('Error deleting item!', 'error')
    return redirect(url_for('inventory'))

@app.route('/inventory/bulk_price_update', methods=['POST'])
def inventory_bulk_price_update():
    try:
        percentage = float(request.form.get('percentage') or 0.0)
        if percentage == 0:
            flash('Percentage must be non-zero.', 'warning')
            return redirect(url_for('inventory'))
        
        factor = 1 + (percentage / 100.0)
        updated_count = 0
        for item in hms.inventory:
            item.unit_price = round(item.unit_price * factor, 2)
            updated_count += 1
        
        if updated_count > 0:
            hms.save_data()
            flash(f'Successfully updated prices for {updated_count} items by {percentage}%.', 'success')
        else:
            flash('No items found to update.', 'info')
            
    except Exception as e:
        flash(f'Error updating prices: {e}', 'error')
    return redirect(url_for('inventory'))



if __name__ == '__main__':
    # We use use_reloader=False to avoid threading issues during interpreter shutdown
    app.run(debug=True, port=5000, threaded=True, use_reloader=False)
