"""
Comprehensive API Test Suite for Vehicle Rental System
Tests every endpoint: GET /api/data, POST /api/bookings, 
POST /api/vehicles, POST /api/customers, POST /api/reseed
"""

import json
import socket
import urllib.request
import urllib.error

# Global 15-second timeout on all socket operations (prevents hanging)
socket.setdefaulttimeout(15)

BASE_URL = "http://localhost:8000"
PASS = 0
FAIL = 0

def req(method, path, body=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def check(label, condition, got=None):
    global PASS, FAIL
    if condition:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}  |  got: {got}")
        FAIL += 1

# ============================================================
# STEP 0 — Reseed the database so tests run on clean state
# ============================================================
print("\n=== STEP 0: RESEED DATABASE ===")
status, body = req("POST", "/api/reseed")
check("POST /api/reseed returns 200", status == 200, status)
check("Reseed returns success=True", body.get("success") is True, body)

# ============================================================
# STEP 1 — GET /api/data — full data load
# ============================================================
print("\n=== STEP 1: GET /api/data (Full Data Load) ===")
status, data = req("GET", "/api/data")
check("GET /api/data returns 200", status == 200, status)
check("Response has 'vehicles' key", "vehicles" in data, list(data.keys()))
check("Response has 'customers' key", "customers" in data, list(data.keys()))
check("Response has 'bookings' key", "bookings" in data, list(data.keys()))
check("Response has 'stats' key", "stats" in data, list(data.keys()))

vehicles = data.get("vehicles", [])
customers = data.get("customers", [])
bookings = data.get("bookings", [])
stats = data.get("stats", {})

check("Vehicles list is not empty (seeded)", len(vehicles) > 0, len(vehicles))
check("Customers list is not empty (seeded)", len(customers) > 0, len(customers))
check("Bookings list is not empty (seeded)", len(bookings) > 0, len(bookings))
check("stats.total_vehicles > 0", stats.get("total_vehicles", 0) > 0, stats)
check("stats.total_revenue is numeric", isinstance(stats.get("total_revenue"), (int, float)), stats)

# Verify vehicle record schema
v = vehicles[0]
check("Vehicle has 'id' field", "id" in v, list(v.keys()))
check("Vehicle has 'make' field", "make" in v, list(v.keys()))
check("Vehicle has 'model' field", "model" in v, list(v.keys()))
check("Vehicle has 'hourly_rate' field", "hourly_rate" in v, list(v.keys()))
check("Vehicle has 'daily_rate' field", "daily_rate" in v, list(v.keys()))
check("Vehicle has 'status' field", "status" in v, list(v.keys()))
check("Vehicle has 'license_plate' field", "license_plate" in v, list(v.keys()))

# Verify booking billing record schema
b = bookings[0]
check("Booking has 'booking_id'", "booking_id" in b, list(b.keys()))
check("Booking has 'vehicle_name'", "vehicle_name" in b, list(b.keys()))
check("Booking has 'customer_name'", "customer_name" in b, list(b.keys()))
check("Booking has 'total_hours'", "total_hours" in b, list(b.keys()))
check("Booking has 'full_days'", "full_days" in b, list(b.keys()))
check("Booking has 'remaining_hours'", "remaining_hours" in b, list(b.keys()))
check("Booking has 'total_cost'", "total_cost" in b, list(b.keys()))
check("Booking has 'status'", "status" in b, list(b.keys()))

# ============================================================
# STEP 2 — POST /api/vehicles  
# ============================================================
print("\n=== STEP 2: POST /api/vehicles ===")

# 2a. Valid vehicle creation
status, body = req("POST", "/api/vehicles", {
    "license_plate": "TEST-001",
    "make": "BMW",
    "model": "X5",
    "year": 2025,
    "hourly_rate": 25.00,
    "daily_rate": 120.00,
    "status": "active"
})
check("Valid vehicle creation returns 201", status == 201, status)
check("Response has success=True", body.get("success") is True, body)

# 2b. Duplicate license plate (must fail)
status, body = req("POST", "/api/vehicles", {
    "license_plate": "TEST-001",  # duplicate
    "make": "Audi",
    "model": "Q7",
    "year": 2024,
    "hourly_rate": 20.00,
    "daily_rate": 100.00,
    "status": "active"
})
check("Duplicate license plate returns 400", status == 400, status)

# 2c. Missing required fields (must fail with 400)
status, body = req("POST", "/api/vehicles", {
    "make": "Honda",  # missing license_plate, model, year, rates
})
check("Missing required vehicle fields returns 400", status == 400, status)

# 2d. Maintenance status vehicle creation
status, body = req("POST", "/api/vehicles", {
    "license_plate": "MAINT-002",
    "make": "Ford",
    "model": "F-150",
    "year": 2022,
    "hourly_rate": 18.00,
    "daily_rate": 85.00,
    "status": "maintenance"
})
check("Maintenance-status vehicle creation returns 201", status == 201, status)

# ============================================================
# STEP 3 — POST /api/customers
# ============================================================
print("\n=== STEP 3: POST /api/customers ===")

# 3a. Valid customer creation
status, body = req("POST", "/api/customers", {
    "name": "Test User Alpha",
    "email": "alpha@testdomain.com",
    "phone": "555-9999"
})
check("Valid customer creation returns 201", status == 201, status)
check("Customer response has success=True", body.get("success") is True, body)

