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
import sqlite3
import csv
import io
from flask import Response

app = Flask(__name__)
app.secret_key = 'super_secret_key'
hms = HospitalManagementSystem()

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

hms.save_data()


# ── HELPER FUNCTIONS (must all be defined before any routes) ──────────────────

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role', '').strip().lower() not in ['admin', 'admin doctor', 'admin_doctor']:
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


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
    for username, password, role in users:
        if not any(u.username == username for u in hms.users):
            hms.register_user(username, password, role, actor_role='admin')


def paginate_list(items, page, per_page=20):
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages


def add_missing_column():
    conn = hms.db.get_connection()
    cursor = conn.cursor()

    migrations = [
        "ALTER TABLE prescriptions ADD COLUMN date_prescribed TEXT",
        "ALTER TABLE inventory ADD COLUMN reorder_level INTEGER DEFAULT 10",
    ]

    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"Migration applied: {sql}")
        except sqlite3.OperationalError as e:
            print(f"Skipped (already exists): {e}")

    conn.close()


@app.route('/inventory/import', methods=['GET', 'POST'])
@admin_required
def inventory_import():
    if request.method == 'POST':
        try:
            provider = request.form.get('provider')
            items_text = request.form.get('items_text', '')

            lines = items_text.strip().split('\n')
            imported_count = 0

            conn = hms.db.get_connection()
            cursor = conn.cursor()

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                code = parts[0]
                price = parts[-1]
                name = " ".join(parts[1:-1])

                try:
                    price_val = float(price)
                except ValueError:
                    continue

                # Check if item exists by name
                cursor.execute("SELECT item_id, billing_codes FROM inventory WHERE name = ?", (name,))
                row = cursor.fetchone()

                if row:
                    item_id = row['item_id']
                    billing_codes = {}
                    if row['billing_codes']:
                        try:
                            billing_codes = json.loads(row['billing_codes'])
                        except:
                            pass

                    billing_codes[provider] = code

                    cursor.execute("""
                        UPDATE inventory SET unit_price = ?, billing_codes = ? WHERE item_id = ?
                    """, (price_val, json.dumps(billing_codes), item_id))
                else:
                    # Insert new
                    billing_codes = {provider: code}
                    item_id = hms.generate_id('INV')
                    cursor.execute("""
                        INSERT INTO inventory (item_id, name, category, quantity, unit_price, supplier, billing_codes, is_medicine)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item_id, name, 'Medicines', 0, price_val, 'Imported', json.dumps(billing_codes), 1))

                imported_count += 1

            conn.commit()
            conn.close()

            flash(f'Successfully imported {imported_count} items.', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            flash(f'Error importing items: {e}', 'error')
            return redirect(url_for('inventory_import'))

    return render_template('inventory_import.html', providers=PROVIDERS, active_page='inventory')


@app.route('/inventory/bulk_price_update', methods=['POST'])
@admin_required
def inventory_bulk_price_update():
    try:
        percentage = float(request.form.get('percentage', 0))
        if percentage == 0:
            flash('Percentage cannot be zero!', 'error')
            return redirect(url_for('inventory'))

        multiplier = 1 + (percentage / 100)

        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET unit_price = unit_price * ?", (multiplier,))
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()

        flash(f'Successfully updated prices for {updated_count} items by {percentage}%.', 'success')
        notify('Inventory Price Update', f"All inventory prices updated by {percentage}%.", 'admin')
    except Exception as e:
        flash(f'Error updating prices: {e}', 'error')

    return redirect(url_for('inventory'))        


@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory_item():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            quantity = int(request.form.get('quantity', 0))
            unit = request.form.get('unit', '').strip()
            unit_price = float(request.form.get('unit_price', 0))
            reorder_level = int(request.form.get('reorder_level', 10))
            supplier = request.form.get('supplier', '').strip()
            notes = request.form.get('notes', '').strip()

            if not name:
                flash('Item name is required!', 'error')
                return redirect(url_for('add_inventory_item'))

            item_id = hms.generate_id('INV')
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (item_id, name, category, quantity, unit,
                                       unit_price, reorder_level, supplier, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, name, category, quantity, unit,
                  unit_price, reorder_level, supplier, notes))
            conn.commit()
            conn.close()
            flash('Inventory item added successfully!', 'success')
            notify('Inventory Updated', f"New item '{name}' added to inventory.", 'admin')
            return redirect(url_for('inventory'))
        except Exception as e:
            flash(f'Error adding inventory item: {e}', 'error')

    return render_template('add_inventory_item.html', active_page='inventory')


@app.route('/inventory/<item_id>/edit', methods=['GET', 'POST'])
def edit_inventory_item(item_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE item_id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        flash('Item not found!', 'error')
        return redirect(url_for('inventory'))

    item = hms.db._row_to_obj(InventoryItem, row)

    if request.method == 'POST':
        try:
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inventory SET
                    name = ?, category = ?, quantity = ?, unit = ?,
                    unit_price = ?, reorder_level = ?, supplier = ?, notes = ?
                WHERE item_id = ?
            """, (
                request.form.get('name', item.name),
                request.form.get('category', ''),
                int(request.form.get('quantity', 0)),
                request.form.get('unit', ''),
                float(request.form.get('unit_price', 0)),
                int(request.form.get('reorder_level', 10)),
                request.form.get('supplier', ''),
                request.form.get('notes', ''),
                item_id
            ))
            conn.commit()
            conn.close()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            flash(f'Error updating item: {e}', 'error')

    return render_template('edit_inventory_item.html', item=item, active_page='inventory')


@app.route('/inventory/<item_id>/delete')
@admin_required
def delete_inventory_item(item_id):
    try:
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()
        flash('Item deleted successfully!', 'success')
        notify('Inventory Updated', f"Item {item_id} deleted from inventory.", 'admin')
    except Exception as e:
        flash(f'Error deleting item: {e}', 'error')
    return redirect(url_for('inventory'))


@app.route('/inventory/<item_id>/restock', methods=['POST'])
def restock_inventory_item(item_id):
    try:
        quantity_to_add = int(request.form.get('quantity', 0))
        if quantity_to_add <= 0:
            flash('Quantity must be greater than zero!', 'error')
            return redirect(url_for('inventory'))
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE item_id = ?",
                       (quantity_to_add, item_id))
        conn.commit()
        conn.close()
        flash(f'Added {quantity_to_add} units to stock.', 'success')
        notify('Inventory Restocked', f"Item {item_id} restocked by {quantity_to_add} units.", 'admin')
    except Exception as e:
        flash(f'Error restocking item: {e}', 'error')
    return redirect(url_for('inventory'))


seed_users()
add_missing_column()


# ── FLASK HOOKS ───────────────────────────────────────────────────────────────

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


