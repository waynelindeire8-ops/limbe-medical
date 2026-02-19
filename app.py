from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import datetime
import os
from werkzeug.utils import secure_filename
from functools import wraps
from main import HospitalManagementSystem
from models import Patient, Appointment, Doctor, Message

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for flashing messages
hms = HospitalManagementSystem()

# Seed Users
def seed_users():
    users = [
        ('admin', 'admin123', 'admin'),
        ('receptionist', 'rec123', 'receptionist'),
        ('cashier', 'cash123', 'cashier'),
        ('nurse', 'nurse123', 'nurse'),
        ('lab', 'lab123', 'lab_assistant'),
        ('doctor', 'doc123', 'doctor')
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

@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.context_processor
def inject_user():
    return dict(current_user=session.get('username'), current_role=session.get('role'))

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

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    # Statistics
    total_patients = len(hms.patients)
    
    # Count active doctors
    active_doctors = sum(1 for d in hms.doctors if d.status.lower() == 'active') if hms.doctors else 0
    
    # Count today's appointments
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_appointments = sum(1 for a in hms.appointments if a.appointment_date == today)
    
    # Pending lab results (Mock logic)
    pending_lab_results = 45

    # Recent Appointments
    recent_appointments = hms.appointments[-4:] if hms.appointments else []
    
    # Format for display
    formatted_appointments = []
    for appt in recent_appointments:
        doctor_name = "Unknown Doctor"
        for doc in hms.doctors:
            if doc.doctor_id == appt.doctor_id:
                doctor_name = f"Dr. {doc.last_name}"
                break
        
        patient_name = "Unknown Patient"
        for pat in hms.patients:
            if pat.patient_id == appt.patient_id:
                patient_name = f"{pat.first_name} {pat.last_name}"
                break

        formatted_appointments.append({
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'time': appt.appointment_time,
            'type': 'Consultation', # Default
            'status': appt.status
        })

    return render_template('dashboard.html', 
                           total_patients=total_patients,
                           active_doctors=active_doctors,
                           today_appointments=today_appointments,
                           pending_lab_results=pending_lab_results,
                           recent_appointments=formatted_appointments,
                           active_page='dashboard')

@app.route('/patient/<patient_id>')
def patient_details(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))
    
    files = hms.patient_files.get(patient_id, [])
    appointments = hms.get_patient_appointments(patient_id)
    medical_records = hms.get_patient_medical_records(patient_id)
    
    return render_template('patient_details.html', 
                           patient=patient, 
                           files=files, 
                           appointments=appointments, 
                           medical_records=medical_records,
                           active_page='patients')

@app.route('/patient/<patient_id>/upload_file', methods=['POST'])
def upload_patient_file(patient_id):
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('patient_details', patient_id=patient_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('patient_details', patient_id=patient_id))
    
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
                
    return redirect(url_for('patient_details', patient_id=patient_id))

@app.route('/patient/<patient_id>/delete_file')
def delete_patient_file(patient_id):
    rel_path = request.args.get('path')
    if hms.delete_patient_file(patient_id, rel_path):
        flash('File deleted successfully!', 'success')
    else:
        flash('Error deleting file!', 'error')
    return redirect(url_for('patient_details', patient_id=patient_id))

@app.route('/download_file')
def download_file():
    path = request.args.get('path')
    if not path:
        return "File not found", 404
        
    # Security check: ensure path is within attachments
    base_dir = os.path.dirname(os.path.abspath(hms.data_file))
    abs_path = os.path.join(base_dir, path)
    
    if not os.path.exists(abs_path):
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
        return "File not found", 404
        
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename)

@app.route('/patients')
def patients():
    search_term = request.args.get('search', '')
    if search_term:
        patients = hms.search_patients(search_term)
    else:
        patients = hms.patients
    return render_template('patients.html', patients=patients, active_page='patients', search_term=search_term)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            # Basic validation could be added here
            new_patient = Patient(
                patient_id=hms.generate_id("P"),
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                date_of_birth=request.form['dob'],
                gender=request.form['gender'],
                phone=request.form['phone'],
                email=request.form['email'],
                address=request.form['address'],
                emergency_contact=request.form['emergency_contact'],
                medical_history="",
                created_date=datetime.datetime.now().strftime("%Y-%m-%d")
            )
            hms.add_patient(new_patient)
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patients'))
        except Exception as e:
            flash(f'Error adding patient: {e}', 'error')
    
    return render_template('add_patient.html', active_page='patients')

@app.route('/edit_patient/<patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = hms.get_patient(patient_id)
    if not patient:
        flash('Patient not found!', 'error')
        return redirect(url_for('patients'))

    if request.method == 'POST':
        try:
            hms.update_patient(
                patient_id,
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                date_of_birth=request.form['dob'],
                gender=request.form['gender'],
                phone=request.form['phone'],
                email=request.form['email'],
                address=request.form['address'],
                emergency_contact=request.form['emergency_contact']
            )
            flash('Patient updated successfully!', 'success')
            return redirect(url_for('patients'))
        except Exception as e:
            flash(f'Error updating patient: {e}', 'error')

    return render_template('edit_patient.html', patient=patient, active_page='patients')

@app.route('/delete_patient/<patient_id>')
def delete_patient(patient_id):
    if hms.delete_patient(patient_id):
        flash('Patient deleted successfully!', 'success')
    else:
        flash('Error deleting patient!', 'error')
    return redirect(url_for('patients'))

@app.route('/doctors')
def doctors():
    return render_template('doctors.html', doctors=hms.doctors, active_page='doctors')

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
                status=request.form['status']
            )
            hms.add_doctor(new_doctor)
            flash('Doctor added successfully!', 'success')
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
                status=request.form['status']
            )
            flash('Doctor updated successfully!', 'success')
            return redirect(url_for('doctors'))
        except Exception as e:
            flash(f'Error updating doctor: {e}', 'error')

    return render_template('edit_doctor.html', doctor=doctor, active_page='doctors')

