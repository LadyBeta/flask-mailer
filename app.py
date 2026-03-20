from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Contact, SmtpAccount
from csv_import import import_contacts
from security import decrypt, encrypt
from mailer import send_email
from flask_apscheduler import APScheduler 
import os
from werkzeug.utils import secure_filename
import csv

app = Flask(__name__)
app.secret_key = "kite_floral_ozel_anahtar_123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mailer.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


scheduler = APScheduler()

db.init_app(app)


def mask_email(email: str) -> str:
    if "@" not in email: return email
    name, domain = email.split("@")
    name_mask = name[:2] + "***" if len(name) > 2 else "***"
    domain_name, domain_ext = domain.split(".")
    domain_mask = domain_name[:2] + "***"
    return f"{name_mask}@{domain_mask}.{domain_ext}"


def reset_daily_limits_task():
    """Her gece 00:00'da çalışacak olan sıfırlama fonksiyonu"""
    with app.app_context():
        accounts = SmtpAccount.query.all()
        for a in accounts:
            a.sent_today = 0
        db.session.commit()
        print(">>> Günlük gönderim limitleri başarıyla sıfırlandı.")

with app.app_context():
    db.create_all()
    import_contacts("contacts.csv")
    
   
    if not scheduler.running:
      
        scheduler.add_job(id='reset_job', func=reset_daily_limits_task, trigger='cron', hour=0, minute=0)
        scheduler.init_app(app)
        scheduler.start()


@app.route("/", methods=["GET"])
def home():
    return render_template("base.html")


@app.route("/contacts")
def contacts():
    data = []
    for c in Contact.query.all():
        email = decrypt(c.email_enc)
        data.append({
            "name": c.name,
            "email": mask_email(email)
        })
    return render_template("contacts.html", contacts=data)


@app.route("/send-mail", methods=["GET", "POST"])
def send_mail_page():
    all_contacts = []
    for c in Contact.query.all():
        all_contacts.append({
            "id": c.id,
            "name": c.name,
            "email": mask_email(decrypt(c.email_enc))
        })

    if request.method == "POST":
        subject = request.form["subject"] 
        body = request.form["body"]
        selected_ids = request.form.getlist("selected_contacts")

        if not selected_ids:
            flash("Lütfen en az bir alıcı seçin!", "warning")
            return redirect(url_for('send_mail_page'))

        contacts_to_send = Contact.query.filter(Contact.id.in_(selected_ids)).all()
        report = send_email(subject, body, contacts_to_send)
        return render_template("success.html", results=report)
    
    return render_template("send.html", contacts=all_contacts)


@app.route("/smtp-accounts", methods=["GET", "POST"])
def smtp_accounts_page():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        daily_limit = int(request.form.get("daily_limit", 100))

        if not email or not password:
            flash("E-posta veya şifre boş bırakılamaz!", "danger")
            return redirect(url_for('smtp_accounts_page'))

        mevcut_hesaplar = SmtpAccount.query.all()
        for hesap in mevcut_hesaplar:
            if decrypt(hesap.email_enc).lower() == email.lower():
                flash(f"'{email}' adresi zaten kayıtlı!", "warning")
                return redirect(url_for('smtp_accounts_page'))

        acc = SmtpAccount(
            email_enc=encrypt(email),
            password_enc=encrypt(password),
            daily_limit=daily_limit,
            sent_today=0,
            active=True
        )
        db.session.add(acc)
        db.session.commit()
        flash("SMTP hesabı başarıyla eklendi.", "success")
        return redirect(url_for('smtp_accounts_page'))

    accounts = []
    for a in SmtpAccount.query.all():
        accounts.append({
            "id": a.id,
            "email": mask_email(decrypt(a.email_enc)),
            "daily_limit": a.daily_limit,
            "sent_today": a.sent_today,
            "active": a.active,
            "is_full": a.sent_today >= a.daily_limit
        })
    return render_template("smtp.html", accounts=accounts)


@app.route("/reset-single-limit/<int:account_id>")
def reset_single_limit(account_id):
    account = SmtpAccount.query.get_or_404(account_id)
    account.sent_today = 0
    db.session.commit()

    email_raw = decrypt(account.email_enc)
    flash(f"{mask_email(email_raw)} hesabının limiti sıfırlandı.", "success")
    return redirect(url_for('smtp_accounts_page'))


@app.route("/dashboard")
def dashboard():
    contacts = []
    for c in Contact.query.all():
        contacts.append({
            "name": c.name,
            "email": mask_email(decrypt(c.email_enc))
        })

    accounts = []
    for a in SmtpAccount.query.all():
       accounts.append({
    "email": mask_email(decrypt(a.email_enc)),
    "daily_limit": a.daily_limit,
    "sent_today": a.sent_today,
    "active": a.active,
    "is_full": a.sent_today >= a.daily_limit
     })

    return render_template("index.html", contacts=contacts, accounts=accounts)


@app.route("/import-contacts", methods=["GET", "POST"])
def import_page():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("Dosya seçilmedi!", "danger")
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash("Dosya adı boş!", "warning")
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join("uploads", filename)
            if not os.path.exists("uploads"): os.makedirs("uploads")
            file.save(filepath)

            existing_emails = [decrypt(c.email_enc) for c in Contact.query.all()]
            new_count = 0
            
            with open(filepath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row["email"].strip().lower()
                    if email not in existing_emails:
                        contact = Contact(name=row["name"], email_enc=encrypt(email))
                        db.session.add(contact)
                        existing_emails.append(email)
                        new_count += 1
            
            db.session.commit()
            os.remove(filepath)
            
            flash(f"Uçurtma başarıyla havalandı! {new_count} yeni kişi listeye eklendi.", "success")
            return redirect(url_for('dashboard')) 
            
    return render_template("import.html")

if __name__ == "__main__":
    app.run(debug=True)