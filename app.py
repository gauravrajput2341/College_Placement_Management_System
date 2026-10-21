from datetime import date
from flask import Flask, render_template, request, redirect, session, flash, abort, send_from_directory
import os, uuid
import os
import mysql.connector, bcrypt
from resume_utils import extract_text
from matcher import match_drives, match_applicants
from flask_wtf import CSRFProtect
from decimal import Decimal, InvalidOperation

def validate_package(value):
    try:
        package = Decimal(str(value).strip())
        if not package.is_finite() or package <= 0:
            return None

        return package

    except (InvalidOperation, ValueError, TypeError):
        return None
app = Flask(__name__)
app.config["SECRET_KEY"] = (
    os.getenv("SECRET_KEY") or "cpms-local-dev-key-change-before-deployment"
)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
csrf = CSRFProtect(app)
# ---- Resume upload settings ----
UPLOAD_FOLDER = os.path.join(app.root_path, "uploads", "resumes")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024   # max 2 MB

@app.errorhandler(413)

def file_too_large(e):

    flash("File is too large. Maximum 2 MB allowed.")

    return redirect("/student")



# Allowed departments (the register page shows these in a dropdown).

# To add a new department, just add it to this list.

DEPARTMENTS = ["CSE", "CSE-AIML", "IT", "ECE", "EE", "ME", "CE"]

print("DB_PASSWORD configured:", os.getenv("DB_PASSWORD") is not None)

def get_db():

    return mysql.connector.connect(

        host="localhost",

        user="root",

        password=os.getenv("DB_PASSWORD"),

        database="cpms2"

    )



def notify(cur, student_id, message):

    """Save one notification for a student (uses the caller's cursor, so it commits together)."""

    cur.execute("INSERT INTO notification (student_id, message) VALUES (%s, %s)",

                (student_id, message))



@app.route("/")

def home():

    return render_template("index.html")





# ---------------- STUDENT ----------------

@app.route("/register", methods=["GET", "POST"])

def register():

    msg = ""

    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        password = request.form["password"]

        department = request.form["department"]

        cgpa = float(request.form["cgpa"])



        if department not in DEPARTMENTS:

            msg = "Please select a valid department."

        elif not 0 <= cgpa <= 10:

            msg = "CGPA must be between 0 and 10."

        else:

            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            try:

                db = get_db()

                cur = db.cursor()

                cur.execute(

                    "INSERT INTO student (name, email, password_hash, department, cgpa) VALUES (%s, %s, %s, %s, %s)",

                    (name, email, pw_hash, department, cgpa))

                db.commit()

                cur.close()

                db.close()

                msg = "Registered successfully! Now you can login."

            except mysql.connector.IntegrityError:

                msg = "This email is already registered."

    return render_template("register.html", msg=msg, departments=DEPARTMENTS)



@app.route("/login", methods=["GET", "POST"])

def login():

    msg = ""

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]



        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM student WHERE email = %s", (email,))

        user = cur.fetchone()

        cur.close()

        db.close()



        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):

            session.clear()

            session["student_id"] = user["student_id"]

            return redirect("/student")

        msg = "Wrong email or password."

    return render_template("login.html", msg=msg)



@app.route("/student")

