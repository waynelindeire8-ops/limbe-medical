# Limbe Medical Clinic - Hospital Management System

A comprehensive Python-based hospital management system designed for Limbe Medical Clinic to manage patients, appointments, doctors, medical records, billing, and inventory.

## Features

### Patient Management
- Register new patients
- Search patients by name or ID
- Update patient information
- View patient details and medical history
- List all patients

### Doctor Management
- Add new doctors
- View doctor details and specializations
- List all doctors
- Update doctor schedules
- Track doctor availability

### Appointment Management
- Schedule new appointments
- View patient appointments
- View doctor appointments by date
- Update appointment status (Scheduled, Confirmed, In Progress, Completed, Cancelled)
- Cancel appointments

### Medical Records (Coming Soon)
- Create and manage medical records
- View patient medical history
- Add diagnosis and treatment information
- Prescription management

### Billing & Payments (Coming Soon)
- Generate bills for appointments
- Track payment status
- View patient billing history
- Manage insurance information

### Inventory Management (Coming Soon)
- Track medical supplies and equipment
- Low stock alerts
- Supplier management
- Expiry date tracking

### Reports & Analytics (Coming Soon)
- Patient statistics
- Appointment analytics
- Revenue reports
- Inventory reports

## Installation

1. Ensure you have Python 3.7 or higher installed
2. No additional dependencies required - uses only Python standard library

## Usage

### Starting the System

1. Navigate to the project directory
2. Run the main interface:

```bash
python interface.py
```

### Main Menu Options

1. **Patient Management** - Manage all patient-related operations
2. **Doctor Management** - Manage doctor information and schedules
3. **Appointment Management** - Schedule and manage appointments
4. **Medical Records** - Access and manage medical records (Coming Soon)
5. **Billing & Payments** - Handle billing and payments (Coming Soon)
6. **Inventory Management** - Manage medical supplies (Coming Soon)
7. **Reports & Analytics** - Generate reports (Coming Soon)
8. **Exit** - Close the application

### Data Storage

The system automatically saves all data to a `hospital_data.json` file in the same directory. This file is created automatically when you first run the system and is updated whenever you make changes.

### Sample Usage Workflow

1. **First Time Setup:**
   - Add doctors to the system
   - Register patients
   - Schedule appointments

2. **Daily Operations:**
   - View scheduled appointments
   - Update appointment status as patients arrive
   - Add new patients as they register
   - Generate bills for completed appointments

3. **Data Management:**
   - Search for patient information
   - Update patient details
   - View doctor schedules
   - Check inventory levels

## System Architecture

### Core Classes

- `HospitalManagementSystem` - Main system class managing all operations
- `Patient` - Patient data model
- `Doctor` - Doctor data model
- `Appointment` - Appointment data model
- `MedicalRecord` - Medical record data model
- `Bill` - Billing data model
- `InventoryItem` - Inventory data model

### Key Methods

- Patient registration and search
- Appointment scheduling and management
- Doctor availability tracking
- Data persistence with JSON storage
- Comprehensive search functionality

## Error Handling

The system includes error handling for:
- Invalid user input
- Missing patient/doctor records
- Duplicate IDs
- File I/O operations

## Security Features

- Unique ID generation for all records
- Data validation
- Input sanitization
- Secure file storage

## Future Enhancements

- User authentication and role-based access
- Advanced reporting and analytics
- Integration with external systems
- Mobile app interface
- Advanced billing features
- Insurance management
- Laboratory integration
- Prescription management

## Support

For technical support or feature requests, please contact the development team.

## License

This system is developed exclusively for Limbe Medical Clinic.

---

**Version:** 1.0  
**Last Updated:** December 2024  
**Developer:** Hospital Management System Team