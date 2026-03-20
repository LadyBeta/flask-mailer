import smtplib
import time
import random
from email.mime.text import MIMEText
from sqlalchemy import func
from models import db, SmtpAccount
from security import decrypt

def send_email(subject, body, contacts):
    report = []

    for contact in contacts:
        contact_email = decrypt(contact.email_enc)
        # Kişinin ismini de decrypt etmen gerekiyorsa buraya ekle
        # contact_name = decrypt(contact.name_enc) veya sadece contact.name
        contact_name = contact.name 

        # --- KRİTİK DEĞİŞİKLİK BURADA ---
        # Taslak içindeki {{name}} kısmını gerçek isimle değiştiriyoruz
        kisiye_ozel_body = body.replace('{{name}}', contact_name)
        # -------------------------------

        account = SmtpAccount.query.filter(
            SmtpAccount.active == True,
            SmtpAccount.sent_today < SmtpAccount.daily_limit
        ).order_by(
            SmtpAccount.sent_today.asc(),
            func.random()
        ).first()

        if not account:
            report.append({
                "email": contact_email,
                "status": "Başarısız (Tüm SMTP hesaplarının limiti doldu)"
            })
            continue

        try:
            acc_email = decrypt(account.email_enc)
            acc_password = decrypt(account.password_enc)

            # 'body' yerine 'kisiye_ozel_body' kullanıyoruz
            msg = MIMEText(kisiye_ozel_body, "html", "utf-8")
            msg["Subject"] = subject
            msg["From"] = acc_email
            msg["To"] = contact_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(acc_email, acc_password)
                smtp.send_message(msg)

            account.sent_today += 1
            db.session.commit()

            report.append({
                "email": contact_email,
                "status": "Başarılı"
            })

            time.sleep(random.uniform(2, 6))

        except Exception as e:
            report.append({
                "email": contact_email,
                "status": f"Hata: {str(e)}"
            })

    return report