def student_page():

    if "student_id" not in session:

        return redirect("/login")



    db = get_db()

    cur = db.cursor(dictionary=True)



    cur.execute("SELECT * FROM student WHERE student_id = %s", (session["student_id"],))

    me = cur.fetchone()



    cur.execute("""

        SELECT d.*, c.name AS company,

               (SELECT COUNT(*) FROM application a

                WHERE a.drive_id = d.drive_id AND a.student_id = %s) AS applied

        FROM drive d JOIN company c ON c.company_id = d.company_id

        WHERE d.min_cgpa <= %s AND d.status = 'approved'

        ORDER BY d.drive_date""", (me["student_id"], me["cgpa"]))

    drives = cur.fetchall()



    # AI/ML: match the student's resume text with each drive's required skills

    scores = match_drives(me.get("resume_text") or "", drives)

    for d in drives:

        d["match"] = scores[d["drive_id"]]

    if me.get("resume_text"):          # best matches first

        drives.sort(key=lambda d: (-d["match"]["skill_match"], -d["match"]["similarity"]))



    cur.execute("""

        SELECT a.applied_on, a.status, d.job_role, c.name AS company,

               r.outcome, r.offered_package

        FROM application a

        JOIN drive d ON d.drive_id = a.drive_id

        JOIN company c ON c.company_id = d.company_id

        LEFT JOIN result r ON r.application_id = a.application_id

        WHERE a.student_id = %s ORDER BY a.applied_on DESC""", (me["student_id"],))

    apps = cur.fetchall()



    cur.execute("""

        SELECT * FROM notification WHERE student_id = %s

        ORDER BY created_at DESC, notification_id DESC LIMIT 10""", (me["student_id"],))

    notes = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS n FROM notification WHERE student_id = %s AND is_read = 0",

                (me["student_id"],))

    unread = cur.fetchone()["n"]



    cur.close()

    db.close()

    return render_template("student.html", me=me, drives=drives, apps=apps,

                           today=date.today(), notes=notes, unread=unread)



@app.route("/student/notifications/read", methods=["POST"])

def mark_notifications_read():

    if "student_id" not in session:

        return redirect("/login")



    db = get_db()

    cur = db.cursor()

    cur.execute("UPDATE notification SET is_read = 1 WHERE student_id = %s", (session["student_id"],))

    db.commit()

    cur.close()

    db.close()

    return redirect("/student")



@app.route("/student/apply/<int:drive_id>", methods=["POST"])

def apply(drive_id):

    if "student_id" not in session:

        return redirect("/login")



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM student WHERE student_id = %s", (session["student_id"],))

    me = cur.fetchone()

    cur.execute("SELECT * FROM drive WHERE drive_id = %s", (drive_id,))

    drive = cur.fetchone()



    if not drive or drive["status"] != "approved":

        flash("Drive not available.")

    elif drive["deadline"] < date.today():

        flash("Deadline is over. You cannot apply.")

    elif me["cgpa"] < drive["min_cgpa"]:

        flash("Your CGPA is below the minimum for this drive.")

    else:

        try:

            cur.execute("INSERT INTO application (student_id, drive_id) VALUES (%s, %s)",

                        (me["student_id"], drive_id))

            db.commit()

            flash("Applied successfully!")

        except mysql.connector.IntegrityError:

            flash("You have already applied to this drive.")



    cur.close()

    db.close()

    return redirect("/student")



@app.route("/student/resume", methods=["POST"])

def upload_resume():

    if "student_id" not in session:

        return redirect("/login")



    f = request.files.get("resume")

    if not f or f.filename == "":

        flash("Please choose a file.")

        return redirect("/student")

    if not f.filename.lower().endswith(".pdf"):

        flash("Only PDF files are allowed.")

        return redirect("/student")

    if f.read(4) != b"%PDF":          # real PDFs start with these 4 characters

        flash("This file is not a valid PDF.")

        return redirect("/student")

    f.seek(0)



    new_name = f"{session['student_id']}_{uuid.uuid4().hex}.pdf"

    save_path = os.path.join(UPLOAD_FOLDER, new_name)

    f.save(save_path)

    text = extract_text(save_path)      # resume text, used later for AI/ML matching



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT resume_file FROM student WHERE student_id = %s", (session["student_id"],))

    old = cur.fetchone()["resume_file"]

    cur.execute("UPDATE student SET resume_file = %s, resume_text = %s WHERE student_id = %s",

                (new_name, text, session["student_id"]))

    db.commit()

    cur.close()

    db.close()



    if old:   # delete the old resume file

        try:

            os.remove(os.path.join(UPLOAD_FOLDER, old))

        except FileNotFoundError:

            pass

    if text:

        flash("Resume uploaded.")

    else:

        flash("Resume uploaded, but no readable text was found. Please upload a text-based PDF (not a scanned image).")

    return redirect("/student")



