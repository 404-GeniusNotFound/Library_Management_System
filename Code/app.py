import os
from flask import render_template, Flask, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from functools import wraps
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_
import bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SCHEDULER_API_ENABLED'] = True
app.config['SCHEDULER_TIMEZONE'] = "Asia/Kolkata"
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'home'
LIBRARIAN_PIN = '121212'

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

ist = pytz.timezone('Asia/Kolkata')
datetime_ist = datetime.now(ist)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            if current_user.role != role:
                flash('You do not have the right privileges to access this page.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    requests = db.relationship('BookRequest', backref='user_requests', lazy=True)
    borrowed_books = db.relationship(
        'BookRequest',
        primaryjoin="and_(User.id==BookRequest.user_id, "
                    "BookRequest.is_purchased==False)",
        backref='borrower',
        lazy='dynamic'
    )

    purchased_books = db.relationship(
        'BookRequest',
        primaryjoin="and_(User.id==BookRequest.user_id, "
                    "BookRequest.is_purchased==True)",
        backref='purchaser',
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash)


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id', name='fk_section_id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime_ist)
    rating_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    cover_image_path = db.Column(db.String(255), nullable=True)
    pdf_path = db.Column(db.String(255), nullable=True)
    genre = db.Column(db.String(100), nullable=True)

    feedbacks = db.relationship('Feedback', backref='book_feedbacks', lazy=True, cascade="all, delete-orphan")
    requests = db.relationship('BookRequest', backref='book_requests', lazy=True)


class BookRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', name='fk_book_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_user_id'), nullable=False)
    date_requested = db.Column(db.DateTime, default=datetime_ist)
    status = db.Column(db.String(20), default='pending')
    date_issued = db.Column(db.DateTime, nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    is_purchased = db.Column(db.Boolean, default=False)
    date_purchased = db.Column(db.DateTime, default=None)
    book = db.relationship('Book', backref='book_requests', lazy=True)
    user = db.relationship('User', backref='user_requests', lazy=True)


User.requested_books = db.relationship('BookRequest', backref='requesting_user')


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime_ist)

    book = db.relationship('Book', backref='book_feedback')
    user = db.relationship('User', backref='user_feedback')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/librarian/register', methods=['GET', 'POST'])
