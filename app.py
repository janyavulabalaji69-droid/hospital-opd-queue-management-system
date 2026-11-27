from flask import Flask, render_template, request, redirect, flash
from database import create_tables, get_connection

app = Flask(__name__)

app.secret_key = "opd-project-secret-key"

# Create database tables
create_tables()

# Average consultation time
AVERAGE_CONSULTATION_TIME = 10


# ---------------------------------------------------------
# WAITING TIME CALCULATOR
# ---------------------------------------------------------

def calculate_waiting_time(position):
    return position * AVERAGE_CONSULTATION_TIME


# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# RECEPTION DASHBOARD
# ---------------------------------------------------------

@app.route("/reception")
def reception():

    connection = get_connection()
    cursor = connection.cursor()

    # Get all doctors
    cursor.execute("""
        SELECT id, name, department, available
        FROM doctors
        ORDER BY id
    """)

    doctors = cursor.fetchall()

    # Get waiting patients whose doctor is unavailable
    cursor.execute("""
        SELECT
            tokens.id,
            tokens.token_number,
            patients.name AS patient_name,
            doctors.name AS doctor_name,
            doctors.department

        FROM tokens

        JOIN patients
            ON tokens.patient_id = patients.id

        JOIN doctors
            ON tokens.doctor_id = doctors.id

        WHERE tokens.status = 'WAITING'

        AND doctors.available = 0

        ORDER BY tokens.token_number ASC
    """)

    reassignment_patients = cursor.fetchall()

    connection.close()

    return render_template(
        "reception.html",
        doctors=doctors,
        reassignment_patients=reassignment_patients
    )


# ---------------------------------------------------------
# ADD PATIENT + GENERATE TOKEN
# ---------------------------------------------------------


