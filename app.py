from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import json
import os

# --- Flask Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'thisissecret-shhh67'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/realestate.sqlite'
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "realestate.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ============================
#        DATABASE MODELS
# ============================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'agent' or 'client'
    agent_code = db.Column(db.String(6), nullable=True)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)


class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='available')  # available, reserved, sold
    polygon = db.Column(db.Text)  # JSON list of coordinates
    acquired_by = db.Column(db.String(200), nullable=True)
    acquired_on = db.Column(db.DateTime, nullable=True)
    build_start = db.Column(db.Date, nullable=True)
    expected_finish = db.Column(db.Date, nullable=True)
    base_price = db.Column(db.Integer, default=1000000)
    floorplan_image = db.Column(db.String(300), nullable=True)
    tour_url = db.Column(db.String(400), nullable=True)


class AgentCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


# ============================
#       LOGIN MANAGER
# ============================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================
#           ROUTES
# ============================


@app.route('/')
def index():
    return redirect(url_for('map_view'))


@app.route('/map')
def map_view():
    units = Unit.query.all()

    units_data = []
    for u in units:
        coords = json.loads(u.polygon) if u.polygon else []
        units_data.append({
            'id': u.id,
            'name': u.name,
            'status': u.status,
            'polygon': coords,
            'base_price': u.base_price
        })

    return render_template(
        'map.html',
        units=json.dumps(units_data),
        map_image_url=url_for('static', filename='images/subdivision_map.png')
    )


@app.route('/unit/<int:unit_id>')
def unit_page(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    return render_template('unit.html', unit=unit)


# ============================
#     PRICE COMPUTATION API
# ============================

@app.route('/compute_price/<int:unit_id>', methods=['POST'])
def compute_price(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    data = request.json or {}
    extras = data.get('extras', {})
    total = unit.base_price

    if extras.get('garage'):
        total += 50000
    if extras.get('landscaping'):
        total += 20000
    if extras.get('premium_finish'):
        total += int(unit.base_price * 0.08)

    return jsonify({'total': total})


# ============================
#        LOGIN & REGISTER
# ============================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(pwd):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('map_view'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        role = request.form['role']

        if role not in ('client', 'agent'):
            flash('Invalid role.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        if role == 'agent':
            code = request.form.get('agent_code', '').strip()
            ac = AgentCode.query.filter_by(code=code, active=True).first()
            if not ac:
                flash('Invalid agent code.', 'danger')
                return redirect(url_for('register'))
        else:
            code = None

        new_user = User(
            email=email,
            password_hash=generate_password_hash(pwd),
            role=role,
            agent_code=code
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Registered successfully.', 'success')
        return redirect(url_for('map_view'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


# ============================
#      AGENT-ONLY API
# ============================

@app.route('/api/unit/<int:unit_id>', methods=['PUT'])
@login_required
def api_update_unit(unit_id):
    if current_user.role != 'agent':
        return jsonify({'error': 'forbidden'}), 403

    u = Unit.query.get_or_404(unit_id)
    data = request.json or {}

    if 'status' in data:
        if data['status'] not in ('available', 'reserved', 'sold'):
            return jsonify({'error': 'invalid status'}), 400

        u.status = data['status']

        if u.status == 'sold':
            u.acquired_by = data.get('acquired_by', u.acquired_by)
            u.acquired_on = datetime.datetime.utcnow()

    if 'build_start' in data:
        try:
            u.build_start = datetime.date.fromisoformat(data['build_start'])
        except:
            pass

    if 'expected_finish' in data:
        try:
            u.expected_finish = datetime.date.fromisoformat(data['expected_finish'])
        except:
            pass

    db.session.commit()
    return jsonify({'ok': True})


# ============================
#        API FOR UNITS
# ============================

@app.route('/api/units')
def api_units():
    units = Unit.query.all()

    out = []
    for u in units:
        out.append({
            'id': u.id,
            'name': u.name,
            'status': u.status,
            'polygon': json.loads(u.polygon) if u.polygon else [],
            'base_price': u.base_price
        })

    return jsonify(out)


# ============================
#          RUN APP
# ============================

if __name__ == "__main__":
    # ensure instance folder exists
    os.makedirs('instance', exist_ok=True)

    # create tables inside app context
    with app.app_context():
        db.create_all()

    # start the server
    app.run(debug=True)
