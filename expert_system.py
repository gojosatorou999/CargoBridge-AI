"""
CargoBridge AI — Expert System
3-parameter weighted scoring engine + slot optimizer.
No LLMs. Fully deterministic, explainable, auditable.
"""
import math
from datetime import datetime, timedelta


# ── Confidence band definitions ──────────────────────────────────────────────

CONFIDENCE_BANDS = [
    (85, 100, 'Highly Reliable',   'fast-track'),
    (60,  84, 'Good Confidence',   'standard'),
    (40,  59, 'Questionable',      'investigation'),
    (0,   39, 'Low Confidence',    'flagged'),
]

ROLE_TRUST = {
    'port_worker':   1.20,
    'truck_driver':  1.00,
    'msme_exporter': 0.85,
    'analyst':       1.10,
    'admin':         1.20,
}

# Weather codes that corroborate disruption reports
ADVERSE_WEATHER_CODES = {45, 48, 51, 53, 55, 61, 63, 65, 71, 73, 75, 77,
                          80, 81, 82, 85, 86, 95, 96, 99}

VESSEL_DELAY_DISRUPTIONS = {'vessel_delay', 'weather', 'equipment_failure'}
ROAD_DISRUPTIONS = {'road_accident', 'gate_congestion', 'strike', 'customs_delay'}


def haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Parameter 1: Spatial Corroboration (33%) ─────────────────────────────────

def score_spatial_corroboration(report, all_reports, radius_km=5.0, window_hours=24):
    """
    Count similar reports within radius_km in the last window_hours.
    Returns 0–100.
    """
    if report.latitude is None or report.longitude is None:
        return 30.0  # neutral score if no location

    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    cluster = 0
    for r in all_reports:
        if r.id == report.id:
            continue
        if r.created_at < cutoff:
            continue
        if r.latitude is None or r.longitude is None:
            continue
        dist = haversine_km(report.latitude, report.longitude, r.latitude, r.longitude)
        if dist <= radius_km and r.disruption_type == report.disruption_type:
            cluster += 1

    # Map cluster count to score: 0→25, 1→50, 2→70, 3→82, 4+→95
    mapping = {0: 25, 1: 50, 2: 70, 3: 82}
    return mapping.get(cluster, 95) if cluster <= 3 else 95


# ── Parameter 2: AIS + Weather Alignment (33%) ───────────────────────────────

def score_ais_weather_alignment(report, weather_snapshots, ais_snapshots):
    """
    Check whether live weather and AIS data support the disruption claim.
    Returns 0–100.
    """
    score = 50.0  # neutral baseline

    # Weather alignment
    if weather_snapshots:
        latest = weather_snapshots[0]
        weather_code = latest.weather_code or 0
        wind = latest.wind_speed_kmh or 0
        wave = latest.wave_height_m or 0

        is_adverse = weather_code in ADVERSE_WEATHER_CODES or wind > 50 or wave > 2.5

        if report.disruption_type in ('weather', 'vessel_delay') and is_adverse:
            score += 30
        elif report.disruption_type in ROAD_DISRUPTIONS and is_adverse:
            score += 10
        elif report.disruption_type in ('weather', 'vessel_delay') and not is_adverse:
            score -= 20

    # AIS alignment
    if ais_snapshots:
        vessel_count = len(ais_snapshots)
        if report.disruption_type in VESSEL_DELAY_DISRUPTIONS:
            if vessel_count > 8:
                score += 20
            elif vessel_count > 4:
                score += 10

    return max(0.0, min(100.0, score))


# ── Parameter 3: Reporter Credibility (34%) ──────────────────────────────────