# 3b. Duplicate email (must fail)
status, body = req("POST", "/api/customers", {
    "name": "Another Person",
    "email": "alpha@testdomain.com",  # duplicate
    "phone": "555-0001"
})
check("Duplicate email returns 400", status == 400, status)

# 3c. Missing name (must fail)
status, body = req("POST", "/api/customers", {
    "email": "noname@test.com"
    # missing 'name'
})
check("Missing name returns 400", status == 400, status)

# 3d. Missing email (must fail)
status, body = req("POST", "/api/customers", {
    "name": "No Email Person"
    # missing 'email'
})
check("Missing email returns 400", status == 400, status)

# 3e. Customer without phone (optional field)
status, body = req("POST", "/api/customers", {
    "name": "No Phone Person",
    "email": "nophone@testdomain.com"
    # no phone
})
check("Customer without phone (optional) returns 201", status == 201, status)

# ============================================================
# STEP 4 — POST /api/bookings  
# ============================================================
print("\n=== STEP 4: POST /api/bookings ===")

# Fetch fresh data to get valid IDs
_, fresh = req("GET", "/api/data")
active_vehicles = [v for v in fresh["vehicles"] if v["status"] == "active"]
customers = fresh["customers"]

v_id = active_vehicles[0]["id"]
c_id = customers[0]["id"]

# 4a. Valid booking creation
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id,
    "customer_id": c_id,
    "start_time": "2026-09-01 10:00:00",
    "end_time":   "2026-09-01 15:00:00",
    "status": "confirmed"
})
check("Valid booking creation returns 201", status == 201, status)
check("Booking response has success=True", body.get("success") is True, body)

# 4b. Double booking — same vehicle, overlapping times (must fail with 409)
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id,
    "customer_id": c_id,
    "start_time": "2026-09-01 12:00:00",  # overlaps 10:00–15:00
    "end_time":   "2026-09-01 17:00:00",
    "status": "confirmed"
})
check("Double booking overlap returns 409", status == 409, status)
check("Double booking error message present", "Double Booking" in body.get("error",""), body)

# 4c. Reverse time (end before start) — must fail 400
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id,
    "customer_id": c_id,
    "start_time": "2026-09-05 17:00:00",
    "end_time":   "2026-09-05 10:00:00",  # end < start
    "status": "confirmed"
})
check("Reversed times (end < start) returns 400", status == 400, status)

# 4d. Contiguous booking (immediately after) — must succeed
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id,
    "customer_id": c_id,
    "start_time": "2026-09-01 15:00:00",  # starts exactly when previous ends
    "end_time":   "2026-09-01 18:00:00",
    "status": "confirmed"
})
check("Contiguous (touching) booking returns 201", status == 201, status)

# 4e. Missing required fields
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id
    # missing customer_id, start_time, end_time
})
check("Missing booking fields returns 400", status == 400, status)

# 4f. Same vehicle but 'cancelled' status should not block overlapping slot
status, body = req("POST", "/api/bookings", {
    "vehicle_id": v_id,
    "customer_id": c_id,
    "start_time": "2026-09-01 12:00:00",
    "end_time":   "2026-09-01 14:00:00",
    "status": "cancelled"  # cancelled — trigger should NOT fire
})
check("Cancelled-status overlapping booking returns 201", status == 201, status)

# ============================================================
# STEP 5 — Static asset serving
# ============================================================
print("\n=== STEP 5: Static File Serving ===")

def req_raw(path):
    url = BASE_URL + path
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""

status, ct = req_raw("/")
check("GET / returns 200", status == 200, status)
check("GET / serves text/html", "text/html" in ct, ct)

status, ct = req_raw("/index.css")
check("GET /index.css returns 200", status == 200, status)
check("GET /index.css serves text/css", "text/css" in ct, ct)

status, ct = req_raw("/index.js")
check("GET /index.js returns 200", status == 200, status)
check("GET /index.js serves application/javascript", "javascript" in ct, ct)

status, ct = req_raw("/does-not-exist.html")
check("GET /nonexistent returns 404", status == 404, status)

# ============================================================
# STEP 6 — Data consistency verification after all mutations
# ============================================================
print("\n=== STEP 6: Data Consistency After All Mutations ===")
_, final = req("GET", "/api/data")

total_vehicles = final["stats"]["total_vehicles"]
total_revenue = final["stats"]["total_revenue"]

check("Total vehicles count > seeded count (new ones added)", total_vehicles > 5, total_vehicles)
check("Total revenue is positive (bookings exist)", total_revenue > 0, total_revenue)

# Verify billing math on a known booking: 5 hours @ active vehicle rate
billing_entries = final["bookings"]
sept1_booking = next((b for b in billing_entries if b["start_time"] == "2026-09-01 10:00:00"), None)
check("September test booking is in billing view", sept1_booking is not None, [b["start_time"] for b in billing_entries])
if sept1_booking:
    check("September booking total_hours = 5", sept1_booking["total_hours"] == 5, sept1_booking["total_hours"])
    check("September booking full_days = 0", sept1_booking["full_days"] == 0, sept1_booking["full_days"])
    check("September booking remaining_hours = 5", sept1_booking["remaining_hours"] == 5, sept1_booking["remaining_hours"])

# ============================================================
# FINAL SUMMARY
# ============================================================
total = PASS + FAIL
print(f"\n{'='*45}")
print(f" RESULTS: {PASS}/{total} tests passed, {FAIL} failed")
print(f"{'='*45}\n")
if FAIL > 0:
    exit(1)