@app.route("/student/resume/view")

def view_my_resume():

    if "student_id" not in session:

        return redirect("/login")



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT resume_file FROM student WHERE student_id = %s", (session["student_id"],))

    row = cur.fetchone()

    cur.close()

    db.close()



    if not row or not row["resume_file"]:

        abort(404)

    return send_from_directory(UPLOAD_FOLDER, row["resume_file"])



# ---------------- COMPANY ----------------

@app.route("/company/register", methods=["GET", "POST"])

def company_register():

    msg = ""

    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        pw_hash = bcrypt.hashpw(request.form["password"].encode(), bcrypt.gensalt()).decode()

        try:

            db = get_db()

            cur = db.cursor()

            cur.execute("INSERT INTO company (name, email, password_hash) VALUES (%s, %s, %s)",

                        (name, email, pw_hash))

            db.commit()

            cur.close()

            db.close()

            msg = "Company registered! Now you can login."

        except mysql.connector.IntegrityError:

            msg = "This email is already registered."

    return render_template("company_register.html", msg=msg)



@app.route("/company/login", methods=["GET", "POST"])

def company_login():

    msg = ""

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]



        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM company WHERE email = %s", (email,))

        user = cur.fetchone()

        cur.close()

        db.close()



        if user and user["password_hash"] and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):

            session.clear()

            session["company_id"] = user["company_id"]

            return redirect("/company")

        msg = "Wrong email or password."

    return render_template("company_login.html", msg=msg)




