from flask import Flask, render_template, request, redirect, session, url_for, flash
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64
import os
import csv
import uuid
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "pak_election_secret_key_2024" 

# File Paths
CANDIDATES_FILE = "candidates.csv"
USERS_FILE = "users.csv"
VOTES_FILE = "votes.csv"
DETAILS_FILE = "voter_details.csv"
ADMIN_USERS_FILE = "admin_users.csv"

# Owner Credentials
OWNER_USERNAME = "admin"
OWNER_PASSWORD = "secret123" 

# Pakistan Cities Data
PAKISTAN_CITIES = {
    "Punjab": ["Lahore", "Rawalpindi", "Faisalabad", "Multan", "Gujranwala", "Sialkot", "Bahawalpur", "Sargodha", "Sheikhupura", "Jhang", "Rahim Yar Khan", "Gujrat", "Mardan", "Kasur", "Dera Ghazi Khan", "Sahiwal", "Narowal", "Okara", "Chiniot", "Sadiqabad", "Burewala", "Khanewal", "Hafizabad", "Kohat", "Muzaffargarh", "Khanpur", "Gojra", "Bahawalnagar", "Muridke", "Pakpattan", "Abottabad", "Toba Tek Singh", "Jhelum", "Kamoke"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah", "Mirpur Khas", "Jacobabad", "Shikarpur", "Khairpur", "Dadu", "Thatta", "Umerkot", "Tando Allahyar", "Jamshoro", "Badin", "Ghotki", "Sanghar", "Benazirabad", "Kashmore", "Matiari", "Tando Muhammad Khan", "Hala", "Diplo", "Islamkot"],
    "KPK": ["Peshawar", "Mardan", "Abbottabad", "Swat", "Kohat", "Bannu", "Dera Ismail Khan", "Charsadda", "Nowshera", "Haripur", "Tank", "Mansehra", "Mingora", "Hangu", "Lakki Marwat", "Batagram", "Upper Dir", "Lower Dir", "Shangla", "Tor Ghar"],
    "Balochistan": ["Quetta", "Gwadar", "Turbat", "Zhob", "Khuzdar", "Sibi", "Chaman", "Kalat", "Nasirabad", "Jaffarabad", "Loralai", "Musakhel", "Barkhan", "Killa Abdullah", "Killa Saifullah", "Ziarat", "Harnai", "Sherani", "Pishin", "Panjgur", "Washuk", "Awaran"],
    "Islamabad": ["Islamabad"],
    "Gilgit-Baltistan": ["Gilgit", "Skardu", "Hunza", "Nagar", "Ghanche", "Diamer"],
    "Azad Kashmir": ["Muzaffarabad", "Mirpur", "Kotli", "Rawalakot", "Bagh", "Poonch"]
}

# -------------------------
# 1. FILE INITIALIZATION
# -------------------------
def setup_files():
    # Users CSV
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Password", "CNIC", "Phone"])
    
    # Votes CSV
    if not os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Voted"])
            
    # Voter Details CSV
    if not os.path.exists(DETAILS_FILE):
        with open(DETAILS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "CNIC", "City", "Province", "Candidate", "Timestamp"])
            
    # Candidates CSV
    if not os.path.exists(CANDIDATES_FILE):
        data = [
            ["Candidate", "Party", "Votes"],
            ["Imran Khan", "PTI", 0],
            ["Shehbaz Sharif", "PML-N", 0],
            ["Bilawal Bhutto Zardari", "PPP", 0],
            ["Maulana Fazlur Rehman", "JUI-F", 0],
            ["Siraj-ul-Haq", "JI", 0]
        ]
        with open(CANDIDATES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    # Admin Users CSV (NEW)
    if not os.path.exists(ADMIN_USERS_FILE):
        with open(ADMIN_USERS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "Password", "Role"])
            # Create main owner automatically
            writer.writerow([OWNER_USERNAME, generate_password_hash(OWNER_PASSWORD), "Owner"])
        print("[OK] Admin Users DB Initialized")

    print("[OK] System Ready with CNIC Support")

setup_files()

# -------------------------
# 2. HELPER FUNCTIONS
# -------------------------
def validate_cnic(cnic):
    pattern = r'^\d{5}-\d{7}-\d{1}$'
    return re.match(pattern, cnic) is not None

