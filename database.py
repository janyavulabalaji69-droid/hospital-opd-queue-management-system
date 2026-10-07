import sqlite3

DATABASE = "hospital.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    # Doctors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            available INTEGER DEFAULT 1
        )
    """)

    # Add default doctors
    cursor.execute("""
        INSERT OR IGNORE INTO doctors (id, name, department, available)
        VALUES (1, 'Dr. Ravi', 'General Medicine', 1)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO doctors (id, name, department, available)
        VALUES (2, 'Dr. Priya', 'Cardiology', 1)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO doctors (id, name, department, available)
        VALUES (3, 'Dr. Kumar', 'Orthopedics', 1)
    """)

    # Patients table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            phone TEXT
        )
    """)

    # Tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_number INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            status TEXT DEFAULT 'WAITING',
            emergency INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    # -----------------------------------------------------
    # Add original_doctor_id column if it does not exist
    # -----------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(tokens)
    """)

    columns = cursor.fetchall()

    column_names = [column["name"] for column in columns]

    if "original_doctor_id" not in column_names:

        cursor.execute("""
            ALTER TABLE tokens
            ADD COLUMN original_doctor_id INTEGER
        """)

    # -----------------------------------------------------
    # Fill original doctor for existing tokens
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE tokens
        SET original_doctor_id = doctor_id
        WHERE original_doctor_id IS NULL
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully!")