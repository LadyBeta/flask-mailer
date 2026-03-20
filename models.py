from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email_enc = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True)

class SmtpAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_enc = db.Column(db.Text, nullable=False)
    password_enc = db.Column(db.Text, nullable=False)
    daily_limit = db.Column(db.Integer, default=100)
    sent_today = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
