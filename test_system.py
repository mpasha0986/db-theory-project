import sqlite3
import datetime
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(DB_DIR, "schema_sqlite.sql")
QUERIES_PATH = os.path.join(DB_DIR, "queries.sql")

def setup_database():
    """Initializes an in-memory SQLite database and loads the schema and views."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Read and execute schema
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    
    # Read and execute views/queries
    with open(QUERIES_PATH, "r") as f:
        queries_sql = f.read()
    conn.executescript(queries_sql)
    
    return conn

def insert_seed_data(conn):
    """Inserts test customers and test vehicles."""
    cursor = conn.cursor()
    
    # Insert a vehicle with $10/hour, $50/day
    cursor.execute("""
        INSERT INTO vehicles (id, license_plate, make, model, year, hourly_rate, daily_rate, status)
        VALUES (1, 'AAA-1234', 'Toyota', 'Corolla', 2022, 10.00, 50.00, 'active')
    """)
    
    # Insert another vehicle with $15/hour, $75/day
    cursor.execute("""
        INSERT INTO vehicles (id, license_plate, make, model, year, hourly_rate, daily_rate, status)
        VALUES (2, 'BBB-5678', 'Tesla', 'Model 3', 2023, 15.00, 75.00, 'active')
    """)
    
    # Insert customers
    cursor.execute("""
        INSERT INTO customers (id, name, email, phone)
        VALUES (1, 'Alice Smith', 'alice@example.com', '555-0199')
    """)
    cursor.execute("""
        INSERT INTO customers (id, name, email, phone)
        VALUES (2, 'Bob Jones', 'bob@example.com', '555-0244')
    """)
    
    conn.commit()

def test_rate_calculations(conn):
    """Verifies that billing calculations in the view matches business rules."""
    print("\n=========================================")
    print("TESTING: HOURLY / DAILY RATE CALCULATIONS")
    print("=========================================")
    
    cursor = conn.cursor()
    
    # Test cases mapping (start, end) to expected cost and reason
    # Vehicle 1 has: hourly = 10 PKR, daily = 50 PKR
    test_cases = [
        # (Start, End, Expected Cost, Description)
        (
            "2026-07-01 10:00:00", "2026-07-01 13:00:00", 30.0, 
            "Pure hourly: 3 hours @ PKR 10/hr = PKR 30 (less than daily rate PKR 50)"
        ),
        (
            "2026-07-01 10:00:00", "2026-07-01 16:00:00", 50.0, 
            "Hourly capped at daily rate: 6 hours @ PKR 10/hr = PKR 60, capped at PKR 50"
        ),
        (
            "2026-07-01 10:00:00", "2026-07-02 12:00:00", 70.0, 
            "Multi-day + hourly: 26 hours total -> 1 day (PKR 50) + 2 hours @ PKR 10/hr (PKR 20) = PKR 70"
        ),
        (
            "2026-07-01 10:00:00", "2026-07-02 16:00:00", 100.0, 
            "Multi-day + capped hours: 30 hours total -> 1 day (PKR 50) + 6 hours @ PKR 10/hr (PKR 60 capped at PKR 50) = PKR 100"
        ),
        (
            "2026-07-01 10:00:00", "2026-07-02 10:00:00", 50.0, 
            "Exactly 1 day: 24 hours total = PKR 50"
        ),
        (
            "2026-07-01 10:00:00", "2026-07-01 12:00:01", 30.0, 
            "Partial hours rounding: 2 hours and 1 second should round up to 3 hours (PKR 30)"
        )
    ]
    
    for start, end, expected, desc in test_cases:
        # Clear existing bookings
        cursor.execute("DELETE FROM bookings;")
        
        # Insert booking
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (1, 1, ?, ?, 'confirmed')
        """, (start, end))
        conn.commit()
        
        # Fetch calculation from view
        cursor.execute("SELECT total_hours, full_days, remaining_hours, total_cost FROM view_booking_billing LIMIT 1;")
        res = cursor.fetchone()
        
        hours, days, rem_hours, cost = res
        assert abs(cost - expected) < 0.001, f"Expected PKR {expected}, but got PKR {cost}. Details: {res}"
        print(f"PASS: {desc}")
        print(f"      Result: {hours} hrs ({days} days, {rem_hours} remaining hrs) -> Total: PKR {cost:.2f}\n")

