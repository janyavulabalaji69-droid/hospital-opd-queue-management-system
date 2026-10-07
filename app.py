from flask import Flask, render_template, request, redirect
from database import create_tables, get_connection

app = Flask(__name__)

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

    # Get patient information
    name = request.form["name"]
    age = request.form["age"]
    phone = request.form["phone"]

    # Get selected doctor
    doctor_id = request.form["doctor"]

    # Get patient type
    # 0 = Normal
    # 1 = Emergency
    emergency = request.form["emergency"]

    # -----------------------------------------------------
    # CONNECT TO DATABASE
    # -----------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK IF SELECTED DOCTOR IS AVAILABLE
    # -----------------------------------------------------

    cursor.execute("""
        SELECT name, available
        FROM doctors
        WHERE id = ?
    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:

        connection.close()

        return "Doctor not found"

    if doctor["available"] == 0:

        connection.close()

        return """
            <div style="
                text-align:center;
                margin-top:100px;
                font-family:Arial;
            ">

                <h2>Doctor is currently unavailable.</h2>

                <p>Please select another doctor.</p>

                <br>

                <button onclick="window.location.href='/reception'">
                    Back to Reception
                </button>

                &nbsp;&nbsp;

                <button onclick="window.location.href='/'">
                    Back to Home
                </button>

            </div>
        """

    # -----------------------------------------------------
    # ADD PATIENT TO PATIENTS TABLE
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO patients (name, age, phone)
        VALUES (?, ?, ?)
    """, (name, age, phone))

    patient_id = cursor.lastrowid

    # -----------------------------------------------------
    # GENERATE NEXT TOKEN NUMBER
    # -----------------------------------------------------

    cursor.execute("""
        SELECT MAX(token_number)
        FROM tokens
        WHERE doctor_id = ?
    """, (doctor_id,))

    result = cursor.fetchone()

    if result[0] is None:

        token_number = 1

    else:

        token_number = result[0] + 1

    # -----------------------------------------------------
    # ADD TOKEN
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO tokens
        (
            token_number,
            patient_id,
            doctor_id,
            status,
            emergency,
            original_doctor_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        token_number,
        patient_id,
        doctor_id,
        "WAITING",
        emergency,
        doctor_id
    ))

    connection.commit()
    connection.close()

    # -----------------------------------------------------
    # SHOW PATIENT TYPE
    # -----------------------------------------------------

    if emergency == "1":

        patient_type = "🚨 EMERGENCY"

    else:

        patient_type = "Normal"

    # -----------------------------------------------------
    # SHOW TOKEN RESULT
    # -----------------------------------------------------

    return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>Token Generated</title>

        </head>

        <body>

            <div style="
                text-align:center;
                margin-top:100px;
                font-family:Arial;
            ">

                <h1>Token Generated Successfully!</h1>

                <h2>Token Number: {token_number}</h2>

                <p>Patient: {name}</p>

                <p>Patient Type: {patient_type}</p>

                <p>Status: WAITING</p>

                <br>

                <button
                    onclick="window.location.href='/reception'">

                    Back to Reception

                </button>

                &nbsp;&nbsp;

                <button
                    onclick="window.location.href='/'">

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

    patients_with_waiting_time = []

    for position, patient in enumerate(patients):

        patient_data = dict(patient)

        patient_data["waiting_time"] = (
            calculate_waiting_time(position)
        )

        patients_with_waiting_time.append(
            patient_data
        )

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

