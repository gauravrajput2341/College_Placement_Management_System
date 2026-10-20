import getpass
import bcrypt, mysql.connector
import config

new_email = input(" gaurav@cpms.com ").strip()
new_pw = getpass.getpass(" gunnu123 ")

if not new_email or len(new_pw) < 6:
    print("Email is required and the password must be at least 6 characters.")
    raise SystemExit

pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()

db = mysql.connector.connect(host="localhost", user="root",
                             password=config.DB_PASSWORD, database="cpms2")
cur = db.cursor()
cur.execute("UPDATE admin SET email = %s, password_hash = %s WHERE admin_id = 1",
            (new_email, pw_hash))
db.commit()
print("Done. Rows updated:", cur.rowcount)
cur.close()
db.close()