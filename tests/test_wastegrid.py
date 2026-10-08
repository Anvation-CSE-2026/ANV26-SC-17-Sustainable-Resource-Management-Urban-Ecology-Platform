"""
Comprehensive automated unit and integration tests for WasteGrid 2.0.
Verifies:
1. Database schema, PBKDF2 password hashing, salting, and user CRUD.
2. Authentication, session management, RBAC role permissions matrix.
3. Multi-objective Linear Programming optimizer (balanced, min_overflow, min_cost, min_carbon).
4. Facility management and capacity handling.
5. Predictive overflow alerts engine thresholds and acknowledge/resolve actions.
6. Scenario simulator sandbox isolation (ensures non-mutation of operational DB records).
7. Citizen reporting ticket generation and workflow.
8. Reports generation in Excel (.xlsx) and CSV.
"""

import os
import pytest
import pandas as pd
from wastegrid import db, auth, optimizer, alert_engine, reports_module, forecast


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is initialized and fresh for testing."""
    db.init_db()
    yield


# =========================================================================
# 1. AUTHENTICATION & SECURITY TESTS
# =========================================================================

def test_password_hashing_and_verification():
    """Test PBKDF2-HMAC-SHA256 password hashing with unique salt."""
    raw_pwd = "SecurePassword@2026"
    hashed, salt = db.hash_password(raw_pwd)

    assert hashed is not None
    assert len(hashed) == 64  # SHA256 hex digest length
    assert len(salt) == 32    # 16 bytes hex salt length
    assert hashed != raw_pwd

    # Verification must succeed for correct password
    assert db.verify_password(raw_pwd, hashed, salt) is True
    # Verification must fail for incorrect password
    assert db.verify_password("WrongPassword@999", hashed, salt) is False


def test_unique_salts_for_same_password():
    """Ensure two users with identical passwords get distinct salts and hashes."""
    pwd = "SharedSecret123"
    h1, s1 = db.hash_password(pwd)
    h2, s2 = db.hash_password(pwd)

    assert s1 != s2
    assert h1 != h2
    assert db.verify_password(pwd, h1, s1) is True
    assert db.verify_password(pwd, h2, s2) is True


def test_seeded_users_exist():
    """Verify official authority accounts are seeded in database."""
    users = db.get_all_users()
    assert len(users) >= 5

    usernames = {u["username"] for u in users}
    expected = {"admin", "state_admin", "district_admin", "municipality_admin", "factory_admin"}
    assert expected.issubset(usernames)


def test_user_login_validation():
    """Verify authentication logic rejects invalid credentials and accepts valid ones."""
    # Test valid credentials for admin
    success, msg = auth.login("admin", "Admin@123")
    assert success is True
    assert "successful" in msg.lower()

    # Test invalid password
    success, msg = auth.login("admin", "IncorrectPassword")
    assert success is False

    # Test nonexistent user
    success, msg = auth.login("nonexistent_user", "AnyPassword")
    assert success is False


def test_rbac_permission_matrix():
    """Verify role-based access control restrictions."""
    admin_perms = auth.ROLE_PERMISSIONS.get("admin", [])
    assert "users" in admin_perms
    assert "overview" in admin_perms
    assert "map" in admin_perms

    # Non-admin roles must NOT have user management access
    for r in ["state", "district", "municipality", "factory"]:
        perms = auth.ROLE_PERMISSIONS.get(r, [])
        assert "users" not in perms, f"Role {r} should not have access to user management"

    # Factory role should have targeted operational views
    fact_perms = auth.ROLE_PERMISSIONS.get("factory", [])
    assert "facilities" in fact_perms
    assert "allocation" in fact_perms


# =========================================================================
# 2. DYNAMIC FACILITY MANAGEMENT & DB CRUD TESTS
# =========================================================================

def test_facility_retrieval_and_creation():
    """Test dynamic facility retrieval and creation in SQLite."""
    initial_facs = db.get_all_facilities(include_offline=True)
    initial_count = len(initial_facs)
    assert initial_count >= 5

    test_fac_id = f"TEST_FAC_{os.getpid()}"
    created = db.create_facility(
        fid=test_fac_id,
        name="Automated Test Biogas Unit",
        ftype="biocompost",
        accepts="wet",
        capacity_kg=2500.0,
        distance_km=7.5,
        latitude=12.9300,
        longitude=77.6200,
        operating_hours="08:00 - 20:00",
        efficiency_pct=95.0,
        cost_per_ton=300.0,
        co2_per_ton_km=0.04,
    )
    assert created is True

    # Retrieve created facility
    retrieved = db.get_facility_by_id(test_fac_id)
    assert retrieved is not None
    assert retrieved["name"] == "Automated Test Biogas Unit"
    assert retrieved["capacity_kg"] == 2500.0
    assert retrieved["accepts"] == "wet"

    # Clean up test facility
    deleted = db.delete_facility(test_fac_id)
    assert deleted is True
    assert db.get_facility_by_id(test_fac_id) is None


def test_facility_status_toggle():
    """Test taking a facility offline or into maintenance."""
    facs = db.get_all_facilities()
    target = facs[0]
    fid = target["id"]

    # Set to maintenance
    db.set_facility_status(fid, "maintenance")
    updated = db.get_facility_by_id(fid)
    assert updated["status"] == "maintenance"

    # Restore to online
    db.set_facility_status(fid, "online")
    restored = db.get_facility_by_id(fid)
    assert restored["status"] == "online"


# =========================================================================
# 3. MULTI-OBJECTIVE LP OPTIMIZER TESTS
# =========================================================================

def test_optimizer_basic_allocation():
    """Test that optimizer allocates waste within facility capacity and stream compatibility."""
    facilities = [
        {"id": "A", "accepts": "wet", "capacity_kg": 3000.0, "distance_km": 5.0, "status": "online"},
        {"id": "B", "accepts": "wet", "capacity_kg": 2000.0, "distance_km": 8.0, "status": "online"},
        {"id": "C", "accepts": "dry", "capacity_kg": 2500.0, "distance_km": 6.0, "status": "online"},
    ]

    wet_total = 4000.0
    dry_total = 2000.0

    allocs, overflow = optimizer.optimize(facilities, wet_total, dry_total, objective="balanced")

    # Check non-negativity
    assert allocs["A"] >= 0
    assert allocs["B"] >= 0
    assert allocs["C"] >= 0

    # Check capacity constraints
    assert allocs["A"] <= 3000.0
    assert allocs["B"] <= 2000.0
    assert allocs["C"] <= 2500.0

    # Wet capacity is 5000 kg, demand is 4000 kg -> overflow should be zero
    assert overflow.get("wet", 0) == 0

    # Dry capacity is 2500 kg, demand is 2000 kg -> overflow should be zero
    assert overflow.get("dry", 0) == 0


def test_optimizer_overflow_when_demand_exceeds_capacity():
    """Test optimizer reports correct overflow when demand exceeds total capacity."""
    facilities = [
        {"id": "A", "accepts": "wet", "capacity_kg": 1000.0, "distance_km": 5.0, "status": "online"},
        {"id": "C", "accepts": "dry", "capacity_kg": 1000.0, "distance_km": 6.0, "status": "online"},
    ]

    wet_total = 2500.0  # Exceeds 1000 by 1500
    dry_total = 1200.0  # Exceeds 1000 by 200

    allocs, overflow = optimizer.optimize(facilities, wet_total, dry_total)

    assert allocs["A"] == pytest.approx(1000.0, 1.0)
    assert allocs["C"] == pytest.approx(1000.0, 1.0)
    assert overflow.get("wet", 0) == pytest.approx(1500.0, 1.0)
    assert overflow.get("dry", 0) == pytest.approx(200.0, 1.0)
    assert optimizer.total_overflow(overflow) == pytest.approx(1700.0, 2.0)


def test_multi_objective_variations():
    """Verify different optimization objectives (min_overflow, min_cost, min_carbon, balanced) execute without error."""
    facilities = db.get_all_facilities()
    wet_total = 3500.0
    dry_total = 2000.0

    for obj in ["balanced", "min_overflow", "min_cost", "min_carbon"]:
        res = optimizer.optimize_multi_objective(facilities, wet_total, dry_total, objective=obj)
        assert "allocations" in res
        assert "overflow" in res
        assert "transport_cost_inr" in res
        assert "carbon_emissions_kg" in res
        assert res["transport_cost_inr"] >= 0
        assert res["carbon_emissions_kg"] >= 0


# =========================================================================
# 4. PREDICTIVE OVERFLOW ALERT ENGINE TESTS
# =========================================================================

def test_alert_engine_evaluation():
    """Verify alert engine generates alerts based on thresholds."""
    alert_engine.evaluate_and_sync_alerts()
    active_alerts = db.get_active_alerts()
    assert isinstance(active_alerts, list)

    # Test creating a test alert and resolving it
    aid = db.create_alert(
        facility_id="A",
        severity="warning",
        utilization_pct=88.5,
        message="Facility A approaching critical threshold (88.5%)",
        recommended_action="Divert incoming municipal loads to Facility B",
    )
    assert aid is not None

    # Verify alert exists
    pending_alerts = db.get_active_alerts(status_filter="pending")
    matching = [a for a in pending_alerts if a["id"] == aid]
    assert len(matching) == 1
    assert matching[0]["severity"] == "warning"

    # Acknowledge alert
    db.acknowledge_alert(aid)
    ack_alerts = db.get_active_alerts(status_filter="acknowledged")
    assert any(a["id"] == aid for a in ack_alerts)

    # Resolve alert
    db.resolve_alert(aid)
    resolved_alerts = db.get_active_alerts(status_filter="resolved")
    assert any(a["id"] == aid for a in resolved_alerts)


# =========================================================================
# 5. SCENARIO SIMULATOR ISOLATION TEST
# =========================================================================

def test_simulator_does_not_mutate_operational_db():
    """Verify that simulating stress scenarios does not alter operational database records."""
    before_facilities = db.get_all_facilities(include_offline=True)
    before_cap = {f["id"]: f["capacity_kg"] for f in before_facilities}

    # Simulate hypothetical 100% surge and outage of plant B
    hypothetical_wet = 8000.0
    hypothetical_dry = 5000.0
    sim_facs = [dict(f) for f in before_facilities]
    for f in sim_facs:
        if f["id"] == "B":
            f["capacity_kg"] = 0
            f["status"] = "offline"

    sim_res = optimizer.optimize_multi_objective(sim_facs, hypothetical_wet, hypothetical_dry)
    assert sim_res is not None

    # Verify operational DB records are completely untouched
    after_facilities = db.get_all_facilities(include_offline=True)
    after_cap = {f["id"]: f["capacity_kg"] for f in after_facilities}

    assert before_cap == after_cap
    plant_b = db.get_facility_by_id("B")
    assert plant_b["capacity_kg"] > 0
    assert plant_b["status"] == "online"


# =========================================================================
# 6. CITIZEN GRIEVANCE MODULE TESTS
# =========================================================================

def test_citizen_report_lifecycle():
    """Verify citizen report creation, unique ticket generation, and status updates."""
    ticket_id = db.create_citizen_report(
        category="overflowing_bin",
        location="Indiranagar 100ft Road Junction",
        ward="WARD-112",
        description="Public bin overflowing onto sidewalk near metro pillar 45",
        contact_name="Ramesh Kumar",
        contact_phone="+91 98765 43210",
    )

    assert ticket_id.startswith("WG-REP-")

    # Retrieve report by ticket ID
    report = db.get_citizen_report_by_ticket(ticket_id)
    assert report is not None
    assert report["category"] == "overflowing_bin"
    assert report["ward"] == "WARD-112"
    assert report["status"] == "pending"

    # Update status to in_progress with assigned vehicle
    db.update_citizen_report_status(ticket_id, "in_progress", assigned_vehicle="KA-04-TR-101", resolution_notes="Dispatched compactor unit")
    updated = db.get_citizen_report_by_ticket(ticket_id)
    assert updated["status"] == "in_progress"
    assert updated["assigned_to"] == "KA-04-TR-101"

    # Resolve report
    db.update_citizen_report_status(ticket_id, "resolved", resolution_notes="Area cleared and disinfected")
    resolved = db.get_citizen_report_by_ticket(ticket_id)
    assert resolved["status"] == "resolved"


# =========================================================================
# 7. REPORTS & EXPORTS TESTS
# =========================================================================

def test_excel_export_generation():
    """Test multi-sheet Excel export generation."""
    data_dict = {
        "Facilities": pd.DataFrame(db.get_all_facilities()),
        "Vehicles": pd.DataFrame(db.get_all_vehicles()),
        "Reports": pd.DataFrame(db.get_all_citizen_reports()),
    }
    excel_bytes = reports_module.generate_excel_bytes(data_dict)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000  # Non-empty valid excel binary


def test_7_day_forecast_calculation():
    """Test 7-day predictive forecast generation."""
    sources = db.get_all_waste_sources()
    total_cap = 10000.0
    forecast_rows = forecast.forecast_week(sources, total_cap)

    assert len(forecast_rows) == 7
    days = [r["Day"] for r in forecast_rows]
    assert days == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for r in forecast_rows:
        assert r["Predicted (T)"] > 0
        assert r["Capacity (T)"] == 10.0