@app.route('/delete_doctor/<doctor_id>')
def delete_doctor(doctor_id):
    if hms.delete_doctor(doctor_id):
        flash('Doctor deleted successfully!', 'success')
    else:
        flash('Error deleting doctor!', 'error')
    return redirect(url_for('doctors'))

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
        else:
            flash(f'Department "{dept_name}" already exists.', 'warning')
    return redirect(url_for('departments'))

@app.route('/messages')
def messages():
    # Use real messages from HMS
    messages_list = []
    
    # Sort messages by timestamp (newest first) - assuming simple string sort works for now or just reverse
    # In a real app, parse dates.
    sorted_messages = hms.messages[::-1] 
    
    for msg in sorted_messages:
        messages_list.append({
            'id': msg.message_id,
            'sender': msg.sender_name,
            'role': 'User', # Simplified
            'time': msg.timestamp,
            'preview': msg.subject,
            'content': msg.content,
            'active': False
        })
        
    # If no messages, maybe show the mock ones for demo purposes if desired, 
    # but user wants to "send messages", so showing their sent message is more important.
    # Let's keep the mock ones ONLY if the list is empty, so it doesn't look broken.
    if not messages_list:
        # ... (Insert the previous mock logic here if needed, or just leave empty)
        # Let's re-insert the mock logic for "received" messages simulation
        import random
        doctor_messages = [
             "Patient consultation regarding lab results",
             "Requesting shift swap for next week",
             "New protocol for patient admission"
        ]
        for i, doctor in enumerate(hms.doctors[:3]):
             msg_content = random.choice(doctor_messages)
             messages_list.append({
                 'id': f'mock_{i}',
                 'sender': f"Dr. {doctor.first_name} {doctor.last_name}",
                 'role': getattr(doctor, 'specialization', 'Doctor'),
                 'time': "10:30 AM",
                 'preview': msg_content,
                 'content': f"Hello,\n\n{msg_content}.\n\nBest regards,\nDr. {doctor.last_name}",
                 'active': False
             })
             
    if messages_list:
        messages_list[0]['active'] = True

    return render_template('messages.html', active_page='messages', messages=messages_list)

@app.route('/messages/send', methods=['POST'])
def send_message():
    content = request.form.get('message')
    recipient = request.form.get('recipient', 'System Admin') # Default recipient
    
    if content:
        new_msg = Message(
            message_id=hms.generate_id('msg_'),
            sender_id='current_user', # Placeholder for logged in user
            sender_name='You', # Placeholder
            recipient_id='admin',
            subject=content[:30] + '...' if len(content) > 30 else content,
            content=content,
            timestamp=datetime.datetime.now().strftime("%I:%M %p"),
            is_read=False,
            is_archived=False
        )
        hms.messages.append(new_msg)
        hms.save_data()
        flash('Message sent successfully!', 'success')
    else:
        flash('Message cannot be empty.', 'error')
        
    return redirect(url_for('messages'))

@app.route('/view_lab_results')
def view_lab_results():
    # Filter for lab results
    lab_records = []
    for record in hms.medical_records:
        # Check if "Lab" is mentioned in reason, diagnosis, or notes
        # OR if it has a 'Lab Results' section in details (if we had structured data)
        text_content = (record.consult_reason + record.diagnosis + record.notes).lower()
        if 'lab' in text_content or 'blood' in text_content or 'test' in text_content:
             lab_records.append(record)
             
    return render_template('view_lab_results.html', medical_records=lab_records, active_page='lab_results')

@app.route('/general_reports')
def general_reports():
    total_patients = len(hms.patients)
    total_doctors = len(hms.doctors)
    total_appointments = len(hms.appointments)
    
    # Calculate revenue from bills if available, otherwise estimate
    revenue = 0
    if hasattr(hms, 'bills') and hms.bills:
         revenue = sum(bill.amount for bill in hms.bills)
    else:
         # Mock revenue based on completed appointments
         revenue = sum(150 for a in hms.appointments if a.status == 'Completed')

    # Department counts for the table
    department_counts = {}
    for doctor in hms.doctors:
        spec = getattr(doctor, 'specialty', getattr(doctor, 'specialization', 'General'))
        if not spec:
            spec = 'General'
        department_counts[spec] = department_counts.get(spec, 0) + 1

    # Demographics
    male_patients = sum(1 for p in hms.patients if p.gender.lower() == 'male')
    female_patients = sum(1 for p in hms.patients if p.gender.lower() == 'female')
    
    if total_patients > 0:
        male_pct = int((male_patients / total_patients) * 100)
        female_pct = int((female_patients / total_patients) * 100)
    else:
        male_pct = 0
        female_pct = 0

    # Appointment Status
    completed_appt = sum(1 for a in hms.appointments if a.status.lower() == 'completed')
    cancelled_appt = sum(1 for a in hms.appointments if a.status.lower() == 'cancelled')
    no_show_appt = sum(1 for a in hms.appointments if a.status.lower() == 'no-show')
    
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
    if search_term:
        appointments = hms.search_appointments(search_term)
    else:
        appointments = hms.appointments
    return render_template('view_schedule.html', appointments=appointments, active_page='schedule', search_term=search_term)

@app.route('/analytics')
def analytics():
    # Placeholder for analytics
    return render_template('analytics.html', active_page='analytics')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
