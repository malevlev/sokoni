import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
import os

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fleetms-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_pNWKv8itVg1C@ep-fragrant-queen-am8bkbh7-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# ── Models ────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='available')  # available, on_trip, off_duty
    vehicles = db.relationship('Vehicle', backref='current_driver', lazy=True, foreign_keys='Vehicle.driver_id')
    trips = db.relationship('Trip', backref='driver', lazy=True)

    def status_label(self):
        return {'available': 'Available', 'on_trip': 'On Trip', 'off_duty': 'Off Duty'}.get(self.status, self.status)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    registration = db.Column(db.String(20), unique=True, nullable=False)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    status = db.Column(db.String(20), default='active')  # active, maintenance, stalled, inactive
    fuel_level = db.Column(db.Integer, default=100)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=True)
    trips = db.relationship('Trip', backref='vehicle', lazy=True)
    maintenance_records = db.relationship('Maintenance', backref='vehicle', lazy=True)

    def status_label(self):
        return {'active': 'Active', 'maintenance': 'Maintenance', 'stalled': 'Stalled', 'inactive': 'Inactive'}.get(self.status, self.status)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='ongoing')  # ongoing, completed, cancelled
    distance_km = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def status_label(self):
        return {'ongoing': 'Ongoing', 'completed': 'Completed', 'cancelled': 'Cancelled'}.get(self.status, self.status)


class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, default=datetime.utcnow)
    cost = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_progress, completed
    next_due = db.Column(db.Date, nullable=True)

    def status_label(self):
        return {'scheduled': 'Scheduled', 'in_progress': 'In Progress', 'completed': 'Completed'}.get(self.status, self.status)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total_vehicles = Vehicle.query.count()
    active_vehicles = Vehicle.query.filter_by(status='active').count()
    total_drivers = Driver.query.count()
    available_drivers = Driver.query.filter_by(status='available').count()
    ongoing_trips = Trip.query.filter_by(status='ongoing').count()
    maintenance_vehicles = Vehicle.query.filter_by(status='maintenance').count()
    recent_trips = Trip.query.order_by(Trip.start_time.desc()).limit(5).all()
    recent_maintenance = Maintenance.query.order_by(Maintenance.date.desc()).limit(5).all()
    vehicles = Vehicle.query.all()
    return render_template('dashboard.html',
        total_vehicles=total_vehicles,
        active_vehicles=active_vehicles,
        total_drivers=total_drivers,
        available_drivers=available_drivers,
        ongoing_trips=ongoing_trips,
        maintenance_vehicles=maintenance_vehicles,
        recent_trips=recent_trips,
        recent_maintenance=recent_maintenance,
        vehicles=vehicles,
    )


# ── Vehicles ──────────────────────────────────────────────────────────────────

@app.route('/vehicles')
@login_required
def vehicles():
    vehicle_list = Vehicle.query.order_by(Vehicle.name).all()
    return render_template('vehicles.html', vehicles=vehicle_list)


@app.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    drivers = Driver.query.filter_by(status='available').all()
    if request.method == 'POST':
        v = Vehicle(
            name=request.form['name'].strip(),
            registration=request.form['registration'].strip().upper(),
            make=request.form.get('make', '').strip(),
            model=request.form.get('model', '').strip(),
            year=request.form.get('year') or None,
            status=request.form.get('status', 'active'),
            fuel_level=int(request.form.get('fuel_level', 100)),
            driver_id=request.form.get('driver_id') or None,
        )
        db.session.add(v)
        db.session.commit()
        flash('Vehicle added successfully.', 'success')
        return redirect(url_for('vehicles'))
    return render_template('add_vehicle.html', drivers=drivers)


