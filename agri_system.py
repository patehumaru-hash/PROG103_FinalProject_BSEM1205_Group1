"""
=============================================================
 PROG103 – Principles of Structured Programming
 Final Project: Structured Digital Solution for Public Service
 Title  : AgriTrack SL – Agriculture Support System (GUI)
 SDG    : SDG 2 – Zero Hunger | SDG 1 – No Poverty
 Country: Sierra Leone
 License: MIT
=============================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import hashlib
import os
import random
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

# ─────────────────────────────────────────────────────────────
#  CONSTANTS & THEME
# ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "agritrack.db")

# Earthy-green palette inspired by Sierra Leone's agriculture
C_BG        = "#F5F7F2"   # off-white background
C_SIDEBAR   = "#2D4A1E"   # deep forest green
C_ACCENT    = "#6BAA4C"   # leaf green
C_ACCENT2   = "#E8A020"   # harvest gold
C_WHITE     = "#FFFFFF"
C_TEXT_DARK = "#1A2E0D"
C_TEXT_MID  = "#4A6741"
C_TEXT_LITE = "#A8C49A"
C_DANGER    = "#C0392B"
C_ROW_ALT   = "#EBF2E6"

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_HEAD   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Courier New", 9)

GENDERS  = ["Male", "Female", "Other"]
STATUSES = ["Active", "Inactive", "Pending"]
DISTRICTS = ["Western Area", "Bo", "Kenema", "Makeni", "Kono", "Pujehun",
             "Bonthe", "Moyamba", "Tonkolili", "Kailahun", "Koinadugu", "Port Loko"]
CROP_TYPES = ["Rice", "Cassava", "Maize", "Groundnut", "Sweet Potato",
              "Yam", "Cocoa", "Coffee", "Palm Oil", "Vegetables"]

# ─────────────────────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────────────────────
def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables and seed data."""
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    DEFAULT 'officer'
        )
    """)

    # Farmers records table
    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name    TEXT    NOT NULL,
            gender       TEXT    NOT NULL,
            status       TEXT    NOT NULL,
            created_date TEXT    NOT NULL,
            district     TEXT,
            crop_type    TEXT,
            farm_size    REAL,
            contact      TEXT
        )
    """)

    # Seed admin user (password: admin123)
    pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
              ("admin", pw, "admin"))

    # Seed 25 sample farmer records if empty
    c.execute("SELECT COUNT(*) FROM records")
    if c.fetchone()[0] == 0:
        names = [
            ("Amara Koroma", "Male"), ("Fatmata Sesay", "Female"),
            ("Ibrahim Bangura", "Male"), ("Mariama Conteh", "Female"),
            ("Mohamed Kamara", "Male"), ("Aminata Turay", "Female"),
            ("Sorie Fofanah", "Male"), ("Hawa Mansaray", "Female"),
            ("Tamba Musa", "Male"), ("Isata Kargbo", "Female"),
            ("Alpha Bah", "Male"), ("Kadiatu Jalloh", "Female"),
            ("Brima Koroma", "Male"), ("Memunatu Sei", "Female"),
            ("Samuel Kanu", "Male"), ("Adama Dabo", "Female"),
            ("Yankuba Barrie", "Male"), ("Rosaline Cole", "Female"),
            ("Joseph Lahai", "Male"), ("Zainab Koroma", "Female"),
            ("Edward Samura", "Male"), ("Nancy Turay", "Female"),
            ("David Gbassay", "Male"), ("Kumba Rogers", "Female"),
            ("Gibril Kanneh", "Male"),
        ]
        base_date = datetime(2024, 1, 10)
        for i, (name, gender) in enumerate(names):
            delta_days = random.randint(0, 530)
            rec_date = base_date + timedelta(days=delta_days)
            c.execute("""
                INSERT INTO records
                    (full_name, gender, status, created_date, district, crop_type, farm_size, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, gender,
                random.choice(STATUSES),
                rec_date.strftime("%Y-%m-%d"),
                random.choice(DISTRICTS),
                random.choice(CROP_TYPES),
                round(random.uniform(0.5, 10.0), 1),
                f"+232-{random.randint(70,99)}-{random.randint(100000,999999)}"
            ))

    conn.commit()
    conn.close()


def verify_login(username, password):
    pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, pw))
    row = c.fetchone()
    conn.close()
    return row  # (id, role) or None


def fetch_records(search="", gender_filter="All", status_filter="All",
                  date_filter="All", start_date=None, end_date=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, full_name, gender, status, created_date, district, crop_type, farm_size, contact FROM records WHERE 1=1"
    params = []

    if search:
        query += " AND (full_name LIKE ? OR CAST(id AS TEXT) LIKE ? OR district LIKE ? OR crop_type LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if gender_filter != "All":
        query += " AND gender=?"
        params.append(gender_filter)
    if status_filter != "All":
        query += " AND status=?"
        params.append(status_filter)

    today = datetime.today()
    if date_filter == "Daily":
        start_date = today.strftime("%Y-%m-%d")
        end_date   = today.strftime("%Y-%m-%d")
    elif date_filter == "Weekly":
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date   = today.strftime("%Y-%m-%d")
    elif date_filter == "Monthly":
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date   = today.strftime("%Y-%m-%d")
    elif date_filter == "Yearly":
        start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
        end_date   = today.strftime("%Y-%m-%d")

    if start_date and end_date:
        query += " AND created_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    query += " ORDER BY created_date DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def add_record(full_name, gender, status, district, crop_type, farm_size, contact):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO records (full_name, gender, status, created_date, district, crop_type, farm_size, contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (full_name, gender, status, datetime.today().strftime("%Y-%m-%d"),
          district, crop_type, farm_size, contact))
    conn.commit()
    conn.close()


def delete_record(rec_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id=?", (rec_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM records")
    stats["total"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM records WHERE status='Active'")
    stats["active"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM records WHERE status='Inactive'")
    stats["inactive"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM records WHERE status='Pending'")
    stats["pending"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM records WHERE gender='Male'")
    stats["male"] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM records WHERE gender='Female'")
    stats["female"] = c.fetchone()[0]
    # monthly trend (last 12 months)
    monthly = []
    for i in range(11, -1, -1):
        d = datetime.today().replace(day=1) - timedelta(days=i*28)
        ym = d.strftime("%Y-%m")
        c.execute("SELECT COUNT(*) FROM records WHERE created_date LIKE ?", (f"{ym}%",))
        monthly.append((d.strftime("%b %Y"), c.fetchone()[0]))
    stats["monthly"] = monthly
    conn.close()
    return stats


# ─────────────────────────────────────────────────────────────
#  PDF REPORT GENERATION
# ─────────────────────────────────────────────────────────────
def generate_pdf_report(report_type, records, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 textColor=colors.HexColor("#2D4A1E"),
                                 fontSize=18, spaceAfter=6)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                               textColor=colors.HexColor("#6BAA4C"),
                               fontSize=11, spaceAfter=4)
    normal = styles["Normal"]

    story.append(Paragraph("AgriTrack SL – Agriculture Support System", title_style))
    story.append(Paragraph(f"{report_type} Farmer Records Report", sub_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y  %H:%M')}", normal))
    story.append(Spacer(1, 0.4*cm))

    # Summary
    story.append(Paragraph(f"Total Records: <b>{len(records)}</b>", normal))
    story.append(Spacer(1, 0.3*cm))

    # Table
    headers = ["ID", "Full Name", "Gender", "Status", "Date", "District", "Crop", "Farm(ha)"]
    data = [headers]
    for r in records:
        data.append([str(r[0]), r[1], r[2], r[3], r[4], r[5] or "", r[6] or "", str(r[7] or "")])

    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#2D4A1E")),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.white),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EBF2E6")]),
        ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#A8C49A")),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tbl)
    doc.build(story)


# ─────────────────────────────────────────────────────────────
#  REUSABLE WIDGET HELPERS
# ─────────────────────────────────────────────────────────────
def rounded_frame(parent, bg=C_WHITE, **kwargs):
    """Simple LabelFrame acting as a card."""
    f = tk.Frame(parent, bg=bg, bd=0, highlightthickness=1,
                 highlightbackground=C_ACCENT2, **kwargs)
    return f


def stat_card(parent, label, value, col):
    card = tk.Frame(parent, bg=col, padx=18, pady=14)
    card.pack(side="left", fill="both", expand=True, padx=6, pady=4)
    tk.Label(card, text=str(value), font=("Segoe UI", 26, "bold"),
             bg=col, fg=C_WHITE).pack(anchor="w")
    tk.Label(card, text=label, font=FONT_SMALL, bg=col,
             fg=C_WHITE).pack(anchor="w")


def styled_button(parent, text, command, bg=C_ACCENT, fg=C_WHITE, **kwargs):
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, font=FONT_BODY,
                    relief="flat", cursor="hand2",
                    activebackground=C_TEXT_MID, activeforeground=C_WHITE,
                    padx=12, pady=6, **kwargs)
    return btn


# ─────────────────────────────────────────────────────────────
#  LOGIN WINDOW
# ─────────────────────────────────────────────────────────────
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AgriTrack SL – Login")
        self.geometry("440x540")
        self.resizable(False, False)
        self.configure(bg=C_SIDEBAR)
        self._build()
        self.eval("tk::PlaceWindow . center")

    def _build(self):
        # Logo / branding area
        top = tk.Frame(self, bg=C_SIDEBAR, pady=30)
        top.pack(fill="x")
        tk.Label(top, text="🌾", font=("Segoe UI", 48), bg=C_SIDEBAR,
                 fg=C_ACCENT2).pack()
        tk.Label(top, text="AgriTrack SL", font=("Segoe UI", 22, "bold"),
                 bg=C_SIDEBAR, fg=C_WHITE).pack()
        tk.Label(top, text="Agriculture Support System", font=FONT_SMALL,
                 bg=C_SIDEBAR, fg=C_TEXT_LITE).pack()

        # Card
        card = tk.Frame(self, bg=C_WHITE, padx=36, pady=32)
        card.pack(fill="both", expand=True, padx=30, pady=0)

        tk.Label(card, text="Sign In", font=FONT_HEAD,
                 bg=C_WHITE, fg=C_TEXT_DARK).pack(anchor="w", pady=(0, 18))

        tk.Label(card, text="Username", font=FONT_SMALL,
                 bg=C_WHITE, fg=C_TEXT_MID).pack(anchor="w")
        self.username_var = tk.StringVar()
        tk.Entry(card, textvariable=self.username_var, font=FONT_BODY,
                 relief="flat", bg=C_BG, highlightthickness=1,
                 highlightbackground=C_ACCENT, width=28,
                 insertbackground=C_TEXT_DARK).pack(fill="x", ipady=8, pady=(2, 14))

        tk.Label(card, text="Password", font=FONT_SMALL,
                 bg=C_WHITE, fg=C_TEXT_MID).pack(anchor="w")
        self.password_var = tk.StringVar()
        self.pw_entry = tk.Entry(card, textvariable=self.password_var,
                                  show="•", font=FONT_BODY, relief="flat",
                                  bg=C_BG, highlightthickness=1,
                                  highlightbackground=C_ACCENT, width=28,
                                  insertbackground=C_TEXT_DARK)
        self.pw_entry.pack(fill="x", ipady=8, pady=(2, 6))

        # Show/hide password
        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Show password", variable=self.show_pw,
                       command=self._toggle_pw, bg=C_WHITE, fg=C_TEXT_MID,
                       font=FONT_SMALL, cursor="hand2",
                       activebackground=C_WHITE).pack(anchor="w", pady=(0, 18))

        self.error_lbl = tk.Label(card, text="", font=FONT_SMALL,
                                   bg=C_WHITE, fg=C_DANGER)
        self.error_lbl.pack(anchor="w")

        styled_button(card, "  Login  ", self._login,
                      bg=C_ACCENT2, fg=C_WHITE).pack(fill="x", pady=(8, 4))

        tk.Label(card, text="Default: admin / admin123", font=FONT_SMALL,
                 bg=C_WHITE, fg=C_TEXT_LITE).pack(pady=(10, 0))

        # Bind Enter key
        self.bind("<Return>", lambda e: self._login())

    def _toggle_pw(self):
        self.pw_entry.config(show="" if self.show_pw.get() else "•")

    def _login(self):
        u = self.username_var.get().strip()
        p = self.password_var.get()
        if not u or not p:
            self.error_lbl.config(text="⚠  Please enter both fields.")
            return
        result = verify_login(u, p)
        if result:
            self.destroy()
            app = MainApp(u, result[1])
            app.mainloop()
        else:
            self.error_lbl.config(text="✗  Incorrect username or password.")
            self.password_var.set("")


# ─────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────
class MainApp(tk.Tk):
    def __init__(self, username, role):
        super().__init__()
        self.username = username
        self.role = role
        self.title("AgriTrack SL – Agriculture Support System")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(bg=C_BG)
        self.current_page = None
        self._build_layout()
        self._show_dashboard()
        self.eval("tk::PlaceWindow . center")

    # ── Layout skeleton ──────────────────────────────────────
    def _build_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg=C_SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_f = tk.Frame(self.sidebar, bg=C_SIDEBAR, pady=24)
        logo_f.pack(fill="x")
        tk.Label(logo_f, text="🌾 AgriTrack SL", font=("Segoe UI", 14, "bold"),
                 bg=C_SIDEBAR, fg=C_WHITE).pack()
        tk.Label(logo_f, text=f"  {self.username}  [{self.role}]",
                 font=FONT_SMALL, bg=C_SIDEBAR, fg=C_TEXT_LITE).pack(pady=(4, 0))

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=10)

        # Nav buttons
        nav_items = [
            ("📊  Dashboard",     self._show_dashboard),
            ("👨‍🌾  Farmers",        self._show_records),
            ("📈  Analytics",     self._show_charts),
            ("➕  Add Farmer",    self._show_add_form),
            ("📄  PDF Report",    self._show_pdf_panel),
        ]
        self.nav_buttons = []
        for label, cmd in nav_items:
            btn = tk.Button(self.sidebar, text=label, anchor="w",
                            font=FONT_BODY, bg=C_SIDEBAR, fg=C_WHITE,
                            relief="flat", cursor="hand2", padx=20, pady=11,
                            activebackground=C_ACCENT, activeforeground=C_WHITE,
                            command=cmd)
            btn.pack(fill="x")
            self.nav_buttons.append(btn)

        # Logout at bottom
        tk.Frame(self.sidebar, bg=C_SIDEBAR).pack(fill="y", expand=True)
        styled_button(self.sidebar, "⏻  Logout", self._logout,
                      bg=C_DANGER, fg=C_WHITE).pack(fill="x", padx=16, pady=16)

        # Main content area
        self.content = tk.Frame(self, bg=C_BG)
        self.content.pack(side="right", fill="both", expand=True)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _header(self, title, subtitle=""):
        hdr = tk.Frame(self.content, bg=C_WHITE, pady=14, padx=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=FONT_TITLE,
                 bg=C_WHITE, fg=C_TEXT_DARK).pack(side="left")
        if subtitle:
            tk.Label(hdr, text=subtitle, font=FONT_SMALL,
                     bg=C_WHITE, fg=C_TEXT_MID).pack(side="left", padx=12)
        ttk.Separator(self.content).pack(fill="x")

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.destroy()
            LoginWindow().mainloop()

    # ── DASHBOARD ────────────────────────────────────────────
    def _show_dashboard(self):
        self._clear_content()
        self._header("Dashboard", "— Overview")
        stats = get_stats()

        # Stat cards row
        cards_row = tk.Frame(self.content, bg=C_BG, pady=12, padx=16)
        cards_row.pack(fill="x")
        stat_card(cards_row, "Total Farmers",  stats["total"],    "#2D4A1E")
        stat_card(cards_row, "Active",         stats["active"],   "#6BAA4C")
        stat_card(cards_row, "Inactive",       stats["inactive"], "#E8A020")
        stat_card(cards_row, "Pending",        stats["pending"],  "#8B4513")

        # Mini charts row
        charts_row = tk.Frame(self.content, bg=C_BG, padx=16, pady=4)
        charts_row.pack(fill="both", expand=True)

        self._mini_bar(charts_row, stats)
        self._mini_pie(charts_row, stats)
        self._mini_line(charts_row, stats)

    def _mini_bar(self, parent, stats):
        fig, ax = plt.subplots(figsize=(3.6, 2.8))
        fig.patch.set_facecolor(C_WHITE)
        ax.set_facecolor(C_BG)
        cats = ["Active", "Inactive", "Pending"]
        vals = [stats["active"], stats["inactive"], stats["pending"]]
        bars = ax.bar(cats, vals, color=["#6BAA4C", "#E8A020", "#8B4513"], width=0.5)
        ax.set_title("Records by Status", fontsize=9, color=C_TEXT_DARK, pad=6)
        ax.tick_params(labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
                    str(v), ha="center", va="bottom", fontsize=8)
        fig.tight_layout()
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def _mini_pie(self, parent, stats):
        fig, ax = plt.subplots(figsize=(3.6, 2.8))
        fig.patch.set_facecolor(C_WHITE)
        m, f = stats["male"], stats["female"]
        other = stats["total"] - m - f
        vals   = [v for v in [m, f, other] if v > 0]
        labels = [l for l, v in zip(["Male","Female","Other"],[m,f,other]) if v > 0]
        colors_list = ["#2D4A1E","#E8A020","#6BAA4C"][:len(vals)]
        ax.pie(vals, labels=labels, colors=colors_list,
               autopct="%1.0f%%", startangle=90,
               textprops={"fontsize": 8})
        ax.set_title("Gender Distribution", fontsize=9, color=C_TEXT_DARK, pad=6)
        fig.tight_layout()
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def _mini_line(self, parent, stats):
        fig, ax = plt.subplots(figsize=(3.6, 2.8))
        fig.patch.set_facecolor(C_WHITE)
        ax.set_facecolor(C_BG)
        months = [m[0][-3:] for m in stats["monthly"]]  # short month
        counts = [m[1] for m in stats["monthly"]]
        ax.plot(months, counts, color=C_ACCENT, marker="o", linewidth=2, markersize=4)
        ax.fill_between(range(len(months)), counts, alpha=0.12, color=C_ACCENT)
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels(months, rotation=45, fontsize=7)
        ax.set_title("Monthly Registrations", fontsize=9, color=C_TEXT_DARK, pad=6)
        ax.tick_params(labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ── RECORDS TABLE ────────────────────────────────────────
    def _show_records(self):
        self._clear_content()
        self._header("Farmer Records", f"— {fetch_records.__name__}")

        # Toolbar
        toolbar = tk.Frame(self.content, bg=C_BG, pady=8, padx=16)
        toolbar.pack(fill="x")

        # Search
        tk.Label(toolbar, text="Search:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT_MID).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self.search_var,
                                font=FONT_BODY, width=20, relief="flat",
                                bg=C_WHITE, highlightthickness=1,
                                highlightbackground=C_ACCENT)
        search_entry.pack(side="left", ipady=5, padx=(4, 14))

        # Gender filter
        tk.Label(toolbar, text="Gender:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT_MID).pack(side="left")
        self.gender_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.gender_var,
                     values=["All"] + GENDERS, width=10, state="readonly",
                     font=FONT_SMALL).pack(side="left", padx=(4, 12))

        # Status filter
        tk.Label(toolbar, text="Status:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT_MID).pack(side="left")
        self.status_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.status_var,
                     values=["All"] + STATUSES, width=10, state="readonly",
                     font=FONT_SMALL).pack(side="left", padx=(4, 12))

        # Date filter
        tk.Label(toolbar, text="Period:", font=FONT_SMALL,
                 bg=C_BG, fg=C_TEXT_MID).pack(side="left")
        self.date_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.date_var,
                     values=["All", "Daily", "Weekly", "Monthly", "Yearly"],
                     width=10, state="readonly", font=FONT_SMALL).pack(side="left", padx=(4, 12))

        styled_button(toolbar, "🔍 Search", self._apply_filter).pack(side="left", padx=4)
        styled_button(toolbar, "↺ Reset", self._reset_filter, bg=C_TEXT_MID).pack(side="left", padx=4)
        styled_button(toolbar, "🗑 Delete Selected", self._delete_selected,
                      bg=C_DANGER).pack(side="right", padx=8)

        # Treeview
        cols = ("ID", "Full Name", "Gender", "Status", "Date",
                "District", "Crop", "Farm (ha)", "Contact")
        frame_tree = tk.Frame(self.content, bg=C_BG, padx=16, pady=4)
        frame_tree.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Agri.Treeview", font=FONT_SMALL, rowheight=24,
                         background=C_WHITE, fieldbackground=C_WHITE,
                         foreground=C_TEXT_DARK)
        style.configure("Agri.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                         background=C_SIDEBAR, foreground=C_WHITE)
        style.map("Agri.Treeview", background=[("selected", C_ACCENT)])

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical")
        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal")

        self.tree = ttk.Treeview(frame_tree, columns=cols, show="headings",
                                  style="Agri.Treeview",
                                  yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        widths = [40, 160, 70, 80, 90, 110, 100, 80, 130]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=w, minwidth=40)

        self.tree.tag_configure("alt", background=C_ROW_ALT)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # Count label
        self.count_lbl = tk.Label(self.content, text="", font=FONT_SMALL,
                                   bg=C_BG, fg=C_TEXT_MID)
        self.count_lbl.pack(anchor="w", padx=18, pady=4)

        self._load_tree()

    def _load_tree(self):
        self.tree.delete(*self.tree.get_children())
        records = fetch_records(
            search=self.search_var.get().strip(),
            gender_filter=self.gender_var.get(),
            status_filter=self.status_var.get(),
            date_filter=self.date_var.get()
        )
        for i, row in enumerate(records):
            tag = "alt" if i % 2 else ""
            self.tree.insert("", "end", iid=row[0], values=row, tags=(tag,))
        self.count_lbl.config(text=f"Showing {len(records)} record(s)")

    def _apply_filter(self):
        self._load_tree()

    def _reset_filter(self):
        self.search_var.set("")
        self.gender_var.set("All")
        self.status_var.set("All")
        self.date_var.set("All")
        self._load_tree()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select a record first.")
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete {len(sel)} selected record(s)?"):
            for iid in sel:
                delete_record(int(iid))
            self._load_tree()

    def _sort_tree(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0]) if x[0].replace(".","").isdigit() else x[0].lower())
        except Exception:
            items.sort(key=lambda x: x[0].lower())
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
            self.tree.item(k, tags=("alt" if idx % 2 else "",))

    # ── ANALYTICS (FULL CHARTS) ──────────────────────────────
    def _show_charts(self):
        self._clear_content()
        self._header("Analytics", "— Data Visualizations")

        canvas_frame = tk.Frame(self.content, bg=C_BG)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                   command=canvas.yview)
        scroll_inner = tk.Frame(canvas, bg=C_BG)
        scroll_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        stats = get_stats()
        self._full_bar(scroll_inner, stats)
        self._full_pie(scroll_inner, stats)
        self._full_line(scroll_inner, stats)

    def _full_bar(self, parent, stats):
        tk.Label(parent, text="Bar Chart — Records by Status & Gender",
                 font=FONT_HEAD, bg=C_BG, fg=C_TEXT_DARK).pack(
                     anchor="w", padx=20, pady=(16, 4))
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        fig.patch.set_facecolor(C_WHITE)

        # Status bar
        ax1 = axes[0]
        ax1.set_facecolor(C_BG)
        cats = ["Active", "Inactive", "Pending"]
        vals = [stats["active"], stats["inactive"], stats["pending"]]
        b = ax1.bar(cats, vals, color=["#6BAA4C","#E8A020","#8B4513"], width=0.5)
        ax1.set_title("By Status", fontsize=10)
        for bar, v in zip(b, vals):
            ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                     str(v), ha="center", va="bottom", fontsize=9)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        # Gender bar
        ax2 = axes[1]
        ax2.set_facecolor(C_BG)
        other = stats["total"] - stats["male"] - stats["female"]
        gcats = ["Male", "Female", "Other"]
        gvals = [stats["male"], stats["female"], other]
        b2 = ax2.bar(gcats, gvals, color=["#2D4A1E","#E8A020","#6BAA4C"], width=0.5)
        ax2.set_title("By Gender", fontsize=10)
        for bar, v in zip(b2, gvals):
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                     str(v), ha="center", va="bottom", fontsize=9)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        fig.tight_layout(pad=2)
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(fill="x", padx=20, pady=4)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack()
        plt.close(fig)

    def _full_pie(self, parent, stats):
        tk.Label(parent, text="Pie Charts — Percentage Distribution",
                 font=FONT_HEAD, bg=C_BG, fg=C_TEXT_DARK).pack(
                     anchor="w", padx=20, pady=(16, 4))
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        fig.patch.set_facecolor(C_WHITE)

        # Status pie
        s_vals = [stats["active"], stats["inactive"], stats["pending"]]
        s_labels = ["Active", "Inactive", "Pending"]
        s_colors = ["#6BAA4C","#E8A020","#8B4513"]
        axes[0].pie([v for v in s_vals if v > 0],
                    labels=[l for l,v in zip(s_labels,s_vals) if v > 0],
                    colors=[c for c,v in zip(s_colors,s_vals) if v > 0],
                    autopct="%1.1f%%", startangle=90,
                    textprops={"fontsize": 9})
        axes[0].set_title("Status Distribution", fontsize=10)

        # Gender pie
        m, f = stats["male"], stats["female"]
        other = stats["total"] - m - f
        g_vals = [v for v in [m, f, other] if v > 0]
        g_labels = [l for l,v in zip(["Male","Female","Other"],[m,f,other]) if v > 0]
        axes[1].pie(g_vals, labels=g_labels,
                    colors=["#2D4A1E","#E8A020","#6BAA4C"][:len(g_vals)],
                    autopct="%1.1f%%", startangle=90,
                    textprops={"fontsize": 9})
        axes[1].set_title("Gender Distribution", fontsize=10)

        fig.tight_layout(pad=2)
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(fill="x", padx=20, pady=4)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack()
        plt.close(fig)

    def _full_line(self, parent, stats):
        tk.Label(parent, text="Line Graph — Monthly Registration Trend",
                 font=FONT_HEAD, bg=C_BG, fg=C_TEXT_DARK).pack(
                     anchor="w", padx=20, pady=(16, 4))
        fig, ax = plt.subplots(figsize=(10, 3.6))
        fig.patch.set_facecolor(C_WHITE)
        ax.set_facecolor(C_BG)
        months = [m[0] for m in stats["monthly"]]
        counts = [m[1] for m in stats["monthly"]]
        ax.plot(months, counts, color=C_ACCENT, marker="o",
                linewidth=2.5, markersize=6, markerfacecolor=C_ACCENT2)
        ax.fill_between(range(len(months)), counts, alpha=0.15, color=C_ACCENT)
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels(months, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Registrations", fontsize=9)
        ax.set_title("Monthly Farmer Registrations (Last 12 Months)", fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()
        card = tk.Frame(parent, bg=C_WHITE, bd=0, highlightthickness=1,
                        highlightbackground="#DDE8D5")
        card.pack(fill="x", padx=20, pady=(4, 20))
        FigureCanvasTkAgg(fig, master=card).get_tk_widget().pack()
        plt.close(fig)

    # ── ADD FARMER FORM ──────────────────────────────────────
    def _show_add_form(self):
        self._clear_content()
        self._header("Add New Farmer", "— Register a farmer")

        form_wrap = tk.Frame(self.content, bg=C_BG)
        form_wrap.pack(fill="both", expand=True)

        card = tk.Frame(form_wrap, bg=C_WHITE, padx=32, pady=28,
                        highlightthickness=1, highlightbackground="#DDE8D5")
        card.pack(padx=40, pady=20)

        fields = {}

        def row(label, widget_fn, **kw):
            r = tk.Frame(card, bg=C_WHITE)
            r.pack(fill="x", pady=6)
            tk.Label(r, text=label, font=FONT_SMALL, bg=C_WHITE,
                     fg=C_TEXT_MID, width=16, anchor="w").pack(side="left")
            w = widget_fn(r, **kw)
            w.pack(side="left", fill="x", expand=True, ipady=5)
            return w

        def entry(parent, **kw):
            return tk.Entry(parent, font=FONT_BODY, relief="flat",
                            bg=C_BG, highlightthickness=1,
                            highlightbackground=C_ACCENT,
                            insertbackground=C_TEXT_DARK, **kw)

        def combo(parent, values, **kw):
            v = tk.StringVar(value=values[0])
            cb = ttk.Combobox(parent, textvariable=v, values=values,
                              state="readonly", font=FONT_BODY, **kw)
            cb._var = v
            return cb

        fields["full_name"] = row("Full Name *", entry)
        fields["gender"]    = row("Gender *", combo, values=GENDERS)
        fields["status"]    = row("Status *", combo, values=STATUSES)
        fields["district"]  = row("District", combo, values=DISTRICTS)
        fields["crop_type"] = row("Crop Type", combo, values=CROP_TYPES)
        fields["farm_size"] = row("Farm Size (ha)", entry)
        fields["contact"]   = row("Contact Number", entry)

        self.form_msg = tk.Label(card, text="", font=FONT_SMALL,
                                  bg=C_WHITE, fg=C_DANGER)
        self.form_msg.pack(anchor="w", pady=(4, 0))

        def submit():
            name = fields["full_name"].get().strip()
            gender = fields["gender"]._var.get()
            status = fields["status"]._var.get()
            district = fields["district"]._var.get()
            crop = fields["crop_type"]._var.get()
            size_str = fields["farm_size"].get().strip()
            contact = fields["contact"].get().strip()

            if not name:
                self.form_msg.config(text="⚠  Full Name is required.")
                return
            if len(name) < 3:
                self.form_msg.config(text="⚠  Name must be at least 3 characters.")
                return

            try:
                size = float(size_str) if size_str else 0.0
                if size < 0:
                    raise ValueError
            except ValueError:
                self.form_msg.config(text="⚠  Farm size must be a positive number.")
                return

            add_record(name, gender, status, district, crop, size, contact)
            messagebox.showinfo("Success", f"Farmer '{name}' registered successfully!")
            # Clear fields
            fields["full_name"].delete(0, "end")
            fields["farm_size"].delete(0, "end")
            fields["contact"].delete(0, "end")
            self.form_msg.config(text="✓  Record added.", fg=C_ACCENT)

        btn_row = tk.Frame(card, bg=C_WHITE)
        btn_row.pack(fill="x", pady=(16, 0))
        styled_button(btn_row, "  Save Farmer  ", submit, bg=C_ACCENT2).pack(side="left")
        styled_button(btn_row, "  View Records  ", self._show_records,
                      bg=C_TEXT_MID).pack(side="left", padx=8)

    # ── PDF REPORT PANEL ─────────────────────────────────────
    def _show_pdf_panel(self):
        self._clear_content()
        self._header("PDF Report Generator", "— Export farmer data")

        panel = tk.Frame(self.content, bg=C_BG, padx=40, pady=30)
        panel.pack(fill="both", expand=True)

        card = tk.Frame(panel, bg=C_WHITE, padx=30, pady=26,
                        highlightthickness=1, highlightbackground="#DDE8D5")
        card.pack(fill="x")

        tk.Label(card, text="Select Report Type", font=FONT_HEAD,
                 bg=C_WHITE, fg=C_TEXT_DARK).pack(anchor="w", pady=(0, 12))

        self.report_type_var = tk.StringVar(value="Monthly")
        for rt in ["Weekly", "Monthly", "Yearly"]:
            tk.Radiobutton(card, text=rt, variable=self.report_type_var,
                           value=rt, font=FONT_BODY, bg=C_WHITE,
                           fg=C_TEXT_DARK, activebackground=C_WHITE,
                           cursor="hand2").pack(anchor="w", pady=3)

        ttk.Separator(card).pack(fill="x", pady=12)
        tk.Label(card, text="Output directory (leave blank for current folder):",
                 font=FONT_SMALL, bg=C_WHITE, fg=C_TEXT_MID).pack(anchor="w")
        self.pdf_dir_var = tk.StringVar(value=os.path.dirname(os.path.abspath(__file__)))
        tk.Entry(card, textvariable=self.pdf_dir_var, font=FONT_SMALL,
                 relief="flat", bg=C_BG, highlightthickness=1,
                 highlightbackground=C_ACCENT, width=50).pack(
                     fill="x", ipady=5, pady=(4, 16))

        self.pdf_msg = tk.Label(card, text="", font=FONT_SMALL,
                                 bg=C_WHITE, fg=C_ACCENT)
        self.pdf_msg.pack(anchor="w", pady=(0, 8))

        styled_button(card, "📄  Generate PDF Report",
                      self._generate_pdf, bg=C_ACCENT2).pack(anchor="w")

    def _generate_pdf(self):
        rt = self.report_type_var.get()
        out_dir = self.pdf_dir_var.get().strip() or os.path.dirname(os.path.abspath(__file__))

        date_filter_map = {"Weekly": "Weekly", "Monthly": "Monthly", "Yearly": "Yearly"}
        records = fetch_records(date_filter=date_filter_map[rt])

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"AgriTrackSL_{rt}_Report_{ts}.pdf"
        filepath = os.path.join(out_dir, filename)

        try:
            generate_pdf_report(rt, records, filepath)
            self.pdf_msg.config(
                text=f"✓  Report saved: {filename}  ({len(records)} records)",
                fg=C_ACCENT)
            messagebox.showinfo("PDF Generated",
                                f"Report saved to:\n{filepath}")
        except Exception as e:
            self.pdf_msg.config(text=f"✗  Error: {e}", fg=C_DANGER)


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app = LoginWindow()
    app.mainloop()
