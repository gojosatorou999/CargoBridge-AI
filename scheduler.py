"""
CargoBridge AI — APScheduler background jobs.
All jobs are registered here and started from app.py.
"""
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)


def init_scheduler(scheduler, app):
    """Register all scheduled jobs on the given APScheduler instance."""

    # Morning briefing — 6:00 AM daily
    scheduler.add_job(
        func=_morning_briefing,
        args=[app],
        trigger='cron',
        hour=6, minute=0,
        id='morning_briefing',
        replace_existing=True,
    )

    # Weekly performance report — Monday 7:00 AM
    scheduler.add_job(
        func=_weekly_report,
        args=[app],
        trigger='cron',
        day_of_week='mon', hour=7, minute=0,
        id='weekly_report',
        replace_existing=True,
    )

    # AIS + ETA refresh — every 15 minutes
    scheduler.add_job(
        func=_ais_eta_refresh,
        args=[app],
        trigger='interval',
        minutes=15,
        id='ais_eta_refresh',
        replace_existing=True,
    )

    # Weather refresh — every 30 minutes
    scheduler.add_job(
        func=_weather_refresh,
        args=[app],
        trigger='interval',
        minutes=30,
        id='weather_refresh',
        replace_existing=True,
    )

    # Alert expiry — every hour
    scheduler.add_job(
        func=_expire_alerts,
        args=[app],
        trigger='interval',
        hours=1,
        id='alert_expiry',
        replace_existing=True,
    )

    # Leaderboard refresh — every Sunday midnight
    scheduler.add_job(
        func=_refresh_leaderboard,
        args=[app],
        trigger='cron',
        day_of_week='sun', hour=0, minute=0,
        id='leaderboard_refresh',
        replace_existing=True,
    )

    # Audit log archive — 1st of every month
    scheduler.add_job(
        func=_archive_audit_logs,
        args=[app],
        trigger='cron',
        day=1, hour=2, minute=0,
        id='audit_log_archive',
        replace_existing=True,
    )

    log.info('APScheduler jobs registered.')


# ── Job implementations ───────────────────────────────────────────────────────

def _morning_briefing(app):
    with app.app_context():
        try:
            from models import db, User, DisruptionReport, WeatherSnapshot
            from utils import send_whatsapp, format_morning_briefing
            from expert_system import run_resilience_simulation

            drivers = User.query.filter(
                User.role.in_(['truck_driver', 'msme_exporter']),
                User.whatsapp_number.isnot(None)
            ).all()

            active = DisruptionReport.query.filter_by(verification_status='approved').all()
            weather = WeatherSnapshot.query.filter_by(
                port_code='nhava_sheva').order_by(WeatherSnapshot.recorded_at.desc()).first()

            sim = run_resilience_simulation({'traffic_density': 5, 'vessel_queue_count': 4,
                                             'rainfall_mm': 0, 'wind_speed_kmh': 15,
                                             'time_of_day': 'morning'})
            windows = sim.get('dispatch_windows', [])

            for user in drivers:
                msg = format_morning_briefing(user, active, weather, windows)
                send_whatsapp(f"whatsapp:{user.whatsapp_number}", msg)

            log.info(f'Morning briefing sent to {len(drivers)} users.')
        except Exception as e:
            log.error(f'Morning briefing error: {e}')


def _weekly_report(app):
    with app.app_context():
        try:
            from models import db, User, Shipment
            from utils import send_whatsapp

            exporters = User.query.filter(
                User.role == 'msme_exporter',
                User.whatsapp_number.isnot(None)
            ).all()

            for user in exporters:
                total_savings = sum(s.dd_saving_usd for s in user.shipments)
                msg = (
                    f"📊 CargoBridge Weekly Report — {datetime.utcnow().strftime('%d %b %Y')}\n"
                    f"Hello {user.username},\n"
                    f"• Cumulative D&D savings: ${total_savings:.2f}\n"
                    f"• Level: {user.level} ({user.points} pts)\n"
                    f"Have a great week!"
                )
                send_whatsapp(f"whatsapp:{user.whatsapp_number}", msg)

            log.info(f'Weekly report sent to {len(exporters)} exporters.')
        except Exception as e:
            log.error(f'Weekly report error: {e}')