@app.route('/vehicles/<int:vid>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    drivers = Driver.query.all()
    if request.method == 'POST':
        v.name = request.form['name'].strip()
        v.registration = request.form['registration'].strip().upper()
        v.make = request.form.get('make', '').strip()
        v.model = request.form.get('model', '').strip()
        v.year = request.form.get('year') or None
        v.status = request.form.get('status', 'active')
        v.fuel_level = int(request.form.get('fuel_level', 100))
        v.driver_id = request.form.get('driver_id') or None
        db.session.commit()
        flash('Vehicle updated.', 'success')
        return redirect(url_for('vehicles'))
    return render_template('edit_vehicle.html', vehicle=v, drivers=drivers)


@app.route('/vehicles/<int:vid>/delete', methods=['POST'])
@login_required
def delete_vehicle(vid):
    v = Vehicle.query.get_or_404(vid)
    db.session.delete(v)
    db.session.commit()
    flash('Vehicle deleted.', 'success')
    return redirect(url_for('vehicles'))


# ── Drivers ───────────────────────────────────────────────────────────────────

@app.route('/drivers')
@login_required
def drivers():
    driver_list = Driver.query.order_by(Driver.full_name).all()
    return render_template('drivers.html', drivers=driver_list)


@app.route('/drivers/add', methods=['GET', 'POST'])
@login_required
def add_driver():
    if request.method == 'POST':
        d = Driver(
            full_name=request.form['full_name'].strip(),
            license_number=request.form['license_number'].strip(),
            phone=request.form.get('phone', '').strip(),
            status=request.form.get('status', 'available'),
        )
        db.session.add(d)
        db.session.commit()
        flash('Driver added successfully.', 'success')
        return redirect(url_for('drivers'))
    return render_template('add_driver.html')


@app.route('/drivers/<int:did>/edit', methods=['GET', 'POST'])
@login_required
def edit_driver(did):
    d = Driver.query.get_or_404(did)
    if request.method == 'POST':
        d.full_name = request.form['full_name'].strip()
        d.license_number = request.form['license_number'].strip()
        d.phone = request.form.get('phone', '').strip()
        d.status = request.form.get('status', 'available')
        db.session.commit()
        flash('Driver updated.', 'success')
        return redirect(url_for('drivers'))
    return render_template('edit_driver.html', driver=d)


@app.route('/drivers/<int:did>/delete', methods=['POST'])
@login_required
def delete_driver(did):
    d = Driver.query.get_or_404(did)
    db.session.delete(d)
    db.session.commit()
    flash('Driver deleted.', 'success')
    return redirect(url_for('drivers'))


# ── Trips ─────────────────────────────────────────────────────────────────────

@app.route('/trips')
@login_required
def trips():
    trip_list = Trip.query.order_by(Trip.start_time.desc()).all()
    return render_template('trips.html', trips=trip_list)


@app.route('/trips/add', methods=['GET', 'POST'])
@login_required
def add_trip():
    vehicles = Vehicle.query.filter_by(status='active').all()
    drivers = Driver.query.filter_by(status='available').all()
    if request.method == 'POST':
        t = Trip(
            vehicle_id=request.form['vehicle_id'],
            driver_id=request.form['driver_id'],
            origin=request.form['origin'].strip(),
            destination=request.form['destination'].strip(),
            status=request.form.get('status', 'ongoing'),
            distance_km=request.form.get('distance_km') or None,
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(t)
        db.session.commit()
        flash('Trip added successfully.', 'success')
        return redirect(url_for('trips'))
    return render_template('add_trip.html', vehicles=vehicles, drivers=drivers)


@app.route('/trips/<int:tid>/delete', methods=['POST'])
@login_required
def delete_trip(tid):
    t = Trip.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    flash('Trip deleted.', 'success')
    return redirect(url_for('trips'))


# ── Maintenance ───────────────────────────────────────────────────────────────

@app.route('/maintenance')
@login_required
def maintenance():
    records = Maintenance.query.order_by(Maintenance.date.desc()).all()
    return render_template('maintenance.html', records=records)


@app.route('/maintenance/add', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    vehicles = Vehicle.query.all()
    if request.method == 'POST':
        m = Maintenance(
            vehicle_id=request.form['vehicle_id'],
            type=request.form['type'].strip(),
            description=request.form.get('description', '').strip(),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            cost=float(request.form.get('cost', 0) or 0),
            status=request.form.get('status', 'scheduled'),
            next_due=datetime.strptime(request.form['next_due'], '%Y-%m-%d').date() if request.form.get('next_due') else None,
        )
        db.session.add(m)
        db.session.commit()
        flash('Maintenance record added.', 'success')
        return redirect(url_for('maintenance'))
    return render_template('add_maintenance.html', vehicles=vehicles)


@app.route('/maintenance/<int:mid>/delete', methods=['POST'])
@login_required
def delete_maintenance(mid):
    m = Maintenance.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('maintenance'))


# ── Init ──────────────────────────────────────────────────────────────────────

def create_tables():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Default admin created: username=admin password=admin123')


create_tables()

if __name__ == '__main__':
    app.run(debug=True)
