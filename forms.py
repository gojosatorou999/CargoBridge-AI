from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, SelectField, TextAreaField,
                     FloatField, IntegerField, BooleanField, SubmitField,
                     HiddenField, TelField)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 128)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[
        ('msme_exporter', 'MSME Exporter'),
        ('truck_driver', 'Truck Driver / Transporter'),
        ('port_worker', 'Port Worker'),
        ('analyst', 'Logistics Analyst'),
    ])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    whatsapp_number = TelField('WhatsApp Number (with country code)', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Create Account')


class DisruptionReportForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired(), Length(10, 1000)])
    disruption_type = SelectField('Disruption Type', choices=[
        ('gate_congestion', 'Gate Congestion'),
        ('vessel_delay', 'Vessel Delay / Berth Unavailability'),
        ('road_accident', 'Road Accident / Blockage'),
        ('weather', 'Weather Disruption'),
        ('strike', 'Strike / Labour Stoppage'),
        ('equipment_failure', 'Equipment Failure'),
        ('customs_delay', 'Customs Delay'),
        ('other', 'Other'),
    ], validators=[DataRequired()])
    location_name = StringField('Location', validators=[Optional(), Length(max=200)])
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    image = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif'], 'Images only')
    ])
    terms = BooleanField('I confirm this report is accurate to the best of my knowledge',
                         validators=[DataRequired(message='You must accept the terms to submit.')])
    submit = SubmitField('Submit Report')


class RejectReportForm(FlaskForm):
    rejected_reason = TextAreaField('Reason for Rejection', validators=[DataRequired(), Length(5, 500)])
    submit = SubmitField('Reject Report')


class ShipmentForm(FlaskForm):
    container_number = StringField('Container Number', validators=[DataRequired(), Length(max=20)])
    vessel_name = StringField('Vessel Name', validators=[Optional(), Length(max=100)])
    voyage_number = StringField('Voyage Number', validators=[Optional(), Length(max=50)])
    origin_city = StringField('Origin City', validators=[Optional(), Length(max=100)])
    destination_port = SelectField('Destination Port', choices=[
        ('nhava_sheva', 'Nhava Sheva (Mumbai)'),
        ('mundra', 'Mundra'),
        ('jebel_ali', 'Jebel Ali (Dubai)'),
    ])
    submit = SubmitField('Add Shipment')


class AgencyRegisterForm(FlaskForm):
    name = StringField('Agency Name', validators=[DataRequired(), Length(max=200)])
    type = SelectField('Agency Type', choices=[
        ('shipping_line', 'Shipping Line'),
        ('port_authority', 'Port Authority'),
        ('freight_forwarder', 'Freight Forwarder'),
        ('ngo', 'NGO'),
    ])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone', validators=[Optional(), Length(max=20)])
    ports_covered = StringField('Ports Covered', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Register Agency')


class SimulatorForm(FlaskForm):
    rainfall_mm = FloatField('Rainfall (mm)', validators=[Optional(), NumberRange(0, 500)], default=0)
    wind_speed_kmh = FloatField('Wind Speed (km/h)', validators=[Optional(), NumberRange(0, 200)], default=0)
    vessel_queue_count = IntegerField('Vessel Queue Count', validators=[Optional(), NumberRange(0, 50)], default=0)
    traffic_density = FloatField('Traffic Density (0–10)', validators=[Optional(), NumberRange(0, 10)], default=0)
    time_of_day = SelectField('Time of Day', choices=[
        ('morning', 'Morning (06:00–12:00)'),
        ('afternoon', 'Afternoon (12:00–18:00)'),
        ('evening', 'Evening (18:00–22:00)'),
        ('night', 'Night (22:00–06:00)'),
    ])
    submit = SubmitField('Run Simulation')


class TripPostForm(FlaskForm):
    route_description = TextAreaField('Trip Summary', validators=[DataRequired(), Length(5, 500)])
    on_time = BooleanField('Completed On Time')
    photo = FileField('Photo (optional)', validators=[
        Optional(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif'], 'Images only')
    ])
    submit = SubmitField('Share Trip')


class UserManagementForm(FlaskForm):
    role = SelectField('Role', choices=[
        ('msme_exporter', 'MSME Exporter'),
        ('truck_driver', 'Truck Driver'),
        ('port_worker', 'Port Worker'),
        ('analyst', 'Analyst'),
        ('admin', 'Admin'),
    ])
    submit = SubmitField('Update Role')


class ProfileForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    whatsapp_number = TelField('WhatsApp Number', validators=[Optional(), Length(max=20)])
    language = SelectField('Language', choices=[
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('te', 'Telugu'),
        ('ta', 'Tamil'),
        ('ml', 'Malayalam'),
        ('or', 'Odia'),
        ('gu', 'Gujarati'),
        ('bn', 'Bengali'),
        ('ar', 'Arabic'),
    ])
    submit = SubmitField('Save Profile')