def _ais_eta_refresh(app):
    with app.app_context():
        try:
            from models import db, AISSnapshot, Shipment
            from utils import fetch_ais_vessels, check_dd_risk
            import flask

            api_key = app.config.get('AIS_API_KEY', '')
            vessels = fetch_ais_vessels(api_key)

            for v in vessels:
                snap = AISSnapshot(
                    vessel_name=v.get('vessel_name'),
                    mmsi=v.get('mmsi'),
                    latitude=v.get('latitude'),
                    longitude=v.get('longitude'),
                    destination_port=v.get('destination_port'),
                    eta=v.get('eta'),
                    speed_knots=v.get('speed_knots'),
                )
                db.session.add(snap)

            # Re-check D&D risk on all in-flight shipments
            in_flight = Shipment.query.filter(
                Shipment.status.notin_(['Delivered', 'Origin'])
            ).all()
            for shipment in in_flight:
                shipment.dd_risk_flag = check_dd_risk(shipment)

            db.session.commit()
            log.info(f'AIS refresh: {len(vessels)} vessels, {len(in_flight)} shipments checked.')
        except Exception as e:
            log.error(f'AIS refresh error: {e}')


def _weather_refresh(app):
    with app.app_context():
        try:
            from models import db, WeatherSnapshot
            from utils import fetch_weather

            for port_code in ['nhava_sheva', 'mundra', 'jebel_ali']:
                data = fetch_weather(port_code)
                if not data:
                    continue
                snap = WeatherSnapshot(
                    port_code=port_code,
                    temp_c=data.get('temp_c'),
                    wind_speed_kmh=data.get('wind_speed_kmh'),
                    humidity=data.get('humidity'),
                    weather_code=data.get('weather_code'),
                    wave_height_m=data.get('wave_height_m'),
                )
                db.session.add(snap)

            db.session.commit()
            log.info('Weather refresh complete.')
        except Exception as e:
            log.error(f'Weather refresh error: {e}')


def _expire_alerts(app):
    with app.app_context():
        try:
            from models import db, Notification
            now = datetime.utcnow()
            expired = Notification.query.filter(
                Notification.expires_at.isnot(None),
                Notification.expires_at < now,
                Notification.is_read == False,
            ).all()
            for n in expired:
                n.is_read = True
            db.session.commit()
            log.info(f'Expired {len(expired)} stale alerts.')
        except Exception as e:
            log.error(f'Alert expiry error: {e}')


def _refresh_leaderboard(app):
    with app.app_context():
        try:
            from models import db, User, Leaderboard

            # Individual — truck drivers ranked by points
            drivers = User.query.filter_by(role='truck_driver').order_by(User.points.desc()).all()
            for rank, user in enumerate(drivers, 1):
                entry = Leaderboard(
                    user_id=user.id,
                    scope='individual',
                    score=user.points,
                    rank=rank,
                    week_of=datetime.utcnow(),
                )
                db.session.add(entry)

            # Company — exporters ranked by cumulative D&D savings
            exporters = User.query.filter_by(role='msme_exporter').all()
            company_scores = []
            for user in exporters:
                total = sum(s.dd_saving_usd for s in user.shipments)
                company_scores.append((user, total))
            company_scores.sort(key=lambda x: x[1], reverse=True)

            for rank, (user, score) in enumerate(company_scores, 1):
                entry = Leaderboard(
                    user_id=user.id,
                    scope='company',
                    score=score,
                    rank=rank,
                    week_of=datetime.utcnow(),
                )
                db.session.add(entry)

            db.session.commit()
            log.info('Leaderboard refreshed.')
        except Exception as e:
            log.error(f'Leaderboard refresh error: {e}')


def _archive_audit_logs(app):
    with app.app_context():
        try:
            from models import db, AuditLog
            cutoff = datetime.utcnow() - timedelta(days=180)
            old = AuditLog.query.filter(AuditLog.timestamp < cutoff).count()
            # In production: move to cold storage table. Here we just log.
            log.info(f'Audit archive: {old} entries older than 6 months identified.')
        except Exception as e:
            log.error(f'Audit archive error: {e}')
