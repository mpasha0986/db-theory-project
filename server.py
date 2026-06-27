import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
from datetime import datetime

PORT = 8000
DB_FILE = "rental_system.db"
DB_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(DB_DIR, "schema_sqlite.sql")
QUERIES_PATH = os.path.join(DB_DIR, "queries.sql")

def init_db():
    """Initializes the database schema and views. Seeds default data if empty."""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")  # WAL mode: allows concurrent reads during writes
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Execute schema SQL
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    
    # Execute queries/views SQL
    with open(QUERIES_PATH, "r") as f:
        queries_sql = f.read()
    conn.executescript(queries_sql)
    
    # Seed default data if empty
    _seed_if_empty(conn)
    conn.close()

def _seed_data(conn):
    """Inserts the standard demo seed data. Assumes tables are empty."""
    cursor = conn.cursor()
    vehicles = [
        ('SUV-2024', 'Ford', 'Explorer', 2024, 4200.00, 21000.00, 'active'),
        ('SED-2023', 'Toyota', 'Camry', 2023, 2800.00, 14000.00, 'active'),
        ('EV-2023', 'Tesla', 'Model Y', 2023, 5040.00, 25200.00, 'active'),
        ('TRK-2022', 'Chevrolet', 'Silverado', 2022, 5600.00, 28000.00, 'active'),
        ('MNT-2021', 'Honda', 'Civic', 2021, 2240.00, 11200.00, 'maintenance')
    ]
    cursor.executemany("""
        INSERT INTO vehicles (license_plate, make, model, year, hourly_rate, daily_rate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, vehicles)
    
    customers = [
        ('Jane Doe', 'jane@example.com', '555-0101'),
        ('John Smith', 'john@example.com', '555-0102'),
        ('Sarah Connor', 'sarah@example.com', '555-0103')
    ]
    cursor.executemany("""
        INSERT INTO customers (name, email, phone)
        VALUES (?, ?, ?)
    """, customers)
    
    # One completed booking and one upcoming confirmed booking
    cursor.execute("INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status) VALUES (2, 1, '2026-06-25 08:00:00', '2026-06-25 12:00:00', 'completed')")
    cursor.execute("INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status) VALUES (1, 2, '2026-06-28 09:00:00', '2026-06-29 17:00:00', 'confirmed')")
    conn.commit()

def _seed_if_empty(conn):
    """Seeds data only if the vehicles table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    if cursor.fetchone()[0] == 0:
        print("Seeding database with initial demo data...")
        _seed_data(conn)
        print("Seeding complete.")

def reseed_db():
    """Clears all data and re-seeds with fresh demo data. Safe under concurrent access."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = OFF;")  # Disable FK checks during bulk delete
        cursor = conn.cursor()
        # Delete in dependency order (bookings first, then customers and vehicles)
        cursor.execute("DELETE FROM bookings")
        cursor.execute("DELETE FROM customers")
        cursor.execute("DELETE FROM vehicles")
        # Reset autoincrement counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('bookings','customers','vehicles')")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_data(conn)
    finally:
        if conn:
            conn.close()
    print("Database reseeded successfully.")

class RentalSystemHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to keep stdout clean
        pass
        
    def _send_response(self, status, content, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
        if isinstance(content, str):
            self.wfile.write(content.encode('utf-8'))
        else:
            self.wfile.write(json.dumps(content).encode('utf-8'))

    def do_OPTIONS(self):
        self._send_response(200, "")

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # API Endpoints
        if path == "/api/data":
            self.handle_get_data()
        
        # Static Assets File Server
        else:
            if path == "/" or path == "":
                path = "/index.html"
            
            # Map path to local project folder
            local_path = os.path.join(DB_DIR, path.lstrip("/"))
            
            # Prevent directory traversal attacks
            local_path = os.path.abspath(local_path)
            if not local_path.startswith(os.path.abspath(DB_DIR)):
                self._send_response(403, {"error": "Access Denied"})
                return
                
            if os.path.exists(local_path) and os.path.isfile(local_path):
                content_type = "text/plain"
                if local_path.endswith(".html"):
                    content_type = "text/html"
                elif local_path.endswith(".css"):
                    content_type = "text/css"
                elif local_path.endswith(".js"):
                    content_type = "application/javascript"
                elif local_path.endswith(".json"):
                    content_type = "application/json"
                elif local_path.endswith(".ico"):
                    content_type = "image/x-icon"
                
                try:
                    with open(local_path, "rb") as f:
                        self.send_response(200)
                        self.send_header("Content-Type", content_type)
                        self.end_headers()
                        self.wfile.write(f.read())
                except Exception as e:
                    self._send_response(500, {"error": str(e)})
            else:
                self._send_response(404, {"error": "File Not Found"})

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            self._send_response(400, {"error": "Invalid JSON format"})
            return

        if path == "/api/bookings":
            self.handle_create_booking(body)
        elif path == "/api/vehicles":
            self.handle_create_vehicle(body)
        elif path == "/api/customers":
            self.handle_create_customer(body)
        elif path == "/api/reseed":
            self.handle_reseed()
        else:
            self._send_response(404, {"error": "Endpoint Not Found"})

    # --- API Action Handlers ---
    
    def handle_get_data(self):
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch vehicles
            cursor.execute("SELECT * FROM vehicles ORDER BY id DESC")
            vehicles = [dict(row) for row in cursor.fetchall()]
            
            # Fetch customers
            cursor.execute("SELECT * FROM customers ORDER BY id DESC")
            customers = [dict(row) for row in cursor.fetchall()]
            
            # Fetch bookings (with calculated billing from query view)
            cursor.execute("SELECT * FROM view_booking_billing ORDER BY booking_id DESC")
            bookings = [dict(row) for row in cursor.fetchall()]
            
            # Calculate stats
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'active'")
            active_vehicles_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vehicles")
            total_vehicles_count = cursor.fetchone()[0]
            
            # Active bookings right now
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE status = 'confirmed' 
                  AND datetime(?) >= datetime(start_time) 
                  AND datetime(?) < datetime(end_time)
            """, (now_str, now_str))
            active_bookings_count = cursor.fetchone()[0]
            
            # Total revenue
            cursor.execute("SELECT SUM(total_cost) FROM view_booking_billing WHERE status IN ('confirmed', 'completed')")
            total_revenue = cursor.fetchone()[0] or 0.0
            
            self._send_response(200, {
                "vehicles": vehicles,
                "customers": customers,
                "bookings": bookings,
                "stats": {
                    "total_vehicles": total_vehicles_count,
                    "active_vehicles": active_vehicles_count,
                    "active_bookings": active_bookings_count,
                    "total_revenue": round(total_revenue, 2)
                }
            })
            
        except Exception as e:
            self._send_response(500, {"error": f"Database query failed: {str(e)}"})
        finally:
            if conn:
                conn.close()


    def handle_create_booking(self, body):
        vehicle_id = body.get("vehicle_id")
        customer_id = body.get("customer_id")
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        status = body.get("status", "confirmed")
        
        if not all([vehicle_id, customer_id, start_time, end_time]):
            self._send_response(400, {"error": "Missing required booking details (vehicle_id, customer_id, start_time, end_time)."})
            return
            
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            
            # Insert booking
            cursor.execute("""
                INSERT INTO bookings (vehicle_id, customer_id, start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?)
            """, (vehicle_id, customer_id, start_time, end_time, status))
            conn.commit()
            
            self._send_response(201, {"success": True, "message": "Booking created successfully!"})
            
        except sqlite3.IntegrityError as e:
            err_msg = str(e)
            if "Double booking error" in err_msg:
                self._send_response(409, {
                    "error": "Double Booking Alert",
                    "details": "This vehicle is already booked for a confirmed reservation overlapping this time period. The database trigger rejected the insertion."
                })
            elif "chk_booking_times" in err_msg or "CHECK constraint failed" in err_msg:
                self._send_response(400, {
                    "error": "Invalid Time Range",
                    "details": "The booking start time must be chronologically before the end time."
                })
            else:
                self._send_response(400, {"error": "Database constraint violation", "details": err_msg})
        except Exception as e:
            self._send_response(500, {"error": "System failure", "details": str(e)})
        finally:
            if conn:
                conn.close()

    def handle_create_vehicle(self, body):
        license_plate = body.get("license_plate")
        make = body.get("make")
        model = body.get("model")
        year = body.get("year")
        hourly_rate = body.get("hourly_rate")
        daily_rate = body.get("daily_rate")
        status = body.get("status", "active")
        
        if any(x is None for x in [license_plate, make, model, year, hourly_rate, daily_rate]):
            self._send_response(400, {"error": "Missing vehicle details."})
            return
            
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vehicles (license_plate, make, model, year, hourly_rate, daily_rate, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (license_plate, make, model, year, hourly_rate, daily_rate, status))
            conn.commit()
            self._send_response(201, {"success": True, "message": "Vehicle added successfully!"})
        except sqlite3.IntegrityError as e:
            self._send_response(400, {"error": "Validation Error", "details": "License plate must be unique, and rates must be positive numbers."})
        except Exception as e:
            self._send_response(500, {"error": "Database error", "details": str(e)})
        finally:
            if conn:
                conn.close()

    def handle_create_customer(self, body):
        name = body.get("name")
        email = body.get("email")
        phone = body.get("phone")
        
        if not name or not email:
            self._send_response(400, {"error": "Name and email are required fields."})
            return
            
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers (name, email, phone)
                VALUES (?, ?, ?)
            """, (name, email, phone))
            conn.commit()
            self._send_response(201, {"success": True, "message": "Customer created successfully!"})
        except sqlite3.IntegrityError as e:
            self._send_response(400, {"error": "Validation Error", "details": "Email address must be unique."})
        except Exception as e:
            self._send_response(500, {"error": "Database error", "details": str(e)})
        finally:
            if conn:
                conn.close()

    def handle_reseed(self):
        try:
            reseed_db()
            self._send_response(200, {"success": True, "message": "Database reset and seeded with clean demo data!"})
        except Exception as e:
            self._send_response(500, {"error": "Reset failed", "details": str(e)})

def run_server():
    init_db()
    
    # Use ThreadingTCPServer so each request is handled in its own thread.
    # This prevents the server from blocking when multiple requests arrive
    # concurrently (e.g. browser loading JS/CSS simultaneously with API calls).
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server_address = ('', PORT)
    httpd = socketserver.ThreadingTCPServer(server_address, RentalSystemHandler)
    
    print(f"\n==================================================")
    print(f" VEHICLE RENTAL DATABASE SYSTEM ONLINE")
    print(f" Local Web Server Running: http://localhost:{PORT}")
    print(f" Press Ctrl+C to terminate the process.")
    print(f"==================================================\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