def score_reporter_credibility(user, user_reports):
    """
    Based on historical approval rate, account age, and role trust multiplier.
    Returns 0–100.
    """
    base = 50.0

    # Role multiplier
    trust = ROLE_TRUST.get(user.role, 1.0)

    # Historical approval rate
    approved = [r for r in user_reports if r.verification_status == 'approved']
    rejected = [r for r in user_reports if r.verification_status == 'rejected']
    total = len(approved) + len(rejected)
    if total >= 3:
        approval_rate = len(approved) / total
        base = approval_rate * 80  # max 80 from history
    elif total == 0:
        base = 40.0  # new user — lower trust

    # Account age bonus (up to +15)
    if user.created_at:
        age_days = (datetime.utcnow() - user.created_at).days
        age_bonus = min(15, age_days // 30)  # +1 per month, cap 15
        base += age_bonus

    return max(0.0, min(100.0, base * trust))


# ── Composite Score ───────────────────────────────────────────────────────────

def compute_confidence_score(report, user, all_reports, user_reports,
                              weather_snapshots, ais_snapshots):
    """
    Combines 3 parameters into a single confidence score (0–100).
    Returns (score, breakdown_dict, band_label, queue_action).
    """
    s1 = score_spatial_corroboration(report, all_reports)
    s2 = score_ais_weather_alignment(report, weather_snapshots, ais_snapshots)
    s3 = score_reporter_credibility(user, user_reports)

    composite = round(s1 * 0.33 + s2 * 0.33 + s3 * 0.34, 2)

    band_label = 'Low Confidence'
    queue_action = 'flagged'
    for lo, hi, label, action in CONFIDENCE_BANDS:
        if lo <= composite <= hi:
            band_label = label
            queue_action = action
            break

    breakdown = {
        'spatial_corroboration': round(s1, 2),
        'ais_weather_alignment': round(s2, 2),
        'reporter_credibility': round(s3, 2),
        'composite': composite,
        'band': band_label,
        'action': queue_action,
    }
    return composite, breakdown, band_label, queue_action


# ── Slot Optimizer ────────────────────────────────────────────────────────────

PORT_COORDS = {
    'nhava_sheva': (18.9500, 72.8370),
    'mundra':      (22.8330, 69.7167),
    'jebel_ali':   (25.0115, 55.0806),
}

DETENTION_RATE_USD = 150   # per day baseline
USD_TO_AED = 3.67


def _congestion_level(traffic_density, vessel_queue):
    """Map numeric inputs to Low/Medium/High."""
    combined = (traffic_density / 10.0) * 50 + min(vessel_queue, 20) * 2.5
    if combined < 30:
        return 'Low'
    if combined < 60:
        return 'Medium'
    return 'High'


def _estimate_wait_mins(congestion_level):
    return {'Low': 15, 'Medium': 40, 'High': 90}.get(congestion_level, 30)


def generate_slot_recommendation(report, driver, weather_snapshots, ais_snapshots,
                                  traffic_density=5.0):
    """
    Generate an optimal slot recommendation dict for a driver after a disruption.
    Returns a dict with all SlotRecommendation fields populated.
    """
    now = datetime.utcnow()
    vessel_queue = len(ais_snapshots) if ais_snapshots else 4

    weather = weather_snapshots[0] if weather_snapshots else None
    wind = weather.wind_speed_kmh if weather else 15
    weather_code = weather.weather_code if weather else 0
    temp = weather.temp_c if weather else 28

    congestion = _congestion_level(traffic_density, vessel_queue)
    wait_mins = _estimate_wait_mins(congestion)

    # Congestion clearance window — offset slot from now by estimated clearance
    clearance_offset = {'Low': 1, 'Medium': 3, 'High': 6}.get(congestion, 2)
    slot_time = now + timedelta(hours=clearance_offset)

    # Round to nearest 15-minute mark
    minutes = (slot_time.minute // 15 + 1) * 15
    slot_time = slot_time.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)

    # Carbon & fuel savings (baseline vs optimal)
    # Baseline assumption: truck idles 90 min at gate = 3.2 kg CO2, 1.4 L fuel
    idle_reduction_ratio = {'Low': 0.8, 'Medium': 0.5, 'High': 0.2}.get(congestion, 0.5)
    carbon_saving = round(3.2 * idle_reduction_ratio, 2)
    fuel_saving = round(1.4 * idle_reduction_ratio, 2)

    # D&D risk if original slot kept
    days_at_risk = clearance_offset / 24.0
    dd_risk_usd = round(DETENTION_RATE_USD * days_at_risk, 2)
    dd_risk_aed = round(dd_risk_usd * USD_TO_AED, 2)

    # Weather condition string
    if weather_code in ADVERSE_WEATHER_CODES:
        weather_str = 'Adverse'
    elif wind > 30:
        weather_str = 'Windy'
    else:
        weather_str = f'Clear, {int(temp)}°C'

    return {
        'report_id': report.id,
        'truck_driver_id': driver.id,
        'recommended_slot_time': slot_time,
        'estimated_wait_mins': wait_mins,
        'congestion_level': congestion,
        'weather_condition': weather_str,
        'carbon_saving_kg': carbon_saving,
        'fuel_saving_litres': fuel_saving,
        'dd_risk_usd': dd_risk_usd,
        'dd_risk_aed': dd_risk_aed,
        'status': 'pending',
    }


# ── Resilience Simulator ──────────────────────────────────────────────────────

def run_resilience_simulation(inputs):
    """
    Inputs: rainfall_mm, wind_speed_kmh, vessel_queue_count,
            traffic_density (0–10), time_of_day
    Returns: prediction dict with gate_congestion, dispatch_windows,
             dd_risk_usd, sectoral_impact
    """
    rain = inputs.get('rainfall_mm', 0)
    wind = inputs.get('wind_speed_kmh', 0)
    vessels = inputs.get('vessel_queue_count', 0)
    traffic = inputs.get('traffic_density', 0)
    tod = inputs.get('time_of_day', 'morning')

    # Congestion index (0–100)
    rain_factor = min(rain / 100.0, 1.0) * 25
    wind_factor = min(wind / 80.0, 1.0) * 20
    vessel_factor = min(vessels / 20.0, 1.0) * 30
    traffic_factor = (traffic / 10.0) * 20
    tod_factor = {'morning': 5, 'afternoon': 3, 'evening': 8, 'night': 0}.get(tod, 0)

    congestion_index = rain_factor + wind_factor + vessel_factor + traffic_factor + tod_factor

    if congestion_index < 30:
        gate_congestion = 'Low'
    elif congestion_index < 60:
        gate_congestion = 'Medium'
    else:
        gate_congestion = 'High'

    # Optimal dispatch windows (24h)
    windows = _compute_dispatch_windows(congestion_index, tod)

    # D&D risk
    daily_risk = DETENTION_RATE_USD * (congestion_index / 100.0) * 3
    dd_risk_usd = round(daily_risk, 2)

    # Sectoral impact scores
    sectoral = {
        'Port Gate Operations': round(congestion_index, 1),
        'Road Haulage': round(traffic_factor + rain_factor, 1),
        'Vessel Berth Queue': round(vessel_factor + wind_factor, 1),
        'Customs Clearance': round(tod_factor * 2 + rain_factor * 0.5, 1),
    }

    return {
        'gate_congestion': gate_congestion,
        'congestion_index': round(congestion_index, 1),
        'dispatch_windows': windows,
        'dd_risk_usd': dd_risk_usd,
        'dd_risk_aed': round(dd_risk_usd * USD_TO_AED, 2),
        'sectoral_impact': sectoral,
    }


def _compute_dispatch_windows(congestion_index, tod):
    """Return list of recommended 2-hour dispatch windows for next 24h."""
    now = datetime.utcnow()
    windows = []

    # Generate candidate windows every 2 hours
    candidates = []
    for h in range(0, 24, 2):
        candidate = (now + timedelta(hours=h)).replace(minute=0, second=0, microsecond=0)
        hour = candidate.hour
        # Base suitability — mornings and early afternoon preferred
        if 5 <= hour <= 7:
            suitability = 90
        elif 13 <= hour <= 15:
            suitability = 80
        elif 8 <= hour <= 11:
            suitability = 65
        elif 22 <= hour or hour <= 4:
            suitability = 55
        else:
            suitability = 50
        suitability -= congestion_index * 0.3
        candidates.append((candidate, max(10, suitability)))

    # Return top 3
    candidates.sort(key=lambda x: x[1], reverse=True)
    for dt, score in candidates[:3]:
        windows.append({
            'time': dt.strftime('%H:%M'),
            'date': dt.strftime('%d %b'),
            'suitability': round(score, 0),
        })
    return windows


# ── Badge Award Logic ─────────────────────────────────────────────────────────

def check_and_award_badges(user, db_session):
    """Check criteria and award badges to user if not already held."""
    from models import Badge, UserBadge, DisruptionReport

    held_ids = {ub.badge_id for ub in user.badges}

    approved_count = DisruptionReport.query.filter_by(
        submitted_by_id=user.id, verification_status='approved').count()
    total_reports = DisruptionReport.query.filter_by(submitted_by_id=user.id).count()

    badge_checks = {
        'First Report Filed': total_reports >= 1,
        '10 Approved Reports': approved_count >= 10,
        'On-Time Champion': user.points >= 200,
        'Disruption Scout': approved_count >= 1,
    }

    awarded = []
    for badge_name, condition in badge_checks.items():
        if not condition:
            continue
        badge = Badge.query.filter_by(name=badge_name).first()
        if badge and badge.id not in held_ids:
            ub = UserBadge(user_id=user.id, badge_id=badge.id)
            db_session.add(ub)
            awarded.append(badge_name)

    if awarded:
        db_session.commit()
    return awarded
