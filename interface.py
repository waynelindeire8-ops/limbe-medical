#!/usr/bin/env python3
"""
User Interface for Limbe Medical Clinic - Hospital Management System
Provides command-line interface for all system operations.
"""

import os
import sys
from datetime import datetime
from main import HospitalManagementSystem, Patient, Doctor, Appointment, MedicalRecord, Bill, InventoryItem

class HospitalInterface:
    def __init__(self):
        self.hms = HospitalManagementSystem()
        self.current_user = None
    
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display application header"""
        print("=" * 80)
        print("LIMBE MEDICAL CLINIC - HOSPITAL MANAGEMENT SYSTEM")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def display_main_menu(self):
        """Display main menu options"""
        print("\nMAIN MENU:")
        print("1. Patient Management")
        print("2. Doctor Management")
        print("3. Appointment Management")
        print("4. Medical Records")
        print("5. Billing & Payments")
        print("6. Inventory Management")
        print("7. Reports & Analytics")
        print("8. Exit")
        print("-" * 40)
    
    def get_user_choice(self, prompt: str, min_val: int, max_val: int) -> int:
        """Get validated user choice"""
        while True:
            try:
                choice = int(input(prompt))
                if min_val <= choice <= max_val:
                    return choice
                else:
                    print(f"Please enter a number between {min_val} and {max_val}")
            except ValueError:
                print("Please enter a valid number")
    
    def patient_management_menu(self):
        """Patient management submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nPATIENT MANAGEMENT:")
            print("1. Register New Patient")
            print("2. Search Patient")
            print("3. Update Patient Information")
            print("4. View Patient Details")
            print("5. List All Patients")
            print("6. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 6)
            
            if choice == 1:
                self.register_patient()
            elif choice == 2:
                self.search_patient()
            elif choice == 3:
                self.update_patient()
            elif choice == 4:
                self.view_patient_details()
            elif choice == 5:
                self.list_all_patients()
            elif choice == 6:
                break
            
            input("\nPress Enter to continue...")
    
    def register_patient(self):
        """Register a new patient"""
        print("\nREGISTER NEW PATIENT")
        print("-" * 30)
        
        patient_id = self.hms.generate_id("PAT")
        first_name = input("First Name: ").strip()
        last_name = input("Last Name: ").strip()
        date_of_birth = input("Date of Birth (YYYY-MM-DD): ").strip()
        gender = input("Gender (M/F/O): ").strip().upper()
        phone = input("Phone Number: ").strip()
        email = input("Email: ").strip()
        address = input("Address: ").strip()
        emergency_contact = input("Emergency Contact: ").strip()
        medical_history = input("Medical History (if any): ").strip()
        
        patient = Patient(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            phone=phone,
            email=email,
            address=address,
            emergency_contact=emergency_contact,
            medical_history=medical_history,
            created_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        if self.hms.add_patient(patient):
            print(f"\nPatient registered successfully!")
            print(f"Patient ID: {patient_id}")
        else:
            print("\nError registering patient!")
    
    def search_patient(self):
        """Search for patients"""
        print("\nSEARCH PATIENT")
        print("-" * 20)
        search_term = input("Enter patient name or ID: ").strip()
        
        results = self.hms.search_patients(search_term)
        
        if results:
            print(f"\nFound {len(results)} patient(s):")
            print("-" * 80)
            print(f"{'ID':<12} {'Name':<20} {'Phone':<15} {'Email':<25}")
            print("-" * 80)
            for patient in results:
                print(f"{patient.patient_id:<12} {patient.first_name} {patient.last_name:<19} "
                      f"{patient.phone:<15} {patient.email:<25}")
        else:
            print("No patients found matching your search.")
    
    def update_patient(self):
        """Update patient information"""
        print("\nUPDATE PATIENT INFORMATION")
        print("-" * 35)
        patient_id = input("Enter Patient ID: ").strip()
        
        patient = self.hms.get_patient(patient_id)
        if not patient:
            print("Patient not found!")
            return
        
        print(f"\nCurrent Information for {patient.first_name} {patient.last_name}:")
        print(f"Phone: {patient.phone}")
        print(f"Email: {patient.email}")
        print(f"Address: {patient.address}")
        print(f"Emergency Contact: {patient.emergency_contact}")
        
        print("\nEnter new information (leave blank to keep current):")
        phone = input(f"Phone ({patient.phone}): ").strip() or patient.phone
        email = input(f"Email ({patient.email}): ").strip() or patient.email
        address = input(f"Address ({patient.address}): ").strip() or patient.address
        emergency_contact = input(f"Emergency Contact ({patient.emergency_contact}): ").strip() or patient.emergency_contact
        
        if self.hms.update_patient(patient_id, phone=phone, email=email, 
                                   address=address, emergency_contact=emergency_contact):
            print("Patient information updated successfully!")
        else:
            print("Error updating patient information!")
    
    def view_patient_details(self):
        """View detailed patient information"""
        print("\nVIEW PATIENT DETAILS")
        print("-" * 25)
        patient_id = input("Enter Patient ID: ").strip()
        
        patient = self.hms.get_patient(patient_id)
        if not patient:
            print("Patient not found!")
            return
        
        print(f"\nPatient Details:")
        print("-" * 40)
        print(f"Patient ID: {patient.patient_id}")
        print(f"Name: {patient.first_name} {patient.last_name}")
        print(f"Date of Birth: {patient.date_of_birth}")
        print(f"Gender: {patient.gender}")
        print(f"Phone: {patient.phone}")
        print(f"Email: {patient.email}")
        print(f"Address: {patient.address}")
        print(f"Emergency Contact: {patient.emergency_contact}")
        print(f"Medical History: {patient.medical_history}")
        print(f"Registration Date: {patient.created_date}")
    
    def list_all_patients(self):
        """List all patients"""
        print("\nALL PATIENTS")
        print("-" * 15)
        
        if not self.hms.patients:
            print("No patients registered yet.")
            return
        
        print("-" * 80)
        print(f"{'ID':<12} {'Name':<20} {'DOB':<12} {'Phone':<15} {'Email':<25}")
        print("-" * 80)
        
        for patient in self.hms.patients:
            print(f"{patient.patient_id:<12} {patient.first_name} {patient.last_name:<19} "
                  f"{patient.date_of_birth:<12} {patient.phone:<15} {patient.email:<25}")
    
    def doctor_management_menu(self):
        """Doctor management submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nDOCTOR MANAGEMENT:")
            print("1. Add New Doctor")
            print("2. View Doctor Details")
            print("3. List All Doctors")
            print("4. Update Doctor Schedule")
            print("5. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 5)
            
            if choice == 1:
                self.add_doctor()
            elif choice == 2:
                self.view_doctor_details()
            elif choice == 3:
                self.list_all_doctors()
            elif choice == 4:
                self.update_doctor_schedule()
            elif choice == 5:
                break
            
            input("\nPress Enter to continue...")
    
    def add_doctor(self):
        """Add a new doctor"""
        print("\nADD NEW DOCTOR")
        print("-" * 20)
        
        doctor_id = self.hms.generate_id("DOC")
        first_name = input("First Name: ").strip()
        last_name = input("Last Name: ").strip()
        specialization = input("Specialization: ").strip()
        phone = input("Phone Number: ").strip()
        email = input("Email: ").strip()
        schedule = input("Working Schedule: ").strip()
        status = "Available"
        
        doctor = Doctor(
            doctor_id=doctor_id,
            first_name=first_name,
            last_name=last_name,
            specialization=specialization,
            phone=phone,
            email=email,
            schedule=schedule,
            status=status
        )
        
        if self.hms.add_doctor(doctor):
            print(f"\nDoctor added successfully!")
            print(f"Doctor ID: {doctor_id}")
        else:
            print("\nError adding doctor!")
    
    def view_doctor_details(self):
        """View doctor details"""
        print("\nVIEW DOCTOR DETAILS")
        print("-" * 25)
        doctor_id = input("Enter Doctor ID: ").strip()
        
        doctor = self.hms.get_doctor(doctor_id)
        if not doctor:
            print("Doctor not found!")
            return
        
        print(f"\nDoctor Details:")
        print("-" * 40)
        print(f"Doctor ID: {doctor.doctor_id}")
        print(f"Name: {doctor.first_name} {doctor.last_name}")
        print(f"Specialization: {doctor.specialization}")
        print(f"Phone: {doctor.phone}")
        print(f"Email: {doctor.email}")
        print(f"Schedule: {doctor.schedule}")
        print(f"Status: {doctor.status}")
    
    def list_all_doctors(self):
        """List all doctors"""
        print("\nALL DOCTORS")
        print("-" * 15)
        
        if not self.hms.doctors:
            print("No doctors registered yet.")
            return
        
        print("-" * 80)
        print(f"{'ID':<12} {'Name':<20} {'Specialization':<20} {'Phone':<15} {'Status':<10}")
        print("-" * 80)
        
        for doctor in self.hms.doctors:
            print(f"{doctor.doctor_id:<12} {doctor.first_name} {doctor.last_name:<19} "
                  f"{doctor.specialization:<20} {doctor.phone:<15} {doctor.status:<10}")
    
    def update_doctor_schedule(self):
        """Update doctor schedule"""
        print("\nUPDATE DOCTOR SCHEDULE")
        print("-" * 30)
        doctor_id = input("Enter Doctor ID: ").strip()
        
        doctor = self.hms.get_doctor(doctor_id)
        if not doctor:
            print("Doctor not found!")
            return
        
        print(f"\nCurrent Schedule: {doctor.schedule}")
        new_schedule = input("Enter new schedule: ").strip()
        
        if self.hms.update_patient(doctor_id, schedule=new_schedule):
            print("Doctor schedule updated successfully!")
        else:
            print("Error updating doctor schedule!")
    
    def appointment_management_menu(self):
        """Appointment management submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nAPPOINTMENT MANAGEMENT:")
            print("1. Schedule New Appointment")
            print("2. View Patient Appointments")
            print("3. View Doctor Appointments")
            print("4. Update Appointment Status")
            print("5. Cancel Appointment")
            print("6. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 6)
            
            if choice == 1:
                self.schedule_appointment()
            elif choice == 2:
                self.view_patient_appointments()
            elif choice == 3:
                self.view_doctor_appointments()
            elif choice == 4:
                self.update_appointment_status()
            elif choice == 5:
                self.cancel_appointment()
            elif choice == 6:
                break
            
            input("\nPress Enter to continue...")
    
    def schedule_appointment(self):
        """Schedule a new appointment"""
        print("\nSCHEDULE NEW APPOINTMENT")
        print("-" * 30)
        
        patient_id = input("Patient ID: ").strip()
        if not self.hms.get_patient(patient_id):
            print("Patient not found!")
            return
        
        # Show available doctors
        available_doctors = self.hms.get_available_doctors()
        if not available_doctors:
            print("No available doctors!")
            return
        
        print("\nAvailable Doctors:")
        for doctor in available_doctors:
            print(f"{doctor.doctor_id}: {doctor.first_name} {doctor.last_name} - {doctor.specialization}")
        
        doctor_id = input("Doctor ID: ").strip()
        if not self.hms.get_doctor(doctor_id):
            print("Doctor not found!")
            return
        
        appointment_date = input("Appointment Date (YYYY-MM-DD): ").strip()
        appointment_time = input("Appointment Time (HH:MM): ").strip()
        reason = input("Reason for appointment: ").strip()
        
        appointment = Appointment(
            appointment_id=self.hms.generate_id("APT"),
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status="Scheduled",
            notes=""
        )
        
        if self.hms.schedule_appointment(appointment):
            print(f"\nAppointment scheduled successfully!")
            print(f"Appointment ID: {appointment.appointment_id}")
        else:
            print("\nError scheduling appointment!")
    
    def view_patient_appointments(self):
        """View patient appointments"""
        print("\nVIEW PATIENT APPOINTMENTS")
        print("-" * 30)
        patient_id = input("Patient ID: ").strip()
        
        patient = self.hms.get_patient(patient_id)
        if not patient:
            print("Patient not found!")
            return
        
        appointments = self.hms.get_patient_appointments(patient_id)
        if not appointments:
            print("No appointments found for this patient.")
            return
        
        print(f"\nAppointments for {patient.first_name} {patient.last_name}:")
        print("-" * 80)
        print(f"{'ID':<12} {'Date':<12} {'Time':<8} {'Doctor':<20} {'Status':<12} {'Reason':<20}")
        print("-" * 80)
        
        for apt in appointments:
            doctor = self.hms.get_doctor(apt.doctor_id)
            doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor else "Unknown"
            print(f"{apt.appointment_id:<12} {apt.appointment_date:<12} {apt.appointment_time:<8} "
                  f"{doctor_name:<20} {apt.status:<12} {apt.reason:<20}")
    
    def view_doctor_appointments(self):
        """View doctor appointments"""
        print("\nVIEW DOCTOR APPOINTMENTS")
        print("-" * 30)
        doctor_id = input("Doctor ID: ").strip()
        appointment_date = input("Date (YYYY-MM-DD): ").strip()
        
        doctor = self.hms.get_doctor(doctor_id)
        if not doctor:
            print("Doctor not found!")
            return
        
        appointments = self.hms.get_doctor_appointments(doctor_id, appointment_date)
        if not appointments:
            print(f"No appointments found for Dr. {doctor.last_name} on {appointment_date}.")
            return
        
        print(f"\nAppointments for Dr. {doctor.first_name} {doctor.last_name} on {appointment_date}:")
        print("-" * 80)
        print(f"{'ID':<12} {'Time':<8} {'Patient':<20} {'Status':<12} {'Reason':<20}")
        print("-" * 80)
        
        for apt in appointments:
            patient = self.hms.get_patient(apt.patient_id)
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
            print(f"{apt.appointment_id:<12} {apt.appointment_time:<8} {patient_name:<20} "
                  f"{apt.status:<12} {apt.reason:<20}")
    
    def update_appointment_status(self):
        """Update appointment status"""
        print("\nUPDATE APPOINTMENT STATUS")
        print("-" * 35)
        appointment_id = input("Appointment ID: ").strip()
        
        print("\nStatus options:")
        print("1. Scheduled")
        print("2. Confirmed")
        print("3. In Progress")
        print("4. Completed")
        print("5. Cancelled")
        
        status_choice = self.get_user_choice("Select new status: ", 1, 5)
        status_map = {1: "Scheduled", 2: "Confirmed", 3: "In Progress", 
                     4: "Completed", 5: "Cancelled"}
        
        if self.hms.update_appointment_status(appointment_id, status_map[status_choice]):
            print("Appointment status updated successfully!")
        else:
            print("Error updating appointment status!")
    
    def cancel_appointment(self):
        """Cancel appointment"""
        print("\nCANCEL APPOINTMENT")
        print("-" * 25)
        appointment_id = input("Appointment ID: ").strip()
        
        if self.hms.update_appointment_status(appointment_id, "Cancelled"):
            print("Appointment cancelled successfully!")
        else:
            print("Error cancelling appointment!")
    
    def medical_records_menu(self):
        """Medical records submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nMEDICAL RECORDS:")
            print("1. Create Medical Record")
            print("2. View Patient Medical Records")
            print("3. Update Medical Record")
            print("4. Search Medical Records")
            print("5. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 5)
            
            if choice == 1:
                self.create_medical_record()
            elif choice == 2:
                self.view_patient_medical_records()
            elif choice == 3:
                self.update_medical_record()
            elif choice == 4:
                self.search_medical_records()
            elif choice == 5:
                break
            
            input("\nPress Enter to continue...")
    
    def create_medical_record(self):
        """Create a new medical record"""
        print("\nCREATE MEDICAL RECORD")
        print("-" * 30)
        
        patient_id = input("Patient ID: ").strip()
        if not self.hms.get_patient(patient_id):
            print("Patient not found!")
            return
        
        # Show available doctors
        available_doctors = self.hms.get_available_doctors()
        if not available_doctors:
            print("No available doctors!")
            return
        
        print("\nAvailable Doctors:")
        for doctor in available_doctors:
            print(f"{doctor.doctor_id}: {doctor.first_name} {doctor.last_name} - {doctor.specialization}")
        
        doctor_id = input("Doctor ID: ").strip()
        if not self.hms.get_doctor(doctor_id):
            print("Doctor not found!")
            return
        
        visit_date = input("Visit Date (YYYY-MM-DD): ").strip()
        diagnosis = input("Diagnosis: ").strip()
        treatment = input("Treatment: ").strip()
        prescriptions = input("Prescriptions: ").strip()
        notes = input("Additional Notes: ").strip()
        
        medical_record = MedicalRecord(
            record_id=self.hms.generate_id("REC"),
            patient_id=patient_id,
            doctor_id=doctor_id,
            visit_date=visit_date,
            diagnosis=diagnosis,
            treatment=treatment,
            prescriptions=prescriptions,
            notes=notes
        )
        
        if self.hms.add_medical_record(medical_record):
            print(f"\nMedical record created successfully!")
            print(f"Record ID: {medical_record.record_id}")
        else:
            print("\nError creating medical record!")
    
    def view_patient_medical_records(self):
        """View patient medical records"""
        print("\nVIEW PATIENT MEDICAL RECORDS")
        print("-" * 35)
        patient_id = input("Patient ID: ").strip()
        
        patient = self.hms.get_patient(patient_id)
        if not patient:
            print("Patient not found!")
            return
        
        records = self.hms.get_patient_medical_records(patient_id)
        if not records:
            print("No medical records found for this patient.")
            return
        
        print(f"\nMedical Records for {patient.first_name} {patient.last_name}:")
        print("-" * 80)
        print(f"{'Record ID':<12} {'Date':<12} {'Doctor':<20} {'Diagnosis':<25}")
        print("-" * 80)
        
        for record in records:
            doctor = self.hms.get_doctor(record.doctor_id)
            doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor else "Unknown"
            print(f"{record.record_id:<12} {record.visit_date:<12} {doctor_name:<20} {record.diagnosis:<25}")
        
        # Show detailed view option
        record_id = input("\nEnter Record ID for detailed view (or press Enter to skip): ").strip()
        if record_id:
            self.view_detailed_medical_record(record_id)
    
    def view_detailed_medical_record(self, record_id: str):
        """View detailed medical record"""
        for record in self.hms.medical_records:
            if record.record_id == record_id:
                patient = self.hms.get_patient(record.patient_id)
                doctor = self.hms.get_doctor(record.doctor_id)
                
                print(f"\nDetailed Medical Record:")
                print("-" * 50)
                print(f"Record ID: {record.record_id}")
                print(f"Patient: {patient.first_name} {patient.last_name}")
                print(f"Doctor: {doctor.first_name} {doctor.last_name}")
                print(f"Visit Date: {record.visit_date}")
                print(f"Diagnosis: {record.diagnosis}")
                print(f"Treatment: {record.treatment}")
                print(f"Prescriptions: {record.prescriptions}")
                print(f"Notes: {record.notes}")
                return
        
        print("Medical record not found!")
    
    def update_medical_record(self):
        """Update medical record"""
        print("\nUPDATE MEDICAL RECORD")
        print("-" * 30)
        record_id = input("Record ID: ").strip()
        
        # Find the record
        record = None
        for r in self.hms.medical_records:
            if r.record_id == record_id:
                record = r
                break
        
        if not record:
            print("Medical record not found!")
            return
        
        print(f"\nCurrent Information:")
        print(f"Diagnosis: {record.diagnosis}")
        print(f"Treatment: {record.treatment}")
        print(f"Prescriptions: {record.prescriptions}")
        print(f"Notes: {record.notes}")
        
        print("\nEnter new information (leave blank to keep current):")
        diagnosis = input(f"Diagnosis ({record.diagnosis}): ").strip() or record.diagnosis
        treatment = input(f"Treatment ({record.treatment}): ").strip() or record.treatment
        prescriptions = input(f"Prescriptions ({record.prescriptions}): ").strip() or record.prescriptions
        notes = input(f"Notes ({record.notes}): ").strip() or record.notes
        
        # Update the record
        record.diagnosis = diagnosis
        record.treatment = treatment
        record.prescriptions = prescriptions
        record.notes = notes
        
        self.hms.save_data()
        print("Medical record updated successfully!")
    
    def search_medical_records(self):
        """Search medical records"""
        print("\nSEARCH MEDICAL RECORDS")
        print("-" * 30)
        search_term = input("Enter patient name, doctor name, or diagnosis: ").strip().lower()
        
        results = []
        for record in self.hms.medical_records:
            patient = self.hms.get_patient(record.patient_id)
            doctor = self.hms.get_doctor(record.doctor_id)
            
            if (search_term in record.diagnosis.lower() or
                search_term in patient.first_name.lower() or
                search_term in patient.last_name.lower() or
                search_term in doctor.first_name.lower() or
                search_term in doctor.last_name.lower()):
                results.append(record)
        
        if results:
            print(f"\nFound {len(results)} medical record(s):")
            print("-" * 80)
            print(f"{'Record ID':<12} {'Date':<12} {'Patient':<20} {'Doctor':<20} {'Diagnosis':<25}")
            print("-" * 80)
            
            for record in results:
                patient = self.hms.get_patient(record.patient_id)
                doctor = self.hms.get_doctor(record.doctor_id)
                print(f"{record.record_id:<12} {record.visit_date:<12} "
                      f"{patient.first_name} {patient.last_name:<19} "
                      f"{doctor.first_name} {doctor.last_name:<19} {record.diagnosis:<25}")
        else:
            print("No medical records found matching your search.")
    
    def billing_menu(self):
        """Billing and payments submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nBILLING & PAYMENTS:")
            print("1. Create Bill")
            print("2. View Patient Bills")
            print("3. Update Payment Status")
            print("4. Generate Payment Report")
            print("5. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 5)
            
            if choice == 1:
                self.create_bill()
            elif choice == 2:
                self.view_patient_bills()
            elif choice == 3:
                self.update_payment_status()
            elif choice == 4:
                self.generate_payment_report()
            elif choice == 5:
                break
            
            input("\nPress Enter to continue...")
    
    def create_bill(self):
        """Create a new bill"""
        print("\nCREATE BILL")
        print("-" * 15)
        
        patient_id = input("Patient ID: ").strip()
        if not self.hms.get_patient(patient_id):
            print("Patient not found!")
            return
        
        # Show patient's appointments
        appointments = self.hms.get_patient_appointments(patient_id)
        if not appointments:
            print("No appointments found for this patient.")
            return
        
        print("\nPatient Appointments:")
        print("-" * 80)
        print(f"{'Appointment ID':<15} {'Date':<12} {'Doctor':<20} {'Status':<12} {'Reason':<20}")
        print("-" * 80)
        
        for apt in appointments:
            if apt.status == "Completed":
                doctor = self.hms.get_doctor(apt.doctor_id)
                doctor_name = f"{doctor.first_name} {doctor.last_name}" if doctor else "Unknown"
                print(f"{apt.appointment_id:<15} {apt.appointment_date:<12} {doctor_name:<20} "
                      f"{apt.status:<12} {apt.reason:<20}")
        
        appointment_id = input("\nAppointment ID for billing: ").strip()
        
        # Verify appointment exists and is completed
        appointment = None
        for apt in appointments:
            if apt.appointment_id == appointment_id and apt.status == "Completed":
                appointment = apt
                break
        
        if not appointment:
            print("Invalid appointment ID or appointment not completed!")
            return
        
        print("\nServices provided:")
        services = []
        while True:
            service = input("Enter service (or 'done' to finish): ").strip()
            if service.lower() == 'done':
                break
            services.append(service)
        
        try:
            amount = float(input("Total Amount: "))
        except ValueError:
            print("Invalid amount!")
            return
        
        bill = Bill(
            bill_id=self.hms.generate_id("BILL"),
            patient_id=patient_id,
            appointment_id=appointment_id,
            amount=amount,
            services=", ".join(services),
            status="Pending",
            created_date=datetime.now().strftime('%Y-%m-%d'),
            created_at=datetime.now().isoformat()
        )
        
        if self.hms.create_bill(bill):
            print(f"\nBill created successfully!")
            print(f"Bill ID: {bill.bill_id}")
            print(f"Amount: ${amount:.2f}")
        else:
            print("\nError creating bill!")
    
    def view_patient_bills(self):
        """View patient bills"""
        print("\nVIEW PATIENT BILLS")
        print("-" * 25)
        patient_id = input("Patient ID: ").strip()
        
        patient = self.hms.get_patient(patient_id)
        if not patient:
            print("Patient not found!")
            return
        
        bills = self.hms.get_patient_bills(patient_id)
        if not bills:
            print("No bills found for this patient.")
            return
        
        print(f"\nBills for {patient.first_name} {patient.last_name}:")
        print("-" * 90)
        print(f"{'Bill ID':<12} {'Date':<12} {'Services':<30} {'Amount':<10} {'Status':<12}")
        print("-" * 90)
        
        total_amount = 0
        for bill in bills:
            print(f"{bill.bill_id:<12} {bill.created_date:<12} {bill.services:<30} "
                  f"${bill.amount:<9.2f} {bill.status:<12}")
            total_amount += bill.amount
        
        print("-" * 90)
        print(f"Total Amount: ${total_amount:.2f}")
    
    def update_payment_status(self):
        """Update payment status"""
        print("\nUPDATE PAYMENT STATUS")
        print("-" * 30)
        bill_id = input("Bill ID: ").strip()
        
        print("\nPayment Status Options:")
        print("1. Pending")
        print("2. Paid")
        print("3. Partially Paid")
        print("4. Cancelled")
        
        status_choice = self.get_user_choice("Select payment status: ", 1, 4)
        status_map = {1: "Pending", 2: "Paid", 3: "Partially Paid", 4: "Cancelled"}
        
        if self.hms.update_bill_status(bill_id, status_map[status_choice]):
            print("Payment status updated successfully!")
        else:
            print("Error updating payment status!")
    
    def generate_payment_report(self):
        """Generate payment report"""
        print("\nPAYMENT REPORT")
        print("-" * 20)
        
        print("\nReport Options:")
        print("1. All Bills")
        print("2. Pending Payments")
        print("3. Paid Bills")
        print("4. Date Range Report")
        
        choice = self.get_user_choice("Select report type: ", 1, 4)
        
        if choice == 1:
            bills = self.hms.bills
            title = "All Bills"
        elif choice == 2:
            bills = [b for b in self.hms.bills if b.status == "Pending"]
            title = "Pending Payments"
        elif choice == 3:
            bills = [b for b in self.hms.bills if b.status == "Paid"]
            title = "Paid Bills"
        elif choice == 4:
            start_date = input("Start Date (YYYY-MM-DD): ").strip()
            end_date = input("End Date (YYYY-MM-DD): ").strip()
            bills = [b for b in self.hms.bills if start_date <= b.created_date <= end_date]
            title = f"Bills from {start_date} to {end_date}"
        
        if not bills:
            print(f"No bills found for {title}.")
            return
        
        print(f"\n{title} Report:")
        print("-" * 90)
        print(f"{'Bill ID':<12} {'Patient ID':<12} {'Date':<12} {'Amount':<10} {'Status':<12}")
        print("-" * 90)
        
        total_amount = 0
        pending_amount = 0
        paid_amount = 0
        
        for bill in bills:
            patient = self.hms.get_patient(bill.patient_id)
            patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
            print(f"{bill.bill_id:<12} {patient_name:<12} {bill.created_date:<12} "
                  f"${bill.amount:<9.2f} {bill.status:<12}")
            
            total_amount += bill.amount
            if bill.status == "Pending":
                pending_amount += bill.amount
            elif bill.status == "Paid":
                paid_amount += bill.amount
        
        print("-" * 90)
        print(f"Total Amount: ${total_amount:.2f}")
        print(f"Pending Amount: ${pending_amount:.2f}")
        print(f"Paid Amount: ${paid_amount:.2f}")
    
    def inventory_menu(self):
        """Inventory management submenu"""
        while True:
            self.clear_screen()
            self.display_header()
            print("\nINVENTORY MANAGEMENT:")
            print("1. Add New Item")
            print("2. View All Items")
            print("3. Update Item Quantity")
            print("4. Check Low Stock Items")
            print("5. Search Items")
            print("6. Back to Main Menu")
            print("-" * 40)
            
            choice = self.get_user_choice("Enter your choice: ", 1, 6)
            
            if choice == 1:
                self.add_inventory_item()
            elif choice == 2:
                self.view_all_inventory()
            elif choice == 3:
                self.update_item_quantity()
            elif choice == 4:
                self.check_low_stock()
            elif choice == 5:
                self.search_inventory()
            elif choice == 6:
                break
            
            input("\nPress Enter to continue...")
    
    def add_inventory_item(self):
        """Add new inventory item"""
        print("\nADD NEW INVENTORY ITEM")
        print("-" * 30)
        
        item_id = self.hms.generate_id("INV")
        name = input("Item Name: ").strip()
        category = input("Category (Medicine/Equipment/Supply): ").strip()
        
        try:
            quantity = int(input("Quantity: "))
            unit_price = float(input("Unit Price: "))
            min_quantity = int(input("Minimum Quantity Alert: "))
        except ValueError:
            print("Invalid number input!")
            return
        
        supplier = input("Supplier: ").strip()
        expiry_date = input("Expiry Date (YYYY-MM-DD, optional): ").strip()
        
        inventory_item = InventoryItem(
            item_id=item_id,
            name=name,
            category=category,
            quantity=quantity,
            unit_price=unit_price,
            supplier=supplier,
            expiry_date=expiry_date or "N/A",
            min_quantity=min_quantity
        )
        
        if self.hms.add_inventory_item(inventory_item):
            print(f"\nInventory item added successfully!")
            print(f"Item ID: {item_id}")
        else:
            print("\nError adding inventory item!")
    
    def view_all_inventory(self):
        """View all inventory items"""
        print("\nALL INVENTORY ITEMS")
        print("-" * 25)
        
        if not self.hms.inventory:
            print("No inventory items found.")
            return
        
        print("-" * 100)
        print(f"{'ID':<12} {'Name':<25} {'Category':<15} {'Qty':<8} {'Price':<10} {'Supplier':<20} {'Expiry':<12}")
        print("-" * 100)
        
        for item in self.hms.inventory:
            print(f"{item.item_id:<12} {item.name:<25} {item.category:<15} {item.quantity:<8} "
                  f"${item.unit_price:<9.2f} {item.supplier:<20} {item.expiry_date:<12}")
    
    def update_item_quantity(self):
        """Update item quantity"""
        print("\nUPDATE ITEM QUANTITY")
        print("-" * 25)
        item_id = input("Item ID: ").strip()
        
        # Find the item
        item = None
        for inv_item in self.hms.inventory:
            if inv_item.item_id == item_id:
                item = inv_item
                break
        
        if not item:
            print("Item not found!")
            return
        
        print(f"\nCurrent Information:")
        print(f"Name: {item.name}")
        print(f"Current Quantity: {item.quantity}")
        print(f"Minimum Quantity: {item.min_quantity}")
        
        try:
            new_quantity = int(input("New Quantity: "))
        except ValueError:
            print("Invalid quantity!")
            return
        
        if self.hms.update_inventory_quantity(item_id, new_quantity):
            print("Item quantity updated successfully!")
            
            # Check if quantity is low
            if new_quantity <= item.min_quantity:
                print(f"WARNING: Quantity is at or below minimum level ({item.min_quantity})!")
        else:
            print("Error updating item quantity!")
    
    def check_low_stock(self):
        """Check for low stock items"""
        print("\nLOW STOCK ALERTS")
        print("-" * 20)
        
        low_stock_items = self.hms.get_low_stock_items()
        
        if not low_stock_items:
            print("No items with low stock.")
            return
        
        print(f"\nFound {len(low_stock_items)} item(s) with low stock:")
        print("-" * 90)
        print(f"{'ID':<12} {'Name':<25} {'Current Qty':<12} {'Min Qty':<10} {'Status':<15}")
        print("-" * 90)
        
        for item in low_stock_items:
            status = "CRITICAL" if item.quantity == 0 else "LOW"
            print(f"{item.item_id:<12} {item.name:<25} {item.quantity:<12} {item.min_quantity:<10} {status:<15}")
    
    def search_inventory(self):
        """Search inventory items"""
        print("\nSEARCH INVENTORY ITEMS")
        print("-" * 30)
        search_term = input("Enter item name, category, or supplier: ").strip().lower()
        
        results = []
        for item in self.hms.inventory:
            if (search_term in item.name.lower() or
                search_term in item.category.lower() or
                search_term in item.supplier.lower()):
                results.append(item)
        
        if results:
            print(f"\nFound {len(results)} item(s):")
            print("-" * 100)
            print(f"{'ID':<12} {'Name':<25} {'Category':<15} {'Qty':<8} {'Price':<10} {'Supplier':<20}")
            print("-" * 100)
            
            for item in results:
                print(f"{item.item_id:<12} {item.name:<25} {item.category:<15} {item.quantity:<8} "
                      f"${item.unit_price:<9.2f} {item.supplier:<20}")
        else:
            print("No inventory items found matching your search.")
    
    def run(self):
        """Main interface loop"""
        while True:
            self.clear_screen()
            self.display_header()
            self.display_main_menu()
            
            choice = self.get_user_choice("Enter your choice: ", 1, 8)
            
            if choice == 1:
                self.patient_management_menu()
            elif choice == 2:
                self.doctor_management_menu()
            elif choice == 3:
                self.appointment_management_menu()
            elif choice == 4:
                self.medical_records_menu()
            elif choice == 5:
                self.billing_menu()
            elif choice == 6:
                self.inventory_menu()
            elif choice == 7:
                print("\nReports & Analytics - Coming Soon!")
                input("\nPress Enter to continue...")
            elif choice == 8:
                print("\nThank you for using Limbe Medical Clinic HMS!")
                print("Goodbye!")
                break

if __name__ == "__main__":
    interface = HospitalInterface()
    interface.run()