import csv
from models import db, Contact
from security import encrypt, decrypt

def import_contacts(csv_file):

    existing_contacts = Contact.query.all()
    existing_emails = [decrypt(c.email_enc) for c in existing_contacts]
    new_contacts_count = 0
    
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email_to_add = row["email"].strip().lower() 
            
            
            if email_to_add in existing_emails:
                print(f"Atlandı (Zaten Kayıtlı): {email_to_add}")
                continue
            
            contact = Contact(
                name=row["name"],
                email_enc=encrypt(email_to_add)
            )
            db.session.add(contact)
            existing_emails.append(email_to_add)
            new_contacts_count += 1
            
        db.session.commit()
        print(f"İşlem tamamlandı! {new_contacts_count} yeni müşteri KITE'a eklendi.")