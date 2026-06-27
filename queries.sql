-- Rate Calculations and Queries
-- Vehicle Rental System

-- ============================================================================
-- SECTION 1: SQLite Billing View & Queries
-- ============================================================================

-- Create a view in SQLite that calculates the duration, breaks it down,
-- caps remaining hours at the daily rate, and returns the total cost.
-- Uses pure integer arithmetic to implement CEIL(seconds/3600) for portability.
CREATE VIEW IF NOT EXISTS view_booking_billing AS
SELECT 
    b.id AS booking_id,
    b.vehicle_id,
    v.make || ' ' || v.model AS vehicle_name,
    b.customer_id,
    c.name AS customer_name,
    b.start_time,
    b.end_time,
    b.status,
    v.hourly_rate AS hourly_rate,
    v.daily_rate AS daily_rate,
    -- Calculate total duration in hours, rounded up (CEIL)
    CAST(
        (strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600 
        AS INTEGER
    ) AS total_hours,
    -- Full days rented
    CAST(
        ((strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600) / 24
        AS INTEGER
    ) AS full_days,
    -- Remaining hours after full days
    CAST(
        ((strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600) % 24
        AS INTEGER
    ) AS remaining_hours,
    -- Total cost calculation
    (
        CAST(
            ((strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600) / 24
            AS INTEGER
        ) * v.daily_rate
    ) + 
    CASE 
        WHEN (CAST(
            ((strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600) % 24
            AS INTEGER
        ) * v.hourly_rate) < v.daily_rate
        THEN (CAST(
            ((strftime('%s', b.end_time) - strftime('%s', b.start_time) + 3599) / 3600) % 24
            AS INTEGER
        ) * v.hourly_rate)
        ELSE v.daily_rate
    END AS total_cost
FROM bookings b
JOIN vehicles v ON b.vehicle_id = v.id
JOIN customers c ON b.customer_id = c.id;


-- ============================================================================
-- SECTION 2: PostgreSQL Billing View (Equivalent Logic)
-- ============================================================================
/*
CREATE OR REPLACE VIEW postgres_booking_billing AS
WITH billing_calculations AS (
    SELECT 
        b.id AS booking_id,
        b.vehicle_id,
        v.make || ' ' || v.model AS vehicle_name,
        b.customer_id,
        c.name AS customer_name,
        b.start_time,
        b.end_time,
        b.status,
        v.hourly_rate,
        v.daily_rate,
        -- Calculate total billing hours using CEIL on epoch difference
        CEIL(EXTRACT(EPOCH FROM (b.end_time - b.start_time)) / 3600.0)::INT AS total_hours
    FROM bookings b
    JOIN vehicles v ON b.vehicle_id = v.id
    JOIN customers c ON b.customer_id = c.id
)
SELECT 
    booking_id,
    vehicle_id,
    vehicle_name,
    customer_id,
    customer_name,
    start_time,
    end_time,
    status,
    hourly_rate,
    daily_rate,
    total_hours,
    (total_hours / 24)::INT AS full_days,
    (total_hours % 24)::INT AS remaining_hours,
    -- Calculate final amount with cap
    (total_hours / 24)::INT * daily_rate + 
    CASE 
        WHEN (total_hours % 24) * hourly_rate < daily_rate 
        THEN (total_hours % 24) * hourly_rate
        ELSE daily_rate
    END AS total_cost
FROM billing_calculations;
*/


-- ============================================================================
-- SECTION 3: Useful System Queries
-- ============================================================================

-- 1. Find the current availability of all active vehicles
-- Shows if a vehicle is currently occupied based on confirmed, ongoing bookings.
-- (This query is designed for SQLite, but works on standard SQL).
-- To test with a specific time, replace datetime('now') with the target time.
-- SELECT * FROM vehicle_availability;
CREATE VIEW IF NOT EXISTS vehicle_availability AS
SELECT 
    v.id AS vehicle_id,
    v.make,
    v.model,
    v.license_plate,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM bookings b
            WHERE b.vehicle_id = v.id
              AND b.status = 'confirmed'
              -- Check if current time falls within booking range
              AND datetime('now') >= datetime(b.start_time)
              AND datetime('now') < datetime(b.end_time)
        ) THEN 'Occupied'
        ELSE 'Available'
    END AS availability_status
FROM vehicles v
WHERE v.status = 'active';

-- 2. Total revenue generated per vehicle
-- SELECT * FROM vehicle_revenue_report;
CREATE VIEW IF NOT EXISTS vehicle_revenue_report AS
SELECT 
    vehicle_id,
    vehicle_name,
    COUNT(booking_id) AS total_bookings,
    SUM(CASE WHEN status = 'completed' OR status = 'confirmed' THEN total_cost ELSE 0 END) AS total_revenue
FROM view_booking_billing
GROUP BY vehicle_id
ORDER BY total_revenue DESC;
