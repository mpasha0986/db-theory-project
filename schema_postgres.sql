-- Schema for PostgreSQL
-- Vehicle Rental System

-- Enable btree_gist extension (required for mixing scalar columns like vehicle_id with ranges in exclusion constraints)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 1. Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    hourly_rate DECIMAL(10, 2) NOT NULL CHECK(hourly_rate >= 0),
    daily_rate DECIMAL(10, 2) NOT NULL CHECK(daily_rate >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'maintenance', 'retired'))
);

-- 2. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20)
);

-- 3. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    customer_id INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed' CHECK(status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    
    -- Ensure chronological order
    CONSTRAINT chk_booking_times CHECK (end_time > start_time),
    
    -- PostgreSQL Exclusion Constraint:
    -- Prevents two bookings from having the same vehicle_id AND overlapping times (&&)
    -- only when the status is 'confirmed'.
    CONSTRAINT exclude_double_booking EXCLUDE USING gist (
        vehicle_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status = 'confirmed')
);

-- Index for regular queries filtering by status and range
CREATE INDEX IF NOT EXISTS idx_bookings_vehicle_dates 
ON bookings (vehicle_id, start_time, end_time);
