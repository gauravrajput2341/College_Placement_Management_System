import bcrypt, mysql.connector
import config

EMAIL = "gaurav@cpms.com"
PASSWORD = "gunnu123"

pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

db = mysql.connector.connect(host="localhost", user="root",
                             password=config.DB_PASSWORD, database="cpms2")
cur = db.cursor(dictionary=True)

cur.execute("DELETE FROM admin")
cur.execute("INSERT INTO admin (name, email, password_hash) VALUES (%s, %s, %s)",
            ("TPO Admin", EMAIL, pw_hash))
db.commit()

cur.execute("SELECT email, password_hash FROM admin")
row = cur.fetchone()
print("Stored email:", row["email"])
print("Password check:", bcrypt.checkpw(PASSWORD.encode(), row["password_hash"].encode()))
cur.close()
db.close()