// Global Application State
let appData = {
    vehicles: [],
    customers: [],
    bookings: [],
    stats: {}
};

// API Endpoint URLs
const API_DATA = "/api/data";
const API_BOOKINGS = "/api/bookings";
const API_VEHICLES = "/api/vehicles";
const API_CUSTOMERS = "/api/customers";
const API_RESEED = "/api/reseed";

// Initialize application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initForms();
    initPriceEstimator();
    loadAllData();
});

// 1. Navigation Controller (Tabs switcher)
function initNavigation() {
    const menuItems = document.querySelectorAll(".menu-item");
    const tabPanes = document.querySelectorAll(".tab-pane");

    menuItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // Remove active classes
            menuItems.forEach(m => m.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            // Add active class to clicked menu item
            item.classList.add("active");
            
            // Show target tab pane
            const tabId = `tab-${item.dataset.tab}`;
            const targetPane = document.getElementById(tabId);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });
}

// 2. Load Data from Backend API
async function loadAllData() {
    try {
        const response = await fetch(API_DATA);
        if (!response.ok) throw new Error("Failed to fetch dashboard data");
        
        appData = await response.json();
        
        updateStats();
        populateTables();
        populateFormDropdowns();
        renderVehiclesGrid();
    } catch (error) {
        showToast("Database Connection Error", error.message, "error");
    }
}

// 3. Update Dashboard Stats Cards
function formatCurrency(amount) {
    return `PKR ${Number(amount || 0).toFixed(2)}`;
}

function updateStats() {
    const stats = appData.stats;
    document.getElementById("stat-total-vehicles").innerText = stats.total_vehicles || 0;
    document.getElementById("stat-active-bookings").innerText = stats.active_bookings || 0;
    document.getElementById("stat-total-revenue").innerText = formatCurrency(stats.total_revenue || 0);
}

