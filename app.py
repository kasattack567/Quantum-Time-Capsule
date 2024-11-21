import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import base64
import time
import uuid
import logging
from email_validator import validate_email, EmailNotValidError
from collections import Counter

# Initialize the Flask app
app = Flask(__name__)

# Set a secret key for session management and flash messages
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# MySQL database configuration using environment variables
db_username = os.environ.get('DB_USERNAME')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME')

# Ensure all environment variables are set
if not all([db_username, db_password, db_host, db_name]):
    raise ValueError("Database environment variables are not fully set.")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and migration tool
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Model
class Message(db.Model):
    id = Column(Integer, primary_key=True)
    message_id = Column(String(36), unique=True, nullable=False, index=True)
    ciphertext = Column(Text, nullable=False)
    key_gen_time = Column(Float, nullable=False)
    encryption_time = Column(Float, nullable=False)
    public_key_n = Column(Text, nullable=False)
    public_exponent_e = Column(Integer, nullable=False)
    name = Column(String(120), nullable=True)
    email = Column(String(120), nullable=True, index=True)
    age = Column(Integer, nullable=True)
    subject = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# Function to generate RSA key pair
def generate_rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Function to encrypt a message
def encrypt_message(public_key, message):
    ciphertext = public_key.encrypt(
        message.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

# Validate age (age should be between 0 and 120)
def validate_age(age):
    return age is None or (0 <= age <= 120)

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
            return render_template('index.html', error=f"Message is too long. Maximum length is {max_characters} characters.")

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

@app.route('/demographics')
def demographics():
    import pycountry
    from collections import Counter

    try:
        # Total users with valid demographic data
        total_users = Message.query.filter(
            (Message.age != None) |
            (Message.subject != None) |
            (Message.country != None)
        ).count()

        # Total messages sent
        total_messages = Message.query.count()

        # Median, youngest, and oldest ages
        ages = [age for (age,) in db.session.query(Message.age).filter(Message.age != None).order_by(Message.age).all()]
        median_age = ages[len(ages) // 2] if ages else None
        youngest_age = min(ages) if ages else None
        oldest_age = max(ages) if ages else None

        # Count messages per country
        country_counts = Counter([msg.country for msg in Message.query.filter(Message.country != None).all()])

        # Dynamically generate ISO 3166-1 alpha-2 codes for countries
        country_codes = {country.name: country.alpha_2 for country in pycountry.countries}

        # Generate country_data for the template
        country_data = {
            country: {
                "code": country_codes.get(country, "Unknown"),
                "users": count,
                "messages": count  # Adjust if you have separate logic for messages
            }
            for country, count in country_counts.items() if country in country_codes
        }

        # Debugging: Print country_data
        print("DEBUG: country_data:", country_data)

        # Prepare demographics data for the template
        demographics_data = {
            'total_users': total_users,
            'total_messages': total_messages,
            'median_age': median_age,
            'youngest_age': youngest_age,
            'oldest_age': oldest_age,
            'country_data': country_data,  # Pass the country_data here
            'country_codes': country_codes
        }

        # Debugging: Print demographics_data
        print("DEBUG: demographics_data:", demographics_data)

        return render_template('demographics.html', **demographics_data)

    except Exception as e:
        # Log and display error
        print("ERROR: Exception in /demographics route:", e)
        return render_template('error.html', error_message=str(e)), 500

# Route to handle demographic form submission via AJAX
@app.route('/submit_demographics', methods=['POST'])
def submit_demographics():
    message_id = request.form.get('message_id')
    name = request.form.get('name')
    email = request.form.get('email')
    country = request.form.get('country')
    occupation = request.form.get('occupation')
    age = request.form.get('age', type=int)

    if age is not None and not validate_age(age):
        return jsonify({'error': 'Invalid age. Age must be between 0 and 120.'}), 400

    if email and not validate_email_address(email):
        return jsonify({'error': 'Invalid email address.'}), 400

    demographics_message = Message.query.filter_by(message_id=message_id).first()

    if demographics_message:
        demographics_message.name = name if name else None
        demographics_message.email = email if email else None
        demographics_message.age = age if age else None
        demographics_message.country = country if country else None
        demographics_message.subject = occupation if occupation else None
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database error during demographics update: {str(e)}")
            return jsonify({'error': 'Database error during update.'}), 500
    else:
        return jsonify({'error': 'Message not found.'}), 404

    return jsonify({'success': 'Demographics submitted successfully!'})


# Route for about page
@app.route('/about')
def about():
    return render_template('about.html')

# Route to display the encrypted message
import pycountry

@app.route('/message/<message_id>')
def message(message_id):
    try:
        message_data = Message.query.filter_by(message_id=message_id).first()
    except Exception as e:
        logging.error(f"Database error: {str(e)}")
        return render_template('error.html', error_message="A database error occurred. Please try again later.")

    if not message_data:
        return redirect(url_for('index'))

    # Get list of country names
    countries = [country.name for country in pycountry.countries]

    # Example list of occupations (you can extend this list)
    occupations = [
        "Student", "Engineer", "Teacher", "Doctor", "Scientist", "Artist",
        "Lawyer", "Entrepreneur", "Developer", "Designer", "Other"
    ]

    return render_template('result.html', message_data=message_data, countries=countries, occupations=occupations)

# Create the database tables and run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