# ── AUTH ──────────────────────────────────────────────────────────────────────

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


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    try:
        days = 90
        stats = hms.get_dashboard_stats(days)
        total_patients = hms.get_patients_count()

        base = datetime.date.today()
        chart_labels = [(base - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

        reg_map = stats['registration_map']
        appt_map = stats['appointment_map']

        chart_patient_reg = [reg_map.get(d, 0) for d in chart_labels]
        chart_appointments = [appt_map.get(d, 0) for d in chart_labels]

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


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@app.route('/analytics')
def analytics():
    stats = hms.get_stats()

    revenue_data = {}
    today = datetime.date.today()
    for i in range(5, -1, -1):
        month_date = today - datetime.timedelta(days=i * 30)
        month_key = month_date.strftime("%B")
        revenue_data[month_key] = 0

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


# ── QUEUE ─────────────────────────────────────────────────────────────────────

@app.route('/queue')
def queue_dashboard():
    active_queue = hms.get_active_queue()
    queues_by_dept = {}
    for item in active_queue:
        dept = 'General'
        if item.doctor_id:
            doctor = hms.get_doctor(item.doctor_id)
            if doctor and doctor.specialty:
                dept = doctor.specialty
        if dept not in queues_by_dept:
            queues_by_dept[dept] = []
        queues_by_dept[dept].append(item)
    return render_template('queue/dashboard.html', queue=active_queue, queues_by_dept=queues_by_dept, active_page='queue')


@app.route('/queue/checkin', methods=['GET', 'POST'])
def queue_checkin():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()
            priority = request.form.get('priority', 'Routine')
            notes = request.form.get('notes', '')
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('queue_checkin'))
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            queue_item = QueueItem(
                queue_id=hms.generate_id('Q'),
                patient_id=patient_id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                doctor_id=doctor_id,
                priority=priority,
                status='Waiting',
                visit_reason=notes,
                date_added=now_str,
                arrival_time=now_str,
                check_in_time=now_str
            )
            hms.db.save('queue', queue_item, 'queue_id')
            hms.save_data()
            flash(f'{patient.first_name} {patient.last_name} checked in successfully!', 'success')
            notify('Queue Check-in', f"{patient.first_name} {patient.last_name} has checked in.", 'nurse')
            return redirect(url_for('queue_dashboard'))
        except Exception as e:
            flash(f'Error checking in patient: {e}', 'error')
    
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    
    # Get departments from doctors' specialties
    departments = list(set(doc.specialty for doc in doctors if doc.specialty))
    if 'General' not in departments:
        departments.append('General')
    
    urgencies = ['Routine', 'Urgent', 'Emergency']
    
    return render_template('queue/checkin.html', 
                           patients=patients, 
                           doctors=doctors, 
                           departments=departments,
                           urgencies=urgencies,
                           active_page='queue')


@app.route('/queue/clear_all')
@admin_required
def queue_clear_all():
    try:
        hms.queue = [q for q in hms.queue if q.status == 'Completed']
        hms.save_data()
        flash('Queue cleared successfully!', 'success')
        notify('Queue Cleared', 'All active queue items have been cleared.', 'all')
    except Exception as e:
        flash(f'Error clearing queue: {e}', 'error')
    return redirect(url_for('queue_dashboard'))


@app.route('/queue/call/<queue_id>')
def queue_call(queue_id):
    queue_item = next((q for q in hms.queue if q.queue_id == queue_id), None)
    if queue_item:
        queue_item.status = "Calling"
        hms.save_data()
        flash(f'Calling patient for queue item {queue_id}.', 'success')
        notify('Patient Called', f"Queue item {queue_id} is being called.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(url_for('queue_dashboard'))


@app.route('/queue/update/<queue_id>/<status>')
def update_queue_status(queue_id, status):
    queue_item = next((q for q in hms.queue if q.queue_id == queue_id), None)
    if queue_item:
        queue_item.status = status
        hms.save_data()
        flash(f'Queue status updated to {status}.', 'success')
        if status == "In Lab":
            notify('Lab Request', f"Queue item {queue_id} moved to lab.", 'lab_assistant')
        elif status == "With Doctor":
            notify('Consultation Started', f"Queue item {queue_id} is with doctor.", 'doctor')
    else:
        flash('Queue item not found.', 'error')
    return redirect(request.referrer or url_for('queue_dashboard'))


@app.route('/queue/complete/<queue_id>')
def queue_complete(queue_id):
    queue_item = next((q for q in hms.queue if q.queue_id == queue_id), None)
    if queue_item:
        queue_item.status = 'Completed'
        hms.save_data()
        flash('Queue item marked as completed.', 'success')
        notify('Queue Complete', f"Queue item {queue_id} has been completed.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(request.referrer or url_for('queue_dashboard'))


@app.route('/queue/requeue/<queue_id>')
def queue_requeue(queue_id):
    if hms.requeue_patient(queue_id):
        flash('Patient re-queued successfully.', 'success')
        notify('Queue Update', f"Queue item {queue_id} has been re-queued.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(url_for('queue_dashboard'))


@app.route('/queue/noshow/<queue_id>')
def queue_noshow(queue_id):
    if hms.update_queue_status(queue_id, 'No-show'):
        flash('Patient marked as No-show.', 'success')
        notify('Queue Update', f"Queue item {queue_id} marked as no-show.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(url_for('queue_dashboard'))


@app.route('/queue/transfer/<queue_id>', methods=['POST'])
def queue_transfer(queue_id):
    new_dept = request.form.get('department')
    new_doctor_id = request.form.get('doctor_id')
    if hms.transfer_patient(queue_id, new_dept, new_doctor_id):
        flash(f'Patient transferred to {new_dept}.', 'success')
        notify('Queue Transfer', f"Queue item {queue_id} transferred to {new_dept}.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(url_for('queue_dashboard'))


@app.route('/queue/remove/<queue_id>')
def remove_from_queue(queue_id):
    queue_item = next((q for q in hms.queue if q.queue_id == queue_id), None)
    if queue_item:
        hms.queue.remove(queue_item)
        hms.save_data()
        flash('Patient removed from queue.', 'success')
        notify('Queue Update', f"Queue item {queue_id} has been removed.", 'nurse')
    else:
        flash('Queue item not found.', 'error')
    return redirect(request.referrer or url_for('queue_dashboard'))


@app.route('/queue/add/<patient_id>', methods=['GET', 'POST'])
def add_to_queue(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))
    if request.method == 'POST':
        try:
            priority = request.form.get('priority', 'Routine')
            notes = request.form.get('notes', '')
            doctor_id = request.form.get('doctor_id', '')
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            queue_item = QueueItem(
                queue_id=hms.generate_id('Q'),
                patient_id=patient_id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                doctor_id=doctor_id,
                priority=priority,
                status='Waiting',
                visit_reason=notes,
                date_added=now_str,
                arrival_time=now_str,
                check_in_time=now_str
            )
            hms.db.save('queue', queue_item, 'queue_id')
            hms.save_data()
            flash('Patient added to queue successfully!', 'success')
            notify('Queue Update', f"{patient.first_name} {patient.last_name} added to queue.", 'nurse')
            return redirect(url_for('queue_dashboard'))
        except Exception as e:
            flash(f'Error adding to queue: {e}', 'error')
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('queue/add_to_queue.html', patient=patient, doctors=doctors, active_page='queue')


# ── PATIENTS ──────────────────────────────────────────────────────────────────

@app.route('/patients')
def patients():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').replace(',', ' ').strip()
    search_term = " ".join(search_term.split())
    per_page = 10

    conn = hms.db.get_connection()
    cursor = conn.cursor()

    if search_term:
        search_value = f"%{search_term}%"
        query_params = (search_value, search_value, search_value, search_value, search_value, search_value)
        cursor.execute("""
            SELECT * FROM patients
            WHERE is_deleted = 0 AND (
                patient_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                OR (first_name || ' ' || last_name) LIKE ?
                OR (last_name || ' ' || first_name) LIKE ?
                OR phone LIKE ?
            )
            ORDER BY rowid DESC LIMIT ? OFFSET ?
        """, (*query_params, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM patients
            WHERE is_deleted = 0 AND (
                patient_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                OR (first_name || ' ' || last_name) LIKE ?
                OR (last_name || ' ' || first_name) LIKE ?
                OR phone LIKE ?
            )
        """, query_params)
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM patients WHERE is_deleted = 0 ORDER BY rowid DESC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM patients WHERE is_deleted = 0")
        total_count = cursor.fetchone()[0]

    conn.close()
    patients_list = [hms.db._row_to_obj(Patient, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1

    return render_template('patients.html', patients=patients_list, page=page,
                           total_pages=total_pages, total_count=total_count, search_term=search_term)


@app.route('/patient/<patient_id>')
def patient_details(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))
    if hasattr(hms, 'sync_patient_attachments'):
        hms.sync_patient_attachments(patient_id)
    files = hms.patient_files.get(patient_id, [])
    appointments = hms.get_patient_appointments(patient_id)
    medical_records = hms.get_patient_medical_records(patient_id)
    bills = hms.get_patient_bills(patient_id)
    lab_results = [lr for lr in hms.lab_results if lr.patient_id == patient_id]
    queue_item = next((q for q in hms.queue if q.patient_id == patient_id and q.status != 'Completed'), None)
    return render_template('patient_details.html', patient=patient, files=files,
                           appointments=appointments, medical_records=medical_records,
                           bills=bills, lab_results=lab_results, queue_item=queue_item,
                           active_page='patients')


@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            if not patient_id:
                flash('Patient ID is required!', 'error')
                return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)
            if not first_name or not last_name:
                flash('First and Last name are required!', 'error')
                return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)
            if hms.get_patient(patient_id):
                flash(f'Patient ID "{patient_id}" already exists.', 'error')
                return render_template('add_patient.html', active_page='patients', providers=PROVIDERS)
            new_patient = Patient(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=request.form.get('dob', ''),
                gender=request.form.get('gender', ''),
                phone=request.form.get('phone', ''),
                email=request.form.get('email', ''),
                address=request.form.get('address', ''),
                emergency_contact=request.form.get('emergency_contact', ''),
                blood_group=request.form.get('blood_group', ''),
                medical_history=request.form.get('medical_history', ''),
                created_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                scheme_provider=request.form.get('scheme_provider', ''),
                scheme_type=request.form.get('scheme_type', '')
            )
            hms.add_patient(new_patient)
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patients'))
        except Exception as e:
            print("ADD PATIENT ERROR:", e)
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
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('patients'))
            new_id = (request.form.get('patient_id', '') or patient_id).strip()
            update_data = {
                'patient_id': new_id,
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'date_of_birth': request.form.get('dob', ''),
                'gender': request.form.get('gender', ''),
                'phone': request.form.get('phone', ''),
                'email': request.form.get('email', ''),
                'address': request.form.get('address', ''),
                'emergency_contact': request.form.get('emergency_contact', ''),
                'blood_group': request.form.get('blood_group', ''),
                'medical_history': request.form.get('medical_history', ''),
                'scheme_provider': request.form.get('scheme_provider', ''),
                'scheme_type': request.form.get('scheme_type', '')
            }
            update_data = {k: v for k, v in update_data.items() if v is not None}
            success = hms.update_patient(original_id=patient_id, **update_data)
            if success:
                flash('Patient updated successfully!', 'success')
                notify('Patient updated', new_id or patient_id, 'admin')
                return redirect(url_for('patients'))
            else:
                flash('Error updating patient: ID might already be in use.', 'error')
        except Exception as e:
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


@app.route('/patient/<patient_id>/send_to_lab')
def send_to_lab(patient_id):
    queue_item = next((q for q in hms.queue if q.patient_id == patient_id and q.status != 'Completed'), None)
    if queue_item:
        queue_item.status = "In Lab"
        hms.save_data()
        notify('Lab Request', f"{patient_id} sent to lab", 'lab_assistant')
        flash('Patient sent to lab.', 'success')
    else:
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
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    abs_path = os.path.join(base_dir, path)
    if not os.path.exists(abs_path):
        from supabase_data_manager import get_supabase_file_url
        sup_url = get_supabase_file_url(path)
        if sup_url:
            return redirect(sup_url)
        return "File not found", 404
    return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path), as_attachment=True)


@app.route('/serve_file')
def serve_file():
    path = request.args.get('path')
    if not path:
        return "File not found", 404
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    abs_path = os.path.join(base_dir, path)
    if not os.path.exists(abs_path):
        from supabase_data_manager import get_supabase_file_url
        sup_url = get_supabase_file_url(path)
        if sup_url:
            return redirect(sup_url)
        return "File not found", 404
    return send_from_directory(os.path.dirname(abs_path), os.path.basename(abs_path))


# ── DOCTORS ───────────────────────────────────────────────────────────────────

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
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM doctors")
        total_count = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM doctors LIMIT ? OFFSET ?", (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        doctors_slice = [hms.db._row_to_obj(Doctor, row) for row in rows]
        conn.close()
        total_pages = math.ceil(total_count / per_page)
    return render_template('doctors.html', doctors=doctors_slice, active_page='doctors',
                           search_term=search_term, page=page, total_pages=total_pages, total_count=total_count)


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


# ── DEPARTMENTS ───────────────────────────────────────────────────────────────

@app.route('/departments')
def departments():
    all_doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    departments = {}
    for doctor in all_doctors:
        specialty = doctor.specialty or 'General'
        if specialty not in departments:
            departments[specialty] = []
        departments[specialty].append(doctor)
    return render_template('departments.html', departments=departments, active_page='departments')


@app.route('/departments/add', methods=['GET', 'POST'])
@admin_required
def add_department():
    if request.method == 'POST':
        try:
            specialty = request.form.get('specialty', '').strip()
            if not specialty:
                flash('Department name is required!', 'error')
                return redirect(url_for('departments'))
            flash(f'Department "{specialty}" added successfully!', 'success')
            notify('Department Added', f"New department added: {specialty}", 'admin')
        except Exception as e:
            flash(f'Error adding department: {e}', 'error')
    return redirect(url_for('departments'))


# ── APPOINTMENTS ──────────────────────────────────────────────────────────────

@app.route('/appointments/schedule', methods=['GET', 'POST'])
def schedule_appointment():
    patient_id = request.args.get('patient_id', '')
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()
            date = request.form.get('date', '').strip()
            time = request.form.get('time', '').strip()
            reason = request.form.get('reason', '').strip()
            notes = request.form.get('notes', '').strip()
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('schedule_appointment'))
            new_appointment = Appointment(
                appointment_id=hms.generate_id('A'),
                patient_id=patient_id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                doctor_id=doctor_id,
                date=date,
                time=time,
                reason=reason,
                notes=notes,
                status='Scheduled'
            )
            hms.add_appointment(new_appointment)
            flash('Appointment scheduled successfully!', 'success')
            notify('New Appointment',
                   f"Appointment scheduled for {patient.first_name} {patient.last_name} on {date} at {time}.",
                   doctor_id)
            return redirect(url_for('view_schedule'))
        except Exception as e:
            flash(f'Error scheduling appointment: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('schedule_appointment.html', patients=patients, doctors=doctors,
                           patient_id=patient_id, active_page='appointments')


# ── BILLING ───────────────────────────────────────────────────────────────────

@app.route('/billing')
def billing_dashboard():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    if search_term:
        search_value = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM bills WHERE bill_id LIKE ? OR patient_id LIKE ? OR status LIKE ?
            ORDER BY created_date DESC LIMIT ? OFFSET ?
        """, (search_value, search_value, search_value, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM bills WHERE bill_id LIKE ? OR patient_id LIKE ? OR status LIKE ?
        """, (search_value, search_value, search_value))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM bills ORDER BY created_date DESC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM bills")
        total_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM bills WHERE status = 'Paid'")
    total_paid = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM bills WHERE status = 'Unpaid'")
    total_unpaid = cursor.fetchone()[0] or 0
    conn.close()
    bills = [hms.db._row_to_obj(Bill, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1
    return render_template('billing_dashboard.html', bills=bills, page=page, total_pages=total_pages,
                           total_count=total_count, total_paid=total_paid, total_unpaid=total_unpaid,
                           search_term=search_term, active_page='billing')


@app.route('/billing/<bill_id>')
def view_bill(bill_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Bill not found!', 'error')
        return redirect(url_for('billing_dashboard'))
    bill = hms.db._row_to_obj(Bill, row)
    patient = hms.get_patient(bill.patient_id)
    doctor = hms.get_doctor(bill.doctor_id) if hasattr(bill, 'doctor_id') and bill.doctor_id else None
    return render_template('billing/view_bill.html', bill=bill, patient=patient, doctor=doctor, active_page='billing')


@app.route('/billing/<bill_id>/edit', methods=['GET', 'POST'])
def edit_bill(bill_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Bill not found!', 'error')
        return redirect(url_for('billing_dashboard'))
    bill = hms.db._row_to_obj(Bill, row)
    if request.method == 'POST':
        try:
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bills SET amount = ?, status = ?, provider = ?, notes = ? WHERE bill_id = ?
            """, (request.form.get('amount', bill.amount), request.form.get('status', bill.status),
                  request.form.get('provider', ''), request.form.get('notes', ''), bill_id))
            conn.commit()
            conn.close()
            flash('Bill updated successfully!', 'success')
            notify('Bill Updated', f"Bill {bill_id} has been updated.", 'cashier')
            return redirect(url_for('view_bill', bill_id=bill_id))
        except Exception as e:
            flash(f'Error updating bill: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    return render_template('billing/edit_bill.html', bill=bill, patients=patients, providers=PROVIDERS, active_page='billing')


@app.route('/billing/add', methods=['GET', 'POST'])
def add_bill():
    patient_id = request.args.get('patient_id', '')
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            amount = float(request.form.get('amount', 0))
            status = request.form.get('status', 'Unpaid').strip()
            provider = request.form.get('provider', '').strip()
            notes = request.form.get('notes', '').strip()
            description = request.form.get('description', '').strip()
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('add_bill'))
            new_bill = Bill(
                bill_id=hms.generate_id('B'),
                patient_id=patient_id,
                amount=amount,
                status=status,
                provider=provider,
                notes=notes,
                description=description,
                created_date=datetime.datetime.now().strftime("%Y-%m-%d")
            )
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (bill_id, patient_id, amount, status, provider, notes, description, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_bill.bill_id, new_bill.patient_id, new_bill.amount, new_bill.status,
                  new_bill.provider, new_bill.notes, new_bill.description, new_bill.created_date))
            conn.commit()
            conn.close()
            flash('Bill created successfully!', 'success')
            notify('New Bill', f"Bill created for {patient.first_name} {patient.last_name}.", 'cashier')
            return redirect(url_for('billing_dashboard'))
        except Exception as e:
            flash(f'Error creating bill: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    return render_template('add_bill.html', patients=patients, providers=PROVIDERS,
                           patient_id=patient_id, active_page='billing')


@app.route('/billing/create', methods=['GET', 'POST'])
def create_bill():
    return redirect(url_for('add_bill'))


@app.route('/billing/<bill_id>/delete')
@admin_required
def delete_bill(bill_id):
    try:
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bills WHERE bill_id = ?", (bill_id,))
        conn.commit()
        conn.close()
        flash('Bill deleted successfully!', 'success')
        notify('Bill Deleted', f"Bill {bill_id} has been deleted.", 'admin')
    except Exception as e:
        flash(f'Error deleting bill: {e}', 'error')
    return redirect(url_for('billing_dashboard'))


@app.route('/billing/process_payment', methods=['POST'])
def process_payment():
    try:
        bill_id = request.form.get('bill_id', '').strip()
        amount_paid = float(request.form.get('amount_paid', 0))
        payment_method = request.form.get('payment_method', 'Cash').strip()
        notes = request.form.get('notes', '').strip()
        if not bill_id:
            flash('Bill ID is required!', 'error')
            return redirect(url_for('billing_dashboard'))
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
        row = cursor.fetchone()
        if not row:
            flash('Bill not found!', 'error')
            conn.close()
            return redirect(url_for('billing_dashboard'))
        bill = hms.db._row_to_obj(Bill, row)
        total_amount = float(bill.amount)
        if amount_paid >= total_amount:
            new_status = 'Paid'
        elif amount_paid > 0:
            new_status = 'Partial'
        else:
            new_status = bill.status
        payment_note = f"Payment of MWK {amount_paid:,.2f} via {payment_method} on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}."
        if notes:
            payment_note += f" Note: {notes}"
        updated_notes = f"{bill.notes or ''}\n{payment_note}".strip()
        cursor.execute("UPDATE bills SET status = ?, provider = ?, notes = ? WHERE bill_id = ?",
                       (new_status, payment_method, updated_notes, bill_id))
        conn.commit()
        conn.close()
        flash(f'Payment of MWK {amount_paid:,.2f} processed successfully! Status: {new_status}', 'success')
        notify('Payment Processed',
               f"Payment of MWK {amount_paid:,.2f} processed for bill {bill_id} via {payment_method}.", 'cashier')
        return redirect(url_for('view_bill', bill_id=bill_id))
    except ValueError:
        flash('Invalid amount entered!', 'error')
        return redirect(url_for('billing_dashboard'))
    except Exception as e:
        flash(f'Error processing payment: {e}', 'error')
        return redirect(url_for('billing_dashboard'))


@app.route('/billing/<bill_id>/invoice')
def print_invoice(bill_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Bill not found!', 'error')
        return redirect(url_for('billing_dashboard'))
    bill = hms.db._row_to_obj(Bill, row)
    patient = hms.get_patient(bill.patient_id)
    return render_template('billing/print_invoice.html', bill=bill, patient=patient,
                           hospital_name=hms.settings.get('hospital_name', 'Hospital'),
                           hospital_address=hms.settings.get('hospital_address', ''),
                           hospital_phone=hms.settings.get('hospital_phone', ''),
                           hospital_email=hms.settings.get('hospital_email', ''),
                           active_page='billing')


@app.route('/billing/<bill_id>/export_csv')
def export_invoice_csv(bill_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Bill not found!', 'error')
        return redirect(url_for('billing_dashboard'))
    bill = hms.db._row_to_obj(Bill, row)
    patient = hms.get_patient(bill.patient_id)
    hospital_name = hms.settings.get('hospital_name', 'Hospital')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['INVOICE'])
    writer.writerow(['Hospital', hospital_name])
    writer.writerow(['Date Exported', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    writer.writerow(['Bill ID', 'Patient ID', 'Patient Name', 'Amount (MWK)', 'Status', 'Provider', 'Description', 'Notes', 'Date'])
    writer.writerow([
        bill.bill_id, bill.patient_id,
        f"{patient.first_name} {patient.last_name}" if patient else bill.patient_id,
        bill.amount, bill.status, bill.provider or '',
        bill.description if hasattr(bill, 'description') else '',
        bill.notes or '', bill.created_date
    ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=invoice_{bill_id}.csv'})


# ── PRESCRIPTIONS ─────────────────────────────────────────────────────────────

@app.route('/prescriptions')
def prescriptions():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    if search_term:
        search_value = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM prescriptions
            WHERE prescription_id LIKE ? OR patient_id LIKE ? OR doctor_id LIKE ? OR medication LIKE ?
            ORDER BY date_prescribed DESC LIMIT ? OFFSET ?
        """, (search_value, search_value, search_value, search_value, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM prescriptions
            WHERE prescription_id LIKE ? OR patient_id LIKE ? OR doctor_id LIKE ? OR medication LIKE ?
        """, (search_value, search_value, search_value, search_value))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM prescriptions ORDER BY date_prescribed DESC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM prescriptions")
        total_count = cursor.fetchone()[0]
    conn.close()
    prescriptions_list = [hms.db._row_to_obj(Prescription, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1
    return render_template('prescriptions.html', prescriptions=prescriptions_list, page=page,
                           total_pages=total_pages, total_count=total_count,
                           search_term=search_term, active_page='prescriptions')


@app.route('/prescriptions/add', methods=['GET', 'POST'])
def add_prescription():
    patient_id = request.args.get('patient_id', '')
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()
            medication = request.form.get('medication', '').strip()
            dosage = request.form.get('dosage', '').strip()
            frequency = request.form.get('frequency', '').strip()
            duration = request.form.get('duration', '').strip()
            notes = request.form.get('notes', '').strip()
            date_prescribed = request.form.get('date_prescribed', datetime.datetime.now().strftime("%Y-%m-%d")).strip()
            if not patient_id or not medication:
                flash('Patient and medication are required!', 'error')
                return redirect(url_for('add_prescription'))
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('add_prescription'))
            prescription_id = hms.generate_id('RX')
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prescriptions
                    (prescription_id, patient_id, doctor_id, medication, dosage,
                     frequency, duration, notes, date_prescribed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (prescription_id, patient_id, doctor_id, medication, dosage,
                  frequency, duration, notes, date_prescribed))
            conn.commit()
            conn.close()
            flash('Prescription added successfully!', 'success')
            notify('New Prescription',
                   f"Prescription for {medication} added for {patient.first_name} {patient.last_name}.",
                   doctor_id or 'doctor')
            return redirect(url_for('prescriptions'))
        except Exception as e:
            flash(f'Error adding prescription: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('add_prescription.html', patients=patients, doctors=doctors,
                           patient_id=patient_id, active_page='prescriptions')


@app.route('/prescriptions/<prescription_id>')
def view_prescription(prescription_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Prescription not found!', 'error')
        return redirect(url_for('prescriptions'))
    prescription = hms.db._row_to_obj(Prescription, row)
    patient = hms.get_patient(prescription.patient_id)
    doctor = hms.get_doctor(prescription.doctor_id) if prescription.doctor_id else None
    return render_template('view_prescription.html', prescription=prescription,
                           patient=patient, doctor=doctor, active_page='prescriptions')


@app.route('/prescriptions/<prescription_id>/edit', methods=['GET', 'POST'])
def edit_prescription(prescription_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Prescription not found!', 'error')
        return redirect(url_for('prescriptions'))
    prescription = hms.db._row_to_obj(Prescription, row)
    if request.method == 'POST':
        try:
            conn = hms.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE prescriptions SET
                    patient_id = ?, doctor_id = ?, medication = ?, dosage = ?,
                    frequency = ?, duration = ?, notes = ?, date_prescribed = ?
                WHERE prescription_id = ?
            """, (
                request.form.get('patient_id', prescription.patient_id),
                request.form.get('doctor_id', prescription.doctor_id),
                request.form.get('medication', prescription.medication),
                request.form.get('dosage', ''),
                request.form.get('frequency', ''),
                request.form.get('duration', ''),
                request.form.get('notes', ''),
                request.form.get('date_prescribed', ''),
                prescription_id
            ))
            conn.commit()
            conn.close()
            flash('Prescription updated successfully!', 'success')
            return redirect(url_for('view_prescription', prescription_id=prescription_id))
        except Exception as e:
            flash(f'Error updating prescription: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('edit_prescription.html', prescription=prescription,
                           patients=patients, doctors=doctors, active_page='prescriptions')


@app.route('/prescriptions/<prescription_id>/delete')
@admin_required
def delete_prescription(prescription_id):
    try:
        conn = hms.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
        conn.commit()
        conn.close()
        flash('Prescription deleted successfully!', 'success')
        notify('Prescription Deleted', f"Prescription {prescription_id} has been deleted.", 'admin')
    except Exception as e:
        flash(f'Error deleting prescription: {e}', 'error')
    return redirect(url_for('prescriptions'))


@app.route('/prescriptions/<prescription_id>/print')
def print_prescription(prescription_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE prescription_id = ?", (prescription_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        flash('Prescription not found!', 'error')
        return redirect(url_for('prescriptions'))
    prescription = hms.db._row_to_obj(Prescription, row)
    patient = hms.get_patient(prescription.patient_id)
    doctor = hms.get_doctor(prescription.doctor_id) if prescription.doctor_id else None
    return render_template('prescriptions/print.html',
                           prescription=prescription,
                           patient=patient,
                           doctor=doctor,
                           hospital_name=hms.settings.get('hospital_name', 'Hospital'),
                           hospital_address=hms.settings.get('hospital_address', ''),
                           hospital_phone=hms.settings.get('hospital_phone', ''),
                           hospital_email=hms.settings.get('hospital_email', ''))


                   

# ── MEDICAL RECORDS ───────────────────────────────────────────────────────────

@app.route('/medical_records')
def medical_records():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    
    if search_term:
        search_value = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM medical_records 
            WHERE record_id LIKE ? OR patient_id LIKE ? OR diagnosis LIKE ? 
            ORDER BY date DESC LIMIT ? OFFSET ?
        """, (search_value, search_value, search_value, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM medical_records 
            WHERE record_id LIKE ? OR patient_id LIKE ? OR diagnosis LIKE ?
        """, (search_value, search_value, search_value))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM medical_records ORDER BY date DESC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM medical_records")
        total_count = cursor.fetchone()[0]
    
    conn.close()
    records_list = [hms.db._row_to_obj(MedicalRecord, row) for row in rows]
    
    # Enrich records with patient and doctor names
    for record in records_list:
        p = hms.get_patient(record.patient_id)
        d = hms.get_doctor(record.doctor_id)
        record.patient_name = f"{p.first_name} {p.last_name}" if p else record.patient_id
        record.doctor_name = f"Dr. {d.last_name}" if d else record.doctor_id
        
    total_pages = math.ceil(total_count / per_page) if total_count else 1
    
    return render_template('medical_records.html', records=records_list, page=page,
                           total_pages=total_pages, total_count=total_count,
                           search_term=search_term, active_page='patients')


@app.route('/medical_records/add', methods=['GET', 'POST'])
def add_medical_record():
    patient_id = request.args.get('patient_id', '')
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('add_medical_record'))
            new_record = MedicalRecord(
                record_id=hms.generate_id('MR'),
                patient_id=patient_id,
                doctor_id=doctor_id,
                date=request.form.get('date', datetime.datetime.now().strftime("%Y-%m-%d")),
                consult_reason=request.form.get('consult_reason', 'General Consultation'),
                diagnosis=request.form.get('diagnosis', ''),
                treatment=request.form.get('treatment', ''),
                prescriptions=request.form.get('prescriptions', ''),
                notes=request.form.get('notes', '')
            )
            if hms.add_medical_record(new_record):
                flash('Medical record added successfully!', 'success')
                notify('New Medical Record',
                       f"Medical record created for {patient.first_name} {patient.last_name}.", doctor_id)
                return redirect(url_for('patient_details', patient_id=patient_id))
            else:
                flash('Failed to create medical record.', 'error')
        except Exception as e:
            flash(f'Error creating medical record: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('add_medical_record.html', patients=patients, doctors=doctors,
                           patient_id=patient_id, active_page='patients')


@app.route('/create_medical_record', methods=['GET', 'POST'])
def create_medical_record():
    patient_id = request.args.get('patient_id')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    if request.method == 'POST':
        try:
            # Extract basic fields
            p_id = request.form.get('patient_id')
            d_id = request.form.get('doctor_id')
            date = request.form.get('date') or request.form.get('visit_date')
            reason = request.form.get('consult_reason')
            diagnosis = request.form.get('diagnosis')
            treatment = request.form.get('treatment')
            prescriptions = request.form.get('prescriptions') or request.form.get('prescription')
            notes = request.form.get('notes', '')

            # Extract detail fields
            details = {
                'pain_level': request.form.get('pain_level'),
                'blood_pressure': request.form.get('blood_pressure'),
                'heart_rate': request.form.get('heart_rate'),
                'temperature': request.form.get('temperature'),
                'weight': request.form.get('weight'),
                'medical_examination': request.form.get('medical_examination'),
                'problem_start_date': request.form.get('problem_start_date'),
                'problem_description': request.form.get('problem_description'),
                'cause': request.form.getlist('cause'),
                'required_surgery': request.form.get('required_surgery'),
                'surgery_date': request.form.get('surgery_date'),
                'past_medical_history': request.form.getlist('history_item'),
                'surgeries_hospitalizations': request.form.get('surgeries_hospitalizations'),
                'medications_detail': request.form.get('medications_detail'),
                'allergies': request.form.getlist('allergy'),
                'other_allergy': request.form.get('other_allergy'),
                'religious_impact': request.form.get('religious_impact'),
                'additional_comments': request.form.get('additional_comments'),
                'soap_subjective': request.form.get('soap_subjective'),
                'personal_full_name': request.form.get('personal_full_name'),
                'place_of_birth': request.form.get('place_of_birth'),
                'personal_address': request.form.get('personal_address'),
                'personal_phone': request.form.get('personal_phone'),
                'personal_email': request.form.get('personal_email'),
                'id_number': request.form.get('id_number'),
                'ssn': request.form.get('ssn'),
                'marital_status': request.form.get('marital_status'),
                'occupation': request.form.get('occupation'),
                'is_retiree': request.form.get('is_retiree'),
                'personal_note': request.form.get('personal_note'),
                'emergency_contact_name': request.form.get('emergency_contact_name'),
                'emergency_relationship': request.form.get('emergency_relationship'),
                'emergency_home_phone': request.form.get('emergency_home_phone'),
                'emergency_mobile_phone': request.form.get('emergency_mobile_phone'),
                'membership_type': request.form.get('membership_type'),
                'membership_number': request.form.get('membership_number'),
                'payment_type': request.form.get('payment_type'),
                'staff_name': request.form.get('staff_name'),
                'staff_signature': request.form.get('staff_signature'),
                'office_notes': request.form.get('office_notes'),
                'auth_requestor_name': request.form.get('auth_requestor_name'),
                'auth_requestor_address': request.form.get('auth_requestor_address'),
                'auth_city': request.form.get('auth_city'),
                'auth_state': request.form.get('auth_state'),
                'auth_zip': request.form.get('auth_zip'),
                'auth_country': request.form.get('auth_country'),
                'auth_telephone': request.form.get('auth_telephone'),
                'auth_fax': request.form.get('auth_fax'),
                'auth_actions': request.form.getlist('auth_action'),
                'auth_purpose': request.form.get('auth_purpose'),
                'auth_date_from': request.form.get('auth_date_from'),
                'auth_date_to': request.form.get('auth_date_to'),
                'auth_info_released': request.form.getlist('auth_info'),
            }

            new_record = MedicalRecord(
                record_id=hms.generate_id("MR"),
                patient_id=p_id,
                doctor_id=d_id,
                date=date,
                consult_reason=reason,
                diagnosis=diagnosis,
                treatment=treatment,
                prescriptions=prescriptions,
                notes=notes,
                details=details
            )

            if hms.add_medical_record(new_record):
                action = request.form.get('action')
                if action == 'save_lab':
                    flash('Medical record saved and sent to Lab!', 'success')
                else:
                    flash('Medical record created successfully!', 'success')
                return redirect(url_for('patient_details', patient_id=new_record.patient_id))
            else:
                flash('Failed to create medical record in database.', 'error')
        except Exception as e:
            flash(f'Error creating medical record: {e}', 'error')
    return render_template('create_medical_record.html', patients=patients, doctors=doctors,
                           patient_id=patient_id, active_page='patients', today=datetime.date.today().strftime('%Y-%m-%d'))


@app.route('/edit_medical_record/<record_id>', methods=['GET', 'POST'])
def edit_medical_record(record_id):
    record = hms.get_medical_record(record_id)
    if not record:
        flash('Medical record not found!', 'error')
        return redirect(url_for('patients'))

    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()

    if request.method == 'POST':
        try:
            # Extract basic fields
            p_id = request.form.get('patient_id')
            d_id = request.form.get('doctor_id')
            date = request.form.get('date') or request.form.get('visit_date')
            reason = request.form.get('consult_reason')
            diagnosis = request.form.get('diagnosis')
            treatment = request.form.get('treatment')
            prescriptions = request.form.get('prescriptions') or request.form.get('prescription')
            notes = request.form.get('notes', '')

            # Extract detail fields
            details = {
                'pain_level': request.form.get('pain_level'),
                'blood_pressure': request.form.get('blood_pressure'),
                'heart_rate': request.form.get('heart_rate'),
                'temperature': request.form.get('temperature'),
                'weight': request.form.get('weight'),
                'medical_examination': request.form.get('medical_examination'),
                'problem_start_date': request.form.get('problem_start_date'),
                'problem_description': request.form.get('problem_description'),
                'cause': request.form.getlist('cause'),
                'required_surgery': request.form.get('required_surgery'),
                'surgery_date': request.form.get('surgery_date'),
                'past_medical_history': request.form.getlist('history_item'),
                'surgeries_hospitalizations': request.form.get('surgeries_hospitalizations'),
                'medications_detail': request.form.get('medications_detail'),
                'allergies': request.form.getlist('allergy'),
                'other_allergy': request.form.get('other_allergy'),
                'religious_impact': request.form.get('religious_impact'),
                'additional_comments': request.form.get('additional_comments'),
                'soap_subjective': request.form.get('soap_subjective'),
                'personal_full_name': request.form.get('personal_full_name'),
                'place_of_birth': request.form.get('place_of_birth'),
                'personal_address': request.form.get('personal_address'),
                'personal_phone': request.form.get('personal_phone'),
                'personal_email': request.form.get('personal_email'),
                'id_number': request.form.get('id_number'),
                'ssn': request.form.get('ssn'),
                'marital_status': request.form.get('marital_status'),
                'occupation': request.form.get('occupation'),
                'is_retiree': request.form.get('is_retiree'),
                'personal_note': request.form.get('personal_note'),
                'emergency_contact_name': request.form.get('emergency_contact_name'),
                'emergency_relationship': request.form.get('emergency_relationship'),
                'emergency_home_phone': request.form.get('emergency_home_phone'),
                'emergency_mobile_phone': request.form.get('emergency_mobile_phone'),
                'membership_type': request.form.get('membership_type'),
                'membership_number': request.form.get('membership_number'),
                'payment_type': request.form.get('payment_type'),
                'staff_name': request.form.get('staff_name'),
                'staff_signature': request.form.get('staff_signature'),
                'office_notes': request.form.get('office_notes'),
                'auth_requestor_name': request.form.get('auth_requestor_name'),
                'auth_requestor_address': request.form.get('auth_requestor_address'),
                'auth_city': request.form.get('auth_city'),
                'auth_state': request.form.get('auth_state'),
                'auth_zip': request.form.get('auth_zip'),
                'auth_country': request.form.get('auth_country'),
                'auth_telephone': request.form.get('auth_telephone'),
                'auth_fax': request.form.get('auth_fax'),
                'auth_actions': request.form.getlist('auth_action'),
                'auth_purpose': request.form.get('auth_purpose'),
                'auth_date_from': request.form.get('auth_date_from'),
                'auth_date_to': request.form.get('auth_date_to'),
                'auth_info_released': request.form.getlist('auth_info'),
            }

            updated_record = MedicalRecord(
                record_id=record_id,
                patient_id=p_id,
                doctor_id=d_id,
                date=date,
                consult_reason=reason,
                diagnosis=diagnosis,
                treatment=treatment,
                prescriptions=prescriptions,
                notes=notes,
                details=details
            )

            if hms.update_medical_record(updated_record):
                flash('Medical record updated successfully!', 'success')
                return redirect(url_for('patient_details', patient_id=updated_record.patient_id))
            else:
                flash('Failed to update medical record in database.', 'error')
        except Exception as e:
            flash(f'Error updating medical record: {e}', 'error')

    return render_template('create_medical_record.html', record=record, patients=patients,
                           doctors=doctors, active_page='patients', today=record.date)


@app.route('/view_medical_record/<record_id>')
def view_medical_record(record_id):
    record = hms.get_medical_record(record_id)
    if not record:
        flash('Medical record not found!', 'error')
        return redirect(url_for('patients'))

    patient = hms.get_patient(record.patient_id)
    doctor = hms.get_doctor(record.doctor_id)

    return render_template('view_medical_record.html', record=record, patient=patient,
                           doctor=doctor, active_page='patients')


@app.route('/delete_medical_record/<record_id>')
def delete_medical_record(record_id):
    record = hms.get_medical_record(record_id)
    if not record:
        flash('Medical record not found!', 'error')
        return redirect(url_for('patients'))
    
    patient_id = record.patient_id
    if hms.db.delete('medical_records', record_id, 'record_id'):
        flash('Medical record deleted successfully!', 'success')
    else:
        flash('Failed to delete medical record.', 'error')
    return redirect(url_for('patient_details', patient_id=patient_id))


@app.route('/patients/<patient_id>/records')
def patient_records(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))
    
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medical_records WHERE patient_id = ? ORDER BY date DESC", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    
    records = [hms.db._row_to_obj(MedicalRecord, row) for row in rows]
    for record in records:
        d = hms.get_doctor(record.doctor_id)
        record.doctor_name = f"Dr. {d.last_name}" if d else record.doctor_id
        record.patient_name = f"{patient.first_name} {patient.last_name}"

    return render_template('medical_records.html', records=records, patient=patient, 
                           total_pages=1, total_count=len(records), page=1,
                           active_page='patients')


# ── LAB RESULTS ───────────────────────────────────────────────────────────────

@app.route('/lab_results')
def lab_results():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    all_results = hms.lab_results
    if search_term:
        all_results = [r for r in all_results if
                       search_term.lower() in r.test_name.lower() or
                       search_term.lower() in r.patient_id.lower() or
                       search_term.lower() in (r.status or '').lower()]
    all_results = sorted(all_results, key=lambda x: x.test_date, reverse=True)
    results_slice, total_pages = paginate_list(all_results, page, per_page)
    total_count = len(all_results)
    return render_template('lab_results.html', lab_results=results_slice, page=page,
                           total_pages=total_pages, total_count=total_count,
                           search_term=search_term, active_page='lab_results')


@app.route('/lab_results/add', methods=['GET', 'POST'])
def add_lab_result():
    patient_id = request.args.get('patient_id', '')
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()
            test_name = request.form.get('test_name', '').strip()
            result = request.form.get('result', '').strip()
            status = request.form.get('status', 'Pending').strip()
            notes = request.form.get('notes', '').strip()
            test_date = request.form.get('test_date', datetime.datetime.now().strftime("%Y-%m-%d")).strip()
            reference_range = request.form.get('reference_range', '').strip()
            if not patient_id or not test_name:
                flash('Patient and test name are required!', 'error')
                return redirect(url_for('add_lab_result'))
            patient = hms.get_patient(patient_id)
            if not patient:
                flash('Patient not found!', 'error')
                return redirect(url_for('add_lab_result'))
            new_result = LabResult(
                result_id=hms.generate_id('LR'),
                patient_id=patient_id,
                doctor_id=doctor_id,
                test_name=test_name,
                result=result,
                status=status,
                notes=notes,
                test_date=test_date,
                reference_range=reference_range
            )
            hms.lab_results.append(new_result)
            hms.save_data()
            flash('Lab result added successfully!', 'success')
            notify('New Lab Result',
                   f"Lab result '{test_name}' added for {patient.first_name} {patient.last_name}.",
                   'lab_assistant')
            return redirect(url_for('lab_results'))
        except Exception as e:
            flash(f'Error adding lab result: {e}', 'error')
    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('add_lab_result.html', patients=patients, doctors=doctors,
                           patient_id=patient_id, active_page='lab_results')


@app.route('/lab_results/<result_id>')
def view_lab_results(result_id):
    result = next((lr for lr in hms.lab_results if lr.result_id == result_id), None)
    if not result:
        flash('Lab result not found!', 'error')
        return redirect(url_for('lab_results'))
    patient = hms.get_patient(result.patient_id)
    doctor = hms.get_doctor(result.doctor_id) if hasattr(result, 'doctor_id') else None
    return render_template('view_lab_results.html', result=result, patient=patient,
                           doctor=doctor, active_page='lab_results')


@app.route('/lab_results/edit/<result_id>', methods=['GET', 'POST'])
def edit_lab_result(result_id):
    result = hms.get_lab_result(result_id)
    if not result:
        flash('Lab result not found!', 'error')
        return redirect(url_for('lab_results'))

    if request.method == 'POST':
        try:
            result.patient_id = request.form.get('patient_id', '').strip()
            result.doctor_id = request.form.get('doctor_id', '').strip()
            result.test_name = request.form.get('test_name', '').strip()
            result.result = request.form.get('result', '').strip()
            result.status = request.form.get('status', 'Pending').strip()
            result.notes = request.form.get('notes', '').strip()
            result.test_date = request.form.get('test_date', '').strip()
            result.reference_range = request.form.get('reference_range', '').strip()
            
            if hms.update_lab_result(result):
                flash('Lab result updated successfully!', 'success')
                return redirect(url_for('view_lab_results', result_id=result_id))
            else:
                flash('Failed to update lab result.', 'error')
        except Exception as e:
            flash(f'Error updating lab result: {e}', 'error')

    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('add_lab_result.html', result=result, patients=patients, 
                           doctors=doctors, active_page='lab_results')


@app.route('/lab_results/delete/<result_id>')
def delete_lab_result(result_id):
    if hms.delete_lab_result(result_id):
        flash('Lab result deleted successfully!', 'success')
    else:
        flash('Failed to delete lab result.', 'error')
    return redirect(url_for('lab_results'))


# ── INVENTORY ─────────────────────────────────────────────────────────────────

@app.route('/inventory')
def inventory():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    if search_term:
        search_value = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM inventory WHERE item_id LIKE ? OR name LIKE ? OR category LIKE ?
            ORDER BY name ASC LIMIT ? OFFSET ?
        """, (search_value, search_value, search_value, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM inventory WHERE item_id LIKE ? OR name LIKE ? OR category LIKE ?
        """, (search_value, search_value, search_value))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM inventory ORDER BY name ASC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM inventory")
        total_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE quantity <= reorder_level")
    low_stock_count = cursor.fetchone()[0]
    conn.close()
    inventory_list = [hms.db._row_to_obj(InventoryItem, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1
    return render_template('inventory.html', inventory=inventory_list, page=page,
                           total_pages=total_pages, total_count=total_count,
                           low_stock_count=low_stock_count, search_term=search_term,
                           active_page='inventory')


# ── MESSAGES ──────────────────────────────────────────────────────────────────

@app.route('/messages')
def messages():
    username = session.get('username')
    role = session.get('role')
    all_messages = [m for m in hms.messages if m.recipient_id in [username, role, 'all']]
    all_messages.sort(key=lambda m: m.timestamp, reverse=True)
    return render_template('messages.html', messages=all_messages, active_page='messages')


@app.route('/messages/send', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        try:
            recipient_id = request.form.get('recipient_id', 'all').strip()
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            if not subject or not content:
                flash('Subject and content are required!', 'error')
                return redirect(url_for('send_message'))
            username = session.get('username')
            msg = Message(
                message_id=hms.generate_id('msg_'),
                sender_id=username,
                sender_name=username,
                recipient_id=recipient_id,
                subject=subject,
                content=content,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                is_read=False,
                is_archived=False
            )
            hms.messages.append(msg)
            hms.save_data()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('messages'))
        except Exception as e:
            flash(f'Error sending message: {e}', 'error')
    recipients = [{'id': u.username, 'name': u.username} for u in hms.users]
    roles = ['all', 'admin', 'doctor', 'nurse', 'receptionist', 'cashier', 'lab_assistant']
    return render_template('send_message.html', recipients=recipients, roles=roles, active_page='messages')


# ── REPORTS ───────────────────────────────────────────────────────────────────

@app.route('/general_reports')
def general_reports():
    stats = hms.get_stats()
    total_patients = hms.get_patients_count()
    total_appointments = stats['total_appointments']
    status_counts = stats['appointment_statuses']
    total_revenue = stats['total_revenue']
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills ORDER BY created_date DESC LIMIT 20")
    rows = cursor.fetchall()
    recent_bills = [hms.db._row_to_obj(Bill, row) for row in rows]
    conn.close()
    return render_template('general_reports.html', total_patients=total_patients,
                           total_appointments=total_appointments, total_revenue=total_revenue,
                           status_counts=status_counts, recent_bills=recent_bills, active_page='reports')


# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20
    all_users = hms.users
    if search_term:
        all_users = [u for u in all_users if
                     search_term.lower() in u.username.lower() or
                     search_term.lower() in u.role.lower()]
    total_count = len(all_users)
    users_slice, total_pages = paginate_list(all_users, page, per_page)
    return render_template('admin_users.html', users=users_slice, page=page,
                           total_pages=total_pages, total_count=total_count,
                           search_term=search_term, active_page='admin')


@app.route('/admin/update_user_role', methods=['POST'])
@admin_required
def update_user_role():
    target_username = request.form.get('username')
    new_role = request.form.get('role')
    actor_username = session.get('username')
    if hms.update_user_role(target_username, new_role, actor_username):
        flash(f'Role updated for {target_username} to {new_role}', 'success')
    else:
        flash('Failed to update role', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/activate_user/<username>')
@admin_required
def activate_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_status(username, True, actor_username):
        flash(f'User {username} activated', 'success')
    else:
        flash('Failed to activate user', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/deactivate_user/<username>')
@admin_required
def deactivate_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_status(username, False, actor_username):
        flash(f'User {username} deactivated', 'success')
    else:
        flash('Failed to deactivate user', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/verify_user/<username>')
@admin_required
def verify_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_verification(username, True, actor_username):
        flash(f'User {username} verified', 'success')
    else:
        flash('Failed to verify user', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/unverify_user/<username>')
@admin_required
def unverify_user(username):
    actor_username = session.get('username')
    if hms.toggle_user_verification(username, False, actor_username):
        flash(f'User {username} unverified', 'success')
    else:
        flash('Failed to unverify user', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/enable_user_2fa/<username>')
@admin_required
def enable_user_2fa(username):
    actor_username = session.get('username')
    if hms.toggle_user_2fa(username, True, actor_username):
        flash(f'2FA enabled for {username}', 'success')
    else:
        flash('Failed to enable 2FA', 'error')
    return redirect(url_for('admin_users'))


@app.route('/admin/disable_user_2fa/<username>')
@admin_required
def disable_user_2fa(username):
    actor_username = session.get('username')
    if hms.toggle_user_2fa(username, False, actor_username):
        flash(f'2FA disabled for {username}', 'success')
    else:
        flash('Failed to disable 2FA', 'error')
    return redirect(url_for('admin_users'))


# ── SETTINGS ──────────────────────────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        try:
            hms.settings['hospital_name'] = request.form.get('hospital_name', 'Hospital')
            hms.settings['hospital_address'] = request.form.get('hospital_address', '')
            hms.settings['hospital_phone'] = request.form.get('hospital_phone', '')
            hms.settings['hospital_email'] = request.form.get('hospital_email', '')
            hms.settings['currency'] = request.form.get('currency', 'MWK')
            hms.settings['notifications'] = 'notifications' in request.form
            hms.settings['appointment_reminder'] = 'appointment_reminder' in request.form
            hms.settings['low_stock_alert'] = 'low_stock_alert' in request.form
            hms.settings['low_stock_threshold'] = int(request.form.get('low_stock_threshold', 10))
            hms.save_data()
            flash('Settings saved successfully!', 'success')
        except Exception as e:
            flash(f'Error saving settings: {e}', 'error')
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=hms.settings, active_page='settings')


# ── SCHEDULE ──────────────────────────────────────────────────────────────────

@app.route('/schedule')
def view_schedule():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').strip()
    per_page = 20

    conn = hms.db.get_connection()
    cursor = conn.cursor()

    if search_term:
        search_value = f"%{search_term}%"
        cursor.execute("""
            SELECT * FROM appointments 
            WHERE patient_id LIKE ? OR doctor_id LIKE ? OR status LIKE ? OR reason LIKE ?
            ORDER BY appointment_date DESC, appointment_time DESC LIMIT ? OFFSET ?
        """, (search_value, search_value, search_value, search_value, per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("""
            SELECT COUNT(*) FROM appointments 
            WHERE patient_id LIKE ? OR doctor_id LIKE ? OR status LIKE ? OR reason LIKE ?
        """, (search_value, search_value, search_value, search_value))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT * FROM appointments ORDER BY appointment_date DESC, appointment_time DESC LIMIT ? OFFSET ?",
                       (per_page, (page - 1) * per_page))
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM appointments")
        total_count = cursor.fetchone()[0]

    conn.close()
    appointments_list = [hms.db._row_to_obj(Appointment, row) for row in rows]
    total_pages = math.ceil(total_count / per_page) if total_count else 1

    return render_template('view_schedule.html', appointments=appointments_list, page=page,
                           total_pages=total_pages, total_count=total_count,
                           search_term=search_term, active_page='schedule')


@app.route('/edit_appointment/<appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    conn = hms.db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        flash('Appointment not found!', 'error')
        return redirect(url_for('view_schedule'))

    appointment = hms.db._row_to_obj(Appointment, row)

    if request.method == 'POST':
        try:
            hms.db.save('appointments', Appointment(
                appointment_id=appointment_id,
                patient_id=request.form.get('patient_id', appointment.patient_id),
                doctor_id=request.form.get('doctor_id', appointment.doctor_id),
                appointment_date=request.form.get('date', appointment.appointment_date),
                appointment_time=request.form.get('time', appointment.appointment_time),
                reason=request.form.get('reason', appointment.reason),
                status=request.form.get('status', appointment.status),
                notes=request.form.get('notes', appointment.notes)
            ), 'appointment_id')
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('view_schedule'))
        except Exception as e:
            flash(f'Error updating appointment: {e}', 'error')

    patients = hms.patients if hms.patients else hms.get_all_patients()
    doctors = hms.doctors if hms.doctors else hms.get_all_doctors()
    return render_template('edit_appointment.html', appointment=appointment,
                           patients=patients, doctors=doctors, active_page='schedule')


@app.route('/delete_appointment/<appointment_id>')
def delete_appointment(appointment_id):
    if hms.db.delete('appointments', appointment_id, 'appointment_id'):
        flash('Appointment deleted successfully!', 'success')
    else:
        flash('Error deleting appointment!', 'error')
    return redirect(url_for('view_schedule'))


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    try:
        print("[System] Seeding default users...")
        seed_users()
        print("[System] User seeding completed successfully.")
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed during user seeding: {e}")
        import traceback
        traceback.print_exc()
    print("[System] Starting Flask development server...")
    app.run(debug=True, host='0.0.0.0', port=5000)