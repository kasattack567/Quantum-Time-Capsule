from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import base64
import time
import uuid
import logging
from email_validator import validate_email, EmailNotValidError  # To validate email addresses

# Initialize the Flask app
app = Flask(__name__)

# MySQL database configuration (hardcoded)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://kasattack567:Rayhanqasim2!@kasattack567.mysql.pythonanywhere-services.com/kasattack567$default'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database setup
db = SQLAlchemy(app)

# Flask-Migrate setup
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

# Route for the index page
@app.route('/', methods=['GET', 'POST'])
def index():
    max_characters = 350  # Set maximum character limit
    max_message_size = 446  # Maximum message size in bytes

    if request.method == 'POST':
        message_text = request.form.get('message', '')
        name = request.form.get('name', '')
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
        db.session.add(new_message)
        db.session.commit()

        return redirect(url_for('message', message_id=message_id))
    else:
        return render_template('index.html', max_characters=max_characters)

# Route to display the encrypted message
@app.route('/message/<message_id>')
def message(message_id):
    message_data = Message.query.filter_by(message_id=message_id).first()
    if not message_data:
        return redirect(url_for('index'))

    return render_template('result.html', message_data=message_data)

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
