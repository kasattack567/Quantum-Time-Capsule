from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import base64
import time
import uuid
import logging
from email_validator import validate_email, EmailNotValidError
from flask_mail import Mail, Message as MailMessage

# Initialize the Flask app
app = Flask(__name__)

# Set a secret key for session management and flash messages
app.secret_key = 'f21b2c6b9d2b4a6b8d2c8f7c1e4d3b8a'  # Replace with a secure key if needed

# MySQL database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://kasattack567:Rayhanqasim2!@kasattack567.mysql.pythonanywhere-services.com/kasattack567$default'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'quantumtimecapsule@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'siee zwea fawl txrx'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'quantumtimecapsule@gmail.com'  # Replace with your email

mail = Mail(app)  # Initialize Flask-Mail
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    ciphertext = db.Column(db.Text, nullable=False)
    key_gen_time = db.Column(db.Float, nullable=False)
    encryption_time = db.Column(db.Float, nullable=False)
    public_key_n = db.Column(db.Text, nullable=False)
    public_exponent_e = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    age = db.Column(db.Integer, nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

# Function to generate RSA key pair
def generate_rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,  # 4096-bit RSA key
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Function to encrypt a message
def encrypt_message(public_key, message):
    ciphertext = public_key.encrypt(
        message.encode('utf-8'),  # convert message to bytes for encryption
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

# Validate age (age should be between 0 and 120)
def validate_age(age):
    if age is not None and (age < 0 or age > 120):
        return False
    return True

# Validate email using email_validator
def validate_email_address(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

# Route for the intro page (starting screen)
@app.route('/')
def intro():
    return render_template('intro.html')

# Explore Page Route
@app.route('/explore')
def explore():
    return render_template('explore.html')

# Explore More Page Route
@app.route('/explore_more')
def explore_more():
    return render_template('explore_more.html')

# Route for the index (home) page after submitting name
@app.route('/index', methods=['GET', 'POST'])
def index():
    max_characters = 350  # Set maximum character limit
    max_message_size = 446  # Maximum message size in bytes

    if request.method == 'POST':
        name = request.form.get('name')  # Fetch name from intro page form
        message_text = request.form.get('message', '')
        email = request.form.get('email', '')
        age = request.form.get('age', type=int)
        subject = request.form.get('subject', '')
        country = request.form.get('country', '')

        # Validate message length
        message = message_text.encode('utf-8')
        message_length = len(message_text)

        if message_length > max_characters:
            return render_template('index.html', error="Message is too long. Maximum length is {} characters.".format(max_characters))

        if len(message) > max_message_size:
            return render_template('index.html', error="Message is too long due to the characters used. Please shorten your message.")

        # Validate age
        if not validate_age(age):
            return render_template('index.html', error="Invalid age. Age must be between 0 and 120.")

        # Validate email if provided
        if email and not validate_email_address(email):
            return render_template('index.html', error="Invalid email address.")

        # Generate RSA keys
        key_gen_start = time.time()
        private_key, public_key = generate_rsa_keypair()
        key_gen_time = time.time() - key_gen_start

        # Encrypt the message
        encrypt_start = time.time()
        try:
            ciphertext = encrypt_message(public_key, message_text)
        except Exception as e:
            logging.error(f"Encryption error: {str(e)}")
            return render_template('index.html', error=f"Encryption failed: {e}")
        encryption_time = time.time() - encrypt_start

        encoded_ciphertext = base64.b64encode(ciphertext).decode('utf-8')

        # Extract the modulus N and public exponent e
        public_numbers = public_key.public_numbers()
        public_key_n = public_numbers.n  # Modulus N
        public_exponent_e = public_numbers.e  # Public exponent e

        # Generate a unique message ID
        message_id = str(uuid.uuid4())

        # Save the message and public key data to the database
        new_message = Message(
            message_id=message_id,
            ciphertext=encoded_ciphertext,
            key_gen_time=round(key_gen_time, 4),
            encryption_time=round(encryption_time, 4),
            public_key_n=str(public_key_n),  # Save modulus N as string
            public_exponent_e=public_exponent_e,
            name=name if name else None,
            email=email if email else None,
            age=age if age else None,
            subject=subject if subject else None,
            country=country if country else None
        )
        try:
            db.session.add(new_message)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database error: {str(e)}")
            return render_template('index.html', error="Database error occurred. Please try again.")

        return redirect(url_for('message', message_id=message_id))
    else:
        return render_template('index.html', max_characters=max_characters)


# Route to display the encrypted message
@app.route('/message/<message_id>')
def message(message_id):
    try:
        message_data = Message.query.filter_by(message_id=message_id).first()
    except Exception as e:
        logging.error(f"Database error: {str(e)}")
        # You can render an error template or a minimal version of the page
        return render_template('error.html', error_message="A database error occurred. Please try again later.")

    if not message_data:
        return redirect(url_for('index'))

    return render_template('result.html', message_data=message_data)

# Route to handle demographic form submission via AJAX
@app.route('/submit_demographics', methods=['POST'])
def submit_demographics():
    name = request.form.get('name')
    email = request.form.get('email')
    country = request.form.get('country')
    occupation = request.form.get('occupation')
    age = request.form.get('age', type=int)

    # Validate email, if provided
    if email and not validate_email_address(email):
        return jsonify({'error': 'Invalid email address.'}), 400

    # Validate age
    if not validate_age(age):
        return jsonify({'error': 'Invalid age. Age must be between 0 and 120.'}), 400

    # Process and save the demographics data (for example, update an existing message record)
    demographics_message = Message.query.filter_by(email=email).first()

    if demographics_message:
        demographics_message.name = name if name else None
        demographics_message.age = age if age else None
        demographics_message.country = country if country else None
        demographics_message.subject = occupation if occupation else None
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database error during demographics update: {str(e)}")
            return jsonify({'error': 'Database error during update.'}), 500

    return jsonify({'success': 'Demographics submitted successfully!'})

# Route for demographic data
@app.route('/demographics')
def demographics():
    total_users = Message.query.filter(Message.age != None).count()
    average_age = db.session.query(func.avg(Message.age)).scalar()
    subjects = db.session.query(Message.subject, func.count(Message.subject)).group_by(Message.subject).all()
    countries = db.session.query(Message.country, func.count(Message.country)).group_by(Message.country).all()

    return render_template('demographics.html', total_users=total_users, average_age=average_age,
                           subjects=subjects, countries=countries)

# Route for about page
@app.route('/about')
def about():
    return render_template('about.html')

# Create the database tables
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures the tables exist
    app.run(debug=True, port=5002)  # Specify the port directly