// 4. Populate Tables (Bookings, Customers, Fleet Availability, Financial Performance)
function populateTables() {
    // A. Populate Bookings Table
    const bookingsTableBody = document.querySelector("#table-bookings tbody");
    bookingsTableBody.innerHTML = "";
    
    if (appData.bookings.length === 0) {
        bookingsTableBody.innerHTML = `<tr><td colspan="8" class="text-center">No bookings found in database.</td></tr>`;
    } else {
        appData.bookings.forEach(b => {
            const statusClass = b.status === "confirmed" ? "badge-success" : 
                                b.status === "completed" ? "badge-info" :
                                b.status === "pending" ? "badge-warning" : "badge-danger";
            
            // Format dates
            const startStr = formatDate(b.start_time);
            const endStr = formatDate(b.end_time);
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>#${b.booking_id}</strong></td>
                <td>${b.vehicle_name}</td>
                <td>${b.customer_name}</td>
                <td>
                    <div style="font-size: 0.85rem;"><strong>From:</strong> ${startStr}</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary);"><strong>To:</strong> ${endStr}</div>
                </td>
                <td>${b.total_hours} hrs</td>
                <td>
                    <span style="font-size: 0.8rem; color: var(--text-muted);">
                        ${b.full_days}d + ${b.remaining_hours}h
                    </span>
                </td>
                <td><strong style="color: var(--success-color);">${formatCurrency(b.total_cost)}</strong></td>
                <td><span class="badge ${statusClass}">${b.status}</span></td>
            `;
            bookingsTableBody.appendChild(tr);
        });
    }

    // B. Populate Fleet Availability Table (Dashboard)
    const availTableBody = document.querySelector("#table-availability tbody");
    availTableBody.innerHTML = "";
    
    if (appData.vehicles.length === 0) {
        availTableBody.innerHTML = `<tr><td colspan="3" class="text-center">No vehicles registered.</td></tr>`;
    } else {
        // Query availability directly from live database view/calculations
        const now = new Date();
        
        appData.vehicles.forEach(v => {
            // Find if there is a confirmed booking active at the current moment
            const isOccupied = appData.bookings.some(b => {
                if (b.vehicle_id !== v.id || b.status !== "confirmed") return false;
                const start = new Date(b.start_time.replace(/-/g, "/"));
                const end = new Date(b.end_time.replace(/-/g, "/"));
                return now >= start && now < end;
            });
            
            const statusLabel = isOccupied ? "Occupied" : "Available";
            const badgeClass = isOccupied ? "badge-danger" : "badge-success";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${v.make} ${v.model}</strong> <span style="font-size:0.8rem; color:var(--text-secondary)">(${v.year})</span></td>
                <td><span class="plate-badge">${v.license_plate}</span></td>
                <td><span class="badge ${badgeClass}">${statusLabel}</span></td>
            `;
            availTableBody.appendChild(tr);
        });
    }

    // C. Populate Financial Performance Report Table (Dashboard)
    const revTableBody = document.querySelector("#table-revenue tbody");
    revTableBody.innerHTML = "";
    
    // Aggregate data per vehicle based on current bookings loaded
    const revenueMap = {};
    
    // Seed map with all vehicles
    appData.vehicles.forEach(v => {
        revenueMap[v.id] = {
            id: v.id,
            name: `${v.make} ${v.model}`,
            bookings: 0,
            revenue: 0.0
        };
    });
    
    // Aggregate bookings cost
    appData.bookings.forEach(b => {
        if (revenueMap[b.vehicle_id] && (b.status === "confirmed" || b.status === "completed")) {
            revenueMap[b.vehicle_id].bookings += 1;
            revenueMap[b.vehicle_id].revenue += b.total_cost;
        }
    });
    
    const sortedRevenue = Object.values(revenueMap).sort((a, b) => b.revenue - a.revenue);
    
    if (sortedRevenue.length === 0) {
        revTableBody.innerHTML = `<tr><td colspan="4" class="text-center">No bookings data available.</td></tr>`;
    } else {
        sortedRevenue.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>#${row.id}</td>
                <td><strong>${row.name}</strong></td>
                <td>${row.bookings}</td>
                <td><strong style="color: var(--success-color);">${formatCurrency(row.revenue)}</strong></td>
            `;
            revTableBody.appendChild(tr);
        });
    }

    // D. Populate Customers Table
    const customersTableBody = document.querySelector("#table-customers tbody");
    customersTableBody.innerHTML = "";
    
    if (appData.customers.length === 0) {
        customersTableBody.innerHTML = `<tr><td colspan="4" class="text-center">No customers registered.</td></tr>`;
    } else {
        appData.customers.forEach(c => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>#${c.id}</td>
                <td><strong>${c.name}</strong></td>
                <td>${c.email}</td>
                <td>${c.phone || '<span style="color:var(--text-muted)">N/A</span>'}</td>
            `;
            customersTableBody.appendChild(tr);
        });
    }
}