@app.route("/company", methods=["GET", "POST"])
def company_page():
    if "company_id" not in session:
        return redirect("/company/login")

    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        f = request.form

        package_lpa = validate_package(f.get("package_lpa", ""))

        try:
            min_cgpa = Decimal(f.get("min_cgpa", "").strip())
            if not min_cgpa.is_finite() or not (0 <= min_cgpa <= 10):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            flash("CGPA must be between 0 and 10.")
            cur.close()
            db.close()
            return redirect("/company")

        job_role = f.get("job_role", "").strip()
        skills = f.get("required_skills", "").strip()[:2000]
        drive_date = f.get("drive_date", "").strip()
        deadline = f.get("deadline", "").strip()

        if package_lpa is None:
            flash("Package LPA must be greater than 0.")
        elif not job_role:
            flash("Please enter a job role.")
        elif not skills:
            flash("Please enter the required skills.")
        elif not drive_date or not deadline:
            flash("Please enter both drive date and deadline.")
        else:
            try:
                drive_day = date.fromisoformat(drive_date)
                deadline_day = date.fromisoformat(deadline)

                if deadline_day > drive_day:
                    flash("Deadline cannot be after the drive date.")
                else:
                    cur.execute(
                        """
                        INSERT INTO drive
                        (company_id, job_role, package_lpa, min_cgpa,
                         drive_date, deadline, required_skills)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            session["company_id"],
                            job_role,
                            package_lpa,
                            min_cgpa,
                            drive_date,
                            deadline,
                            skills,
                        ),
                    )
                    db.commit()
                    flash(
                        "Drive posted! It will be visible to students "
                        "after admin approval."
                    )
            except ValueError:
                flash("Please enter valid drive dates.")

        cur.close()
        db.close()
        return redirect("/company")

    cur.execute(
        "SELECT * FROM company WHERE company_id = %s",
        (session["company_id"],),
    )
    company = cur.fetchone()

    cur.execute(
        """
        SELECT d.*,
               (SELECT COUNT(*) FROM application a
                WHERE a.drive_id = d.drive_id) AS applicants
        FROM drive d
        WHERE d.company_id = %s
        ORDER BY d.drive_id DESC
        """,
        (session["company_id"],),
    )
    drives = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        "company.html",
        company=company,
        drives=drives,
    )


    if package_lpa is None:
        flash("Package LPA must be greater than 0.", "error")
    return redirect(request.referrer or "/company")

    if request.method == "POST":

        f = request.form

        package = float(f["package_lpa"])

        min_cgpa = float(f["min_cgpa"])

        skills = f.get("required_skills", "").strip()[:2000]

        if package < 0 or not 0 <= min_cgpa <= 10:

            flash("Package must be positive and CGPA between 0 and 10.")

        elif f["deadline"] > f["drive_date"]:

            flash("Deadline cannot be after the drive date.")

        elif not skills:

            flash("Please enter the required skills.")

        else:

            cur.execute(

                "INSERT INTO drive (company_id, job_role, package_lpa, min_cgpa, drive_date, deadline, required_skills) "

                "VALUES (%s, %s, %s, %s, %s, %s, %s)",

                (session["company_id"], f["job_role"], package, min_cgpa, f["drive_date"], f["deadline"], skills))

            db.commit()

            flash("Drive posted! It will be visible to students after admin approval.")

        cur.close()

        db.close()

        return redirect("/company")



    cur.execute("SELECT * FROM company WHERE company_id = %s", (session["company_id"],))

    company = cur.fetchone()

    cur.execute("""

        SELECT d.*, (SELECT COUNT(*) FROM application a WHERE a.drive_id = d.drive_id) AS applicants

        FROM drive d WHERE d.company_id = %s ORDER BY d.drive_id DESC""", (session["company_id"],))

    drives = cur.fetchall()

    cur.close()

    db.close()

    return render_template("company.html", company=company, drives=drives)



@app.route("/company/drive/<int:drive_id>")

def company_drive(drive_id):

    if "company_id" not in session:

        return redirect("/company/login")



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("SELECT * FROM drive WHERE drive_id = %s", (drive_id,))

    drive = cur.fetchone()



    # company can open ONLY its own drives

    if not drive or drive["company_id"] != session["company_id"]:

        cur.close()

        db.close()

        abort(403)



    cur.execute("""

        SELECT a.application_id, a.status, s.name, s.email, s.department, s.cgpa,

               s.resume_file, s.resume_text

        FROM application a

        JOIN student s ON s.student_id = a.student_id

        WHERE a.drive_id = %s ORDER BY s.cgpa DESC""", (drive_id,))

    apps = cur.fetchall()

    cur.close()

    db.close()



    # AI/ML: score every applicant against this drive, best match first (CGPA breaks ties)

    scores = match_applicants(drive.get("required_skills"), apps)

    for a in apps:

        a["match"] = scores[a["application_id"]]

    apps.sort(key=lambda a: (-a["match"]["skill_match"], -a["match"]["similarity"]))



    return render_template("company_applicants.html", drive=drive, apps=apps)



@app.route("/resume/<int:application_id>")

def view_resume(application_id):

    # Admin: can open any resume.

    # Company: can open a resume ONLY if the student applied to one of ITS drives.

    # Everyone else: login page.

    is_admin = "admin_id" in session

    is_company = "company_id" in session

    if not is_admin and not is_company:

        return redirect("/login")



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("""

        SELECT s.resume_file, d.company_id

        FROM application a

        JOIN student s ON s.student_id = a.student_id

        JOIN drive d ON d.drive_id = a.drive_id

        WHERE a.application_id = %s""", (application_id,))

    row = cur.fetchone()

    cur.close()

    db.close()



    if not row or not row["resume_file"]:

        abort(404)

    if not is_admin and row["company_id"] != session["company_id"]:

        abort(403)

    return send_from_directory(UPLOAD_FOLDER, row["resume_file"])



# ---------------- ADMIN ----------------

@app.route("/admin/login", methods=["GET", "POST"])

def admin_login():

    msg = ""

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]



        db = get_db()

        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM admin WHERE email = %s", (email,))

        user = cur.fetchone()

        cur.close()

        db.close()



        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):

            session.clear()

            session["admin_id"] = user["admin_id"]

            return redirect("/admin")

        msg = "Wrong email or password."

    return render_template("admin_login.html", msg=msg)



@app.route("/admin")

def admin_page():

    if "admin_id" not in session:

        return redirect("/admin/login")



    db = get_db()

    cur = db.cursor(dictionary=True)



    cur.execute("SELECT COUNT(*) AS n FROM student")

    total = cur.fetchone()["n"]



    cur.execute("""

        SELECT COUNT(DISTINCT a.student_id) AS placed,

               ROUND(AVG(r.offered_package), 2) AS avg_pkg,

               MAX(r.offered_package) AS max_pkg

        FROM result r JOIN application a ON a.application_id = r.application_id

        WHERE r.outcome = 'selected'""")

    row = cur.fetchone()

    placed = row["placed"]

    stats = {

        "total": total,

        "placed": placed,

        "unplaced": total - placed,

        "percent": round(placed / total * 100, 1) if total else 0,

        "avg_pkg": float(row["avg_pkg"] or 0),

        "max_pkg": float(row["max_pkg"] or 0),

    }



    cur.execute("""

        SELECT s.department,

               COUNT(DISTINCT s.student_id) AS total,

               COUNT(DISTINCT CASE WHEN r.outcome = 'selected' THEN s.student_id END) AS placed

        FROM student s

        LEFT JOIN application a ON a.student_id = s.student_id

        LEFT JOIN result r ON r.application_id = a.application_id

        GROUP BY s.department ORDER BY s.department""")

    dept = cur.fetchall()



    cur.execute("""

        SELECT c.name, COUNT(*) AS selected, ROUND(AVG(r.offered_package), 2) AS avg_pkg

        FROM result r

        JOIN application a ON a.application_id = r.application_id

        JOIN drive d ON d.drive_id = a.drive_id

        JOIN company c ON c.company_id = d.company_id

        WHERE r.outcome = 'selected' GROUP BY c.name ORDER BY selected DESC""")

    companies = cur.fetchall()



    cur.execute("""

        SELECT d.*, c.name AS company FROM drive d

        JOIN company c ON c.company_id = d.company_id

        WHERE d.status = 'pending' ORDER BY d.drive_id""")

    pending = cur.fetchall()

    cur.execute("""

        SELECT d.*, c.name AS company,

               (SELECT COUNT(*) FROM application a WHERE a.drive_id = d.drive_id) AS applicants

        FROM drive d JOIN company c ON c.company_id = d.company_id

        WHERE d.status = 'approved' ORDER BY d.drive_id DESC""")

    approved = cur.fetchall()



    cur.close()

    db.close()

    return render_template("admin.html", stats=stats, dept=dept, companies=companies, pending=pending, approved=approved)





@app.route("/admin/approve/<int:drive_id>", methods=["POST"])

def admin_approve(drive_id):

    if "admin_id" not in session:

        return redirect("/admin/login")



    db = get_db()

    cur = db.cursor()

    cur.execute("UPDATE drive SET status = 'approved' WHERE drive_id = %s", (drive_id,))

    db.commit()

    cur.close()

    db.close()

    flash("Drive approved.")

    return redirect("/admin")



@app.route("/admin/drive/<int:drive_id>")

def admin_drive(drive_id):

    if "admin_id" not in session:

        return redirect("/admin/login")



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("""

        SELECT d.*, c.name AS company FROM drive d

        JOIN company c ON c.company_id = d.company_id

        WHERE d.drive_id = %s""", (drive_id,))

    drive = cur.fetchone()

    if not drive:

        cur.close()

        db.close()

        abort(404)



    cur.execute("""

        SELECT a.application_id, a.status, s.name, s.email, s.department, s.cgpa,

               d.job_role, s.resume_file, s.resume_text, r.outcome, r.offered_package

        FROM application a

        JOIN student s ON s.student_id = a.student_id

        JOIN drive d ON d.drive_id = a.drive_id

        LEFT JOIN result r ON r.application_id = a.application_id

        WHERE a.drive_id = %s ORDER BY s.cgpa DESC""", (drive_id,))

    apps = cur.fetchall()

    cur.close()

    db.close()



    # AI/ML: show match score for every applicant (list stays sorted by CGPA)

    scores = match_applicants(drive.get("required_skills"), apps)

    for a in apps:

        a["match"] = scores[a["application_id"]]



    return render_template("admin_applicants.html", drive=drive, apps=apps)



@app.route("/admin/status/<int:application_id>", methods=["POST"])

def admin_status(application_id):

    if "admin_id" not in session:

        return redirect("/admin/login")



    status = request.form["status"]

    if status not in ("shortlisted", "rejected"):

        abort(400)



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("""

        SELECT a.drive_id, a.student_id, d.job_role, c.name AS company

        FROM application a

        JOIN drive d ON d.drive_id = a.drive_id

        JOIN company c ON c.company_id = d.company_id

        WHERE a.application_id = %s""", (application_id,))

    row = cur.fetchone()

    if not row:

        cur.close()

        db.close()

        abort(404)



    cur.execute("SELECT 1 FROM result WHERE application_id = %s", (application_id,))

    if cur.fetchone():

        flash("Final result already declared. Status cannot be changed.")

    else:

        cur.execute("UPDATE application SET status = %s WHERE application_id = %s",

                    (status, application_id))

        if status == "shortlisted":

            msg = f"You have been shortlisted for {row['job_role']} at {row['company']}."

        else:

            msg = f"Your application for {row['job_role']} at {row['company']} was not successful."

        notify(cur, row["student_id"], msg)

        db.commit()

    cur.close()

    db.close()

    return redirect(f"/admin/drive/{row['drive_id']}")



@app.route("/admin/result/<int:application_id>", methods=["POST"])

def admin_result(application_id):

    if "admin_id" not in session:

        return redirect("/admin/login")



    outcome = request.form["outcome"]

    if outcome not in ("selected", "not_selected"):

        abort(400)



    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("""

        SELECT a.drive_id, a.status, a.student_id, d.job_role, c.name AS company

        FROM application a

        JOIN drive d ON d.drive_id = a.drive_id

        JOIN company c ON c.company_id = d.company_id

        WHERE a.application_id = %s""", (application_id,))

    row = cur.fetchone()

    if not row:

        cur.close()

        db.close()

        abort(404)



    if row["status"] != "shortlisted":

        flash("Result can only be declared for shortlisted students.")

    else:

        package = None

        ok = True
        if outcome == "selected":
            package = validate_package(request.form.get("package", ""))
        if package is None:
            ok = False
            flash("Package must be a valid number greater than 0.")
        if ok:

            try:

                cur.execute(

                    "INSERT INTO result (application_id, outcome, offered_package) VALUES (%s, %s, %s)",

                    (application_id, outcome, package))

                if outcome == "selected":

                    msg = f"Congratulations! You are selected for {row['job_role']} at {row['company']} ({package} LPA)."

                else:

                    msg = f"Final result for {row['job_role']} at {row['company']}: not selected."

                notify(cur, row["student_id"], msg)

                db.commit()

                flash("Result saved.")

            except mysql.connector.IntegrityError:

                flash("Result already declared for this student.")



    cur.close()

    db.close()

    return redirect(f"/admin/drive/{row['drive_id']}")



# ---------------- LOGOUT ----------------

@app.route("/logout")

def logout():

    session.clear()

    return redirect("/")



if __name__ == "__main__":

    app.run(debug=True)