@app.route("/add_patient", methods=["POST"])
def add_patient():

    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    phone = request.form.get("phone", "").strip()
    doctor_id = request.form.get("doctor", "").strip()
    emergency = request.form.get("emergency", "").strip()

    # Validate patient name
    if not name or len(name) > 100:
        flash("Please enter a valid patient name.", "warning")
        return redirect("/reception")

    # Validate age
    if not age.isdigit() or not (1 <= int(age) <= 120):
        flash("Age must be between 1 and 120.", "warning")
        return redirect("/reception")

    # Validate phone number
    if not phone.isdigit() or len(phone) != 10:
        flash("Phone number must contain exactly 10 digits.", "warning")
        return redirect("/reception")

    # Validate doctor selection
    if not doctor_id.isdigit():
        flash("Please select a valid doctor.", "warning")
        return redirect("/reception")

    # Validate patient type
    if emergency not in ("0", "1"):
        flash("Please select a valid patient type.", "warning")
        return redirect("/reception")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Check doctor availability
        cursor.execute("""
            SELECT name, available
            FROM doctors
            WHERE id = ?
        """, (int(doctor_id),))

        doctor = cursor.fetchone()

        if doctor is None or doctor["available"] == 0:
            connection.close()
            flash("Selected doctor is unavailable. Please choose another.", "warning")
            return redirect("/reception")

        # Insert patient
        cursor.execute("""
            INSERT INTO patients (name, age, phone)
            VALUES (?, ?, ?)
        """, (name, int(age), phone))

        patient_id = cursor.lastrowid

        # Generate next token
        cursor.execute("""
            SELECT MAX(token_number)
            FROM tokens
            WHERE doctor_id = ?
        """, (int(doctor_id),))

        result = cursor.fetchone()
        token_number = 1 if result[0] is None else result[0] + 1

        # Insert token
        cursor.execute("""
            INSERT INTO tokens (
                token_number,
                patient_id,
                doctor_id,
                status,
                emergency,
                original_doctor_id,
                original_token_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            token_number,
            patient_id,
            int(doctor_id),
            "WAITING",
            int(emergency),
            int(doctor_id),
            token_number
        ))

        connection.commit()

    except Exception:
        connection.rollback()
        connection.close()
        app.logger.exception("Patient registration failed")
        flash("Registration failed due to a database error. Please try again.", "warning")
        return redirect("/reception")

    connection.close()

    patient_type = "🚨 EMERGENCY" if emergency == "1" else "Normal"

    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Token Generated</title>
            <link rel="stylesheet"
                  href="/static/css/style.css">
        </head>
        <body>
            <div class="container">
                <h1>Token Generated Successfully!</h1>
                <h2>Token Number: {token_number}</h2>
                <p>Patient: {name}</p>
                <p>Patient Type: {patient_type}</p>
                <p>Status: WAITING</p>

                <button onclick="window.location.href='/reception'">
                    Back to Reception
                </button>

                <button onclick="window.location.href='/'">
                    Back to Home
                </button>
            </div>
        </body>
        </html>
    """



# ---------------------------------------------------------
# DOCTOR DASHBOARD
# ---------------------------------------------------------

@app.route("/doctor/<int:doctor_id>")
def doctor_dashboard(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Get all doctors for dropdown
    cursor.execute("""
        SELECT id, name, department, available
        FROM doctors
        ORDER BY id
    """)

    doctors = cursor.fetchall()

    # Get selected doctor
    cursor.execute("""
        SELECT name, department, available
        FROM doctors
        WHERE id = ?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:

        connection.close()

        return "Doctor not found"

    # -----------------------------------------------------
    # GET WAITING PATIENTS
    #
    # Emergency patients come first.
    # Normal patients follow FIFO order.
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            tokens.token_number,
            patients.name AS patient_name,
            tokens.status,
            tokens.emergency

        FROM tokens

        JOIN patients
            ON tokens.patient_id = patients.id

        WHERE tokens.doctor_id = ?

        AND tokens.status = 'WAITING'

        ORDER BY
            tokens.emergency DESC,
            tokens.token_number ASC

    """, (doctor_id,))

    patients = cursor.fetchall()


        # -----------------------------------------------------
    # QUEUE STATISTICS
    # -----------------------------------------------------

    # Total patients for this doctor
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM tokens
        WHERE doctor_id = ?
    """, (doctor_id,))

    total_patients = cursor.fetchone()["total"]


    # Waiting patients
    cursor.execute("""
        SELECT COUNT(*) AS waiting
        FROM tokens
        WHERE doctor_id = ?
        AND status = 'WAITING'
    """, (doctor_id,))

    waiting_patients = cursor.fetchone()["waiting"]


    # Completed patients
    cursor.execute("""
        SELECT COUNT(*) AS completed
        FROM tokens
        WHERE doctor_id = ?
        AND status = 'COMPLETED'
    """, (doctor_id,))

    completed_patients = cursor.fetchone()["completed"]


    # Emergency patients
    cursor.execute("""
        SELECT COUNT(*) AS emergency
        FROM tokens
        WHERE doctor_id = ?
        AND emergency = 1
    """, (doctor_id,))

    emergency_patients = cursor.fetchone()["emergency"]

    # -----------------------------------------------------
    # CALCULATE WAITING TIME
    # -----------------------------------------------------

    
# CALCULATE WAITING TIME

    patients_with_waiting_time = []

    # Check whether a patient is currently being handled
    cursor.execute("""
        SELECT COUNT(*)
        FROM tokens
        WHERE doctor_id = ?
        AND status IN ('CALLED', 'IN_PROGRESS')
    """, (doctor_id,))

    active_patient = cursor.fetchone()[0]

    for position, patient in enumerate(patients):

        patient_data = dict(patient)

        patient_data["waiting_time"] = (
            (position + active_patient) * AVERAGE_CONSULTATION_TIME
        )

        patients_with_waiting_time.append(patient_data)


    # -----------------------------------------------------
    # GET CURRENT PATIENT
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            tokens.id,
            tokens.token_number,
            patients.name AS patient_name,
            tokens.status,
            tokens.emergency

        FROM tokens

        JOIN patients
            ON tokens.patient_id = patients.id

        WHERE tokens.doctor_id = ?

        AND tokens.status IN
        ('CALLED', 'IN_PROGRESS')

        ORDER BY tokens.token_number ASC

        LIMIT 1

    """, (doctor_id,))

    current_patient = cursor.fetchone()

    connection.close()

    # -----------------------------------------------------
    # DISPLAY DOCTOR DASHBOARD
    # -----------------------------------------------------

    return render_template(
        "doctor_dashboard.html",

        doctors=doctors,

        selected_doctor=doctor_id,

        doctor_name=doctor["name"],

        department=doctor["department"],

        doctor_available=doctor["available"],

        patients=patients_with_waiting_time,

        current_patient=current_patient,

        total_patients=total_patients,

        waiting_patients=waiting_patients,

        completed_patients=completed_patients,

        emergency_patients=emergency_patients
    )


# ---------------------------------------------------------
# TOGGLE DOCTOR AVAILABILITY
# ---------------------------------------------------------

@app.route(
    "/toggle_doctor/<int:doctor_id>",
    methods=["POST"]
)
def toggle_doctor(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Get current availability
    cursor.execute("""
        SELECT available
        FROM doctors
        WHERE id = ?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:

        connection.close()

        return "Doctor not found"

    # Toggle availability
    if doctor["available"] == 1:

        new_status = 0

    else:

        new_status = 1

    # Update availability
    cursor.execute("""
        UPDATE doctors
        SET available = ?
        WHERE id = ?
    """, (new_status, doctor_id))

    connection.commit()
    connection.close()

    return redirect(
        f"/doctor/{doctor_id}"
    )


# ---------------------------------------------------------
# REASSIGN PATIENT TO ANOTHER DOCTOR
# ---------------------------------------------------------


@app.route("/reassign_patient/<int:token_id>", methods=["POST"])
def reassign_patient(token_id):

    new_doctor_id = request.form["new_doctor"]

    connection = get_connection()
    cursor = connection.cursor()

    # Get token details
    cursor.execute("""
        SELECT id, token_number, doctor_id, status
        FROM tokens
        WHERE id = ?
    """, (token_id,))

    token = cursor.fetchone()

    if token is None:
        connection.close()
        return "Token not found"

    if token["status"] != "WAITING":
        connection.close()
        return "Only waiting patients can be reassigned."

    # Check new doctor
    cursor.execute("""
        SELECT id, available
        FROM doctors
        WHERE id = ?
    """, (new_doctor_id,))

    new_doctor = cursor.fetchone()

    if new_doctor is None or new_doctor["available"] == 0:
        connection.close()
        return "Selected doctor is unavailable or does not exist."

    if token["doctor_id"] == int(new_doctor_id):
        connection.close()
        return redirect("/reception")

    # Generate next token number for new doctor
    cursor.execute("""
        SELECT MAX(token_number)
        FROM tokens
        WHERE doctor_id = ?
    """, (new_doctor_id,))

    result = cursor.fetchone()

    if result[0] is None:
        new_token_number = 1
    else:
        new_token_number = result[0] + 1

    # Reassign patient and update queue token
    # Original token number remains unchanged
    cursor.execute("""
        UPDATE tokens
        SET doctor_id = ?,
            token_number = ?
        WHERE id = ?
    """, (new_doctor_id, new_token_number, token_id))

    connection.commit()
    connection.close()

    return """
        <h2>Patient reassigned successfully!</h2>
        <p>New Token Number: """ + str(new_token_number) + """</p>
        <p>Original token number has been preserved.</p>
        <button onclick="window.location.href='/reception'">
            Back to Reception
        </button>
    """



# ---------------------------------------------------------
# CALL NEXT PATIENT
# ---------------------------------------------------------



@app.route(
    "/call_next/<int:doctor_id>",
    methods=["POST"]
)
def call_next(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # CHECK DOCTOR AVAILABILITY
    cursor.execute("""
        SELECT available
        FROM doctors
        WHERE id = ?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:
        connection.close()
        return "Doctor not found"

    # CHECK IF DOCTOR IS UNAVAILABLE
    if doctor["available"] == 0:

        connection.close()

        flash(
            "Doctor is unavailable! Please select an available doctor.",
            "warning"
        )

        return redirect(f"/doctor/{doctor_id}")

    # CHECK IF A PATIENT IS ALREADY BEING HANDLED
    cursor.execute("""
        SELECT id
        FROM tokens
        WHERE doctor_id = ?
        AND status IN ('CALLED', 'IN_PROGRESS')
        LIMIT 1
    """, (doctor_id,))

    current = cursor.fetchone()

    if current is not None:
        connection.close()
        return redirect(f"/doctor/{doctor_id}")

    # FIND NEXT PATIENT
    cursor.execute("""
        SELECT id
        FROM tokens
        WHERE doctor_id = ?
        AND status = 'WAITING'
        ORDER BY emergency DESC, token_number ASC
        LIMIT 1
    """, (doctor_id,))

    token = cursor.fetchone()

    if token is None:
        connection.close()
        return redirect(f"/doctor/{doctor_id}")

    # CHANGE STATUS TO CALLED
    cursor.execute("""
        UPDATE tokens
        SET status = 'CALLED'
        WHERE id = ?
    """, (token["id"],))

    connection.commit()
    connection.close()

    return redirect(f"/doctor/{doctor_id}")




# ---------------------------------------------------------
# START CONSULTATION
# ---------------------------------------------------------

@app.route(
    "/start_consultation/<int:doctor_id>",
    methods=["POST"]
)
def start_consultation(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Start the currently CALLED patient
    cursor.execute("""
        UPDATE tokens

        SET status = 'IN_PROGRESS'

        WHERE id = (

            SELECT id

            FROM tokens

            WHERE doctor_id = ?

            AND status = 'CALLED'

            ORDER BY token_number ASC

            LIMIT 1

        )

    """, (doctor_id,))

    connection.commit()
    connection.close()

    return redirect(
        f"/doctor/{doctor_id}"
    )


# ---------------------------------------------------------
# COMPLETE CONSULTATION
# ---------------------------------------------------------

@app.route(
    "/complete_consultation/<int:doctor_id>",
    methods=["POST"]
)
def complete_consultation(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Complete current IN_PROGRESS patient
    cursor.execute("""
        UPDATE tokens

        SET status = 'COMPLETED'

        WHERE id = (

            SELECT id

            FROM tokens

            WHERE doctor_id = ?

            AND status = 'IN_PROGRESS'

            ORDER BY token_number ASC

            LIMIT 1

        )

    """, (doctor_id,))

    connection.commit()
    connection.close()

    return redirect(
        f"/doctor/{doctor_id}"
    )


# ---------------------------------------------------------
# LIVE QUEUE DISPLAY
# ---------------------------------------------------------


@app.route("/live_queue/<int:doctor_id>")
def live_queue(doctor_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Get available doctors
    cursor.execute("""
        SELECT id, name, department
        FROM doctors
        WHERE available = 1
        ORDER BY id
    """)
    doctors = cursor.fetchall()

    # Get selected doctor
    cursor.execute("""
        SELECT name, department
        FROM doctors
        WHERE id = ?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:
        connection.close()
        return "Doctor not found"

    # Get current patient
    cursor.execute("""
        SELECT
            tokens.token_number,
            patients.name AS patient_name,
            tokens.status,
            tokens.emergency
        FROM tokens
        JOIN patients
            ON tokens.patient_id = patients.id
        WHERE tokens.doctor_id = ?
        AND tokens.status IN ('CALLED', 'IN_PROGRESS')
        ORDER BY tokens.token_number ASC
        LIMIT 1
    """, (doctor_id,))

    current_patient = cursor.fetchone()

    # Get all waiting patients
    cursor.execute("""
        SELECT
            tokens.token_number,
            patients.name AS patient_name,
            tokens.status,
            tokens.emergency
        FROM tokens
        JOIN patients
            ON tokens.patient_id = patients.id
        WHERE tokens.doctor_id = ?
        AND tokens.status = 'WAITING'
        ORDER BY tokens.emergency DESC,
                 tokens.token_number ASC
    """, (doctor_id,))

    waiting_patients = cursor.fetchall()

    connection.close()

    # Display live queue
    return render_template(
        "live_display.html",
        doctors=doctors,
        selected_doctor=doctor_id,
        doctor_name=doctor["name"],
        department=doctor["department"],
        current_patient=current_patient,
        waiting_patients=waiting_patients
    )



# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(debug=True)