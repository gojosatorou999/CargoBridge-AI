"""
CargoBridge AI — Utilities
Haversine, WhatsApp sender, geo-fence matching, D&D calculator,
AIS/weather fetchers, PDF/CSV export helpers, audit logger.
"""
import math
import csv
import io
import os
import requests
from datetime import datetime
from functools import wraps

from flask import abort, request, current_app
from flask_login import current_user


# ── Haversine ─────────────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Role-based access control ─────────────────────────────────────────────────

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Audit logger ──────────────────────────────────────────────────────────────

def log_action(db, user_id, action, entity_type=None, entity_id=None, metadata=None):
    from models import AuditLog
    ip = request.remote_addr if request else None
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip,
        metadata_=metadata or {},
    )
    db.session.add(entry)
    db.session.commit()


# ── Geo-fence lane matching ───────────────────────────────────────────────────

LANE_WAYPOINTS = {
    'nhava_sheva_nh48': [
        (19.0760, 72.8777),  # Mumbai
        (19.1500, 73.0500),
        (18.9500, 72.8370),  # Nhava Sheva
    ],
    'mundra_nh8': [
        (23.0225, 72.5714),  # Ahmedabad
        (22.4707, 70.0577),
        (22.8330, 69.7167),  # Mundra
    ],
}


def driver_is_on_lane(driver, disruption_lat, disruption_lon, threshold_km=50.0):
    """Return True if the disruption location is within threshold_km of any
    waypoint on the driver's registered lane."""
    lane = driver.registered_lane
    if not lane or lane not in LANE_WAYPOINTS:
        return True  # no lane registered → send to all
    for wlat, wlon in LANE_WAYPOINTS[lane]:
        if haversine_km(disruption_lat, disruption_lon, wlat, wlon) <= threshold_km:
            return True
    return False


# ── WhatsApp sender (Twilio) ──────────────────────────────────────────────────

def send_whatsapp(to_number, body, media_url=None):
    """Send a WhatsApp message via Twilio. to_number must be 'whatsapp:+...'"""
    try:
        from twilio.rest import Client
        sid = current_app.config.get('TWILIO_ACCOUNT_SID', '')
        token = current_app.config.get('TWILIO_AUTH_TOKEN', '')
        from_number = current_app.config.get('TWILIO_WHATSAPP_NUMBER', '')
        if not sid or not token:
            current_app.logger.warning('Twilio not configured — skipping WhatsApp send')
            return False
        client = Client(sid, token)
        kwargs = {
            'from_': from_number,
            'to': to_number,
            'body': body,
        }
        if media_url:
            kwargs['media_url'] = [media_url]
        client.messages.create(**kwargs)
        return True
    except Exception as e:
        current_app.logger.error(f'WhatsApp send error: {e}')
        return False


def format_slot_alert(report, slot):
    severity_map = {'Low': 'LOW', 'Medium': 'MEDIUM', 'High': 'HIGH'}
    severity = severity_map.get(slot.congestion_level, 'MEDIUM')
    return (
        f"🚨 {report.disruption_type.replace('_', ' ').upper()} ALERT\n"
        f"Location: {report.location_name or 'Unknown'}\n"
        f"GPS: {report.latitude or '—'}, {report.longitude or '—'}\n"
        f"Severity: {severity}\n\n"
        f"Recommended slot: {slot.recommended_slot_time.strftime('%H:%M')} today\n"
        f"Est. wait: {slot.estimated_wait_mins} min\n"
        f"Congestion: {slot.congestion_level} | Weather: {slot.weather_condition}\n"
        f"Carbon saving: {slot.carbon_saving_kg} kg CO₂\n\n"
        f"Reply 1 to Acknowledge\n"
        f"Reply 2 to Request Reroute"
    )


def format_morning_briefing(user, active_disruptions, weather, optimal_windows):
    windows_str = ' or '.join(w['time'] for w in optimal_windows[:2]) if optimal_windows else 'N/A'
    weather_str = f"{weather.temp_c}°C, wind {weather.wind_speed_kmh} km/h" if weather else 'N/A'
    return (
        f"Good morning {user.username}. Today's CargoBridge briefing:\n"
        f"• {len(active_disruptions)} active disruptions on your lane\n"
        f"• Your optimal dispatch windows: {windows_str}\n"
        f"• Weather at port: Clear, {weather_str}"
    )


# ── Weather fetcher (Open-Meteo, no key required) ─────────────────────────────

PORT_LOCATIONS = {
    'nhava_sheva': {'lat': 18.9500, 'lon': 72.8370},
    'mundra':      {'lat': 22.8330, 'lon': 69.7167},
    'jebel_ali':   {'lat': 25.0115, 'lon': 55.0806},
}


def fetch_weather(port_code):
    loc = PORT_LOCATIONS.get(port_code)
    if not loc:
        return None
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={loc['lat']}&longitude={loc['lon']}"
        f"&current=temperature_2m,wind_speed_10m,relative_humidity_2m,weather_code"
        f"&hourly=wave_height&forecast_days=1"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        current = data.get('current', {})
        hourly = data.get('hourly', {})
        wave = hourly.get('wave_height', [None])[0] if hourly else None
        return {
            'temp_c': current.get('temperature_2m'),
            'wind_speed_kmh': current.get('wind_speed_10m'),
            'humidity': current.get('relative_humidity_2m'),
            'weather_code': current.get('weather_code'),
            'wave_height_m': wave,
        }
    except Exception as e:
        return None


