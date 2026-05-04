"""
CargoBridge AI — Main Flask Application
All routes, blueprints, and app factory.
"""
import os
import json
from datetime import datetime, timedelta

from flask import (Flask, render_template, redirect, url_for, request,
                   jsonify, flash, send_file, abort, session, g)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.utils import secure_filename

from config import config_map
from models import (db, User, DisruptionReport, SlotRecommendation, Shipment,
                    Notification, AuditLog, Badge, UserBadge, Leaderboard,
                    Certificate, TripPost, PostLike, Agency,
                    WeatherSnapshot, AISSnapshot, SimulationRun)
from forms import (LoginForm, RegisterForm, DisruptionReportForm, RejectReportForm,
                   ShipmentForm, AgencyRegisterForm, SimulatorForm, TripPostForm,
                   UserManagementForm, ProfileForm)
from utils import (roles_required, log_action, allowed_file, send_whatsapp,
                   format_slot_alert, generate_reports_csv, generate_ops_pdf,
                   driver_is_on_lane, fetch_weather, fetch_ais_vessels,
                   check_dd_risk, calculate_dd_saving, generate_certificate_pdf)
from expert_system import (compute_confidence_score, generate_slot_recommendation,
                            run_resilience_simulation, check_and_award_badges)
from scheduler import init_scheduler
from translations import get_strings, t


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(env='default'):
    app = Flask(__name__)
    app.config.from_object(config_map[env])

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Inject translation helper + user strings into every template
    @app.context_processor
    def inject_globals():
        lang = 'en'
        if current_user.is_authenticated:
            lang = current_user.language or 'en'
        strings = get_strings(lang)
        unread = 0
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False).count()
        return dict(strings=strings, t=t, lang=lang, unread_count=unread,
                    now=datetime.utcnow())

    # Scheduler — skip in testing
    if not app.config.get('TESTING'):
        scheduler = BackgroundScheduler()
        init_scheduler(scheduler, app)
        scheduler.start()

    _register_seed_data(app)

    return app


def _register_seed_data(app):
    """Create default badges and admin user on first run."""
    @app.before_request
    def seed_once():
        if getattr(app, '_seeded', False):
            return
        app._seeded = True
        with app.app_context():
            db.create_all()
            _seed_badges()
            _seed_admin()


def _seed_badges():
    badge_defs = [
        ('First Report Filed',      'Submitted your first disruption report',   'bi-flag-fill'),
        ('10 Approved Reports',     '10 reports approved by port workers',       'bi-check-circle-fill'),
        ('Slot Streak',             'Accepted 5 slot recommendations in a row',  'bi-lightning-fill'),
        ('On-Time Champion',        'Completed 10 trips on time',                'bi-trophy-fill'),
        ('Disruption Scout',        'First to report a confirmed disruption',     'bi-search'),
        ('Carbon Saver',            'Saved 50 kg CO₂ via slot optimization',     'bi-leaf-fill'),
    ]
    for name, desc, icon in badge_defs:
        if not Badge.query.filter_by(name=name).first():
            db.session.add(Badge(name=name, description=desc, icon_class=icon))
    db.session.commit()


def _seed_admin():
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            email='admin@cargobridge.ai',
            role='admin',
            company_name='CargoBridge AI',
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()


app = create_app(os.environ.get('FLASK_ENV', 'default'))


# ── Helpers ───────────────────────────────────────────────────────────────────

def save_upload(file_obj, subfolder='reports'):
    if not file_obj or not allowed_file(file_obj.filename):
        return None
    filename = secure_filename(file_obj.filename)
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S_')
    filename = ts + filename
    folder = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_obj.save(os.path.join(folder, filename))
    return f'uploads/{subfolder}/{filename}'


def add_notification(user_id, message, report_id=None, slot_id=None, is_alert=False):
    notif = Notification(
        user_id=user_id,
        message=message,
        report_id=report_id,
        slot_id=slot_id,
        is_alert=is_alert,
        expires_at=datetime.utcnow() + timedelta(hours=48) if is_alert else None,
    )
    db.session.add(notif)


