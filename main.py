from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt 
import os
from functools import wraps
import time

# Static files are stored in the `Static/` directory in this project.
app = Flask(__name__, static_folder='Static')

# Set a secure secret key from environment variable or fallback
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# --- SQLite/SQLAlchemy Configurations ---
# This line tells SQLAlchemy to use a file-based SQLite database named 'site.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app) 

# --- Database Models ---
# These models define the structure of your database tables
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Storing the secure hash
    password = db.Column(db.String(255), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # pName is at index 1 for compatibility if template uses array access
    pname = db.Column(db.String(255), nullable=False)
    # projectLink is at index 2
    projectlink = db.Column(db.Text)
    # projectDescripton is at index 3
    projectDescripton = db.Column(db.Text)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True) # index 0
    name = db.Column(db.String(100), nullable=False) # index 1
    email = db.Column(db.String(120), nullable=False) # index 2
    message = db.Column(db.Text, nullable=False) # index 3
    created_at = db.Column(db.DateTime, default=db.func.now()) # index 4 (for messages route)

# Login required decorator remains the same
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Admin User Creation Utility ---
# This function is used to create the first secure admin user via the console.
def create_initial_admin():
    with app.app_context():
        if User.query.count() == 0:
            print("\n--- Initial Admin Setup Required ---")
            print("Please create the first admin user for dashboard access.")
            try:
                username = input("Enter admin username: ")
                email = input("Enter admin email: ")
                password = input("Enter admin password: ")

                # Hash the password before saving
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                
                new_user = User(username=username, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                print(f"Admin user '{username}' created successfully!")
            except Exception as e:
                print(f"Failed to create initial user: {e}")
                db.session.rollback()
            print("---------------------------\n")

# Initialize database tables if they don't exist
def init_db():
    try:
        with app.app_context():
            db.create_all()
        # Automatically prompt for admin creation if no users exist
        create_initial_admin()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# --- Helper function for template compatibility ---
def result_to_list_of_tuples(results, model_class):
    """Converts SQLAlchemy objects to a list of tuples/lists 
    to maintain compatibility with templates expecting index-based access."""
    output = []
    # Define attribute order based on the model to match old tuple structure
    if model_class == Project:
        attributes = ['id', 'pname', 'projectlink', 'projectDescripton']
    elif model_class == Contact:
        attributes = ['id', 'name', 'email', 'message', 'created_at']
    else:
        return results # Return objects if unknown model

    for item in results:
        # Create a list matching the expected index order of the old MySQL tuple
        row = [getattr(item, attr) for attr in attributes]
        output.append(row)
    return output

# --- Routes ---

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/about")
def about():
    return render_template('AboutME.html')

@app.route("/contact")
def contact():
    return render_template('contact.html')

@app.route("/skills")
def skills():
    return render_template('Skills.html')

@app.route("/projects")
def projects():
    # Fetch data and convert for compatibility
    projects_data = Project.query.all()
    compatible_projects = result_to_list_of_tuples(projects_data, Project)
    # The template now receives data in the expected array/tuple format
    return render_template('projects.html', projects=compatible_projects)

@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/login", methods=['POST'])
def login_post():
    try:
        username = request.form['uname']
        password = request.form['password']
        
        with app.app_context():
            # Find user by username
            user = User.query.filter_by(username=username).first()

        # Check if user exists AND if the submitted password matches the stored hash
        if user and bcrypt.check_password_hash(user.password, password):
            session['logged_in'] = True
            session['username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
        return redirect(url_for('login'))
    except Exception as e:
        flash(f'Login error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    try:
        with app.app_context():
            # Fetch data and convert for compatibility
            projects_data = Project.query.all()
            compatible_projects = result_to_list_of_tuples(projects_data, Project)
        # The template now receives data in the expected array/tuple format
        return render_template('dashboard.html', projects=compatible_projects)
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route("/messages")
@login_required
def messages():
    try:
        with app.app_context():
            # Fetch data and convert for compatibility
            messages_data = Contact.query.order_by(Contact.created_at.desc()).all()
            compatible_messages = result_to_list_of_tuples(messages_data, Contact)
        # The template now receives data in the expected array/tuple format
        return render_template('message.html', messages=compatible_messages)
    except Exception as e:
        # This will now flash a clearer error if it still fails
        flash(f'Error loading messages: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route("/contact", methods=['POST'])
def contact_post():
    try:
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        with app.app_context():
            new_message = Contact(name=name, email=email, message=message)
            db.session.add(new_message)
            db.session.commit()
            
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    except Exception as e:
        flash(f'Error sending message: {str(e)}', 'error')
        return redirect(url_for('contact'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['uname']
            email = request.form['email']
            password = request.form['password']
            
            # HASH the password before storing
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            with app.app_context():
                new_user = User(username=username, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # Handle unique constraint errors gracefully
            if 'UNIQUE constraint failed' in str(e) or 'IntegrityError' in str(e):
                flash('Username or Email already exists. Please choose another.', 'error')
            else:
                flash(f'Registration error: {str(e)}', 'error')
            return redirect(url_for('register'))
            
    return render_template('registration.html')

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route("/add_project", methods=['POST'])
@login_required
def add_project():
    try:
        pname = request.form['pname']
        projectlink = request.form['projectlink']
        description = request.form['projectDescripton']
        
        with app.app_context():
            new_project = Project(pname=pname, projectlink=projectlink, projectDescripton=description)
            db.session.add(new_project)
            db.session.commit()
        
        flash('Project added successfully!', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error adding project: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route("/delete_project/<pname>")
@login_required
def delete_project(pname):
    try:
        with app.app_context():
            # Find and delete project by name
            project_to_delete = Project.query.filter_by(pname=pname).first()
            if project_to_delete:
                db.session.delete(project_to_delete)
                db.session.commit()
        
        flash('Project deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting project: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@app.route("/delete_message/<int:message_id>")
@login_required
def delete_message(message_id):
    try:
        with app.app_context():
            # Find and delete message by ID
            message_to_delete = Contact.query.get(message_id)
            if message_to_delete:
                db.session.delete(message_to_delete)
                db.session.commit()
        
        flash('Message deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting message: {str(e)}', 'error')
    return redirect(url_for('messages'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    # if init_db(): 
    #     print("Database initialized successfully!")
    # else:
    #     print("Warning: Database initialization failed!")
    
    # app.run(debug=True)