@app.route(
    "/reassign_patient/<int:token_id>",
    methods=["POST"]
)
def reassign_patient(token_id):

    new_doctor_id = request.form["new_doctor"]

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK THE TOKEN
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            token_number,
            doctor_id,
            status

        FROM tokens

        WHERE id = ?
    """, (token_id,))

    token = cursor.fetchone()

    if token is None:

        connection.close()

        return "Token not found"

    # -----------------------------------------------------
    # ONLY WAITING PATIENTS CAN BE REASSIGNED
    # -----------------------------------------------------

    if token["status"] != "WAITING":

        connection.close()

        return """
            <h2>Only waiting patients can be reassigned.</h2>

            <br>

            <button onclick="window.location.href='/reception'">
                Back to Reception
            </button>
        """

    # -----------------------------------------------------
    # CHECK NEW DOCTOR
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            name,
            available

        FROM doctors

        WHERE id = ?
    """, (new_doctor_id,))

    new_doctor = cursor.fetchone()

    if new_doctor is None:

        connection.close()

        return "Doctor not found"

    if new_doctor["available"] == 0:

        connection.close()

        return """
            <h2>Selected doctor is unavailable.</h2>

            <br>

            <button onclick="window.location.href='/reception'">
                Back to Reception
            </button>
        """

    # -----------------------------------------------------
    # REASSIGN PATIENT
    #
    # Token number DOES NOT change.
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE tokens

        SET doctor_id = ?

        WHERE id = ?
    """, (new_doctor_id, token_id))

    connection.commit()
    connection.close()

    return """
        <h2>Patient reassigned successfully!</h2>

        <p>The original token number has been preserved.</p>

        <br>

        <button onclick="window.location.href='/reception'">
            Back to Reception
        </button>

        &nbsp;&nbsp;

        <button onclick="window.location.href='/'">
            Back to Home
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

    # -----------------------------------------------------
    # CHECK IF A PATIENT IS ALREADY BEING HANDLED
    # -----------------------------------------------------

    cursor.execute("""
        SELECT id

        FROM tokens

        WHERE doctor_id = ?

        AND status IN
        ('CALLED', 'IN_PROGRESS')

        LIMIT 1

    """, (doctor_id,))

    current = cursor.fetchone()

    # Don't call another patient while one is active
    if current is not None:

        connection.close()

        return redirect(
            f"/doctor/{doctor_id}"
        )

    # -----------------------------------------------------
    # FIND NEXT PATIENT
    #
    # EMERGENCY FIRST
    # THEN NORMAL FIFO
    # -----------------------------------------------------

    cursor.execute("""
        SELECT id

        FROM tokens

        WHERE doctor_id = ?

        AND status = 'WAITING'

        ORDER BY
            emergency DESC,
            token_number ASC

        LIMIT 1

    """, (doctor_id,))

    token = cursor.fetchone()

    # No waiting patients
    if token is None:

        connection.close()

        return redirect(
            f"/doctor/{doctor_id}"
        )

    # -----------------------------------------------------
    # CHANGE STATUS TO CALLED
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE tokens

        SET status = 'CALLED'

        WHERE id = ?

    """, (token["id"],))

    connection.commit()
    connection.close()

    return redirect(
        f"/doctor/{doctor_id}"
    )


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
        SELECT
            id,
            name,
            department

        FROM doctors

        WHERE available = 1

        ORDER BY id

    """)

    doctors = cursor.fetchall()

    # Get selected doctor
    cursor.execute("""
        SELECT
            name,
            department

        FROM doctors

        WHERE id = ?

    """, (doctor_id,))

    doctor = cursor.fetchone()

    if doctor is None:

        connection.close()

        return "Doctor not found"

    # -----------------------------------------------------
    # GET CURRENT PATIENT
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

        AND tokens.status IN
        ('CALLED', 'IN_PROGRESS')

        ORDER BY tokens.token_number ASC

        LIMIT 1

    """, (doctor_id,))

    current_patient = cursor.fetchone()

    connection.close()

    # -----------------------------------------------------
    # DISPLAY LIVE QUEUE
    # -----------------------------------------------------

    return render_template(
        "live_display.html",

        doctors=doctors,

        selected_doctor=doctor_id,

        doctor_name=doctor["name"],

        department=doctor["department"],

        current_patient=current_patient
    )


# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(debug=True)