def award_points(user, points, action):
    user.points += points
    user.update_level()
    db.session.commit()
    check_and_award_badges(user, db)
    log_action(db, user.id, f'points_awarded:{action}', 'User', user.id,
               {'points': points, 'total': user.points})


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            log_action(db, user.id, 'login', 'User', user.id)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    log_action(db, current_user.id, 'logout', 'User', current_user.id)
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data,
                company_name=form.company_name.data,
                whatsapp_number=form.whatsapp_number.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            log_action(db, user.id, 'register', 'User', user.id)
            flash('Account created! Please sign in.', 'success')
            return redirect(url_for('login'))
    return render_template('login.html', form=form, register=True)


# ── Dashboard routing ─────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    if role == 'port_worker':
        return redirect(url_for('port_worker_dashboard'))
    if role == 'analyst':
        return redirect(url_for('analyst_dashboard'))
    if role == 'truck_driver':
        return redirect(url_for('driver_dashboard'))
    return redirect(url_for('exporter_dashboard'))


@app.route('/dashboard/admin')
@login_required
@roles_required('admin')
def admin_dashboard():
    reports = DisruptionReport.query.order_by(DisruptionReport.created_at.desc()).limit(20).all()
    pending = DisruptionReport.query.filter_by(verification_status='pending').count()
    users = User.query.order_by(User.created_at.desc()).limit(10).all()
    agencies = Agency.query.filter_by(approved=False).count()
    total_savings = db.session.query(db.func.sum(Shipment.dd_saving_usd)).scalar() or 0
    return render_template('dashboard/admin.html',
                           reports=reports, pending=pending,
                           users=users, agencies_pending=agencies,
                           total_savings=total_savings)


@app.route('/dashboard/port-worker')
@login_required
@roles_required('port_worker', 'admin')
def port_worker_dashboard():
    pending_reports = DisruptionReport.query.filter_by(
        verification_status='pending').order_by(DisruptionReport.created_at.desc()).all()
    slots = SlotRecommendation.query.filter_by(status='pending').limit(10).all()
    weather = WeatherSnapshot.query.order_by(WeatherSnapshot.recorded_at.desc()).first()
    vessels = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(10).all()
    return render_template('dashboard/port_worker.html',
                           pending_reports=pending_reports, slots=slots,
                           weather=weather, vessels=vessels)


@app.route('/dashboard/analyst')
@login_required
@roles_required('analyst', 'admin')
def analyst_dashboard():
    reports = DisruptionReport.query.order_by(DisruptionReport.created_at.desc()).limit(50).all()
    vessels = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(20).all()
    weather = WeatherSnapshot.query.order_by(WeatherSnapshot.recorded_at.desc()).first()
    form = SimulatorForm()
    return render_template('dashboard/analyst.html',
                           reports=reports, vessels=vessels,
                           weather=weather, form=form)


@app.route('/dashboard/driver')
@login_required
@roles_required('truck_driver', 'admin')
def driver_dashboard():
    my_slot = SlotRecommendation.query.filter_by(
        truck_driver_id=current_user.id, status='pending').order_by(
        SlotRecommendation.created_at.desc()).first()
    my_reports = DisruptionReport.query.filter_by(
        submitted_by_id=current_user.id).order_by(
        DisruptionReport.created_at.desc()).limit(5).all()
    leaderboard = Leaderboard.query.filter_by(scope='individual').order_by(
        Leaderboard.rank).limit(10).all()
    my_rank = Leaderboard.query.filter_by(
        user_id=current_user.id, scope='individual').order_by(
        Leaderboard.created_at.desc()).first()
    active_disruptions = DisruptionReport.query.filter_by(
        verification_status='approved').order_by(
        DisruptionReport.created_at.desc()).limit(10).all()
    return render_template('dashboard/driver.html',
                           my_slot=my_slot, my_reports=my_reports,
                           leaderboard=leaderboard, my_rank=my_rank,
                           active_disruptions=active_disruptions)