// 5. Render Vehicles Grid Card View (Vehicles Tab)
function renderVehiclesGrid() {
    const grid = document.getElementById("vehicles-grid");
    grid.innerHTML = "";
    
    if (appData.vehicles.length === 0) {
        grid.innerHTML = `<div class="content-card text-center" style="grid-column: 1/-1; padding: 2rem;">No vehicles found. Add one on the left.</div>`;
        return;
    }
    
    appData.vehicles.forEach(v => {
        const statusBadge = v.status === "active" ? "badge-success" : 
                            v.status === "maintenance" ? "badge-warning" : "badge-danger";
                            
        const card = document.createElement("div");
        card.className = "vehicle-card";
        card.innerHTML = `
            <div class="vehicle-card-hero">
                <h3>${v.make} ${v.model}</h3>
                <span class="plate-badge">${v.license_plate}</span>
                <span class="badge ${statusBadge}">${v.status}</span>
            </div>
            <div class="vehicle-card-details">
                <div style="font-size:0.85rem; color:var(--text-secondary)">
                    <strong>Year:</strong> ${v.year}
                </div>
                <div class="rates-list">
                    <div class="rate-item">
                        <span class="rate-val">${formatCurrency(v.hourly_rate)}</span>
                        <span class="rate-lbl">per hour</span>
                    </div>
                    <div class="rate-item">
                        <span class="rate-val">${formatCurrency(v.daily_rate)}</span>
                        <span class="rate-lbl">per day</span>
                    </div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// 6. Populate Form Select Elements (Customers and Vehicles options)
function populateFormDropdowns() {
    const customerSelect = document.getElementById("booking-customer");
    const vehicleSelect = document.getElementById("booking-vehicle");
    
    // Save current values if possible
    const currentCustomer = customerSelect.value;
    const currentVehicle = vehicleSelect.value;
    
    customerSelect.innerHTML = `<option value="" disabled>Select Customer</option>`;
    appData.customers.forEach(c => {
        const option = document.createElement("option");
        option.value = c.id;
        option.innerText = `${c.name} (${c.email})`;
        customerSelect.appendChild(option);
    });
    
    vehicleSelect.innerHTML = `<option value="" disabled>Select Vehicle</option>`;
    appData.vehicles.forEach(v => {
        if (v.status === "active") {
            const option = document.createElement("option");
            option.value = v.id;
            option.innerText = `${v.make} ${v.model} - ${formatCurrency(v.daily_rate)}/day`;
            vehicleSelect.appendChild(option);
        }
    });
    
    // Restore values if still available
    if (currentCustomer) customerSelect.value = currentCustomer;
    if (currentVehicle) vehicleSelect.value = currentVehicle;
}

// 7. Form Handlers & Submission Requests
function initForms() {
    // A. Reseed Database button click
    document.getElementById("btn-reseed").addEventListener("click", async () => {
        if (!confirm("Are you sure you want to reset the database? This will clear all changes and re-seed clean default data.")) return;
        
        try {
            const response = await fetch(API_RESEED, { method: "POST" });
            const result = await response.json();
            
            if (response.ok) {
                showToast("Database Reset Success", result.message, "success");
                loadAllData();
            } else {
                showToast("Database Reset Failed", result.error || "Unknown error occurred.", "error");
            }
        } catch (err) {
            showToast("Server Connection Failed", err.message, "error");
        }
    });
    
    // B. Create Booking Form submission
    document.getElementById("form-new-booking").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const vehicle_id = parseInt(document.getElementById("booking-vehicle").value);
        const customer_id = parseInt(document.getElementById("booking-customer").value);
        const startRaw = document.getElementById("booking-start").value;
        const endRaw = document.getElementById("booking-end").value;
        
        // Convert input dates to ISO8601 strings (YYYY-MM-DD HH:MM:SS) for SQLite
        const start_time = formatDateTimeString(startRaw);
        const end_time = formatDateTimeString(endRaw);
        
        const payload = { vehicle_id, customer_id, start_time, end_time, status: "confirmed" };
        
        try {
            const response = await fetch(API_BOOKINGS, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showToast("Booking Successful!", result.message, "success");
                document.getElementById("form-new-booking").reset();
                document.getElementById("live-estimator").classList.add("hidden");
                loadAllData();
            } else {
                // Display error (e.g. Double Booking overlap warning or timing constraints)
                showToast(result.error || "Booking Failed", result.details || "Constraint check error.", "error");
            }
        } catch (err) {
            showToast("Network Error", err.message, "error");
        }
    });

    // C. Create Vehicle Form submission
    document.getElementById("form-new-vehicle").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const make = document.getElementById("vehicle-make").value.trim();
        const model = document.getElementById("vehicle-model").value.trim();
        const year = parseInt(document.getElementById("vehicle-year").value);
        const license_plate = document.getElementById("vehicle-plate").value.trim().toUpperCase();
        const hourly_rate = parseFloat(document.getElementById("vehicle-hourly").value);
        const daily_rate = parseFloat(document.getElementById("vehicle-daily").value);
        const status = document.getElementById("vehicle-status").value;
        
        const payload = { make, model, year, license_plate, hourly_rate, daily_rate, status };
        
        try {
            const response = await fetch(API_VEHICLES, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showToast("Vehicle Registered", result.message, "success");
                document.getElementById("form-new-vehicle").reset();
                loadAllData();
            } else {
                showToast(result.error || "Registration Failed", result.details || "Error saving vehicle.", "error");
            }
        } catch (err) {
            showToast("Network Error", err.message, "error");
        }
    });

    // D. Create Customer Form submission
    document.getElementById("form-new-customer").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const name = document.getElementById("customer-name").value.trim();
        const email = document.getElementById("customer-email").value.trim();
        const phone = document.getElementById("customer-phone").value.trim();
        
        const payload = { name, email, phone };
        
        try {
            const response = await fetch(API_CUSTOMERS, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showToast("Customer Registered", result.message, "success");
                document.getElementById("form-new-customer").reset();
                loadAllData();
            } else {
                showToast(result.error || "Failed to add Customer", result.details || "Error creating profile.", "error");
            }
        } catch (err) {
            showToast("Network Error", err.message, "error");
        }
    });
}

// 8. Live Estimator Logic (WOW factor)
function initPriceEstimator() {
    const vehicleSelect = document.getElementById("booking-vehicle");
    const startInput = document.getElementById("booking-start");
    const endInput = document.getElementById("booking-end");
    const estimatorPanel = document.getElementById("live-estimator");
    
    const calculateEstimate = () => {
        const vehicleId = parseInt(vehicleSelect.value);
        const startVal = startInput.value;
        const endVal = endInput.value;
        
        if (!vehicleId || !startVal || !endVal) {
            estimatorPanel.classList.add("hidden");
            return;
        }
        
        const startTime = new Date(startVal);
        const endTime = new Date(endVal);
        
        const diffSeconds = (endTime.getTime() - startTime.getTime()) / 1000;
        
        if (diffSeconds <= 0) {
            estimatorPanel.classList.add("hidden");
            return;
        }
        
        // Find vehicle rate details
        const selectedVehicle = appData.vehicles.find(v => v.id === vehicleId);
        if (!selectedVehicle) {
            estimatorPanel.classList.add("hidden");
            return;
        }
        
        const hourlyRate = selectedVehicle.hourly_rate;
        const dailyRate = selectedVehicle.daily_rate;
        
        // Perform standard database math:
        // total_hours = CEIL(diffSeconds / 3600)
        const totalHours = Math.ceil(diffSeconds / 3600);
        const days = Math.floor(totalHours / 24);
        const remainingHours = totalHours % 24;
        
        const hourlyCost = remainingHours * hourlyRate;
        const cappedHourlyCost = Math.min(hourlyCost, dailyRate);
        const totalCost = (days * dailyRate) + cappedHourlyCost;
        
        // Populate UI
        document.getElementById("est-duration").innerText = `${totalHours} Hour${totalHours > 1 ? 's' : ''}`;
        document.getElementById("est-days").innerText = `${days} Day${days !== 1 ? 's' : ''} (${formatCurrency(days * dailyRate)})`;
        document.getElementById("est-hours").innerText = `${remainingHours} Hr${remainingHours !== 1 ? 's' : ''} (${formatCurrency(hourlyCost)}${hourlyCost > dailyRate ? ` capped at ${formatCurrency(dailyRate)}` : ''})`;
        document.getElementById("est-price").innerText = formatCurrency(totalCost);
        
        estimatorPanel.classList.remove("hidden");
    };
    
    // Bind listeners
    vehicleSelect.addEventListener("change", calculateEstimate);
    startInput.addEventListener("input", calculateEstimate);
    endInput.addEventListener("input", calculateEstimate);
}

// Helper: Format HTML datetime-local picker string to SQLite YYYY-MM-DD HH:MM:SS format
function formatDateTimeString(dateTimeLocalStr) {
    if (!dateTimeLocalStr) return "";
    // Input is 'YYYY-MM-DDTHH:MM' -> replace T with space and append seconds ':00'
    return dateTimeLocalStr.replace("T", " ") + ":00";
}

// Helper: Format raw ISO8601 database string YYYY-MM-DD HH:MM:SS to client-friendly text
function formatDate(dbDateStr) {
    if (!dbDateStr) return "-";
    // Replace space with T to satisfy JS Date constructor
    const date = new Date(dbDateStr.replace(" ", "T"));
    return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
    }) + " at " + date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit"
    });
}

// 9. Floating Toast Notifications Builder
function showToast(title, message, type = "success") {
    const container = document.getElementById("toast-container");
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    const icon = type === "success" 
        ? '<i class="fa-solid fa-circle-check toast-icon"></i>' 
        : '<i class="fa-solid fa-triangle-exclamation toast-icon"></i>';
        
    toast.innerHTML = `
        ${icon}
        <div class="toast-body">
            <h4>${title}</h4>
            <p>${message}</p>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Remove toast after 6 seconds
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(50px)";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 6000);
}