def librarian_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pin = request.form['pin'].strip()

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken', 'error')
        elif len(password) < 8:
            flash('Password too short', 'error')
        elif not any(char.isdigit() for char in password):
            flash('Password should contain at least one number', 'error')
        elif pin != LIBRARIAN_PIN:
            flash('Incorrect PIN', 'error')
        else:
            try:
                new_user = User(username=username, role='librarian')
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Librarian registered successfully', 'success')
                return redirect(url_for('librarian_login'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred during registration: {e}', 'error')
                return render_template('register_librarian.html')

    return render_template('register_librarian.html')


@app.route('/librarian/login', methods=['GET', 'POST'])
def librarian_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful', 'success')
            return redirect(url_for('librarian_dashboard'))
        else:
            flash('Password incorrect or user does not exist', 'error')

    return render_template('login_librarian.html')


@app.route('/reader/register', methods=['GET', 'POST'])
def reader_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken.', 'error')
        elif len(password) < 8:
            flash('Password too short. Must be at least 8 characters.', 'error')
        elif not any(char.isdigit() for char in password):
            flash('Password should contain at least one number.', 'error')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            try:
                db.session.commit()
                flash('Reader registered successfully.', 'success')
                return redirect(url_for('reader_login'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'error')

    return render_template('register_reader.html')


@app.route('/reader/login', methods=['GET', 'POST'])
def reader_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful.', 'success')
            return redirect(url_for('reader_dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login_reader.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/reader/dashboard')
@login_required
@login_required
def reader_dashboard():

    borrowed_books = Book.query.join(BookRequest).filter(
        and_(
            BookRequest.user_id == current_user.id,
            BookRequest.status == 'issued'
        )
    ).all()


    purchased_books = Book.query.join(BookRequest).filter(
        and_(
            BookRequest.user_id == current_user.id,
            BookRequest.is_purchased == True
        )
    ).all()

    return render_template('reader_dashboard.html', borrowed_books=borrowed_books, purchased_books=purchased_books)



@app.route('/reader/request_book/<int:book_id>', methods=['POST'])
@login_required
def request_book(book_id):
    if BookRequest.query.filter_by(user_id=current_user.id, status='pending').count() >= 5:
        flash('You have reached the maximum number of pending requests.', 'error')
        return redirect(url_for('books'))

    new_request = BookRequest(book_id=book_id, user_id=current_user.id)
    db.session.add(new_request)
    db.session.commit()

    flash('Your request has been submitted.', 'success')
    return redirect(url_for('book_details'))

@app.route('/librarian/update_request/<int:request_id>/<action>', methods=['POST'])
@login_required
@role_required('librarian')
def update_request(request_id, action):
    book_request = BookRequest.query.get_or_404(request_id)

    if action == 'issue' and book_request.status == 'pending':
        book_request.date_issued = datetime_ist
        book_request.return_date = datetime_ist + timedelta(days=7)
        flash('Book has been issued.', category='success')
    elif action == 'revoke' and book_request.status == 'issued':
        book_request.return_date = datetime_ist
        book_request.status = 'revoked'
        flash('Book access has been revoked.', category='success')
    else:
        flash('Invalid action or request status.', category='error')

    db.session.commit()
    return redirect(url_for('manage_requests'))

@app.route('/librarian/issue_all_books', methods=['POST'])
@login_required
@role_required('librarian')
def issue_all_books():

    pending_requests = BookRequest.query.filter_by(status='pending').all()

    for request in pending_requests:
        request.status = 'issued'
        request.date_issued = datetime_ist
        request.return_date=datetime_ist + timedelta(days=7)
    try:
        db.session.commit()
        flash('All pending requests have been issued.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while issuing books.', 'error')

    return redirect(url_for('manage_requests'))

def check_and_revoke_overdue_books():
    with app.app_context():
        now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
        overdue_books = BookRequest.query.filter(
            BookRequest.status == 'issued',
            BookRequest.return_date < now_ist
        ).all()

        for book_request in overdue_books:
            book_request.status = 'revoked'
        if overdue_books:
            db.session.commit()

scheduler.add_job(id='ScheduledTask', func=check_and_revoke_overdue_books, trigger='interval', hours=24)

@app.teardown_appcontext
def shutdown_scheduler(response_or_exc):
    if scheduler.running:
        scheduler.shutdown(wait=False)
    return response_or_exc

@app.route('/librarian/dashboard')
@login_required
@role_required('librarian')
def librarian_dashboard():
    return render_template('librarian_dashboard.html')

@app.route('/librarian/manage_requests', methods=['GET'])
@login_required
@role_required('librarian')
def manage_requests():
    requests = BookRequest.query.all()
    return render_template('manage_requests.html', requests=requests)

@app.route('/librarian/manage_books')
@login_required
@role_required('librarian')
def manage_books():
    books = Book.query.all()
    return render_template('manage_books.html', books=books)


@app.route('/book_details/<int:book_id>')
@login_required
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    book_feedbacks = book.feedbacks
    return render_template('book_details.html', book=book)


@app.route('/section/new', methods=['GET', 'POST'])
@login_required
@role_required('librarian')
def add_section():
    if request.method == 'POST':
        section_name = request.form.get('name')
        section_description = request.form.get('description')

        if not section_name:
            return 'Section name is required', 400

        # Check if a section with the same name already exists
        existing_section = Section.query.filter_by(name=section_name).first()
        if existing_section:
            return f'A section with the name {section_name} already exists.', 400

        new_section = Section(name=section_name, description=section_description)
        db.session.add(new_section)
        db.session.commit()

        return redirect(url_for('add_section'))

    return render_template('add_section.html')


@app.route('/rate_book/<int:book_id>', methods=['POST'])
@login_required
def rate_book(book_id):
    try:
        rating = float(request.form.get('rating'))
    except (TypeError, ValueError):
        flash('Invalid rating value.', 'error')
        return redirect(url_for('book_details', book_id=book_id))

    book = Book.query.get_or_404(book_id)

    if book.rating_count and book.rating:
        new_rating = ((book.rating * book.rating_count) + rating) / (book.rating_count + 1)
        book.rating_count += 1
        book.rating = new_rating
    else:
        book.rating = rating
        book.rating_count = 1

    db.session.commit()
    flash('Thank you for rating the book!', 'success')
    return redirect(url_for('book_details', book_id=book_id))


@app.route('/submit_feedback/<int:book_id>', methods=['POST'])
@login_required
def submit_feedback(book_id):
    feedback_text = request.form.get('feedback_text')

    if not current_user.is_authenticated:
        flash('You must be logged in to submit feedback.', 'error')
        return redirect(url_for('home'))

    if feedback_text:
        feedback = Feedback(book_id=book_id, user_id=current_user.id, text=feedback_text)
        db.session.add(feedback)
        db.session.commit()
        flash('Your feedback has been submitted.', 'success')
    else:
        flash('Feedback cannot be empty.', 'error')
    return redirect(url_for('book_details', book_id=book_id))


@app.route('/feedback/<int:book_id>')
@login_required
def feedback_page(book_id):
    book = Book.query.get_or_404(book_id)
    feedbacks = Feedback.query.filter_by(book_id=book_id).all()
    return render_template('feedback.html', feedbacks=feedbacks, book=book)


@app.route('/book/new', methods=['GET', 'POST'])
@login_required
@role_required('librarian')
def add_book():
    if request.method == 'POST':
        name = request.form.get('name')
        author = request.form.get('author')
        content = request.form.get('content')
        section_id = request.form.get('section_id')
        cover_image = request.files.get('cover_image')
        pdf_file = request.files.get('pdf_file')
        genre = request.form.get('genre')
        new_section = request.form.get('new_section')
        if new_section:
            section = Section(name=new_section)
            db.session.add(section)
            db.session.commit()

        if not name or not author or not section_id or not cover_image or not pdf_file:
            flash('Book name, author, section, cover image, and PDF are required', 'error')
            return render_template('add_book.html')

        cover_filename = cover_image.filename
        pdf_filename = pdf_file.filename
        cover_image.save(os.path.join(app.root_path, 'static/books_data/cover_image', cover_filename))
        pdf_file.save(os.path.join(app.root_path, 'static/books_data/book_pdf', pdf_filename))

        new_book = Book(
            name=name,
            author=author,
            content=content,
            section_id=section_id,
            cover_image_path=cover_filename,
            pdf_path=pdf_filename,
            genre=genre
        )
        db.session.add(new_book)
        db.session.commit()

        flash('Book added successfully!', 'success')
        return redirect(url_for('books'))

    sections = Section.query.all()
    return render_template('add_book.html', sections=sections)


@app.route('/books', methods=['GET', 'POST'])
@login_required
def books():
    query = request.args.get('search')
    section_filter = request.args.get('section')
    genre_filter = request.args.get('genre')
    sort_filter = request.args.get('sort')  # New sort filter parameter

    books_query = Book.query

    if query:
        books_query = books_query.filter(Book.name.ilike(f'%{query}%'))
    if section_filter and section_filter.isdigit():
        books_query = books_query.filter_by(section_id=section_filter)
    if genre_filter:
        books_query = books_query.filter(Book.genre.ilike(f'%{genre_filter}%'))

    if sort_filter == 'recent':
        books_query = books_query.order_by(Book.date_created.desc())
    elif sort_filter == 'top_rated':
        books_query = books_query.order_by(Book.rating.desc())

    books = books_query.all()
    sections = Section.query.all()
    genres = db.session.query(Book.genre.distinct().label("genre")).all()

    return render_template('books.html', books=books, sections=sections, genres=genres)


@app.route('/reader/my_books')
@login_required
def my_books():
    filter = request.args.get('book_filter', 'borrowed')
    borrowed_book_requests = []
    purchased_book_requests = []

    if filter == 'borrowed':
        borrowed_book_requests = BookRequest.query.filter(
            and_(
                BookRequest.user_id == current_user.id,
                BookRequest.status == 'issued'
            )
        ).all()
    elif filter == 'purchased':
        purchased_book_requests = BookRequest.query.filter(
            and_(
                BookRequest.user_id == current_user.id,
                BookRequest.is_purchased == True
            )
        ).all()

    borrowed_books = [br.book for br in borrowed_book_requests]
    purchased_books = [pr.book for pr in purchased_book_requests]

    return render_template(
        'my_books.html',
        borrowed_books=borrowed_books,
        purchased_books=purchased_books,
        borrowed_book_requests=borrowed_book_requests,
        purchased_book_requests=purchased_book_requests,
        filter=filter
    )



@app.route('/my_borrowed_books')
@login_required
def my_borrowed_books():
    current_time = datetime_ist
    borrowed_books = Book.query.filter(Book.user_id == current_user.id, Book.return_date > current_time).all()
    borrowed_books_with_days_left = [
        {
            'book': book,
            'days_left': (book.return_date - current_time).days
        } for book in borrowed_books
    ]
    return render_template('my_borrowed_books.html', borrowed_books=borrowed_books_with_days_left)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


@app.route('/book/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@role_required('librarian')
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    sections = Section.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        author = request.form.get('author')
        content = request.form.get('content')
        section_id = request.form.get('section_id')
        genre = request.form.get('genre')

        book.name = name
        book.author = author
        book.content = content
        book.section_id = section_id
        book.genre = genre

        cover_image = request.files.get('cover_image')
        if cover_image and cover_image.filename != '':
            cover_filename = secure_filename(cover_image.filename)
            cover_image_path = os.path.join('static', 'books_data', 'cover_image', cover_filename)
            cover_image.save(cover_image_path)
            book.cover_image_path = cover_filename

        pdf_file = request.files.get('pdf_file')
        if pdf_file and pdf_file.filename != '':
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_file_path = os.path.join('static', 'books_data', 'book_pdf', pdf_filename)
            pdf_file.save(pdf_file_path)
            book.pdf_path = pdf_filename

        db.session.commit()
        flash('Book updated successfully!', category='success')
        return redirect(url_for('manage_books'))

    return render_template('edit_book.html', book=book, sections=sections)


@app.route('/book/delete/<int:book_id>', methods=['POST'])
@login_required
@role_required('librarian')
def delete_book(book_id):

    BookRequest.query.filter_by(book_id=book_id).delete()


    Feedback.query.filter_by(book_id=book_id).delete()


    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()

    flash('Book successfully deleted.', 'success')
    return redirect(url_for('manage_books'))

@app.route('/librarian/book_activity')
@login_required
def book_activity():

    borrowed_books_details = BookRequest.query.filter_by(is_purchased=False).all()

    purchased_books_details = BookRequest.query.filter_by(is_purchased=True).all()

    return render_template(
        'book_activity.html',
        borrowed_books_details=borrowed_books_details,
        purchased_books_details=purchased_books_details
    )

@app.route('/borrow_book/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):

    existing_borrow_or_pending = BookRequest.query.filter(
        and_(
            BookRequest.user_id == current_user.id,
            BookRequest.book_id == book_id,
            or_(
                BookRequest.status == 'issued',
                BookRequest.status == 'pending'
            )
        )
    ).first()

    if existing_borrow_or_pending:
        flash('You already have this book borrowed or have a pending request.', 'warning')
        return redirect(url_for('book_details', book_id=book_id))


    borrowed_count = BookRequest.query.filter(
        and_(
            BookRequest.user_id == current_user.id,
            BookRequest.status == 'issued'
        )
    ).count()

    if borrowed_count >= 5:
        flash('You cannot borrow more than 5 books at a time.', 'warning')
        return redirect(url_for('book_details', book_id=book_id))


    new_borrow_request = BookRequest(
        book_id=book_id,
        user_id=current_user.id,
        date_requested=datetime_ist,
        status='pending'
    )
    db.session.add(new_borrow_request)
    try:
        db.session.commit()
        flash('Your borrow request has been sent to the librarian.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')

    return redirect(url_for('book_details', book_id=book_id))

@app.route('/borrowed-books')
@login_required
def borrowed_books():
    current_user_id = current_user.id
    borrowed_books = Book.query.filter_by(user_id=current_user_id, status='borrowed').all()
    return render_template('borrowed_books.html', borrowed_books=borrowed_books)


@app.route('/book/purchase/<int:book_id>', methods=['POST'])
@login_required
def purchase_book(book_id):

    payment_successful = True

    if payment_successful:
        new_purchase = BookRequest(
            book_id=book_id,
            user_id=current_user.id,
            is_purchased=True,
            date_purchased=datetime_ist
        )
        db.session.add(new_purchase)
        db.session.commit()
        flash('Please pay and download the book.', 'success')
        return redirect(url_for('book_payment', book_id=book_id))
    else:
        flash('Payment failed.', 'error')
        return redirect(url_for('book_payment', book_id=book_id))


@app.route('/book/payment/<int:book_id>', methods=['GET'])
@login_required
def book_payment(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('payment.html', book=book)

@app.route('/book/payment/<int:book_id>', methods=['POST'])
@login_required
def process_payment(book_id):
    flash('Payment successful. Thank you for your purchase!', 'success')
    return redirect(url_for('book_download_page', book_id=book_id))


@app.route('/book/download_page/<int:book_id>')
@login_required
def book_download_page(book_id):
    book = Book.query.get_or_404(book_id)
    context = {
        'book': book,
        'pdf_url': url_for('static', filename='books_data/book_pdf/' + book.pdf_path),
        'cover_image_url': url_for('static', filename='books_data/cover_image/' + book.cover_image_path)
    }

    return render_template('download_book.html', **context)

@app.route('/book/return/<int:book_request_id>', methods=['POST'])
@login_required
def return_book(book_request_id):

    book_request = BookRequest.query.get_or_404(book_request_id)

    if book_request.user_id == current_user.id:
        book_request.status = 'returned'
        book_request.return_date = datetime_ist

        db.session.commit()

        flash('You have successfully returned the book.', 'success')
    else:
        flash('This book was not borrowed by you.', 'error')

    return redirect(url_for('my_books'))


@app.route('/librarian/stats')
@login_required
def stats():

    borrowed_books_stats = db.session.query(
        User.username, func.count(BookRequest.book_id)
    ).join(BookRequest, User.id == BookRequest.user_id
    ).filter(BookRequest.status.in_(['issued', 'revoked', 'returned'])
    ).group_by(User.username).all()

    purchased_books_stats = db.session.query(
        User.username, func.count(BookRequest.book_id).label('total')
    ).join(BookRequest, User.id == BookRequest.user_id
    ).filter(BookRequest.is_purchased == True
    ).group_by(User.username).all()

    borrowed_labels = [stat[0] for stat in borrowed_books_stats]
    borrowed_counts = [stat[1] for stat in borrowed_books_stats]

    purchased_labels = [stat[0] for stat in purchased_books_stats]
    purchased_counts = [stat[1] for stat in purchased_books_stats]

    return render_template('stats.html',
                           borrowed_labels=borrowed_labels,
                           borrowed_counts=borrowed_counts,
                           purchased_labels=purchased_labels,
                           purchased_counts=purchased_counts)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