@app.route('/dashboard/exporter')
@login_required
@roles_required('msme_exporter', 'admin')
def exporter_dashboard():
    shipments = Shipment.query.filter_by(exporter_id=current_user.id).order_by(
        Shipment.created_at.desc()).all()
    total_savings = sum(s.dd_saving_usd for s in shipments)
    slots = SlotRecommendation.query.filter_by(
        truck_driver_id=current_user.id, status='pending').limit(3).all()
    leaderboard = Leaderboard.query.filter_by(scope='company').order_by(
        Leaderboard.rank).limit(10).all()
    my_rank = Leaderboard.query.filter_by(
        user_id=current_user.id, scope='company').order_by(
        Leaderboard.created_at.desc()).first()
    return render_template('dashboard/exporter.html',
                           shipments=shipments, total_savings=total_savings,
                           slots=slots, leaderboard=leaderboard, my_rank=my_rank)


# ── Disruption reports ────────────────────────────────────────────────────────

@app.route('/report', methods=['GET', 'POST'])
@login_required
def submit_report():
    form = DisruptionReportForm()
    if form.validate_on_submit():
        image_path = save_upload(form.image.data) if form.image.data else None

        report = DisruptionReport(
            title=f"{form.disruption_type.data.replace('_', ' ').title()} — {form.location_name.data or 'Unknown'}",
            description=form.description.data,
            disruption_type=form.disruption_type.data,
            location_name=form.location_name.data,
            latitude=float(form.latitude.data) if form.latitude.data else None,
            longitude=float(form.longitude.data) if form.longitude.data else None,
            image_file=image_path,
            submitted_by_id=current_user.id,
            source='web',
        )
        db.session.add(report)
        db.session.flush()  # get report.id

        # Run expert system scoring
        all_reports = DisruptionReport.query.all()
        user_reports = DisruptionReport.query.filter_by(submitted_by_id=current_user.id).all()
        weather_snaps = WeatherSnapshot.query.order_by(WeatherSnapshot.recorded_at.desc()).limit(5).all()
        ais_snaps = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(10).all()

        score, breakdown, band, action = compute_confidence_score(
            report, current_user, all_reports, user_reports, weather_snaps, ais_snaps)

        report.confidence_score = score
        report.parameter_breakdown = breakdown
        db.session.commit()

        log_action(db, current_user.id, 'submit_report', 'DisruptionReport', report.id,
                   {'score': score, 'band': band})

        flash(f'Report submitted. AI Confidence: {score:.0f}% ({band}).', 'success')
        return redirect(url_for('dashboard'))

    return render_template('report.html', form=form)


@app.route('/api/reports')
@login_required
def api_reports():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    q = DisruptionReport.query.order_by(DisruptionReport.created_at.desc())
    if status:
        q = q.filter_by(verification_status=status)
    reports = q.paginate(page=page, per_page=20, error_out=False)
    return jsonify({
        'reports': [{
            'id': r.id, 'title': r.title, 'type': r.disruption_type,
            'status': r.verification_status, 'score': r.confidence_score,
            'lat': r.latitude, 'lon': r.longitude, 'location': r.location_name,
            'image': r.image_file, 'created_at': r.created_at.isoformat(),
            'submitted_by': r.submitter.username if r.submitter else None,
        } for r in reports.items],
        'total': reports.total, 'page': reports.page, 'pages': reports.pages,
    })


@app.route('/api/report/<int:report_id>/score')
@login_required
def api_report_score(report_id):
    report = DisruptionReport.query.get_or_404(report_id)
    return jsonify(report.parameter_breakdown or {})


@app.route('/report/<int:report_id>/approve', methods=['POST'])
@login_required
@roles_required('port_worker', 'admin')
def approve_report(report_id):
    report = DisruptionReport.query.get_or_404(report_id)
    if report.verification_status != 'pending':
        flash('Report already processed.', 'warning')
        return redirect(url_for('port_worker_dashboard'))

    report.verification_status = 'approved'
    report.approved_by_id = current_user.id
    db.session.commit()

    # Award points to reporter
    reporter = report.submitter
    if reporter:
        award_points(reporter, 30, 'report_approved')

    # Generate slot recommendations for affected drivers
    _dispatch_slot_recommendations(report)

    log_action(db, current_user.id, 'approve_report', 'DisruptionReport', report.id)
    flash('Report approved and slot recommendations dispatched.', 'success')
    return redirect(url_for('port_worker_dashboard'))