# ── AIS fetcher (mock / real) ─────────────────────────────────────────────────

MOCK_VESSELS = [
    {'vessel_name': 'EVER GIVEN',      'mmsi': '353136000', 'latitude': 19.10, 'longitude': 72.90, 'destination_port': 'nhava_sheva', 'eta': None, 'speed_knots': 12.5},
    {'vessel_name': 'MSC GULSUN',      'mmsi': '636019832', 'latitude': 18.80, 'longitude': 72.75, 'destination_port': 'nhava_sheva', 'eta': None, 'speed_knots': 14.1},
    {'vessel_name': 'CMA CGM MARCO',   'mmsi': '215289000', 'latitude': 22.90, 'longitude': 69.80, 'destination_port': 'mundra',      'eta': None, 'speed_knots': 11.3},
    {'vessel_name': 'MAERSK ELBA',     'mmsi': '219632000', 'latitude': 25.10, 'longitude': 55.20, 'destination_port': 'jebel_ali',   'eta': None, 'speed_knots': 13.8},
    {'vessel_name': 'COSCO SHIPPING',  'mmsi': '477311400', 'latitude': 25.05, 'longitude': 55.10, 'destination_port': 'jebel_ali',   'eta': None, 'speed_knots': 10.9},
]


def fetch_ais_vessels(api_key=None):
    """Fetch AIS data. Falls back to mock data if no key or call fails."""
    if not api_key:
        return MOCK_VESSELS
    try:
        # MarineTraffic API endpoint (adapt as needed)
        url = f"https://services.marinetraffic.com/api/getvessel/v:3/{api_key}/protocol:jsono"
        resp = requests.get(url, timeout=15)
        return resp.json()
    except Exception:
        return MOCK_VESSELS


# ── D&D savings calculator ────────────────────────────────────────────────────

DETENTION_RATE_USD = 150   # per day baseline
USD_TO_AED = 3.67


def calculate_dd_saving(days_saved, rate_per_day=DETENTION_RATE_USD):
    usd = round(rate_per_day * days_saved, 2)
    aed = round(usd * USD_TO_AED, 2)
    return usd, aed


def check_dd_risk(shipment):
    """Return True if current ETA puts free time at risk (within 2 days)."""
    if not shipment.current_eta or not shipment.free_time_expiry:
        return False
    delta = shipment.free_time_expiry - shipment.current_eta
    return delta.days <= 2


# ── CSV export ────────────────────────────────────────────────────────────────

def generate_reports_csv(reports):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Type', 'Location', 'Status', 'Confidence', 'Submitted By', 'Created At'])
    for r in reports:
        writer.writerow([
            r.id, r.disruption_type, r.location_name or '',
            r.verification_status, r.confidence_score,
            r.submitter.username if r.submitter else '',
            r.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    output.seek(0)
    return output.getvalue()


# ── PDF report (ReportLab) ────────────────────────────────────────────────────

def generate_ops_pdf(reports, slots):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph('CargoBridge AI — Operations Report', styles['Title']))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph('Disruption Reports', styles['Heading2']))
    data = [['ID', 'Type', 'Status', 'Confidence', 'Location', 'Date']]
    for r in reports:
        data.append([
            str(r.id), r.disruption_type, r.verification_status,
            f"{r.confidence_score:.0f}%", r.location_name or '—',
            r.created_at.strftime('%d %b %Y'),
        ])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph('Slot Recommendations', styles['Heading2']))
    sdata = [['ID', 'Slot Time', 'Status', 'Congestion', 'D&D Risk (USD)']]
    for s in slots:
        sdata.append([
            str(s.id), s.recommended_slot_time.strftime('%d %b %H:%M'),
            s.status, s.congestion_level, f"${s.dd_risk_usd}",
        ])
    st = Table(sdata, repeatRows=1)
    st.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(st)

    doc.build(elements)
    buf.seek(0)
    return buf


# ── Certificate PDF ───────────────────────────────────────────────────────────

def generate_certificate_pdf(user, quarter, path):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    center = ParagraphStyle('center', parent=styles['Normal'], alignment=TA_CENTER)
    elements = []

    elements.append(Spacer(1, 60))
    elements.append(Paragraph('DP World Compliance Certificate', ParagraphStyle(
        'title', parent=styles['Title'], alignment=TA_CENTER, fontSize=28)))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f'This certifies that', center))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f'<b>{user.username}</b>', ParagraphStyle(
        'name', parent=center, fontSize=22)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f'has demonstrated top 5% performance on CargoBridge AI<br/>'
        f'for the quarter <b>{quarter}</b>, achieving the rank of <b>{user.level}</b>.',
        center))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f'Issued: {datetime.utcnow().strftime("%d %B %Y")}', center))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('CargoBridge AI · Team Tech Max', center))

    doc.build(elements)
    buf.seek(0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(buf.read())


# ── Allowed file extensions ───────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
