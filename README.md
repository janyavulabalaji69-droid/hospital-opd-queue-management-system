
# Hospital OPD Token and Queue Management System

## Project Overview

The Hospital OPD Token and Queue Management System is a Python-based web application developed using Flask and SQLite.

The main purpose of this project is to simplify the outpatient department (OPD) process in hospitals by managing patient registration, token generation, doctor availability and patient queues.

It helps reduce waiting time and makes the patient queue management process more organized and efficient.

## Problem Statement

In many hospitals, OPD queue management is handled manually. This can cause long waiting times, confusion in patient order and difficulty in handling emergency cases.

This project provides a computerized solution for managing patient tokens and queues efficiently.

## Objectives

- To register patients and generate tokens.
- To maintain separate queues for different doctors.
- To give priority to emergency patients.
- To calculate estimated patient waiting time.
- To manage doctor availability.
- To reassign waiting patients when a doctor becomes unavailable.
- To display the live patient queue.

## Technologies Used

- **Programming Language:** Python
- **Backend Framework:** Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS
- **Development Tool:** Visual Studio Code
- **Version Control:** Git and GitHub

## Main Features

### 1. Patient Registration
Reception staff can enter patient details such as name, age and phone number.

### 2. Token Generation
A unique token number is generated for each patient based on the selected doctor.

### 3. Emergency Patient Priority
Emergency patients are given higher priority than normal patients without changing their original token numbers.

### 4. Doctor Dashboard
Doctors can view their waiting patients and manage consultations.

### 5. Live Queue Display
Displays the current patient and waiting patients for the selected doctor.

### 6. Waiting Time Estimation
The system estimates waiting time based on an average consultation duration of 10 minutes per patient.

### 7. Doctor Availability Management
Doctor availability can be changed through the application.

### 8. Patient Reassignment
Waiting patients can be reassigned to another available doctor if their original doctor becomes unavailable.

## Project Modules

1. Reception Module
2. Patient Registration Module
3. Token Generation Module
4. Doctor Dashboard Module
5. Queue Management Module
6. Live Queue Display Module
7. Doctor Availability Module
8. Patient Reassignment Module

## Project Folder Structure

```text
OPD PROJECT/
│
├── app.py
├── database.py
├── hospital.db
│
├── templates/
│   ├── index.html
│   ├── reception.html
│   ├── doctor_dashboard.html
│   └── live_display.html
│
├── static/
│   └── css/
│       └── style.css
│
└── README.md
```

## Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/janyavulabalaji69-droid/hospital-opd-queue-management-system.git
```

### Step 2: Open the Project Folder

```bash
cd hospital-opd-queue-management-system
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 4: Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### Step 5: Install Required Packages

```bash
pip install Flask flask-cors
```

### Step 6: Run the Application

```bash
python app.py
```

### Step 7: Open in Browser

```text
http://127.0.0.1:5000
```

## Future Enhancements

- SMS notifications for patients.
- Online appointment booking.
- Patient login and registration.
- Advanced reporting and analytics.
- Improved waiting time prediction.

## Conclusion

The Hospital OPD Token and Queue Management System provides a simple and efficient way to manage hospital outpatient queues.

It reduces manual work, improves patient queue organization and helps hospitals handle emergency patients and doctor availability more effectively.

## Developer

**Project Name:** Hospital OPD Token and Queue Management System

**GitHub Repository:**
https://github.com/janyavulabalaji69-droid/hospital-opd-queue-management-system