def _dispatch_slot_recommendations(report):
    """Generate and notify slot recommendations for all on-lane drivers."""
    drivers = User.query.filter_by(role='truck_driver').all()
    weather_snaps = WeatherSnapshot.query.order_by(WeatherSnapshot.recorded_at.desc()).limit(3).all()
    ais_snaps = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(10).all()

    for driver in drivers:
        if report.latitude and report.longitude:
            if not driver_is_on_lane(driver, report.latitude, report.longitude):
                continue

        slot_data = generate_slot_recommendation(report, driver, weather_snaps, ais_snaps)
        slot = SlotRecommendation(**slot_data)
        db.session.add(slot)
        db.session.flush()

        msg = format_slot_alert(report, slot)
        add_notification(driver.id, f'New slot recommendation for {report.location_name}',
                         report_id=report.id, slot_id=slot.id, is_alert=True)

        if driver.whatsapp_number:
            image_url = None
            if report.image_file:
                image_url = f"{app.config['BASE_URL']}/static/{report.image_file}"
            send_whatsapp(f"whatsapp:{driver.whatsapp_number}", msg, image_url)

    db.session.commit()


@app.route('/report/<int:report_id>/reject', methods=['GET', 'POST'])
@login_required
@roles_required('port_worker', 'admin')
def reject_report(report_id):
    report = DisruptionReport.query.get_or_404(report_id)
    form = RejectReportForm()
    if form.validate_on_submit():
        report.verification_status = 'rejected'
        report.rejected_reason = form.rejected_reason.data
        report.approved_by_id = current_user.id

        reporter = report.submitter
        if reporter:
            reporter.points = max(0, reporter.points - 5)
            reporter.update_level()

        db.session.commit()
        log_action(db, current_user.id, 'reject_report', 'DisruptionReport', report.id,
                   {'reason': form.rejected_reason.data})
        flash('Report rejected.', 'warning')
        return redirect(url_for('port_worker_dashboard'))
    return render_template('report_reject.html', form=form, report=report)


# ── Slot recommendations ──────────────────────────────────────────────────────

@app.route('/api/slots/active')
@login_required
def api_slots_active():
    slots = SlotRecommendation.query.filter_by(
        truck_driver_id=current_user.id).order_by(
        SlotRecommendation.created_at.desc()).limit(10).all()
    return jsonify([{
        'id': s.id, 'slot_time': s.recommended_slot_time.isoformat(),
        'wait_mins': s.estimated_wait_mins, 'congestion': s.congestion_level,
        'weather': s.weather_condition, 'carbon_kg': s.carbon_saving_kg,
        'fuel_l': s.fuel_saving_litres, 'dd_usd': s.dd_risk_usd,
        'dd_aed': s.dd_risk_aed, 'status': s.status,
    } for s in slots])


@app.route('/api/slot/<int:slot_id>/accept', methods=['POST'])
@login_required
def accept_slot(slot_id):
    slot = SlotRecommendation.query.get_or_404(slot_id)
    if slot.truck_driver_id != current_user.id:
        abort(403)
    slot.status = 'accepted'
    db.session.commit()
    award_points(current_user, 10, 'slot_accepted')
    log_action(db, current_user.id, 'accept_slot', 'SlotRecommendation', slot.id)
    return jsonify({'success': True})


@app.route('/api/slot/<int:slot_id>/request-alternate', methods=['POST'])
@login_required
def request_alternate_slot(slot_id):
    slot = SlotRecommendation.query.get_or_404(slot_id)
    if slot.truck_driver_id != current_user.id:
        abort(403)
    slot.status = 'alternate_requested'
    db.session.commit()

    # Generate next best slot
    report = slot.report
    weather_snaps = WeatherSnapshot.query.order_by(WeatherSnapshot.recorded_at.desc()).limit(3).all()
    ais_snaps = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(10).all()
    new_data = generate_slot_recommendation(report, current_user, weather_snaps, ais_snaps)
    new_slot = SlotRecommendation(**new_data)
    db.session.add(new_slot)
    db.session.flush()

    msg = format_slot_alert(report, new_slot)
    if current_user.whatsapp_number:
        send_whatsapp(f"whatsapp:{current_user.whatsapp_number}", msg)

    db.session.commit()
    log_action(db, current_user.id, 'request_alternate_slot', 'SlotRecommendation', slot.id)
    return jsonify({'success': True, 'new_slot_id': new_slot.id})