def test_double_booking_prevention(conn):
    """Verifies that trigger blocks overlapping confirmed bookings for the same vehicle."""
    print("=========================================")
    print("TESTING: DOUBLE BOOKING PREVENTION (TRIGGERS)")
    print("=========================================")
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings;")
    conn.commit()
    
    # 1. Insert initial booking (Vehicle 1, Alice, July 1st 10:00 to 12:00)
    cursor.execute("""
        INSERT INTO bookings (id, vehicle_id, customer_id, start_time, end_time, status)
        VALUES (101, 1, 1, '2026-07-01 10:00:00', '2026-07-01 12:00:00', 'confirmed')
    """)
    conn.commit()
    print("Inserted baseline booking: Vehicle 1, Confirmed [10:00 - 12:00]")
    
    # Helper to test insertions that should fail
    def assert_insert_fails(start, end, desc):
        try:
            cursor.execute("""
                INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
                VALUES (1, 2, ?, ?, 'confirmed')
            """, (start, end))
            conn.commit()
            raise AssertionError(f"FAIL: Insert succeeded but should have failed: {desc}")
        except sqlite3.IntegrityError as e:
            if "Double booking error" in str(e):
                print(f"PASS: Prevented insertion: {desc} (Trigger raised: {e})")
            else:
                raise e

    # Test cases for overlapping bookings (must fail)
    assert_insert_fails("2026-07-01 11:00:00", "2026-07-01 13:00:00", "Overlapping end boundary [11:00 - 13:00]")
    assert_insert_fails("2026-07-01 09:00:00", "2026-07-01 11:00:00", "Overlapping start boundary [09:00 - 11:00]")
    assert_insert_fails("2026-07-01 10:30:00", "2026-07-01 11:30:00", "Fully inside existing interval [10:30 - 11:30]")
    assert_insert_fails("2026-07-01 09:00:00", "2026-07-01 13:00:00", "Fully engulfing existing interval [09:00 - 13:00]")
    
    # 2. Insert booking for a DIFFERENT vehicle at the SAME time (should succeed)
    try:
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (2, 2, '2026-07-01 10:00:00', '2026-07-01 12:00:00', 'confirmed')
        """)
        conn.commit()
        print("PASS: Allowed booking of different vehicle (Vehicle 2) at the same time [10:00 - 12:00]")
    except sqlite3.IntegrityError as e:
        raise AssertionError(f"FAIL: Booking of vehicle 2 failed: {e}")

    # 3. Insert contiguous bookings (should succeed)
    # A booking ending exactly when the other starts or vice versa is NOT an overlap.
    try:
        # Ends at 10:00 (baseline starts at 10:00)
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (1, 2, '2026-07-01 08:00:00', '2026-07-01 10:00:00', 'confirmed')
        """)
        # Starts at 12:00 (baseline ends at 12:00)
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (1, 2, '2026-07-01 12:00:00', '2026-07-01 14:00:00', 'confirmed')
        """)
        conn.commit()
        print("PASS: Allowed contiguous bookings (ends at 10:00 or starts at 12:00)")
    except sqlite3.IntegrityError as e:
        raise AssertionError(f"FAIL: Contiguous bookings failed: {e}")

    # 4. Insert booking that is overlapping but status is 'cancelled' or 'pending' (should succeed)
    try:
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (1, 2, '2026-07-01 10:30:00', '2026-07-01 11:30:00', 'cancelled')
        """)
        cursor.execute("""
            INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
            VALUES (1, 2, '2026-07-01 10:30:00', '2026-07-01 11:30:00', 'pending')
        """)
        conn.commit()
        print("PASS: Allowed overlapping bookings when status is not 'confirmed' (e.g., cancelled or pending)")
    except sqlite3.IntegrityError as e:
        raise AssertionError(f"FAIL: Allowed status overlap test failed: {e}")

    # 5. Test UPDATE triggers
    # Let's try to update the pending booking to 'confirmed'. It should trigger the overlap error because it overlaps with baseline.
    pending_id = cursor.lastrowid
    try:
        cursor.execute("""
            UPDATE bookings
            SET status = 'confirmed'
            WHERE id = ?
        """, (pending_id,))
        conn.commit()
        raise AssertionError("FAIL: Update to 'confirmed' status succeeded on an overlapping booking!")
    except sqlite3.IntegrityError as e:
        if "Double booking error" in str(e):
            print("PASS: Prevented update changing status to 'confirmed' for overlapping period.")
        else:
            raise e

    # Try updating a non-overlapping booking to overlap
    # We have a booking from 12:00 to 14:00. Let's try updating it to 11:00 to 13:00 (which overlaps baseline 10:00-12:00).
    cursor.execute("SELECT id FROM bookings WHERE start_time = '2026-07-01 12:00:00'")
    target_booking_id = cursor.fetchone()[0]
    
    try:
        cursor.execute("""
            UPDATE bookings
            SET start_time = '2026-07-01 11:00:00', end_time = '2026-07-01 13:00:00'
            WHERE id = ?
        """, (target_booking_id,))
        conn.commit()
        raise AssertionError("FAIL: Update changing time range to overlap succeeded!")
    except sqlite3.IntegrityError as e:
        if "Double booking error" in str(e):
            print("PASS: Prevented update changing times to overlap existing booking.")
        else:
            raise e

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    connection = setup_database()
    insert_seed_data(connection)
    test_rate_calculations(connection)
    test_double_booking_prevention(connection)
    connection.close()