def get_users_list():
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): users.append(row)
    return users

def add_user(username, pwd_hash, cnic, phone):
    with open(USERS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, pwd_hash, cnic, phone])

def get_candidates_df():
    try: return pd.read_csv(CANDIDATES_FILE)
    except: return pd.DataFrame(columns=["Candidate", "Party", "Votes"])

def save_candidates_df(df):
    df.to_csv(CANDIDATES_FILE, index=False)

def get_votes_list():
    votes = []
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): votes.append(row)
    return votes

def add_vote(username):
    with open(VOTES_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, True])

def add_voter_detail(name, cnic, city, province, candidate, timestamp):
    with open(DETAILS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([name, cnic, city, province, candidate, timestamp])

def get_voter_details():
    details = []
    if os.path.exists(DETAILS_FILE):
        with open(DETAILS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f): details.append(row)
    return details

# --- NEW ADMIN HELPERS ---
def get_admin_users():
    admins = []
    if os.path.exists(ADMIN_USERS_FILE):
        with open(ADMIN_USERS_FILE, 'r', newline='') as f:
            for row in csv.DictReader(f):
                admins.append(row)
    return admins

def add_admin_user(username, pwd_hash, role="Observer"):
    with open(ADMIN_USERS_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([username, pwd_hash, role])

# -------------------------
# 3. ROUTES
# -------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if "username" not in session:
        flash("Please login first.", "warning")
        return redirect("/login")

    username = session["username"]
    votes = get_votes_list()
    voted = any(v.get('Username') == username for v in votes)
    candidates = get_candidates_df().to_dict(orient="records")

    if request.method == "POST" and not voted:
        selected = request.form.get("candidate")
        city = request.form.get("city")
        
        province = "Unknown"
        for prov, cities in PAKISTAN_CITIES.items():
            if city in cities:
                province = prov
                break

        if selected and city:
            try:
                df = get_candidates_df()
                df.loc[df["Candidate"] == selected, "Votes"] += 1
                save_candidates_df(df)
                add_vote(username)
                
                users = get_users_list()
                user_cnic = "N/A"
                for u in users:
                    if u['Username'] == username:
                        user_cnic = u.get('CNIC', 'N/A')
                        break
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                add_voter_detail(username, user_cnic, city, province, selected, timestamp)
                
                tx_id = str(uuid.uuid4())[:8].upper()
                session['last_receipt'] = {"candidate": selected, "tx_id": tx_id, "time": timestamp}
                
                flash("Vote cast successfully!", "success")
                return redirect("/results")
            except Exception as e:
                print(f"VOTE ERROR: {e}")
                flash(f"Error: {str(e)}", "danger")
    
    return render_template("index.html", candidates=candidates, voted=voted, cities=PAKISTAN_CITIES)

@app.route("/results")
def results():
    if "username" not in session:
        flash("Please login to view results.", "warning")
        return redirect("/login")
        
    df = get_candidates_df()
    votes = get_votes_list()
    total_voters = len(votes)
    
    winner, loser, chart_bar, chart_pie = "No votes yet", "N/A", "", ""
    total_votes = 0
    candidates = []

    if not df.empty and df["Votes"].sum() > 0:
        total_votes = df["Votes"].sum()
        df["Percentage"] = ((df["Votes"] / total_votes) * 100).round(2)
        
        max_votes = df["Votes"].max()
        winner_rows = df[df["Votes"] == max_votes]
        winner = winner_rows["Candidate"].tolist()[0] + (" & Others" if len(winner_rows) > 1 else "")
        
        min_votes = df["Votes"].min()
        loser_rows = df[df["Votes"] == min_votes]
        loser = loser_rows["Candidate"].tolist()[0] + (" & Others" if len(loser_rows) > 1 else "")

        try:
            img = io.BytesIO()
            plt.figure(figsize=(10, 6))
            colors = ['#ca8a04' if c in winner_rows['Candidate'].values else '#991b1b' if c in loser_rows['Candidate'].values else '#1e3a8a' for c in df['Candidate']]
            plt.bar(df["Candidate"], df["Votes"], color=colors)
            plt.title("Votes by Candidate")
            plt.tight_layout()
            plt.savefig(img, format="png")
            plt.close()
            img.seek(0)
            chart_bar = base64.b64encode(img.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Bar Chart Error: {e}")

        try:
            img2 = io.BytesIO()
            df_pie = df[df['Votes'] > 0]
            if not df_pie.empty:
                plt.figure(figsize=(5, 5))
                plt.pie(df_pie["Votes"], labels=df_pie["Candidate"], autopct="%1.0f%%", startangle=140)
                plt.title("Vote Share")
                plt.tight_layout()
                plt.savefig(img2, format="png", dpi=150)
                plt.close()
                img2.seek(0)
                chart_pie = base64.b64encode(img2.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Pie Chart Error: {e}")

        candidates = df.to_dict(orient="records")

    return render_template("results.html", candidates=candidates, chart_bar=chart_bar, chart_pie=chart_pie, winner=winner, loser=loser, total_votes=total_votes, total_voters=total_voters)

# --- ADMIN: Manage Users (NEW) ---
@app.route("/admin/manage-users", methods=["GET", "POST"])
def admin_manage_users():
    # Only main owner can manage users
    if not session.get('is_owner') or session.get('admin_username') != OWNER_USERNAME:
        flash("Access Denied: Main Owner only.", "danger")
        return redirect("/admin/voter-list")

    if request.method == "POST":
        new_user = request.form.get("username")
        new_pwd = request.form.get("password")
        
        if not new_user or not new_pwd:
            flash("Username and Password required.", "warning")
            return redirect("/admin/manage-users")

        admins = get_admin_users()
        for admin in admins:
            if admin['Username'] == new_user:
                flash("User already exists!", "warning")
                return redirect("/admin/manage-users")
        
        add_admin_user(new_user, generate_password_hash(new_pwd), "Observer")
        flash(f"User '{new_user}' added successfully!", "success")
        return redirect("/admin/manage-users")

    admins = get_admin_users()
    return render_template("admin_manage.html", admins=admins)

# --- ADMIN: Voter List (Updated Logic) ---
@app.route("/admin/voter-list", methods=["GET", "POST"])
def admin_voter_list():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        
        admins = get_admin_users()
        valid_user = False
        
        for admin in admins:
            if admin['Username'] == user and check_password_hash(admin['Password'], pwd):
                valid_user = True
                session['is_owner'] = True
                session['admin_username'] = user
                break
        
        if valid_user:
            return redirect("/admin/voter-list")
        else:
            flash("Access Denied: Invalid Credentials", "danger")
            return redirect("/admin/voter-list")
    
    if not session.get('is_owner'):
        return render_template("admin_login.html")
    
    all_details = get_voter_details()
    filter_party = request.args.get('party')
    
    if filter_party and filter_party != "All":
        filtered_details = [row for row in all_details if row['Candidate'] == filter_party]
    else:
        filtered_details = all_details
    
    parties = sorted(list(set(row['Candidate'] for row in all_details)))

    return render_template("admin_list.html", 
                           details=filtered_details, 
                           all_count=len(all_details),
                           current_filter=filter_party,
                           parties=parties)

@app.route("/admin/back-to-site")
def admin_back_to_site():
    session.pop('is_owner', None)
    session.pop('admin_username', None)
    return redirect("/")

@app.route("/admin/logout")
def admin_logout():
    session.pop('is_owner', None)
    session.pop('admin_username', None)
    flash("Owner session ended.", "info")
    return redirect("/admin/voter-list")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = get_users_list()
        for user in users:
            if user['Username'] == username:
                if check_password_hash(user['Password'], password):
                    session["username"] = username
                    return redirect("/")
                flash("Wrong password", "danger")
                return redirect("/login")
        flash("User not found", "warning")
        return redirect("/register")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        cnic = request.form["cnic"].strip()
        phone = request.form["phone"].strip()

        if not validate_cnic(cnic):
            flash("Invalid CNIC format! Please use XXXXX-XXXXXXX-X", "danger")
            return redirect("/register")

        users = get_users_list()
        
        for user in users:
            existing_user = user.get('Username', None)
            existing_cnic = user.get('CNIC', None)
            
            if existing_user == username or existing_cnic == cnic:
                flash("Username or CNIC already exists!", "danger")
                return redirect("/login")

        add_user(username, generate_password_hash(password), cnic, phone)
        flash("Registered! Please login.", "success")
        return redirect("/login")
    
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    print("Starting Election System...")
    app.run(debug=True)