# ── Shipments ─────────────────────────────────────────────────────────────────

@app.route('/shipments')
@login_required
def shipments():
    form = ShipmentForm()
    my_shipments = Shipment.query.filter_by(
        exporter_id=current_user.id).order_by(Shipment.created_at.desc()).all()
    return render_template('shipments.html', shipments=my_shipments, form=form)


@app.route('/shipment/create', methods=['POST'])
@login_required
def create_shipment():
    form = ShipmentForm()
    if form.validate_on_submit():
        shipment = Shipment(
            exporter_id=current_user.id,
            container_number=form.container_number.data,
            vessel_name=form.vessel_name.data,
            voyage_number=form.voyage_number.data,
            origin_city=form.origin_city.data,
            destination_port=form.destination_port.data,
            current_eta=datetime.utcnow() + timedelta(days=14),
            free_time_expiry=datetime.utcnow() + timedelta(days=21),
        )
        db.session.add(shipment)
        db.session.commit()
        log_action(db, current_user.id, 'create_shipment', 'Shipment', shipment.id)
        flash('Shipment added.', 'success')
    return redirect(url_for('shipments'))


@app.route('/api/shipments')
@login_required
def api_shipments():
    role = current_user.role
    if role in ('admin', 'analyst'):
        qs = Shipment.query.order_by(Shipment.created_at.desc()).limit(50)
    else:
        qs = Shipment.query.filter_by(exporter_id=current_user.id).order_by(Shipment.created_at.desc())
    return jsonify([{
        'id': s.id, 'container': s.container_number, 'vessel': s.vessel_name,
        'voyage': s.voyage_number, 'origin': s.origin_city, 'dest': s.destination_port,
        'status': s.status, 'eta': s.current_eta.isoformat() if s.current_eta else None,
        'free_time': s.free_time_expiry.isoformat() if s.free_time_expiry else None,
        'dd_risk': s.dd_risk_flag, 'dd_saving': s.dd_saving_usd,
    } for s in qs.all()])


@app.route('/api/shipment/<int:shipment_id>/status')
@login_required
def api_shipment_status(shipment_id):
    s = Shipment.query.get_or_404(shipment_id)
    if s.exporter_id != current_user.id and current_user.role not in ('admin', 'analyst'):
        abort(403)
    return jsonify({
        'id': s.id, 'container': s.container_number, 'status': s.status,
        'eta': s.current_eta.isoformat() if s.current_eta else None,
        'dd_risk': s.dd_risk_flag,
    })


# ── Analytics & intelligence ──────────────────────────────────────────────────

@app.route('/api/weather')
@login_required
def api_weather():
    port = request.args.get('port', 'nhava_sheva')
    snap = WeatherSnapshot.query.filter_by(
        port_code=port).order_by(WeatherSnapshot.recorded_at.desc()).first()
    if not snap:
        return jsonify({})
    return jsonify({
        'port': port, 'temp_c': snap.temp_c, 'wind_speed_kmh': snap.wind_speed_kmh,
        'humidity': snap.humidity, 'weather_code': snap.weather_code,
        'wave_height_m': snap.wave_height_m,
        'recorded_at': snap.recorded_at.isoformat(),
    })


@app.route('/api/ais/vessels')
@login_required
def api_ais_vessels():
    snaps = AISSnapshot.query.order_by(AISSnapshot.recorded_at.desc()).limit(20).all()
    return jsonify([{
        'vessel_name': v.vessel_name, 'mmsi': v.mmsi,
        'lat': v.latitude, 'lon': v.longitude,
        'dest': v.destination_port,
        'eta': v.eta.isoformat() if v.eta else None,
        'speed': v.speed_knots,
    } for v in snaps])


