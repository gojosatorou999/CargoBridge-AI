from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='msme_exporter')
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.String(50), default='Reliable Rookie')
    language = db.Column(db.String(10), default='en')
    home_lat = db.Column(db.Float, nullable=True)
    home_lon = db.Column(db.Float, nullable=True)
    whatsapp_number = db.Column(db.String(20), nullable=True)
    whatsapp_session = db.Column(db.JSON, nullable=True)
    registered_lane = db.Column(db.String(100), nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    push_token = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship('DisruptionReport', foreign_keys='DisruptionReport.submitted_by_id', backref='submitter', lazy='dynamic')
    approved_reports = db.relationship('DisruptionReport', foreign_keys='DisruptionReport.approved_by_id', backref='approver', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    shipments = db.relationship('Shipment', backref='exporter', lazy='dynamic')
    badges = db.relationship('UserBadge', backref='user', lazy='dynamic')
    trip_posts = db.relationship('TripPost', backref='author', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_level(self):
        levels = [
            (0, 'Reliable Rookie'),
            (100, 'Steady Hauler'),
            (300, 'Trusted Partner'),
            (600, 'Lane Legend'),
            (1000, 'DP World Elite'),
        ]
        for threshold, name in reversed(levels):
            if self.points >= threshold:
                self.level = name
                break

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'


class DisruptionReport(db.Model):
    __tablename__ = 'disruption_reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    disruption_type = db.Column(db.String(50), nullable=False)
    location_name = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    image_file = db.Column(db.String(256), nullable=True)
    audio_file = db.Column(db.String(256), nullable=True)
    confidence_score = db.Column(db.Float, default=0.0)
    parameter_breakdown = db.Column(db.JSON, nullable=True)
    verification_status = db.Column(db.String(20), default='pending')
    rejected_reason = db.Column(db.Text, nullable=True)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    lane_id = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(20), default='web')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slots = db.relationship('SlotRecommendation', backref='report', lazy='dynamic')
    notifications = db.relationship('Notification', backref='report', lazy='dynamic')

    DISRUPTION_TYPES = [
        ('gate_congestion', 'Gate Congestion'),
        ('vessel_delay', 'Vessel Delay / Berth Unavailability'),
        ('road_accident', 'Road Accident / Blockage'),
        ('weather', 'Weather Disruption'),
        ('strike', 'Strike / Labour Stoppage'),
        ('equipment_failure', 'Equipment Failure'),
        ('customs_delay', 'Customs Delay'),
        ('other', 'Other'),
    ]

    def __repr__(self):
        return f'<DisruptionReport {self.id} [{self.verification_status}]>'


class SlotRecommendation(db.Model):
    __tablename__ = 'slot_recommendations'
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('disruption_reports.id'), nullable=False)
    truck_driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recommended_slot_time = db.Column(db.DateTime, nullable=False)
    estimated_wait_mins = db.Column(db.Integer, default=0)
    congestion_level = db.Column(db.String(10), default='Low')
    weather_condition = db.Column(db.String(50), default='Clear')
    carbon_saving_kg = db.Column(db.Float, default=0.0)
    fuel_saving_litres = db.Column(db.Float, default=0.0)
    dd_risk_usd = db.Column(db.Float, default=0.0)
    dd_risk_aed = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    truck_driver = db.relationship('User', foreign_keys=[truck_driver_id], backref='slot_recommendations')
    shipments = db.relationship('Shipment', backref='assigned_slot', lazy='dynamic')

    def __repr__(self):
        return f'<SlotRecommendation {self.id} [{self.status}]>'


class Shipment(db.Model):
    __tablename__ = 'shipments'
    id = db.Column(db.Integer, primary_key=True)
    exporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    container_number = db.Column(db.String(20), nullable=False)
    vessel_name = db.Column(db.String(100), nullable=True)
    voyage_number = db.Column(db.String(50), nullable=True)
    origin_city = db.Column(db.String(100), nullable=True)
    destination_port = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(30), default='Origin')
    current_eta = db.Column(db.DateTime, nullable=True)
    free_time_expiry = db.Column(db.DateTime, nullable=True)
    assigned_slot_id = db.Column(db.Integer, db.ForeignKey('slot_recommendations.id'), nullable=True)
    dd_saving_usd = db.Column(db.Float, default=0.0)
    dd_risk_flag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    STATUS_PIPELINE = ['Origin', 'In Transit', 'At Gate', 'Loaded', 'On Vessel', 'Delivered']

    def __repr__(self):
        return f'<Shipment {self.container_number}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('disruption_reports.id'), nullable=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot_recommendations.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    is_alert = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Notification {self.id} user={self.user_id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    metadata_ = db.Column('metadata', db.JSON, nullable=True)

    def __repr__(self):
        return f'<AuditLog {self.action} by user={self.user_id}>'


class Badge(db.Model):
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_class = db.Column(db.String(50), default='bi-award')
    criteria = db.Column(db.JSON, nullable=True)

    user_badges = db.relationship('UserBadge', backref='badge', lazy='dynamic')


class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Leaderboard(db.Model):
    __tablename__ = 'leaderboard'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scope = db.Column(db.String(20), default='individual')
    score = db.Column(db.Float, default=0.0)
    rank = db.Column(db.Integer, default=0)
    week_of = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='leaderboard_entries')


class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), default='DP World Compliance')
    quarter = db.Column(db.String(10), nullable=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    pdf_path = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', backref='certificates')


class TripPost(db.Model):
    __tablename__ = 'trip_posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipments.id'), nullable=True)
    route_description = db.Column(db.Text, nullable=True)
    on_time = db.Column(db.Boolean, default=True)
    points_earned = db.Column(db.Integer, default=0)
    photo_file = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    likes = db.relationship('PostLike', backref='post', lazy='dynamic')
    shipment = db.relationship('Shipment', backref='trip_posts')


class PostLike(db.Model):
    __tablename__ = 'post_likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('trip_posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='post_likes')


class Agency(db.Model):
    __tablename__ = 'agencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    ports_covered = db.Column(db.String(200), nullable=True)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    TYPES = [
        ('shipping_line', 'Shipping Line'),
        ('port_authority', 'Port Authority'),
        ('freight_forwarder', 'Freight Forwarder'),
        ('ngo', 'NGO'),
    ]

    def __repr__(self):
        return f'<Agency {self.name}>'


class WeatherSnapshot(db.Model):
    __tablename__ = 'weather_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    port_code = db.Column(db.String(10), nullable=False)
    temp_c = db.Column(db.Float, nullable=True)
    wind_speed_kmh = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    weather_code = db.Column(db.Integer, nullable=True)
    wave_height_m = db.Column(db.Float, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class AISSnapshot(db.Model):
    __tablename__ = 'ais_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    vessel_name = db.Column(db.String(100), nullable=True)
    mmsi = db.Column(db.String(20), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    destination_port = db.Column(db.String(50), nullable=True)
    eta = db.Column(db.DateTime, nullable=True)
    speed_knots = db.Column(db.Float, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class SimulationRun(db.Model):
    __tablename__ = 'simulation_runs'
    id = db.Column(db.Integer, primary_key=True)
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inputs = db.Column(db.JSON, nullable=True)
    outputs = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    analyst = db.relationship('User', backref='simulations')
