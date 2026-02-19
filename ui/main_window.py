import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import datetime

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import HospitalManagementSystem

class HospitalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Limbe Medical Clinic - Hospital Management System")
        self.root.geometry("1280x800")
        
        # Initialize System
        self.hms = HospitalManagementSystem()
        
        # Configure Styles
        self.setup_styles()
        
        # Create Main Layout
        self.create_main_layout()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colors
        self.colors = {
            'primary': '#1a237e',      # Dark Blue
            'secondary': '#2c3e50',    # Dark Gray/Blue
            'accent': '#0d47a1',       # Blue
            'success': '#00bfa5',      # Teal/Green
            'warning': '#ff9800',      # Orange
            'danger': '#e53935',       # Red
            'info': '#1976d2',         # Light Blue
            'bg': '#f5f5f5',           # Light Gray
            'white': '#ffffff'
        }
        
        # Configure generic styles
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('Card.TFrame', background=self.colors['white'])
        
        # Header Style
        self.style.configure('Header.TLabel', font=('Helvetica', 24, 'bold'), background=self.colors['primary'], foreground='white')
        
        # Sidebar Button Style
        self.style.configure(
            'Sidebar.TButton', 
            font=('Helvetica', 11, 'bold'), 
            background=self.colors['primary'], 
            foreground='white',
            borderwidth=0,
            padding=10
        )
        self.style.map('Sidebar.TButton',
            background=[('active', self.colors['accent'])],
            foreground=[('active', 'white')]
        )
        
        # Treeview Style
        self.style.configure("Treeview", 
            background="white",
            foreground="black",
            rowheight=25,
            fieldbackground="white",
            font=('Helvetica', 10)
        )
        self.style.configure("Treeview.Heading", 
            font=('Helvetica', 10, 'bold'),
            background=self.colors['primary'],
            foreground='white'
        )
        self.style.map("Treeview", background=[('selected', self.colors['accent'])])

    def create_main_layout(self):
        # Top Header
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=80)
        header_frame.pack(fill='x', side='top')
        header_frame.pack_propagate(False) # Prevent shrinking
        
        # Logo/Icon placeholder (using text for now)
        logo_label = tk.Label(
            header_frame, 
            text="🏥 Limbe Medical Clinic", 
            bg=self.colors['primary'], 
            fg='white', 
            font=('Helvetica', 26, 'bold')
        )
        logo_label.pack(side='left', padx=20, pady=10)
        
        # Main Container
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True)
        
        # Sidebar
        sidebar_frame = tk.Frame(main_container, bg='white', width=250)
        sidebar_frame.pack(side='left', fill='y')
        
        # Sidebar Title "Navigation"
        tk.Label(sidebar_frame, text="Navigation", font=('Helvetica', 14, 'bold'), bg='white', fg='#333').pack(pady=20)
        
        # Sidebar Buttons
        menu_items = [
            ("📊 Dashboard", self.show_dashboard),
            ("👥 Patients", self.show_patients),
            ("📅 Appointments", self.show_appointments),
            ("💰 Billing", self.show_billing),
            ("📈 Reports", self.show_reports),
            ("⚙️ Settings", self.show_settings),
            ("📁 Files", self.show_files),
            ("❌ Exit", self.root.quit)
        ]
        
        for text, command in menu_items:
            btn = tk.Button(
                sidebar_frame, 
                text=text, 
                command=command, 
                bg=self.colors['primary'], 
                fg='white', 
                font=('Helvetica', 11, 'bold'),
                bd=0,
                pady=10,
                padx=20,
                anchor='w',
                cursor='hand2'
            )
            btn.pack(fill='x', pady=5, padx=10)
            
        # Content Area
        self.content_area = tk.Frame(main_container, bg=self.colors['bg'])
        self.content_area.pack(side='right', fill='both', expand=True, padx=20, pady=20)
        
        # Initial View
        self.show_dashboard()

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def calculate_age(self, dob_str):
        if not dob_str: return "N/A"
        try:
            dob = datetime.datetime.strptime(dob_str, "%Y-%m-%d")
            today = datetime.datetime.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except:
            return "N/A"

    def show_dashboard(self):
        self.clear_content()
        
        # Dashboard Header
        tk.Label(self.content_area, text="System Dashboard", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 20))
        
        # --- Stats Cards Section ---
        stats_container = tk.Frame(self.content_area, bg=self.colors['bg'])
        stats_container.pack(fill='x', pady=(0, 20))
        
        # Calculate Stats
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        today_appts = len([a for a in self.hms.appointments if a.appointment_date == today_str])
        pending_bills = len([b for b in self.hms.bills if b.status == 'Pending'])
        low_stock = len(self.hms.get_low_stock_items())
        
        stats_data = [
            ("Total Patients", len(self.hms.patients), self.colors['accent']),
            ("Total Doctors", len(self.hms.doctors), self.colors['success']),
            ("Today's Appointments", today_appts, self.colors['warning']),
            ("Pending Bills", pending_bills, self.colors['danger']),
            ("Low Stock Items", low_stock, self.colors['danger']),
            ("Total Medical Records", len(self.hms.medical_records), self.colors['info'])
        ]
        
        # Create Grid for Stats
        for i, (title, value, color) in enumerate(stats_data):
            row = i // 3
            col = i % 3
            
            card = tk.Frame(stats_container, bg=color, height=100)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            card.pack_propagate(False) # Prevent shrinking
            
            tk.Label(card, text=str(value), font=('Helvetica', 36, 'bold'), bg=color, fg='white').pack(expand=True, pady=(15, 0))
            tk.Label(card, text=title, font=('Helvetica', 12), bg=color, fg='white').pack(pady=(0, 15))
            
        stats_container.grid_columnconfigure(0, weight=1)
        stats_container.grid_columnconfigure(1, weight=1)
        stats_container.grid_columnconfigure(2, weight=1)

        # --- Bottom Section (Queue & Currently Being Seen) ---
        bottom_container = tk.Frame(self.content_area, bg=self.colors['bg'])
        bottom_container.pack(fill='both', expand=True)
        
        # Patient Queue (Left)
        queue_frame = tk.Frame(bottom_container, bg=self.colors['bg'])
        queue_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(queue_frame, text="Patient Queue", font=('Helvetica', 16, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 10))
        
        # Tabs for Queue
        tab_control = ttk.Notebook(queue_frame)
        tab_awaiting = ttk.Frame(tab_control)
        tab_cancelled = ttk.Frame(tab_control)
        tab_finished = ttk.Frame(tab_control)
        
        tab_control.add(tab_awaiting, text='Awaiting')
        tab_control.add(tab_cancelled, text='Cancelled')
        tab_control.add(tab_finished, text='Finished')
        tab_control.pack(expand=1, fill="both")
        
        # Function to create queue table
        def create_queue_table(parent, status_filter):
            columns = ('Name', 'Visit Time', 'Gender', 'Age', 'Condition')
            tree = ttk.Treeview(parent, columns=columns, show='headings', height=8)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            tree.pack(fill='both', expand=True)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scrollbar.set)
            scrollbar.pack(side='right', fill='y')
            
            # Populate Data
            today_appts_list = [a for a in self.hms.appointments if a.appointment_date == today_str]
            
            for apt in today_appts_list:
                # Map statuses
                apt_status = apt.status
                should_show = False
                
                if status_filter == 'Awaiting' and apt_status in ['Scheduled', 'Confirmed', 'In Progress']:
                    should_show = True
                elif status_filter == 'Cancelled' and apt_status == 'Cancelled':
                    should_show = True
                elif status_filter == 'Finished' and apt_status == 'Completed':
                    should_show = True
                    
                if should_show:
                    patient = self.hms.get_patient(apt.patient_id)
                    if patient:
                        name = f"{patient.first_name} {patient.last_name}"
                        gender = patient.gender
                        age = self.calculate_age(patient.date_of_birth)
                        condition = apt.reason
                        tree.insert('', 'end', values=(name, apt.appointment_time, gender, age, condition))
            return tree

        create_queue_table(tab_awaiting, 'Awaiting')
        create_queue_table(tab_cancelled, 'Cancelled')
        create_queue_table(tab_finished, 'Finished')
        
        # Currently Being Seen (Right)
        current_frame = tk.Frame(bottom_container, bg='white', width=300)
        current_frame.pack(side='right', fill='y')
        current_frame.pack_propagate(False)
        
        # Header
        tk.Label(current_frame, text="Currently Being Seen", font=('Helvetica', 14, 'bold'), bg=self.colors['primary'], fg='white', pady=10).pack(fill='x')
        
        # Find current patient (First 'In Progress' appointment)
        current_appt = next((a for a in self.hms.appointments if a.appointment_date == today_str and a.status == 'In Progress'), None)
        
        if current_appt:
            patient = self.hms.get_patient(current_appt.patient_id)
            if patient:
                tk.Label(current_frame, text="Name", font=('Helvetica', 10), bg='white', fg='gray').pack(pady=(20, 5))
                tk.Label(current_frame, text=f"{patient.first_name} {patient.last_name}", font=('Helvetica', 16, 'bold'), bg='white').pack()
                
                tk.Label(current_frame, text="Condition", font=('Helvetica', 10), bg='white', fg='gray').pack(pady=(20, 5))
                tk.Label(current_frame, text=current_appt.reason, font=('Helvetica', 12), bg='white', wraplength=250).pack()
                
                tk.Label(current_frame, text="Doctor", font=('Helvetica', 10), bg='white', fg='gray').pack(pady=(20, 5))
                doctor = self.hms.get_doctor(current_appt.doctor_id)
                doc_name = f"Dr. {doctor.last_name}" if doctor else "Unknown"
                tk.Label(current_frame, text=doc_name, font=('Helvetica', 12), bg='white').pack()
                
                # Timer placeholder
                tk.Label(current_frame, text="00:15:30", font=('Courier', 24, 'bold'), bg='white', fg=self.colors['success']).pack(pady=30)
        else:
            tk.Label(current_frame, text="No active appointment", font=('Helvetica', 12, 'italic'), bg='white', fg='gray').pack(pady=50)

    def show_patients(self):
        self.clear_content()
        
        # Header
        tk.Label(self.content_area, text="Patient Management", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 20))
        
        # Search Bar Frame
        search_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        search_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        tk.Label(search_frame, text="Search:", font=('Helvetica', 12), bg=self.colors['bg']).pack(side='left', padx=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side='left', padx=(0, 10))
        
        def search_patient():
            query = search_var.get().lower()
            if not query:
                return
            
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
                
            # Filter and insert
            for p in self.hms.patients:
                full_name = f"{p.first_name} {p.last_name}".lower()
                if query in p.patient_id.lower() or query in full_name:
                    tree.insert('', 'end', values=(
                        p.patient_id,
                        f"{p.first_name} {p.last_name}",
                        p.date_of_birth,
                        p.gender
                    ))
        
        def clear_search():
            search_var.set("")
            refresh_table()
            
        tk.Button(search_frame, text="Search", command=search_patient, bg='#e0e0e0', bd=1, padx=10).pack(side='left', padx=(0, 10))
        tk.Button(search_frame, text="Clear", command=clear_search, bg='#e0e0e0', bd=1, padx=10).pack(side='left')
        
        # Patient Table
        columns = ('Patient ID', 'Name', 'Date of Birth', 'Gender')
        tree = ttk.Treeview(self.content_area, columns=columns, show='headings')
        
        # Configure columns
        tree.column('Patient ID', width=150)
        tree.column('Name', width=250)
        tree.column('Date of Birth', width=150)
        tree.column('Gender', width=100)
        
        for col in columns:
            tree.heading(col, text=col)
            
        tree.pack(fill='both', expand=True, padx=20)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        def refresh_table():
            for item in tree.get_children():
                tree.delete(item)
            for p in self.hms.patients:
                tree.insert('', 'end', values=(
                    p.patient_id,
                    f"{p.first_name} {p.last_name}",
                    p.date_of_birth,
                    p.gender
                ))
                
        refresh_table()
        
        # Action Buttons Frame
        action_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        action_frame.pack(fill='x', padx=20, pady=20)
        
        def add_patient_dialog():
            messagebox.showinfo("Info", "Add Patient Dialog - To be implemented")

        def update_patient_dialog():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a patient to update")
                return
            item = tree.item(selected[0])
            patient_id = item['values'][0]
            messagebox.showinfo("Info", f"Update Patient {patient_id} - To be implemented")

        def delete_patient_action():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a patient to delete")
                return
            item = tree.item(selected[0])
            patient_id = item['values'][0]
            
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete patient {patient_id}?"):
                # Placeholder for deletion logic
                # self.hms.delete_patient(patient_id)
                # refresh_table()
                messagebox.showinfo("Info", f"Patient {patient_id} deleted (Simulated)")

        tk.Button(action_frame, text="Add Patient", command=add_patient_dialog, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left', padx=(0, 10))
        tk.Button(action_frame, text="Update Patient", command=update_patient_dialog, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left', padx=(0, 10))
        tk.Button(action_frame, text="Delete Patient", command=delete_patient_action, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left')

    def show_appointments(self):
        self.clear_content()
        
        # Header
        tk.Label(self.content_area, text="Appointment Management", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 20))
        
        # Search Bar Frame
        search_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        search_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        tk.Label(search_frame, text="Search:", font=('Helvetica', 12), bg=self.colors['bg']).pack(side='left', padx=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
        search_entry.pack(side='left', padx=(0, 10))
        
        def search_appointment():
            query = search_var.get().lower()
            if not query:
                return
            
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
                
            # Filter and insert
            for appt in self.hms.appointments:
                patient = self.hms.get_patient(appt.patient_id)
                doctor = self.hms.get_doctor(appt.doctor_id)
                
                patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
                doctor_name = f"Dr. {doctor.last_name}" if doctor else "Unknown"
                
                if (query in appt.appointment_id.lower() or 
                    query in patient_name.lower() or 
                    query in doctor_name.lower()):
                    
                    tree.insert('', 'end', values=(
                        appt.appointment_id,
                        patient_name,
                        doctor_name,
                        appt.appointment_date,
                        appt.appointment_time,
                        appt.status
                    ))
        
        def clear_search():
            search_var.set("")
            refresh_table()
            
        tk.Button(search_frame, text="Search", command=search_appointment, bg='#e0e0e0', bd=1, padx=10).pack(side='left', padx=(0, 10))
        tk.Button(search_frame, text="Clear", command=clear_search, bg='#e0e0e0', bd=1, padx=10).pack(side='left')
        
        # Action Buttons Frame
        action_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        action_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        def schedule_appointment_dialog():
            messagebox.showinfo("Info", "Schedule Appointment Dialog - To be implemented")

        def update_status_dialog():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an appointment to update")
                return
            item = tree.item(selected[0])
            appt_id = item['values'][0]
            messagebox.showinfo("Info", f"Update Status for {appt_id} - To be implemented")

        def cancel_appointment_action():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select an appointment to cancel")
                return
            item = tree.item(selected[0])
            appt_id = item['values'][0]
            
            if messagebox.askyesno("Confirm", f"Are you sure you want to cancel appointment {appt_id}?"):
                # Placeholder for cancellation logic
                # self.hms.update_appointment_status(appt_id, "Cancelled")
                # refresh_table()
                messagebox.showinfo("Info", f"Appointment {appt_id} cancelled (Simulated)")

        tk.Button(action_frame, text="Schedule Appointment", command=schedule_appointment_dialog, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left', padx=(0, 10))
        tk.Button(action_frame, text="Update Status", command=update_status_dialog, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left', padx=(0, 10))
        tk.Button(action_frame, text="Cancel Appointment", command=cancel_appointment_action, bg='#e0e0e0', bd=1, padx=15, pady=5).pack(side='left')

        # Appointment Table
        columns = ('Appointment ID', 'Patient', 'Doctor', 'Date', 'Time', 'Status')
        tree = ttk.Treeview(self.content_area, columns=columns, show='headings')
        
        # Configure columns
        tree.column('Appointment ID', width=100)
        tree.column('Patient', width=200)
        tree.column('Doctor', width=150)
        tree.column('Date', width=100)
        tree.column('Time', width=100)
        tree.column('Status', width=100)
        
        for col in columns:
            tree.heading(col, text=col)
            
        tree.pack(fill='both', expand=True, padx=20)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        def refresh_table():
            for item in tree.get_children():
                tree.delete(item)
            
            for appt in self.hms.appointments:
                patient = self.hms.get_patient(appt.patient_id)
                doctor = self.hms.get_doctor(appt.doctor_id)
                
                patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
                doctor_name = f"Dr. {doctor.last_name}" if doctor else "Unknown"
                
                tree.insert('', 'end', values=(
                    appt.appointment_id,
                    patient_name,
                    doctor_name,
                    appt.appointment_date,
                    appt.appointment_time,
                    appt.status
                ))
                
        refresh_table()
        
    def show_doctors(self):
        self.clear_content()
        ttk.Label(self.content_area, text="Doctors", font=('Helvetica', 18, 'bold')).pack(pady=20)

    def show_billing(self):
        self.clear_content()
        
        # --- Header Section ---
        header_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        header_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(header_frame, text="💳 Billing & Payments Management", font=('Helvetica', 22, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(side='top', anchor='w')
        tk.Label(header_frame, text="Manage patient bills and payment processing", font=('Helvetica', 12), bg=self.colors['bg'], fg='#666').pack(side='top', anchor='w')

        # --- Toolbar Section ---
        toolbar_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        toolbar_frame.pack(fill='x', pady=(0, 20))
        
        def create_bill_dialog():
            messagebox.showinfo("Info", "Create New Bill - To be implemented")
            
        def process_payment_dialog():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a bill to process payment")
                return
            messagebox.showinfo("Info", "Process Payment - To be implemented")

        # Buttons
        tk.Button(toolbar_frame, text="+ Create New Bill", command=create_bill_dialog, bg=self.colors['primary'], fg='white', font=('Helvetica', 10, 'bold'), padx=15, pady=8, bd=0).pack(side='left', padx=(0, 10))
        tk.Button(toolbar_frame, text="Process Payment", command=process_payment_dialog, bg=self.colors['success'], fg='white', font=('Helvetica', 10, 'bold'), padx=15, pady=8, bd=0).pack(side='left', padx=(0, 10))
        
        # Secondary Buttons (Light Gray)
        sec_btn_style = {'bg': '#e0e0e0', 'fg': 'black', 'font': ('Helvetica', 10), 'padx': 10, 'pady': 5, 'bd': 1}
        
        tk.Button(toolbar_frame, text="🔍 Search Bills", **sec_btn_style).pack(side='left', padx=(0, 5))
        tk.Button(toolbar_frame, text="📊 Generate Report", **sec_btn_style).pack(side='left', padx=(0, 5))
        tk.Button(toolbar_frame, text="📄 Generate Invoice", **sec_btn_style).pack(side='left', padx=(0, 5))
        tk.Button(toolbar_frame, text="🖨️ Print Receipt", **sec_btn_style).pack(side='left', padx=(0, 5))
        
        def refresh_data():
            refresh_table()
            update_summary()
            
        tk.Button(toolbar_frame, text="🔄 Refresh", command=refresh_data, **sec_btn_style).pack(side='left', padx=(0, 5))

        # --- Summary Section ---
        summary_frame = tk.Frame(self.content_area, bg='#e3f2fd', bd=1, relief='solid') # Light Blue bg
        summary_frame.pack(fill='x', pady=(0, 20), ipady=10)
        
        tk.Label(summary_frame, text="Billing Summary", font=('Helvetica', 10, 'bold'), bg='#e3f2fd', anchor='w').pack(fill='x', padx=15, pady=(5, 5))
        
        stats_frame = tk.Frame(summary_frame, bg='#e3f2fd')
        stats_frame.pack(fill='x', padx=15)
        
        self.lbl_pending = tk.Label(stats_frame, text="Total Pending: MWK 0.00", font=('Helvetica', 12, 'bold'), bg='#e3f2fd', fg=self.colors['warning'])
        self.lbl_pending.pack(side='left', padx=(0, 20))
        
        self.lbl_paid = tk.Label(stats_frame, text="Total Paid: MWK 0.00", font=('Helvetica', 12, 'bold'), bg='#e3f2fd', fg=self.colors['success'])
        self.lbl_paid.pack(side='left', padx=(0, 20))
        
        self.lbl_overdue = tk.Label(stats_frame, text="Total Overdue: MWK 0.00", font=('Helvetica', 12, 'bold'), bg='#e3f2fd', fg=self.colors['danger'])
        self.lbl_overdue.pack(side='left', padx=(0, 20))
        
        self.lbl_total_bills = tk.Label(stats_frame, text="Total Bills: 0", font=('Helvetica', 12, 'bold'), bg='#e3f2fd', fg='black')
        self.lbl_total_bills.pack(side='left', padx=(0, 20))

        # --- Search Filter Section ---
        filter_frame = tk.Frame(self.content_area, bg='#f5f5f5', bd=1, relief='solid')
        filter_frame.pack(fill='x', pady=(0, 20), ipady=10)
        
        tk.Label(filter_frame, text="Search Bills", font=('Helvetica', 10, 'bold'), bg='#f5f5f5', anchor='w').pack(fill='x', padx=15, pady=(5, 5))
        
        search_controls = tk.Frame(filter_frame, bg='#f5f5f5')
        search_controls.pack(fill='x', padx=15)
        
        tk.Label(search_controls, text="Search by Patient ID, Name, or Bill ID:", bg='#f5f5f5').pack(side='left')
        search_var = tk.StringVar()
        tk.Entry(search_controls, textvariable=search_var, width=30).pack(side='left', padx=10)
        
        tk.Label(search_controls, text="Status:", bg='#f5f5f5').pack(side='left', padx=(10, 5))
        status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(search_controls, textvariable=status_var, values=["All", "Pending", "Paid", "Overdue"], state="readonly", width=15)
        status_combo.pack(side='left')
        
        def perform_search():
            refresh_table(search_var.get(), status_var.get())

        tk.Button(search_controls, text="Search", command=perform_search, bg=self.colors['primary'], fg='white', padx=15).pack(side='left', padx=15)

        # --- Bills List ---
        tk.Label(self.content_area, text="Bills List", font=('Helvetica', 12, 'bold'), bg=self.colors['bg']).pack(anchor='w', pady=(0, 5))
        
        columns = ('Bill ID', 'Patient ID', 'Patient Name', 'Date', 'Amount', 'Status', 'Due Date')
        tree = ttk.Treeview(self.content_area, columns=columns, show='headings', height=10)
        
        tree.column('Bill ID', width=100)
        tree.column('Patient ID', width=100)
        tree.column('Patient Name', width=200)
        tree.column('Date', width=100)
        tree.column('Amount', width=100)
        tree.column('Status', width=100)
        tree.column('Due Date', width=100)
        
        for col in columns:
            tree.heading(col, text=col)
            
        tree.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        # --- Logic Functions ---
        def update_summary():
            pending = sum(b.amount for b in self.hms.bills if b.status == 'Pending')
            paid = sum(b.amount for b in self.hms.bills if b.status == 'Paid')
            # Mock overdue logic since we don't have due dates in model yet
            overdue = 0 
            total_count = len(self.hms.bills)
            
            self.lbl_pending.config(text=f"Total Pending: MWK {pending:,.2f}")
            self.lbl_paid.config(text=f"Total Paid: MWK {paid:,.2f}")
            self.lbl_overdue.config(text=f"Total Overdue: MWK {overdue:,.2f}")
            self.lbl_total_bills.config(text=f"Total Bills: {total_count}")

        def refresh_table(query="", status_filter="All"):
            for item in tree.get_children():
                tree.delete(item)
                
            query = query.lower()
            
            for bill in self.hms.bills:
                # Filter logic
                if status_filter != "All" and bill.status != status_filter:
                    continue
                
                patient = self.hms.get_patient(bill.patient_id)
                patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
                
                if query:
                    if (query not in bill.bill_id.lower() and 
                        query not in bill.patient_id.lower() and 
                        query not in patient_name.lower()):
                        continue
                
                # Calculate Due Date (Mock: Created + 30 days)
                try:
                    created_dt = datetime.datetime.strptime(bill.created_date, "%Y-%m-%d")
                    due_dt = created_dt + datetime.timedelta(days=30)
                    due_date_str = due_dt.strftime("%Y-%m-%d")
                except:
                    due_date_str = "N/A"

                tree.insert('', 'end', values=(
                    bill.bill_id,
                    bill.patient_id,
                    patient_name,
                    bill.created_date,
                    f"MWK {bill.amount:,.2f}",
                    bill.status,
                    due_date_str
                ))
        
        # Initial Load
        update_summary()
        refresh_table()
        
    def show_reports(self):
        self.clear_content()
        
        # Header
        tk.Label(self.content_area, text="System Reports", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 5))
        tk.Label(self.content_area, text="In-depth analytics and summaries", font=('Helvetica', 10), bg=self.colors['bg'], fg='#666').pack(pady=(0, 20))
        
        # Notebook (Tabs)
        notebook = ttk.Notebook(self.content_area)
        notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create Tabs
        tab_overview = ttk.Frame(notebook)
        tab_patients = ttk.Frame(notebook)
        tab_appointments = ttk.Frame(notebook)
        tab_billing = ttk.Frame(notebook)
        tab_inventory = ttk.Frame(notebook)
        tab_doctors = ttk.Frame(notebook)
        tab_activity = ttk.Frame(notebook)
        
        notebook.add(tab_overview, text='Overview')
        notebook.add(tab_patients, text='Patients')
        notebook.add(tab_appointments, text='Appointments')
        notebook.add(tab_billing, text='Billing')
        notebook.add(tab_inventory, text='Inventory')
        notebook.add(tab_doctors, text='Doctors')
        notebook.add(tab_activity, text='Activity')
        
        # --- Overview Tab Content ---
        
        # Scrollable Frame for Overview (in case content is tall)
        # For simplicity, we'll just pack directly into tab_overview for now as per the image layout
        
        # Stats Cards Container
        cards_frame = tk.Frame(tab_overview)
        cards_frame.pack(fill='x', padx=20, pady=20)
        
        # Helper to create card
        def create_card(parent, title, value, col_idx):
            frame = tk.Frame(parent, bg='white', bd=1, relief='solid')
            frame.grid(row=0, column=col_idx, padx=10, sticky='nsew')
            
            tk.Label(frame, text=title, font=('Helvetica', 12, 'bold'), bg='white').pack(pady=(15, 5), padx=20)
            tk.Label(frame, text=str(value), font=('Helvetica', 24, 'bold'), fg=self.colors['accent'], bg='white').pack(pady=(0, 15))
            
        # Data
        counts = {
            "Patients": len(self.hms.patients),
            "Doctors": len(self.hms.doctors),
            "Appointments": len(self.hms.appointments),
            "Bills": len(self.hms.bills),
            "Inventory Items": len(self.hms.inventory)
        }
        
        # Layout cards
        for i, (key, val) in enumerate(counts.items()):
            create_card(cards_frame, key, val, i)
            cards_frame.grid_columnconfigure(i, weight=1)
            
        # Charts Section (Placeholders)
        charts_container = tk.Frame(tab_overview)
        charts_container.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Appointments per Day
        chart1 = tk.Frame(charts_container, bg='white', bd=1, relief='solid')
        chart1.pack(side='left', fill='both', expand=True, padx=(0, 10))
        tk.Label(chart1, text="Appointments per Day", font=('Helvetica', 12, 'bold'), bg='white').pack(pady=10)
        
        # Canvas for Chart 1 (Mockup)
        canvas1 = tk.Canvas(chart1, bg='white', highlightthickness=0)
        canvas1.pack(fill='both', expand=True, padx=10, pady=10)
        # Draw some dummy bars
        canvas1.create_line(20, 180, 280, 180, width=2) # X-axis
        canvas1.create_line(20, 180, 20, 20, width=2)   # Y-axis
        
        # Billing by Status
        chart2 = tk.Frame(charts_container, bg='white', bd=1, relief='solid')
        chart2.pack(side='left', fill='both', expand=True, padx=(10, 0))
        tk.Label(chart2, text="Billing by Status", font=('Helvetica', 12, 'bold'), bg='white').pack(pady=10)
        
        # Canvas for Chart 2 (Mockup)
        canvas2 = tk.Canvas(chart2, bg='white', highlightthickness=0)
        canvas2.pack(fill='both', expand=True, padx=10, pady=10)
        # Draw some dummy pie chart or bars
        canvas2.create_oval(80, 40, 220, 180, outline=self.colors['primary'], width=2)
        canvas2.create_text(150, 110, text="No Data", fill='#999')

        # Add "Under Construction" labels to other tabs
        for tab in [tab_patients, tab_appointments, tab_billing, tab_inventory, tab_doctors, tab_activity]:
             tk.Label(tab, text="Detailed Report View - Under Construction", font=('Helvetica', 14), fg='#666').pack(pady=50)

    def show_settings(self):
        self.clear_content()
        
        # Header
        tk.Label(self.content_area, text="System Settings", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 5))
        tk.Label(self.content_area, text="Configure application preferences below", font=('Helvetica', 10), bg=self.colors['bg'], fg='#666').pack(pady=(0, 20))
        
        # Settings Form Container
        # Using a canvas with scrollbar for the form in case it exceeds height
        container = tk.Frame(self.content_area, bg=self.colors['bg'])
        container.pack(fill='both', expand=True, padx=40)
        
        canvas = tk.Canvas(container, bg='white', bd=1, relief='solid')
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white', padx=20, pady=20)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=800) # Fixed width for form
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Grid Configuration
        scrollable_frame.grid_columnconfigure(1, weight=1)
        
        # Helper to add row
        self.row_idx = 0
        def add_row(label_text, widget_class, **kwargs):
            tk.Label(scrollable_frame, text=label_text + ":", font=('Helvetica', 11), bg='white', anchor='w').grid(row=self.row_idx, column=0, sticky='w', pady=10)
            
            if widget_class == ttk.Combobox:
                var = kwargs.pop('variable', None)
                values = kwargs.pop('values', [])
                widget = ttk.Combobox(scrollable_frame, textvariable=var, values=values, state='readonly', font=('Helvetica', 10))
                if var and not var.get() and values:
                    widget.set(values[0])
            elif widget_class == tk.Checkbutton:
                var = kwargs.pop('variable', None)
                widget = tk.Checkbutton(scrollable_frame, variable=var, bg='white', activebackground='white')
            elif widget_class == tk.Entry:
                var = kwargs.pop('variable', None)
                widget = tk.Entry(scrollable_frame, textvariable=var, font=('Helvetica', 10), bd=1, relief='solid')
            else:
                widget = widget_class(scrollable_frame, **kwargs)
            
            widget.grid(row=self.row_idx, column=1, sticky='w' if widget_class == tk.Checkbutton else 'ew', pady=10, padx=(20, 0))
            self.row_idx += 1
            return widget

        # Variables
        self.var_theme = tk.StringVar(value=self.hms.settings.get('theme', 'Light'))
        self.var_notif = tk.BooleanVar(value=self.hms.settings.get('notifications', True))
        self.var_backup = tk.BooleanVar(value=self.hms.settings.get('auto_backup', False))
        self.var_lang = tk.StringVar(value=self.hms.settings.get('language', 'English'))
        self.var_date_fmt = tk.StringVar(value=self.hms.settings.get('date_format', 'DD/MM/YYYY'))
        self.var_server = tk.StringVar(value=self.hms.settings.get('server_url', ''))
        
        # Supabase Vars
        self.var_sup_proj = tk.StringVar(value=self.hms.settings.get('supabase_project_id', ''))
        self.var_sup_url = tk.StringVar(value=self.hms.settings.get('supabase_url', ''))
        self.var_sup_key = tk.StringVar(value=self.hms.settings.get('supabase_api_key', ''))
        self.var_sup_role = tk.StringVar(value=self.hms.settings.get('supabase_service_role', ''))
        self.var_sup_bucket = tk.StringVar(value=self.hms.settings.get('supabase_bucket', 'hospital'))

        # --- Form Fields ---
        
        # Theme
        add_row("Theme", ttk.Combobox, variable=self.var_theme, values=['Light', 'Dark', 'System'])
        
        # Notifications
        add_row("Enable Notifications", tk.Checkbutton, variable=self.var_notif)
        
        # Auto Backup
        add_row("Enable Auto Backup", tk.Checkbutton, variable=self.var_backup)
        
        # Language
        add_row("Language", ttk.Combobox, variable=self.var_lang, values=['English', 'French', 'Spanish'])
        
        # Date Format
        add_row("Date Format", tk.Entry, variable=self.var_date_fmt)
        
        # Server URL
        add_row("Server URL", tk.Entry, variable=self.var_server)
        
        # Detected URLs (Custom row)
        tk.Label(scrollable_frame, text="Detected URLs:", font=('Helvetica', 11), bg='white', anchor='w').grid(row=self.row_idx, column=0, sticky='w', pady=10)
        
        detected_frame = tk.Frame(scrollable_frame, bg='white')
        detected_frame.grid(row=self.row_idx, column=1, sticky='ew', pady=10, padx=(20, 0))
        
        # Mock detected IP
        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            detected_ips = [f"http://{local_ip}:8000"]
        except:
            detected_ips = ["http://localhost:8000"]
            
        self.var_detected = tk.StringVar()
        combo_detected = ttk.Combobox(detected_frame, textvariable=self.var_detected, values=detected_ips, state='readonly', width=30)
        if detected_ips:
            combo_detected.current(0)
        combo_detected.pack(side='left', fill='x', expand=True)
        
        def use_detected():
            self.var_server.set(self.var_detected.get())
            
        tk.Button(detected_frame, text="Use Detected URL", command=use_detected, bg='#e0e0e0', bd=1, padx=10).pack(side='left', padx=(10, 0))
        self.row_idx += 1

        # Supabase Fields
        add_row("Supabase Project ID", tk.Entry, variable=self.var_sup_proj)
        add_row("Supabase URL", tk.Entry, variable=self.var_sup_url)
        add_row("Supabase API Key", tk.Entry, variable=self.var_sup_key)
        add_row("Supabase Service Role", tk.Entry, variable=self.var_sup_role)
        add_row("Supabase Bucket", tk.Entry, variable=self.var_sup_bucket)
        
        # Save Button
        def save_settings():
            self.hms.settings['theme'] = self.var_theme.get()
            self.hms.settings['notifications'] = self.var_notif.get()
            self.hms.settings['auto_backup'] = self.var_backup.get()
            self.hms.settings['language'] = self.var_lang.get()
            self.hms.settings['date_format'] = self.var_date_fmt.get()
            self.hms.settings['server_url'] = self.var_server.get()
            self.hms.settings['supabase_project_id'] = self.var_sup_proj.get()
            self.hms.settings['supabase_url'] = self.var_sup_url.get()
            self.hms.settings['supabase_api_key'] = self.var_sup_key.get()
            self.hms.settings['supabase_service_role'] = self.var_sup_role.get()
            self.hms.settings['supabase_bucket'] = self.var_sup_bucket.get()
            
            self.hms.save_data()
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        tk.Button(self.content_area, text="Save Settings", command=save_settings, bg=self.colors['primary'], fg='white', font=('Helvetica', 12, 'bold'), padx=20, pady=10).pack(pady=20)
        
    def show_files(self):
        self.clear_content()
        
        # Header
        tk.Label(self.content_area, text="Files", font=('Helvetica', 20, 'bold'), bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=(0, 20))
        
        # Action Buttons Toolbar
        toolbar = tk.Frame(self.content_area, bg=self.colors['bg'])
        toolbar.pack(fill='x', pady=(0, 20))
        
        def new_record_dialog():
            messagebox.showinfo("Info", "New Record Dialog - To be implemented")

        def attach_images_dialog():
            messagebox.showinfo("Info", "Attach Images Dialog - To be implemented")
            
        def attach_to_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a record to attach files to")
                return
            messagebox.showinfo("Info", "Attach to Selected - To be implemented")
            
        def update_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a record to update")
                return
            messagebox.showinfo("Info", "Update Selected - To be implemented")
            
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a record to delete")
                return
            if messagebox.askyesno("Confirm", "Are you sure you want to delete this record?"):
                messagebox.showinfo("Info", "Record deleted (Simulated)")

        # Button Styles
        btn_style_base = {'fg': 'white', 'font': ('Helvetica', 10, 'bold'), 'padx': 15, 'pady': 8, 'bd': 0}
        
        tk.Button(toolbar, text="New Record...", command=new_record_dialog, bg=self.colors['success'], **btn_style_base).pack(side='left', padx=(0, 10))
        tk.Button(toolbar, text="Attach Images...", command=attach_images_dialog, bg=self.colors['primary'], **btn_style_base).pack(side='left', padx=(0, 10))
        tk.Button(toolbar, text="Attach To Selected...", command=attach_to_selected, bg=self.colors['primary'], **btn_style_base).pack(side='left', padx=(0, 10))
        tk.Button(toolbar, text="Update Selected", command=update_selected, bg='#e0e0e0', fg='black', font=('Helvetica', 10), padx=15, pady=8, bd=1).pack(side='left', padx=(0, 10))
        tk.Button(toolbar, text="Delete Selected", command=delete_selected, bg=self.colors['danger'], **btn_style_base).pack(side='left')

        # Records Table
        columns = ('File ID', 'Date', 'Patient ID', 'Patient Name', 'Symptoms', 'Diagnosis', 'Treatment')
        tree = ttk.Treeview(self.content_area, columns=columns, show='headings', height=15)
        
        # Column Config
        tree.column('File ID', width=120)
        tree.column('Date', width=100)
        tree.column('Patient ID', width=100)
        tree.column('Patient Name', width=150)
        tree.column('Symptoms', width=150)
        tree.column('Diagnosis', width=150)
        tree.column('Treatment', width=150)
        
        for col in columns:
            tree.heading(col, text=col)
            
        tree.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        
        # Populate Table
        def refresh_table():
            for item in tree.get_children():
                tree.delete(item)
                
            for record in self.hms.medical_records:
                patient = self.hms.get_patient(record.patient_id)
                patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
                
                # Use record_id as File ID, ensure it looks similar to screenshot if needed
                file_id = record.record_id if record.record_id else "N/A"
                
                tree.insert('', 'end', values=(
                    file_id,
                    record.date,
                    record.patient_id,
                    patient_name,
                    record.consult_reason,
                    record.diagnosis,
                    record.treatment
                ))
        
        refresh_table()

        # Bottom Section (Supabase / Previous Uploads)
        bottom_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        bottom_frame.pack(fill='x', pady=20)
        
        tk.Label(bottom_frame, text="Previous Uploads (Supabase)", font=('Helvetica', 10, 'bold'), bg='#e0e0e0', anchor='w', padx=10, pady=5).pack(fill='x')
        
        controls_frame = tk.Frame(bottom_frame, bg='#f0f0f0', pady=10, padx=10)
        controls_frame.pack(fill='x')
        
        tk.Label(controls_frame, text="Filter by Patient:", bg='#f0f0f0').pack(side='left', padx=(0, 10))
        
        # Get list of patients for filter
        patient_options = ["All"] + [f"{p.first_name} {p.last_name} ({p.patient_id})" for p in self.hms.patients]
        filter_var = tk.StringVar(value="All")
        
        filter_combo = ttk.Combobox(controls_frame, textvariable=filter_var, values=patient_options, state='readonly', width=30)
        filter_combo.pack(side='left', padx=(0, 10))
        
        def refresh_remote():
            messagebox.showinfo("Info", "Refreshing remote files from Supabase...")
            
        tk.Button(controls_frame, text="Refresh Remote", command=refresh_remote, bg='#e0e0e0', bd=1, padx=10).pack(side='left')