@app.route('/api/analytics/charts')
@login_required
@roles_required('analyst', 'admin')
def api_analytics_charts():
    # Disruption type distribution
    from sqlalchemy import func
    type_counts = db.session.query(
        DisruptionReport.disruption_type,
        func.count(DisruptionReport.id)
    ).group_by(DisruptionReport.disruption_type).all()

    # Reports timeline (last 14 days)
    timeline = []
    for i in range(13, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        count = DisruptionReport.query.filter(
            db.func.date(DisruptionReport.created_at) == day
        ).count()
        timeline.append({'date': day.isoformat(), 'count': count})

    # Gate throughput (mock — replace with real data source)
    throughput = [{'hour': h, 'moves': max(0, 45 - abs(h - 10) * 3)} for h in range(24)]

    # Cumulative D&D savings
    savings_data = []
    cumulative = 0
    for i in range(13, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_savings = db.session.query(func.sum(Shipment.dd_saving_usd)).filter(
            db.func.date(Shipment.updated_at) == day
        ).scalar() or 0
        cumulative += day_savings
        savings_data.append({'date': day.isoformat(), 'savings': round(cumulative, 2)})

    return jsonify({
        'type_distribution': [{'type': t, 'count': c} for t, c in type_counts],
        'timeline': timeline,
        'throughput': throughput,
        'savings': savings_data,
    })


@app.route('/api/simulate', methods=['POST'])
@login_required
@roles_required('analyst', 'admin')
def api_simulate():
    data = request.get_json() or {}
    result = run_resilience_simulation(data)

    run = SimulationRun(analyst_id=current_user.id, inputs=data, outputs=result)
    db.session.add(run)
    db.session.commit()
    log_action(db, current_user.id, 'run_simulation', 'SimulationRun', run.id)

    return jsonify(result)


@app.route('/simulator')
@login_required
@roles_required('analyst', 'admin')
def simulator():
    form = SimulatorForm()
    return render_template('simulator.html', form=form)


@app.route('/api/savings/<int:user_id>')
@login_required
def api_savings(user_id):
    if user_id != current_user.id and current_user.role not in ('admin', 'analyst'):
        abort(403)
    user = User.query.get_or_404(user_id)
    shipments = Shipment.query.filter_by(exporter_id=user_id).all()
    total = sum(s.dd_saving_usd for s in shipments)
    return jsonify({'user_id': user_id, 'total_usd': round(total, 2),
                    'total_aed': round(total * 3.67, 2)})


# ── Notifications ─────────────────────────────────────────────────────────────

@app.route('/api/notifications/unread-count')
@login_required
def api_unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@app.route('/api/notification/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    n = Notification.query.get_or_404(notif_id)
    if n.user_id != current_user.id:
        abort(403)
    n.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    Notification.query.filter_by(user_id=current_user.id).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(
        user_id=current_user.id).order_by(
        Notification.created_at.desc()).limit(50).all()
    return render_template('notifications.html', notifications=notifs)


# ── Social feed ───────────────────────────────────────────────────────────────

@app.route('/feed')
@login_required
def feed():
    form = TripPostForm()
    posts = TripPost.query.order_by(TripPost.created_at.desc()).limit(30).all()
    return render_template('feed.html', posts=posts, form=form)


@app.route('/post/create', methods=['POST'])
@login_required
def create_post():
    form = TripPostForm()
    if form.validate_on_submit():
        photo = save_upload(form.photo.data, 'posts') if form.photo.data else None
        post = TripPost(
            user_id=current_user.id,
            route_description=form.route_description.data,
            on_time=form.on_time.data,
            points_earned=current_user.points,
            photo_file=photo,
        )
        db.session.add(post)
        db.session.commit()
        flash('Trip shared!', 'success')
    return redirect(url_for('feed'))


@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    existing = PostLike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(PostLike(user_id=current_user.id, post_id=post_id))
    db.session.commit()
    count = PostLike.query.filter_by(post_id=post_id).count()
    return jsonify({'likes': count})


# ── Agencies ──────────────────────────────────────────────────────────────────

@app.route('/agencies')
@login_required
def agencies():
    form = AgencyRegisterForm()
    all_agencies = Agency.query.filter_by(approved=True).order_by(Agency.name).all()
    return render_template('agencies.html', agencies=all_agencies, form=form)


@app.route('/agency/register', methods=['POST'])
@login_required
def register_agency():
    form = AgencyRegisterForm()
    if form.validate_on_submit():
        agency = Agency(
            name=form.name.data, type=form.type.data,
            contact_person=form.contact_person.data, email=form.email.data,
            phone=form.phone.data, ports_covered=form.ports_covered.data,
        )
        db.session.add(agency)
        db.session.commit()
        log_action(db, current_user.id, 'register_agency', 'Agency', agency.id)
        flash('Agency registration submitted for approval.', 'success')
    return redirect(url_for('agencies'))


@app.route('/agency/<int:agency_id>/approve', methods=['POST'])
@login_required
@roles_required('admin')
def approve_agency(agency_id):
    agency = Agency.query.get_or_404(agency_id)
    agency.approved = True
    db.session.commit()
    log_action(db, current_user.id, 'approve_agency', 'Agency', agency_id)
    flash(f'Agency {agency.name} approved.', 'success')
    return redirect(url_for('admin_dashboard'))


# ── Leaderboard ───────────────────────────────────────────────────────────────

@app.route('/leaderboard')
@login_required
def leaderboard():
    individual = Leaderboard.query.filter_by(scope='individual').order_by(
        Leaderboard.rank).limit(20).all()
    company = Leaderboard.query.filter_by(scope='company').order_by(
        Leaderboard.rank).limit(20).all()
    return render_template('leaderboard.html',
                           individual=individual, company=company)


# ── Profile ───────────────────────────────────────────────────────────────────

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.email = form.email.data or current_user.email
        current_user.company_name = form.company_name.data
        current_user.whatsapp_number = form.whatsapp_number.data
        current_user.language = form.language.data
        db.session.commit()
        flash('Profile updated.', 'success')

    badges = db.session.query(Badge).join(UserBadge).filter(
        UserBadge.user_id == current_user.id).all()
    cert = Certificate.query.filter_by(user_id=current_user.id).order_by(
        Certificate.issued_at.desc()).first()
    recent_reports = DisruptionReport.query.filter_by(
        submitted_by_id=current_user.id).order_by(
        DisruptionReport.created_at.desc()).limit(8).all()

    return render_template('profile.html', form=form, badges=badges, cert=cert,
                           recent_reports=recent_reports)


# ── Admin — user management ───────────────────────────────────────────────────

@app.route('/admin/users')
@login_required
@roles_required('admin')
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/user/<int:user_id>/role', methods=['POST'])
@login_required
@roles_required('admin')
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    form = UserManagementForm()
    if form.validate_on_submit():
        old_role = user.role
        user.role = form.role.data
        db.session.commit()
        log_action(db, current_user.id, 'update_user_role', 'User', user_id,
                   {'from': old_role, 'to': form.role.data})
        flash(f'Role updated for {user.username}.', 'success')
    return redirect(url_for('admin_users'))


# ── Audit log ─────────────────────────────────────────────────────────────────

@app.route('/admin/audit-log')
@login_required
@roles_required('admin')
def audit_log():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False)
    return render_template('audit_log.html', logs=logs)


# ── Export ────────────────────────────────────────────────────────────────────

@app.route('/export/pdf')
@login_required
@roles_required('admin', 'analyst')
def export_pdf():
    reports = DisruptionReport.query.order_by(DisruptionReport.created_at.desc()).limit(100).all()
    slots = SlotRecommendation.query.order_by(SlotRecommendation.created_at.desc()).limit(100).all()
    buf = generate_ops_pdf(reports, slots)
    log_action(db, current_user.id, 'export_pdf', 'System', None)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name='cargobridge_ops_report.pdf')


@app.route('/export/csv')
@login_required
@roles_required('admin', 'analyst')
def export_csv():
    from flask import Response
    reports = DisruptionReport.query.order_by(DisruptionReport.created_at.desc()).all()
    csv_data = generate_reports_csv(reports)
    log_action(db, current_user.id, 'export_csv', 'System', None)
    return Response(csv_data, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment;filename=cargobridge_data.csv'})


# ── WhatsApp webhook ──────────────────────────────────────────────────────────

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Twilio inbound WhatsApp message handler."""
    from_number = request.form.get('From', '')
    body = (request.form.get('Body', '') or '').strip().lower()

    # Look up user by WhatsApp number
    phone = from_number.replace('whatsapp:', '')
    user = User.query.filter_by(whatsapp_number=phone).first()

    if not user:
        # Account linking flow
        session_key = f'wa_session_{phone}'
        wa_state = _get_wa_session(phone)

        if not wa_state:
            _set_wa_session(phone, {'step': 'ask_username'})
            _wa_reply(from_number, "Welcome to CargoBridge AI. Enter your username.")
        elif wa_state['step'] == 'ask_username':
            _set_wa_session(phone, {'step': 'ask_password', 'username': body})
            _wa_reply(from_number, "Enter your password.")
        elif wa_state['step'] == 'ask_password':
            candidate = User.query.filter_by(username=wa_state.get('username', '')).first()
            if candidate and candidate.check_password(request.form.get('Body', '').strip()):
                candidate.whatsapp_number = phone
                db.session.commit()
                _clear_wa_session(phone)
                _wa_reply(from_number,
                          "✅ Linked! You'll receive slot alerts and disruption notices here.")
            else:
                _clear_wa_session(phone)
                _wa_reply(from_number, "❌ Invalid credentials. Send 'Hi' to try again.")
        return ('', 204)

    # Commands for linked users
    if body in ('hi', 'hello'):
        _wa_reply(from_number, f"Welcome back, {user.username}! Reply 'help' for commands.")
    elif body == 'status':
        slot = SlotRecommendation.query.filter_by(
            truck_driver_id=user.id, status='pending').order_by(
            SlotRecommendation.created_at.desc()).first()
        if slot:
            msg = (f"Your slot: {slot.recommended_slot_time.strftime('%H:%M %d %b')}\n"
                   f"Status: {slot.status} | Congestion: {slot.congestion_level}")
        else:
            msg = "No active slot assignment."
        _wa_reply(from_number, msg)
    elif body == 'help':
        _wa_reply(from_number,
                  "Commands:\nstatus — current slot\ncancel — cancel booking\nhelp — this menu")
    elif body == 'cancel':
        slot = SlotRecommendation.query.filter_by(
            truck_driver_id=user.id, status='pending').order_by(
            SlotRecommendation.created_at.desc()).first()
        if slot:
            slot.status = 'declined'
            db.session.commit()
            _wa_reply(from_number, "Slot booking cancelled.")
        else:
            _wa_reply(from_number, "No active booking to cancel.")
    elif body == '1':
        slot = SlotRecommendation.query.filter_by(
            truck_driver_id=user.id, status='pending').order_by(
            SlotRecommendation.created_at.desc()).first()
        if slot:
            slot.status = 'accepted'
            db.session.commit()
            award_points(user, 5, 'alert_acknowledged')
            _wa_reply(from_number, "✅ Acknowledged. Slot accepted.")
    elif body == '2':
        slot = SlotRecommendation.query.filter_by(
            truck_driver_id=user.id, status='pending').order_by(
            SlotRecommendation.created_at.desc()).first()
        if slot:
            slot.status = 'alternate_requested'
            db.session.commit()
            _wa_reply(from_number, "Alternate slot being generated. Check app for update.")
    else:
        _wa_reply(from_number, "Unknown command. Reply 'help' for options.")

    return ('', 204)


# WhatsApp session helpers (stored on User model)
def _get_wa_session(phone):
    dummy = User.query.filter(User.whatsapp_number == phone).first()
    if dummy:
        return dummy.whatsapp_session
    # Use a temporary in-memory dict keyed by phone (sufficient for demo)
    return app.config.get(f'_wa_{phone}')


def _set_wa_session(phone, state):
    app.config[f'_wa_{phone}'] = state


def _clear_wa_session(phone):
    app.config.pop(f'_wa_{phone}', None)


def _wa_reply(to, body):
    send_whatsapp(to, body)


# ── Certificate download ──────────────────────────────────────────────────────

@app.route('/certificate/<int:cert_id>/download')
@login_required
def download_certificate(cert_id):
    cert = Certificate.query.get_or_404(cert_id)
    if cert.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    if not cert.pdf_path or not os.path.exists(cert.pdf_path):
        abort(404)
    return send_file(cert.pdf_path, as_attachment=True,
                     download_name='dp_world_certificate.pdf')


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
