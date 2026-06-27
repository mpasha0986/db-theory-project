-- Schema for SQLite
-- Vehicle Rental System

-- Enable foreign keys support in SQLite
PRAGMA foreign_keys = ON;

-- 1. Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_plate TEXT UNIQUE NOT NULL,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    hourly_rate REAL NOT NULL CHECK(hourly_rate >= 0),
    daily_rate REAL NOT NULL CHECK(daily_rate >= 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'maintenance', 'retired'))
);

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT
);

-- 3. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    start_time TEXT NOT NULL, -- Stored as ISO8601 string: YYYY-MM-DD HH:MM:SS
    end_time TEXT NOT NULL,   -- Stored as ISO8601 string: YYYY-MM-DD HH:MM:SS
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    
    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Ensure chronological order
    CONSTRAINT chk_booking_times CHECK (datetime(end_time) > datetime(start_time))
);

-- Index to optimize conflict resolution and booking lookups
CREATE INDEX IF NOT EXISTS idx_bookings_overlap 
ON bookings (vehicle_id, start_time, end_time) 
WHERE status = 'confirmed';

-- 4. Trigger: Double Booking Prevention on INSERT
CREATE TRIGGER IF NOT EXISTS prevent_booking_overlap_insert
BEFORE INSERT ON bookings
FOR EACH ROW
WHEN NEW.status = 'confirmed'
BEGIN
    SELECT RAISE(ABORT, 'Double booking error: The vehicle is already booked for this time period.')
    WHERE EXISTS (
        SELECT 1 
        FROM bookings
        WHERE vehicle_id = NEW.vehicle_id
          AND status = 'confirmed'
          AND datetime(NEW.start_time) < datetime(end_time)
          AND datetime(NEW.end_time) > datetime(start_time)
    );
END;

-- 5. Trigger: Double Booking Prevention on UPDATE
CREATE TRIGGER IF NOT EXISTS prevent_booking_overlap_update
BEFORE UPDATE OF vehicle_id, start_time, end_time, status ON bookings
FOR EACH ROW
WHEN NEW.status = 'confirmed'
BEGIN
    SELECT RAISE(ABORT, 'Double booking error: The vehicle is already booked for this time period.')
    WHERE EXISTS (
        SELECT 1 
        FROM bookings
        WHERE vehicle_id = NEW.vehicle_id
          AND id != OLD.id
          AND status = 'confirmed'
          AND datetime(NEW.start_time) < datetime(end_time)
          AND datetime(NEW.end_time) > datetime(start_time)
    );
END;
