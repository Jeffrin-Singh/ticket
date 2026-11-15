import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import psycopg2
from psycopg2.extras import RealDictCursor
import subprocess
import threading
import sys
import os
import json
import time
import glob
import datetime
import pandas as pd

# Enable High-DPI sharpness on Windows
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# =========================================================
# Database Configuration
# =========================================================
DB_NAME = "padmavathi_travels"
DB_USER = "postgres"
DB_PASSWORD = "Jeffrin@29072004"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# =========================================================
# Dialog: Add Family + Pilgrims + Payment (Perfected Design)
# =========================================================
class AddFamilyDialog(tk.Toplevel):
    def __init__(self, parent, on_success_callback, edit_group_id=None):
        super().__init__(parent)
        self.edit_group_id = edit_group_id
        self.title("Edit Family & Pilgrims" if edit_group_id else "Add New Family & Pilgrims")
        
        self.win_w = 860
        self.win_h = 720
        self.geometry(f"{self.win_w}x{self.win_h}")
        self.minsize(820, 560)
        self.on_success = on_success_callback
        self.pilgrim_rows = []

        self.setup_styles()
        self.create_widgets()

        if self.edit_group_id:
            self.load_existing_data()
        else:
            self.add_pilgrim_row()

        # Center on parent with explicit geometry size
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = max(0, px + (pw - self.win_w) // 2)
        y = max(0, py + (ph - self.win_h) // 2)
        self.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.transient(parent)
        self.grab_set()

    def on_close(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self.destroy()

    def setup_styles(self):
        s = ttk.Style(self)
        s.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#0f172a")
        s.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#64748b")
        s.configure("Card.TLabelframe", padding=12)
        s.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#1e293b")
        s.configure("GridHeader.TLabel", font=("Segoe UI", 9, "bold"), foreground="#334155")
        s.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), foreground="#ffffff", background="#0284c7")
        s.map("Primary.TButton", background=[("active", "#0369a1")])
        s.configure("Secondary.TButton", font=("Segoe UI", 9))

    def create_widgets(self):
        # 1. Top Header Banner (Fixed)
        top_bar = ttk.Frame(self, padding=(18, 12))
        top_bar.pack(fill="x")
        header_title = "✏️ Edit Family Group & Passengers" if self.edit_group_id else "👨‍👩‍👧‍👦 Add Family Group & Passengers"
        header_sub = "Modify family details, payment settings, or passenger information." if self.edit_group_id else "Enter group identification, payment preferences, and up to 4 pilgrims."
        ttk.Label(top_bar, text=header_title, style="Header.TLabel").pack(anchor="w")
        ttk.Label(top_bar, text=header_sub, style="SubHeader.TLabel").pack(anchor="w")

        # 2. Bottom Fixed Footer Buttons (Fixed at bottom)
        footer = ttk.Frame(self, padding=(18, 12))
        footer.pack(side="bottom", fill="x")
        ttk.Separator(self, orient="horizontal").pack(side="bottom", fill="x")

        btn_text = "💾 Update Database" if self.edit_group_id else "💾 Save to Database"
        self.save_btn = ttk.Button(footer, text=btn_text, command=self.save_family, style="Primary.TButton")
        self.save_btn.pack(side="right", padx=6)
        ttk.Button(footer, text="Cancel", command=self.on_close, style="Secondary.TButton").pack(side="right", padx=6)

        # 3. Main Center Scrollable Container (Canvas + Scrollbar + Mousewheel)
        scroll_container = ttk.Frame(self)
        scroll_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(scroll_container, borderwidth=0, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)

        center_frame = ttk.Frame(self.canvas, padding=(18, 5))
        center_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=center_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        def on_canvas_resize(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", on_canvas_resize)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

        # Mousewheel scroll binding
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Card 1: Family Group Details ---
        f_group = ttk.LabelFrame(center_frame, text=" 1. Family Group Details ", style="Card.TLabelframe")
        f_group.pack(fill="x", pady=(0, 10))
        f_group.columnconfigure(1, weight=2)
        f_group.columnconfigure(3, weight=1)

        ttk.Label(f_group, text="Group Name: *", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.group_name_var = tk.StringVar()
        ttk.Entry(f_group, textvariable=self.group_name_var, font=("Segoe UI", 9)).grid(row=0, column=1, sticky="ew", padx=(0, 20), pady=4)

        ttk.Label(f_group, text="Target Date (YYYY-MM-DD):", font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        self.target_date_var = tk.StringVar(value=today_str)
        ttk.Entry(f_group, textvariable=self.target_date_var, font=("Segoe UI", 9)).grid(row=0, column=3, sticky="ew", pady=4)

        # --- Card 2: Payment Method ---
        p_group = ttk.LabelFrame(center_frame, text=" 2. Payment Method ", style="Card.TLabelframe")
        p_group.pack(fill="x", pady=(0, 10))

        method_row = ttk.Frame(p_group)
        method_row.pack(fill="x", pady=(0, 6))

        ttk.Label(method_row, text="Payment Type:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 12))
        self.payment_type_var = tk.StringVar(value="UPI")
        r_upi = ttk.Radiobutton(method_row, text="UPI (Google Pay / PhonePe / Paytm)", value="UPI", variable=self.payment_type_var, command=self.toggle_payment_fields)
        r_upi.pack(side="left", padx=10)
        r_card = ttk.Radiobutton(method_row, text="Credit / Debit Card", value="CARD", variable=self.payment_type_var, command=self.toggle_payment_fields)
        r_card.pack(side="left", padx=10)

        # Dynamic Payment Inputs Frame
        self.pay_details_frame = ttk.Frame(p_group)
        self.pay_details_frame.pack(fill="x", pady=4)

        # UPI Controls
        self.upi_widget = ttk.Frame(self.pay_details_frame)
        ttk.Label(self.upi_widget, text="UPI ID: *", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        self.upi_id_var = tk.StringVar()
        ttk.Entry(self.upi_widget, textvariable=self.upi_id_var, width=32, font=("Segoe UI", 9)).pack(side="left")
        ttk.Label(self.upi_widget, text="(e.g. mobile@upi or name@okaxis)", font=("Segoe UI", 8, "italic"), foreground="#64748b").pack(side="left", padx=8)

        # Card Controls
        self.card_widget = ttk.Frame(self.pay_details_frame)
        self.card_widget.columnconfigure(1, weight=2)
        self.card_widget.columnconfigure(3, weight=1)

        ttk.Label(self.card_widget, text="Card Number:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=2, padx=(0, 6))
        self.card_num_var = tk.StringVar()
        ttk.Entry(self.card_widget, textvariable=self.card_num_var, font=("Segoe UI", 9), width=20).grid(row=0, column=1, sticky="w", pady=2, padx=(0, 15))

        ttk.Label(self.card_widget, text="Cardholder Name:", font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", pady=2, padx=(0, 6))
        self.cardholder_var = tk.StringVar()
        ttk.Entry(self.card_widget, textvariable=self.cardholder_var, font=("Segoe UI", 9), width=20).grid(row=0, column=3, sticky="w", pady=2)

        exp_frame = ttk.Frame(self.card_widget)
        exp_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=4)

        ttk.Label(exp_frame, text="Expiry MM:").pack(side="left", padx=(0, 4))
        self.exp_m_var = tk.StringVar()
        ttk.Entry(exp_frame, textvariable=self.exp_m_var, width=4).pack(side="left", padx=(0, 10))

        ttk.Label(exp_frame, text="YYYY:").pack(side="left", padx=(0, 4))
        self.exp_y_var = tk.StringVar()
        ttk.Entry(exp_frame, textvariable=self.exp_y_var, width=6).pack(side="left", padx=(0, 15))

        ttk.Label(exp_frame, text="CVV:").pack(side="left", padx=(0, 4))
        self.cvv_var = tk.StringVar()
        ttk.Entry(exp_frame, textvariable=self.cvv_var, width=5, show="*").pack(side="left")

        # Initial view
        self.toggle_payment_fields()

        # --- Card 3: Pilgrims (Max 4 Allowed) ---
        pl_group = ttk.LabelFrame(center_frame, text=" 3. Passengers / Pilgrims (Max 4 Allowed) ", style="Card.TLabelframe")
        pl_group.pack(fill="both", expand=True, pady=(0, 5))

        top_ctrl = ttk.Frame(pl_group)
        top_ctrl.pack(fill="x", pady=(0, 8))

        self.add_p_btn = ttk.Button(top_ctrl, text="➕ Add Passenger", command=self.add_pilgrim_row)
        self.add_p_btn.pack(side="left")
        self.count_lbl = ttk.Label(top_ctrl, text="1 / 4 Passengers", font=("Segoe UI", 9, "italic"), foreground="#475569")
        self.count_lbl.pack(side="left", padx=12)

        # Pilgrims Grid Container
        self.grid_frame = ttk.Frame(pl_group)
        self.grid_frame.pack(fill="both", expand=True)

        # Grid Column Configuration (Ensures 100% Perfect Alignment)
        self.grid_frame.columnconfigure(0, minsize=28, weight=0)   # #
        self.grid_frame.columnconfigure(1, weight=4)               # Full Name
        self.grid_frame.columnconfigure(2, minsize=55, weight=0)   # Age
        self.grid_frame.columnconfigure(3, minsize=80, weight=0)   # Gender
        self.grid_frame.columnconfigure(4, minsize=130, weight=0)  # ID Type
        self.grid_frame.columnconfigure(5, weight=4)               # ID Number
        self.grid_frame.columnconfigure(6, minsize=35, weight=0)   # Delete action

        # Headers Row
        headers = [
            ("#", 0, "center", "ew"),
            ("Full Name (as per ID) *", 1, "w", "w"),
            ("Age *", 2, "center", "ew"),
            ("Gender *", 3, "w", "w"),
            ("ID Proof Type *", 4, "w", "w"),
            ("ID Proof Number / Aadhaar (12 Digits) *", 5, "w", "w"),
            ("", 6, "center", "ew")
        ]
        for title, col, anchor_align, sticky_dir in headers:
            lbl = ttk.Label(self.grid_frame, text=title, style="GridHeader.TLabel", anchor=anchor_align)
            lbl.grid(row=0, column=col, sticky=sticky_dir, padx=4, pady=(0, 6))

    def toggle_payment_fields(self):
        ptype = self.payment_type_var.get()
        if ptype == "UPI":
            self.card_widget.pack_forget()
            self.upi_widget.pack(fill="x", anchor="w")
        else:
            self.upi_widget.pack_forget()
            self.card_widget.pack(fill="x", anchor="w")

    def load_existing_data(self):
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 1. Family Group
            cur.execute("SELECT group_name, target_date, payment_method FROM family_groups WHERE id = %s;", (int(self.edit_group_id),))
            grp = cur.fetchone()
            if not grp:
                messagebox.showerror("Error", "Family group not found in database!")
                self.destroy()
                return

            self.group_name_var.set(str(grp["group_name"] or ""))
            self.target_date_var.set(str(grp["target_date"]) if grp["target_date"] else "")
            
            pm = str(grp["payment_method"] or "UPI").upper()
            if "CARD" in pm:
                self.payment_type_var.set("CARD")
            else:
                self.payment_type_var.set("UPI")

            # 2. Payment
            cur.execute("SELECT * FROM payments WHERE group_id = %s;", (int(self.edit_group_id),))
            pay = cur.fetchone()
            if pay:
                self.upi_id_var.set(str(pay["upi_id"] or ""))
                self.card_num_var.set(str(pay["card_number"] or ""))
                self.cardholder_var.set(str(pay["cardholder_name"] or ""))
                self.exp_m_var.set(str(pay["card_expiry_month"] or ""))
                self.exp_y_var.set(str(pay["card_expiry_year"] or ""))
                self.cvv_var.set(str(pay["card_cvv"] or ""))

            self.toggle_payment_fields()

            # 3. Pilgrims
            cur.execute("""
                SELECT COALESCE(name, full_name) as name, age, gender, 
                       COALESCE(id_type, 'Aadhaar Card') as id_type, 
                       COALESCE(id_number, aadhar_number) as id_number
                FROM pilgrims WHERE group_id = %s ORDER BY id ASC LIMIT 4;
            """, (int(self.edit_group_id),))
            pilgrims = cur.fetchall()

            cur.close()
            conn.close()

            # Remove existing rows if any
            for r in self.pilgrim_rows:
                for w in r["widgets"]:
                    w.destroy()
            self.pilgrim_rows.clear()

            if pilgrims:
                for p in pilgrims:
                    self.add_pilgrim_row(p)
            else:
                self.add_pilgrim_row()

            self.update_count_ui()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load family data: {e}")

    def add_pilgrim_row(self, initial_data=None):
        if len(self.pilgrim_rows) >= 4:
            messagebox.showwarning("Limit Reached", "A maximum of 4 passengers is allowed per family group!")
            return

        row_idx = len(self.pilgrim_rows) + 1  # Grid row (header is 0)

        # 0: Number Label
        lbl_num = ttk.Label(self.grid_frame, text=str(row_idx), font=("Segoe UI", 9, "bold"), anchor="center")
        lbl_num.grid(row=row_idx, column=0, sticky="ew", padx=2, pady=3)

        # 1: Full Name
        name_val = str(initial_data["name"]) if (initial_data and initial_data.get("name") is not None) else ""
        name_var = tk.StringVar(value=name_val)
        e_name = ttk.Entry(self.grid_frame, textvariable=name_var, font=("Segoe UI", 9))
        e_name.grid(row=row_idx, column=1, sticky="ew", padx=3, pady=3)

        # 2: Age
        age_val = str(initial_data["age"]) if (initial_data and initial_data.get("age") is not None) else ""
        age_var = tk.StringVar(value=age_val)
        e_age = ttk.Entry(self.grid_frame, textvariable=age_var, font=("Segoe UI", 9), width=5, justify="center")
        e_age.grid(row=row_idx, column=2, sticky="ew", padx=3, pady=3)

        # 3: Gender
        gender_val = str(initial_data["gender"]) if (initial_data and initial_data.get("gender") is not None) else "Male"
        gender_var = tk.StringVar(value=gender_val)
        c_gender = ttk.Combobox(self.grid_frame, textvariable=gender_var, values=["Male", "Female"], state="readonly", width=7, font=("Segoe UI", 9))
        c_gender.grid(row=row_idx, column=3, sticky="ew", padx=3, pady=3)

        # 4: ID Type
        id_type_val = str(initial_data["id_type"]) if (initial_data and initial_data.get("id_type") is not None) else "Aadhaar Card"
        id_type_var = tk.StringVar(value=id_type_val)
        c_id_type = ttk.Combobox(self.grid_frame, textvariable=id_type_var, values=["Aadhaar Card", "Passport", "Voter ID", "PAN Card", "Driving Licence"], state="readonly", width=14, font=("Segoe UI", 9))
        c_id_type.grid(row=row_idx, column=4, sticky="ew", padx=3, pady=3)

        # 5: ID Number (Aadhaar Card 12-digit strict enforcement)
        id_num_val = str(initial_data["id_number"]) if (initial_data and initial_data.get("id_number") is not None) else ""
        id_num_var = tk.StringVar(value=id_num_val)
        e_id_num = ttk.Entry(self.grid_frame, textvariable=id_num_var, font=("Segoe UI", 9))
        e_id_num.grid(row=row_idx, column=5, sticky="ew", padx=3, pady=3)

        # Live restriction: if Aadhaar Card, allow only digits and max 12 chars
        def enforce_aadhaar_limit(*args):
            if id_type_var.get() == "Aadhaar Card":
                val = id_num_var.get()
                clean = ''.join(c for c in val if c.isdigit())[:12]
                if clean != val:
                    id_num_var.set(clean)

        id_num_var.trace_add("write", enforce_aadhaar_limit)
        id_type_var.trace_add("write", enforce_aadhaar_limit)

        # Run initial cleanup if pre-filled
        enforce_aadhaar_limit()

        row_dict = {
            "num_lbl": lbl_num,
            "name": name_var,
            "age": age_var,
            "gender": gender_var,
            "id_type": id_type_var,
            "id_number": id_num_var,
            "widgets": []
        }

        # 6: Remove button
        del_btn = ttk.Button(self.grid_frame, text="✕", width=3, command=lambda r=row_dict: self.remove_pilgrim_row(r))
        del_btn.grid(row=row_idx, column=6, sticky="ew", padx=2, pady=3)

        row_dict["widgets"] = [lbl_num, e_name, e_age, c_gender, c_id_type, e_id_num, del_btn]
        self.pilgrim_rows.append(row_dict)
        self.update_count_ui()

    def remove_pilgrim_row(self, target_row):
        if len(self.pilgrim_rows) <= 1:
            messagebox.showinfo("Required", "At least 1 passenger is required in the group!")
            return

        if target_row in self.pilgrim_rows:
            self.pilgrim_rows.remove(target_row)
            for w in target_row["widgets"]:
                w.destroy()

            # Re-grid remaining rows so numbering and positions remain clean
            for idx, row in enumerate(self.pilgrim_rows):
                new_grid_row = idx + 1
                row["num_lbl"].config(text=str(new_grid_row))
                for col_idx, w in enumerate(row["widgets"]):
                    w.grid(row=new_grid_row, column=col_idx)

            self.update_count_ui()

    def update_count_ui(self):
        count = len(self.pilgrim_rows)
        self.count_lbl.config(text=f"{count} / 4 Passengers")
        if count >= 4:
            self.add_p_btn.config(state="disabled")
        else:
            self.add_p_btn.config(state="normal")

    def save_family(self):
        group_name = self.group_name_var.get().strip()
        if not group_name:
            messagebox.showerror("Required Field", "Please enter a Group Name (e.g. FAMILY_1)!")
            return

        if len(self.pilgrim_rows) < 1:
            messagebox.showerror("Passenger Missing", "Please add at least 1 passenger!")
            return

        if len(self.pilgrim_rows) > 4:
            messagebox.showerror("Limit Exceeded", "A maximum of 4 passengers is allowed per group!")
            return

        target_date = self.target_date_var.get().strip() or None
        payment_type = self.payment_type_var.get()

        # Validate passengers
        pilgrims_data = []
        for i, row in enumerate(self.pilgrim_rows):
            name = row["name"].get().strip()
            age_str = row["age"].get().strip()
            gender = row["gender"].get().strip()
            id_type = row["id_type"].get().strip()
            id_num = row["id_number"].get().strip()

            if not name:
                messagebox.showerror("Missing Information", f"Passenger #{i+1} is missing Full Name!")
                return
            if not age_str:
                messagebox.showerror("Missing Information", f"Passenger #{i+1} is missing Age!")
                return
            try:
                age = int(age_str)
            except ValueError:
                messagebox.showerror("Invalid Age", f"Passenger #{i+1} Age must be a valid number!")
                return
            if not id_num:
                messagebox.showerror("Missing Information", f"Passenger #{i+1} is missing ID / Aadhaar Number!")
                return

            # Strict 12-Digit Aadhaar Validation
            if id_type == "Aadhaar Card":
                if len(id_num) != 12 or not id_num.isdigit():
                    messagebox.showerror(
                        "Invalid Aadhaar Number", 
                        f"Passenger #{i+1} ({name}) has an invalid Aadhaar number.\n"
                        f"Aadhaar Card must be exactly 12 digits! (Entered: {len(id_num)} digits)"
                    )
                    return

            pilgrims_data.append((name, age, gender, id_type, id_num))

        # Validate Payment
        upi_id = self.upi_id_var.get().strip()
        if payment_type == "UPI" and not upi_id:
            messagebox.showerror("Required Field", "Please provide a valid UPI ID for this booking!")
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            if self.edit_group_id:
                # 1. Update Existing Family Group
                cur.execute("""
                    UPDATE family_groups 
                    SET group_name = %s, target_date = %s, payment_method = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (group_name, target_date, payment_type, self.edit_group_id))
                group_id = self.edit_group_id

                # Clear old records for this group to re-insert cleanly
                cur.execute("DELETE FROM pilgrims WHERE group_id = %s;", (group_id,))
                cur.execute("DELETE FROM payments WHERE group_id = %s;", (group_id,))
            else:
                # 1. Insert New Family Group
                cur.execute("""
                    INSERT INTO family_groups (group_name, target_date, status, payment_method)
                    VALUES (%s, %s, 'PENDING', %s)
                    RETURNING id;
                """, (group_name, target_date, payment_type))
                group_id = cur.fetchone()[0]

            # 2. Insert Pilgrims
            for p in pilgrims_data:
                name, age, gender, id_type, id_num = p
                cur.execute("""
                    INSERT INTO pilgrims (group_id, name, full_name, age, gender, id_type, id_number, aadhar_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (group_id, name, name, age, gender, id_type, id_num, id_num))

            # 3. Insert Payment
            if payment_type == "UPI":
                cur.execute("""
                    INSERT INTO payments (group_id, payment_type, upi_id, payment_status)
                    VALUES (%s, %s, %s, 'PENDING');
                """, (group_id, payment_type, upi_id))
            else:
                cur.execute("""
                    INSERT INTO payments (group_id, payment_type, card_number, cardholder_name, card_expiry_month, card_expiry_year, card_cvv, payment_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING');
                """, (
                    group_id, payment_type,
                    self.card_num_var.get().strip(),
                    self.cardholder_var.get().strip(),
                    self.exp_m_var.get().strip(),
                    self.exp_y_var.get().strip(),
                    self.cvv_var.get().strip()
                ))

            conn.commit()
            cur.close()
            conn.close()

            action_msg = "updated successfully in" if self.edit_group_id else "saved to"
            messagebox.showinfo("Success", f"Family '{group_name}' with {len(pilgrims_data)} passenger(s) was {action_msg} PostgreSQL!")
            self.on_success()
            self.on_close()

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save record:\n{str(e)}")

# =========================================================
# Dialog: Add Login Account (Clean Modern)
# =========================================================
class AddLoginDialog(tk.Toplevel):
    def __init__(self, parent, on_success_callback):
        super().__init__(parent)
        self.title("Add Login Account")
        self.geometry("420x260")
        self.resizable(False, False)
        self.on_success = on_success_callback

        self.create_widgets()

        # Center on parent
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")

        self.transient(parent)
        self.grab_set()

    def create_widgets(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="🔑 New Tirupati Portal Login", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        ttk.Label(frame, text="Login Email: *", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=6)
        self.email_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.email_var, width=28, font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(frame, text="Password: *", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=6)
        self.pwd_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.pwd_var, width=28, font=("Segoe UI", 9), show="*").grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(frame, text="Initial Status:", font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=6)
        self.status_var = tk.StringVar(value="ACTIVE")
        ttk.Combobox(frame, textvariable=self.status_var, values=["ACTIVE", "PASSED"], state="readonly", width=12, font=("Segoe UI", 9)).grid(row=3, column=1, sticky="w", pady=6)

        btn_box = ttk.Frame(frame)
        btn_box.grid(row=4, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(btn_box, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Save Login", command=self.save_login, style="Primary.TButton").pack(side="right")

    def save_login(self):
        email = self.email_var.get().strip()
        pwd = self.pwd_var.get().strip()
        status = self.status_var.get().strip()

        if not email or not pwd:
            messagebox.showerror("Required", "Both Email and Password are required!")
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO logins (email, password, status)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, status = EXCLUDED.status;
            """, (email, pwd, status))
            conn.commit()
            cur.close()
            conn.close()
            messagebox.showinfo("Success", f"Login '{email}' saved successfully!")
            self.on_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save login:\n{str(e)}")

# =========================================================
# Dialog: Live CAPTCHA Preview & Quick Edit (5-Second Auto-Submit)
# =========================================================
class CaptchaPromptDialog(tk.Toplevel):
    def __init__(self, parent, req_data, on_submit_callback):
        super().__init__(parent)
        self.req_data = req_data
        self.on_submit = on_submit_callback
        self.req_id = req_data.get("id", "")
        self.email = req_data.get("email", "")
        self.group = req_data.get("group", "")
        self.ocr_text = req_data.get("ocr_text", "")
        self.img_path = req_data.get("image_path", "")

        self.title(f"🔐 CAPTCHA Verification ({self.email})")
        self.geometry("450x300")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.remaining_ms = 5000
        self.user_edited = False
        self.submitted = False

        self.create_widgets()

        # Start 5-second countdown
        self.countdown_step()

    def create_widgets(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="🔐 Login CAPTCHA Verification", font=("Segoe UI", 11, "bold"), foreground="#0284c7").pack(side="left")
        
        self.timer_badge = ttk.Label(header, text="⏱️ 5.0s", font=("Segoe UI", 10, "bold"), foreground="#ea580c")
        self.timer_badge.pack(side="right")

        # Display CAPTCHA image
        img_frame = ttk.Frame(container, padding=4)
        img_frame.pack(fill="x", pady=4)
        
        self.photo = None
        if self.img_path and os.path.exists(self.img_path):
            try:
                from PIL import ImageTk, Image
                pil_img = Image.open(self.img_path)
                # Resize slightly for better readability if small
                w, h = pil_img.size
                if w < 200:
                    pil_img = pil_img.resize((w * 2, h * 2), Image.Resampling.NEAREST)
                self.photo = ImageTk.PhotoImage(pil_img)
                lbl_img = ttk.Label(img_frame, image=self.photo)
                lbl_img.pack(anchor="center")
            except Exception:
                pass

        # Input row
        edit_box = ttk.LabelFrame(container, text=" Recognized Text (Edit if wrong) ", padding=10)
        edit_box.pack(fill="x", pady=8)

        self.val_var = tk.StringVar(value=self.ocr_text)
        self.entry = ttk.Entry(edit_box, textvariable=self.val_var, font=("Consolas", 16, "bold"), width=12, justify="center")
        self.entry.pack(side="left", padx=(10, 10))
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

        def on_user_type(*args):
            self.user_edited = True

        self.val_var.trace_add("write", on_user_type)
        self.entry.bind("<Return>", lambda e: self.do_submit())

        btn_row = ttk.Frame(container)
        btn_row.pack(fill="x", pady=(8, 0))
        
        ttk.Button(btn_row, text="Submit Immediately (Enter)", command=self.do_submit, style="Success.TButton").pack(side="right")

    def countdown_step(self):
        if self.submitted:
            return
        if self.remaining_ms <= 0:
            self.do_submit()
        else:
            sec = max(0.0, self.remaining_ms / 1000.0)
            self.timer_badge.config(text=f"⏱️ {sec:.1f}s")
            self.remaining_ms -= 100
            self.after(100, self.countdown_step)

    def do_submit(self):
        if self.submitted:
            return
        self.submitted = True
        final_code = self.val_var.get().strip().upper()
        self.on_submit(self.req_id, final_code)
        self.destroy()

# =========================================================
# Dialog: Live Bank OTP Prompt (Automated Bridge)
# =========================================================
class BankOtpPromptDialog(tk.Toplevel):
    def __init__(self, parent, req_data, on_submit_callback):
        super().__init__(parent)
        self.req_data = req_data
        self.on_submit = on_submit_callback
        self.group = req_data.get("group", "Unknown Group")
        self.email = req_data.get("email", "")

        self.title(f"🚨 OTP REQUIRED - {self.group}")
        self.geometry("520x420")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # Bell alert
        try:
            self.bell()
        except Exception:
            pass

        self.create_widgets()

        # Focus OTP entry immediately
        self.after(200, self.otp_entry.focus_set)

    def create_widgets(self):
        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)

        # Header Badge
        hdr = ttk.Frame(container)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="🚨 PAYMENT OTP REQUIRED", font=("Segoe UI", 13, "bold"), foreground="#dc2626").pack(anchor="w")
        ttk.Label(hdr, text=f"Bank 3D-Secure page reached for {self.group} ({self.email})", font=("Segoe UI", 9), foreground="#475569").pack(anchor="w", pady=(2, 0))

        # Instructions card
        card = ttk.LabelFrame(container, text=" Payment Security Verification ", padding=12)
        card.pack(fill="x", pady=6)

        ttk.Label(card, text="Please check the SMS on your registered bank mobile.\nType the received 4 to 8 digit OTP below:", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))

        entry_frame = ttk.Frame(card)
        entry_frame.pack(fill="x", pady=5)
        ttk.Label(entry_frame, text="Enter OTP Code:", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))

        self.otp_var = tk.StringVar()
        self.otp_entry = ttk.Entry(entry_frame, textvariable=self.otp_var, font=("Consolas", 18, "bold"), width=12, justify="center")
        self.otp_entry.pack(side="left")
        self.otp_entry.bind("<Return>", lambda e: self.submit_otp())

        # Timer countdown display
        self.countdown_seconds = 180
        self.timer_lbl = ttk.Label(container, text="⏱️ Time remaining: 180s", font=("Segoe UI", 9, "bold"), foreground="#ea580c")
        self.timer_lbl.pack(anchor="w", pady=8)
        self.update_timer()

        # Submit button
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_bar, text="Cancel", command=self.cancel_otp).pack(side="right", padx=(8, 0))
        ttk.Button(btn_bar, text="🚀 SUBMIT OTP TO BROWSER", command=self.submit_otp, style="Success.TButton").pack(side="right")

    def update_timer(self):
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            self.timer_lbl.config(text=f"⏱️ Time remaining: {self.countdown_seconds}s")
            self.after(1000, self.update_timer)
        else:
            self.timer_lbl.config(text="⏱️ Time expired! Please re-trigger.", foreground="#dc2626")

    def cancel_otp(self):
        # Clean request file so it does not immediately reopen
        try:
            req_file = os.path.join(os.getcwd(), "otp_requests", f"{self.group}_request.json")
            if os.path.exists(req_file):
                os.remove(req_file)
        except Exception:
            pass
        self.destroy()

    def submit_otp(self):
        val = self.otp_var.get().strip()
        if not val or not val.isdigit():
            messagebox.showerror("Invalid OTP", "Please enter a valid numeric OTP code received from your bank!", parent=self)
            return

        # Clean request file upon submission
        try:
            req_file = os.path.join(os.getcwd(), "otp_requests", f"{self.group}_request.json")
            if os.path.exists(req_file):
                os.remove(req_file)
        except Exception:
            pass

        self.on_submit(self.group, val)
        self.destroy()

# =========================================================
# Main Application Window (Polished & Modern)
# =========================================================
class BookingControlCenter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("padmavathi travels booking control center")
        self.geometry("1100x720")
        self.minsize(980, 620)

        # Timing & Concurrency variables (shared across tabs)
        self.tb_h_var = tk.StringVar(value="09")
        self.tb_m_var = tk.StringVar(value="03")
        self.tb_s_var = tk.StringVar(value="00")
        self.tc_h_var = tk.StringVar(value="09")
        self.tc_m_var = tk.StringVar(value="03")
        self.tc_s_var = tk.StringVar(value="00")
        self.sched_enabled_var = tk.BooleanVar(value=True)
        self.b_per_fam_var = tk.StringVar(value="3")

        self.load_timing_config_to_ui()

        self.setup_theme()
        self.create_widgets()
        self.refresh_all()
        self.update_browser_summary()

        # Clean any stale OTP or CAPTCHA request files on startup (>3 minutes old)
        self.cleanup_stale_ipc_files()

        # Automated OTP & CAPTCHA bridge tracking
        self.active_otp_dialogs = {}
        self.active_captcha_dialogs = {}
        self.poll_otp_requests()
        self.poll_captcha_requests()

    def cleanup_stale_ipc_files(self):
        """Cleans orphaned or expired request files from previous sessions."""
        now = time.time()
        for folder in ["otp_requests", "captcha_requests"]:
            dpath = os.path.join(os.getcwd(), folder)
            if os.path.exists(dpath):
                for f in glob.glob(os.path.join(dpath, "*.*")):
                    try:
                        # If file is older than 3 minutes, remove it
                        if now - os.path.getmtime(f) > 180:
                            os.remove(f)
                    except Exception:
                        pass

    def poll_captcha_requests(self):
        """Monitors for CAPTCHA review requests emitted by workers."""
        captcha_dir = os.path.join(os.getcwd(), "captcha_requests")
        if os.path.exists(captcha_dir):
            req_files = glob.glob(os.path.join(captcha_dir, "*_request.json"))
            now = time.time()
            for rf in req_files:
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    req_ts = float(data.get("timestamp", 0))
                    if now - req_ts > 15:  # CAPTCHA requests expire in 15 seconds
                        try:
                            os.remove(rf)
                        except Exception:
                            pass
                        continue

                    req_id = data.get("id")
                    if req_id and req_id not in self.active_captcha_dialogs:
                        dlg = CaptchaPromptDialog(self, data, self.send_captcha_to_worker)
                        self.active_captcha_dialogs[req_id] = dlg

                        def on_close(rid=req_id, fp=rf):
                            if rid in self.active_captcha_dialogs:
                                del self.active_captcha_dialogs[rid]
                            try:
                                if os.path.exists(fp):
                                    os.remove(fp)
                            except Exception:
                                pass

                        dlg.bind("<Destroy>", lambda e, rid=req_id, fp=rf: on_close(rid, fp))
                except Exception:
                    pass

        # Check every 300ms for fast CAPTCHA reaction
        self.after(300, self.poll_captcha_requests)

    def send_captcha_to_worker(self, req_id, final_text):
        """Writes the user's/auto-confirmed CAPTCHA response for the worker."""
        captcha_dir = os.path.join(os.getcwd(), "captcha_requests")
        os.makedirs(captcha_dir, exist_ok=True)
        resp_file = os.path.join(captcha_dir, f"{req_id}_response.json")
        try:
            with open(resp_file, "w", encoding="utf-8") as f:
                json.dump({"id": req_id, "captcha_text": final_text, "timestamp": time.time()}, f)
            self.log(f"🔐 CAPTCHA ({final_text}) sent for {req_id}!")
        except Exception as e:
            self.log(f"⚠️ Error sending CAPTCHA response: {e}")

    def poll_otp_requests(self):
        """Monitors for bank OTP requests emitted by headless workers."""
        otp_dir = os.path.join(os.getcwd(), "otp_requests")
        if os.path.exists(otp_dir):
            req_files = glob.glob(os.path.join(otp_dir, "*_request.json"))
            now = time.time()
            for rf in req_files:
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    req_ts = float(data.get("timestamp", 0))
                    # Stale OTP request (>180s old): remove and skip
                    if now - req_ts > 180:
                        try:
                            os.remove(rf)
                        except Exception:
                            pass
                        continue

                    group = data.get("group")
                    if group and group not in self.active_otp_dialogs:
                        # Display OTP popup dialog
                        dlg = BankOtpPromptDialog(self, data, self.send_otp_to_worker)
                        self.active_otp_dialogs[group] = dlg

                        def on_close(g=group, fp=rf):
                            if g in self.active_otp_dialogs:
                                del self.active_otp_dialogs[g]
                            try:
                                if os.path.exists(fp):
                                    os.remove(fp)
                            except Exception:
                                pass

                        dlg.bind("<Destroy>", lambda e, g=group, fp=rf: on_close(g, fp))
                except Exception:
                    pass

        # Check every 1000ms
        self.after(1000, self.poll_otp_requests)

    def send_otp_to_worker(self, group, otp_code):
        """Writes the user's OTP response for the headless worker to consume and inject."""
        otp_dir = os.path.join(os.getcwd(), "otp_requests")
        os.makedirs(otp_dir, exist_ok=True)
        resp_file = os.path.join(otp_dir, f"{group}_response.json")
        try:
            with open(resp_file, "w", encoding="utf-8") as f:
                json.dump({"group": group, "otp": otp_code, "timestamp": time.time()}, f)
            self.log(f"🔑 OTP for {group} sent to worker!")
            messagebox.showinfo("OTP Sent", f"OTP {otp_code} has been transmitted to {group}'s headless browser!\nSubmitting to bank...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send OTP to worker: {e}")

    def setup_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass

        # Global Fonts & Colors
        default_font = ("Segoe UI", 9)
        heading_font = ("Segoe UI", 10, "bold")
        
        style.configure(".", font=default_font)
        style.configure("Treeview", font=default_font, rowheight=28)
        style.configure("Treeview.Heading", font=heading_font, background="#e2e8f0", foreground="#0f172a")
        style.map("Treeview", background=[("selected", "#0284c7")], foreground=[("selected", "#ffffff")])

        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), foreground="#ffffff", background="#0284c7", padding=(10, 5))
        style.map("Primary.TButton", background=[("active", "#0369a1")])

        style.configure("Success.TButton", font=("Segoe UI", 9, "bold"), foreground="#ffffff", background="#16a34a", padding=(10, 5))
        style.map("Success.TButton", background=[("active", "#15803d")])

        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), foreground="#ffffff", background="#dc2626", padding=(10, 5))
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 7))

    def create_widgets(self):
        # 1. Header banner
        header = ttk.Frame(self, padding=(18, 12))
        header.pack(fill="x")
        ttk.Label(header, text="🏛️padmavathi travels booking control center", font=("Segoe UI", 15, "bold"), foreground="#0f172a").pack(side="left")
        
        info_badge = ttk.Frame(header)
        info_badge.pack(side="right")
        ttk.Label(info_badge, text="Database: ", font=("Segoe UI", 9, "bold"), foreground="#475569").pack(side="left", padx=(0, 6))
        ttk.Label(info_badge, text=f"{DB_NAME} (Connected)", font=("Segoe UI", 9), foreground="#16a34a").pack(side="left", padx=(0, 15))
        ttk.Button(info_badge, text="⚠️ Wipe Entire Database", command=self.delete_entire_database, style="Danger.TButton").pack(side="left")

        # 2. Main Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Tab 1: Families & Pilgrims
        self.tab_families = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_families, text="👨‍👩‍👧‍👦 Families & Pilgrims")
        self.setup_families_tab()

        # Tab 2: Login Accounts
        self.tab_logins = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_logins, text="🔑 Login Accounts")
        self.setup_logins_tab()

        # Tab 3: Payments Details
        self.tab_payments = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_payments, text="💳 Payment Methods")
        self.setup_payments_tab()

        # Tab 4: Automation Runner & Logs
        self.tab_automation = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_automation, text="🚀 Automation Runner")
        self.setup_automation_tab()

        # Tab 5: Target Timers & Schedule Settings
        self.tab_timing = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_timing, text="⏱️ Target Timers & Schedule")
        self.setup_timing_tab()

    # ---------------------------------------------------------
    # Tab 1: Families & Pilgrims
    # ---------------------------------------------------------
    def setup_families_tab(self):
        bar = ttk.Frame(self.tab_families)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Button(bar, text="➕ Add Family & Pilgrims (Max 4)", command=self.open_add_family_dialog, style="Primary.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="📥 Import Excel", command=self.import_excel_to_db).pack(side="left", padx=4)
        ttk.Button(bar, text="✏️ Edit Selected Family", command=self.open_edit_family_dialog).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑️ Delete Selected", command=self.delete_selected_family).pack(side="left", padx=4)
        ttk.Button(bar, text="💥 Delete All Families", command=self.delete_all_families, style="Danger.TButton").pack(side="left", padx=4)
        ttk.Button(bar, text="✅ Mark PASSED", command=lambda: self.update_family_status("PASSED")).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 Reset PENDING", command=lambda: self.update_family_status("PENDING")).pack(side="left", padx=4)
        ttk.Button(bar, text="📋 Success Excel", command=self.open_success_excel).pack(side="left", padx=4)

        ttk.Button(bar, text="🔄 Refresh", command=self.refresh_families).pack(side="right", padx=4)

        # Paned Window Split View
        paned = ttk.PanedWindow(self.tab_families, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # Left Panel: Groups List
        left_box = ttk.LabelFrame(paned, text=" Family Groups ", padding=8)
        paned.add(left_box, weight=2)

        f_cols = ("id", "group_name", "status", "payment_method", "target_date")
        self.family_tree = ttk.Treeview(left_box, columns=f_cols, show="headings", selectmode="browse")
        self.family_tree.heading("id", text="ID")
        self.family_tree.column("id", width=45, anchor="center")
        self.family_tree.heading("group_name", text="Group Name")
        self.family_tree.column("group_name", width=140)
        self.family_tree.heading("status", text="Status")
        self.family_tree.column("status", width=90, anchor="center")
        self.family_tree.heading("payment_method", text="Payment")
        self.family_tree.column("payment_method", width=80, anchor="center")
        self.family_tree.heading("target_date", text="Date")
        self.family_tree.column("target_date", width=95, anchor="center")
        self.family_tree.pack(fill="both", expand=True)
        self.family_tree.bind("<<TreeviewSelect>>", self.on_family_selected)
        self.family_tree.bind("<Double-1>", lambda event: self.open_edit_family_dialog())

        # Right Panel: Pilgrims in Group
        right_box = ttk.LabelFrame(paned, text=" Pilgrims in Selected Family (Max 4) ", padding=8)
        paned.add(right_box, weight=3)

        p_cols = ("name", "age", "gender", "id_type", "id_number")
        self.pilgrims_tree = ttk.Treeview(right_box, columns=p_cols, show="headings")
        self.pilgrims_tree.heading("name", text="Passenger Name")
        self.pilgrims_tree.column("name", width=160)
        self.pilgrims_tree.heading("age", text="Age")
        self.pilgrims_tree.column("age", width=55, anchor="center")
        self.pilgrims_tree.heading("gender", text="Gender")
        self.pilgrims_tree.column("gender", width=80, anchor="center")
        self.pilgrims_tree.heading("id_type", text="ID Proof")
        self.pilgrims_tree.column("id_type", width=120)
        self.pilgrims_tree.heading("id_number", text="ID / Aadhaar Number")
        self.pilgrims_tree.column("id_number", width=160)
        self.pilgrims_tree.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # Tab 2: Login Accounts
    # ---------------------------------------------------------
    def setup_logins_tab(self):
        bar = ttk.Frame(self.tab_logins)
        bar.pack(fill="x", pady=(0, 10))

        ttk.Button(bar, text="➕ Add Login Account", command=self.open_add_login_dialog, style="Primary.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="📥 Import Excel", command=self.import_logins_from_excel).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑️ Delete Selected", command=self.delete_selected_login).pack(side="left", padx=4)
        ttk.Button(bar, text="💥 Delete All Logins", command=self.delete_all_logins, style="Danger.TButton").pack(side="left", padx=4)
        ttk.Button(bar, text="Toggle Status (ACTIVE / PASSED)", command=self.toggle_login_status).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 Refresh Logins", command=self.refresh_logins).pack(side="right", padx=4)

        cols = ("id", "email", "password", "status", "created_at")
        self.logins_tree = ttk.Treeview(self.tab_logins, columns=cols, show="headings")
        self.logins_tree.heading("id", text="ID")
        self.logins_tree.column("id", width=50, anchor="center")
        self.logins_tree.heading("email", text="Email ID")
        self.logins_tree.column("email", width=260)
        self.logins_tree.heading("password", text="Password")
        self.logins_tree.column("password", width=190)
        self.logins_tree.heading("status", text="Status")
        self.logins_tree.column("status", width=110, anchor="center")
        self.logins_tree.heading("created_at", text="Registered Time")
        self.logins_tree.column("created_at", width=180, anchor="center")
        self.logins_tree.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # Tab 3: Payment Methods
    # ---------------------------------------------------------
    def setup_payments_tab(self):
        bar = ttk.Frame(self.tab_payments)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="🔄 Refresh Payments", command=self.refresh_payments).pack(side="left", padx=4)

        cols = ("group_name", "payment_type", "upi_id", "card_masked", "payment_status", "amount")
        self.payments_tree = ttk.Treeview(self.tab_payments, columns=cols, show="headings")
        self.payments_tree.heading("group_name", text="Family Group")
        self.payments_tree.column("group_name", width=160)
        self.payments_tree.heading("payment_type", text="Payment Type")
        self.payments_tree.column("payment_type", width=110, anchor="center")
        self.payments_tree.heading("upi_id", text="Configured UPI ID")
        self.payments_tree.column("upi_id", width=220)
        self.payments_tree.heading("card_masked", text="Card Details")
        self.payments_tree.column("card_masked", width=230)
        self.payments_tree.heading("payment_status", text="Payment Status")
        self.payments_tree.column("payment_status", width=120, anchor="center")
        self.payments_tree.heading("amount", text="Amount (₹)")
        self.payments_tree.column("amount", width=100, anchor="center")
        self.payments_tree.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # Tab 4: Automation Runner & Console
    # ---------------------------------------------------------
    def setup_automation_tab(self):
        top_bar = ttk.Frame(self.tab_automation)
        top_bar.pack(fill="x", pady=(0, 8))

        self.btn_start = ttk.Button(top_bar, text="🚀 START AUTOMATION LAUNCHER", command=self.start_automation, style="Success.TButton")
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ttk.Button(top_bar, text="🛑 STOP AUTOMATION", command=self.stop_automation, style="Danger.TButton", state="disabled")
        self.btn_stop.pack(side="left", padx=(0, 8))

        ttk.Button(top_bar, text="📁 Open Logs Folder", command=self.open_logs_folder).pack(side="right", padx=4)
        ttk.Button(top_bar, text="🧹 Clear Screen", command=self.clear_logs).pack(side="right", padx=4)

        # ---------------- Concurrency Quick Control Bar ----------------
        conc_card = ttk.LabelFrame(self.tab_automation, text=" 👥 Multi-Browser Concurrency Settings ", padding=10)
        conc_card.pack(fill="x", pady=(0, 8))

        conc_row1 = ttk.Frame(conc_card)
        conc_row1.pack(fill="x", pady=(0, 4))

        ttk.Label(conc_row1, text="Browsers per Family:", font=("Segoe UI", 9, "bold"), foreground="#0f172a").pack(side="left", padx=(0, 8))

        self.automation_conc_spin = ttk.Spinbox(
            conc_row1,
            from_=1,
            to=20,
            width=5,
            textvariable=self.b_per_fam_var,
            format="%01.0f",
            justify="center",
            command=self.on_browser_count_changed
        )
        self.automation_conc_spin.pack(side="left", padx=(0, 14))
        self.automation_conc_spin.bind("<KeyRelease>", lambda e: self.on_browser_count_changed())

        ttk.Label(conc_row1, text="Quick Presets:", font=("Segoe UI", 8, "bold"), foreground="#64748b").pack(side="left", padx=(0, 6))
        ttk.Button(conc_row1, text="⭐ 3 (Recommended - Fast)", command=lambda: self.set_browsers_per_family(3)).pack(side="left", padx=3)
        ttk.Button(conc_row1, text="⚡ 2 (Ultra-Light)", command=lambda: self.set_browsers_per_family(2)).pack(side="left", padx=3)
        ttk.Button(conc_row1, text="1 (Single Worker)", command=lambda: self.set_browsers_per_family(1)).pack(side="left", padx=3)
        ttk.Button(conc_row1, text="🔥 Max (All Logins)", command=lambda: self.set_browsers_per_family(10)).pack(side="left", padx=3)

        self.lbl_browser_summary = ttk.Label(conc_card, text="", font=("Segoe UI", 9, "bold"))
        self.lbl_browser_summary.pack(anchor="w", pady=(4, 0))

        ttk.Label(self.tab_automation, text="Real-Time Automation Logs:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 3))
        self.log_text = tk.Text(self.tab_automation, height=20, bg="#0f172a", fg="#22c55e", insertbackground="#ffffff", font=("Consolas", 10), padx=8, pady=8)
        self.log_text.pack(fill="both", expand=True)
        self.log("Ready. Click 'START AUTOMATION LAUNCHER' to launch the parallel browser workers.")

    # ---------------------------------------------------------
    # Tab 5: Target Timers & Schedule Settings
    # ---------------------------------------------------------
    def setup_timing_tab(self):
        container = ttk.Frame(self.tab_timing)
        container.pack(fill="both", expand=True)

        header_frame = ttk.Frame(container)
        header_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(header_frame, text="⏱️ Automation Scheduling & Precision Timers", font=("Segoe UI", 12, "bold"), foreground="#0284c7").pack(anchor="w")
        ttk.Label(header_frame, text="Configure target release times for Step 6 ('Current Booking') and Step C (T+0 'Continue' click). Workers automatically read these settings.", font=("Segoe UI", 9), foreground="#64748b").pack(anchor="w", pady=(2, 0))

        # Live Clock & Status Banner
        clock_card = ttk.LabelFrame(container, text=" 🕒 Live Time Status ", padding=10)
        clock_card.pack(fill="x", pady=(0, 12))

        clock_sub = ttk.Frame(clock_card)
        clock_sub.pack(fill="x")
        self.lbl_live_clock = ttk.Label(clock_sub, text="Current IST Time: --:--:--", font=("Consolas", 12, "bold"), foreground="#0f172a")
        self.lbl_live_clock.pack(side="left")

        self.lbl_time_status = ttk.Label(clock_sub, text="⏳ Monitoring schedule...", font=("Segoe UI", 9, "bold"), foreground="#ea580c")
        self.lbl_time_status.pack(side="right")


        # ---------------- Quick 1-Click Slots: 9:03 AM & 1:03 PM ----------------
        slots_card = ttk.LabelFrame(container, text=" ⚡ Daily Srivani Quota Slots (1-Click Switch) ", padding=10)
        slots_card.pack(fill="x", pady=(0, 12))

        slots_row = ttk.Frame(slots_card)
        slots_row.pack(fill="x")

        def apply_slot(h, m, s=0, label=""):
            self.tb_h_var.set(f"{h:02d}")
            self.tb_m_var.set(f"{m:02d}")
            self.tb_s_var.set(f"{s:02d}")
            self.tc_h_var.set(f"{h:02d}")
            self.tc_m_var.set(f"{m:02d}")
            self.tc_s_var.set(f"{s:02d}")
            self.sched_enabled_var.set(True)
            self.save_timing_config_from_ui()

        ttk.Button(slots_row, text="☀️ Slot 1: 09:03:00 AM (Morning)", command=lambda: apply_slot(9, 3, 0, "Morning 9:03 AM"), style="Primary.TButton").pack(side="left", padx=(0, 10))
        ttk.Button(slots_row, text="🌤️ Slot 2: 01:03:00 PM (13:03:00 Afternoon)", command=lambda: apply_slot(13, 3, 0, "Afternoon 1:03 PM"), style="Primary.TButton").pack(side="left", padx=(0, 10))

        def auto_slot():
            now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
            if now_ist.hour < 11:
                apply_slot(9, 3, 0, "Morning 9:03 AM")
            else:
                apply_slot(13, 3, 0, "Afternoon 1:03 PM")

        ttk.Button(slots_row, text="🤖 Auto-Select Upcoming Slot", command=auto_slot).pack(side="left", padx=(0, 10))

        # ---------------- Section 1: TARGET_BOOKING_HOUR ----------------
        b_frame = ttk.LabelFrame(container, text=" 1️⃣ Step 6: 'Current Booking' Target Time (TARGET_BOOKING_HOUR) ", padding=12)
        b_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(b_frame, text="The browser pauses after entering the donation amount and waits until this exact time before clicking 'Current Booking' (#curr):", font=("Segoe UI", 9), foreground="#334155").pack(anchor="w", pady=(0, 8))

        row_b = ttk.Frame(b_frame)
        row_b.pack(fill="x", pady=(0, 8))

        ttk.Label(row_b, text="Hour (0-23):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        b_hour_spin = ttk.Spinbox(row_b, from_=0, to=23, width=5, textvariable=self.tb_h_var, format="%02.0f", justify="center")
        b_hour_spin.pack(side="left", padx=(0, 16))

        ttk.Label(row_b, text="Minute (0-59):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        b_min_spin = ttk.Spinbox(row_b, from_=0, to=59, width=5, textvariable=self.tb_m_var, format="%02.0f", justify="center")
        b_min_spin.pack(side="left", padx=(0, 16))

        ttk.Label(row_b, text="Second (0-59):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        b_sec_spin = ttk.Spinbox(row_b, from_=0, to=59, width=5, textvariable=self.tb_s_var, format="%02.0f", justify="center")
        b_sec_spin.pack(side="left", padx=(0, 16))

        # Presets for Current Booking
        b_presets = ttk.Frame(b_frame)
        b_presets.pack(fill="x")
        ttk.Label(b_presets, text="Quick Presets:", font=("Segoe UI", 8, "bold"), foreground="#64748b").pack(side="left", padx=(0, 8))

        def set_b_time(h, m, s):
            self.tb_h_var.set(f"{h:02d}")
            self.tb_m_var.set(f"{m:02d}")
            self.tb_s_var.set(f"{s:02d}")

        ttk.Button(b_presets, text="09:03:00 AM", command=lambda: set_b_time(9, 3, 0)).pack(side="left", padx=3)
        ttk.Button(b_presets, text="01:03:00 PM (13:03)", command=lambda: set_b_time(13, 3, 0)).pack(side="left", padx=3)
        ttk.Button(b_presets, text="09:00:00 AM", command=lambda: set_b_time(9, 0, 0)).pack(side="left", padx=3)
        ttk.Button(b_presets, text="10:00:00 AM", command=lambda: set_b_time(10, 0, 0)).pack(side="left", padx=3)

        # ---------------- Section 2: TARGET_HOUR (Continue) ----------------
        c_frame = ttk.LabelFrame(container, text=" 2️⃣ Step C: 'Continue' Click Release Time (TARGET_HOUR) ", padding=12)
        c_frame.pack(fill="x", pady=(0, 12))

        sched_check = ttk.Checkbutton(c_frame, text="Enable T+0 Scheduling (Uncheck to click 'Continue' immediately without waiting)", variable=self.sched_enabled_var)
        sched_check.pack(anchor="w", pady=(0, 8))

        row_c = ttk.Frame(c_frame)
        row_c.pack(fill="x", pady=(0, 8))

        ttk.Label(row_c, text="Hour (0-23):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        c_hour_spin = ttk.Spinbox(row_c, from_=0, to=23, width=5, textvariable=self.tc_h_var, format="%02.0f", justify="center")
        c_hour_spin.pack(side="left", padx=(0, 16))

        ttk.Label(row_c, text="Minute (0-59):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        c_min_spin = ttk.Spinbox(row_c, from_=0, to=59, width=5, textvariable=self.tc_m_var, format="%02.0f", justify="center")
        c_min_spin.pack(side="left", padx=(0, 16))

        ttk.Label(row_c, text="Second (0-59):", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        c_sec_spin = ttk.Spinbox(row_c, from_=0, to=59, width=5, textvariable=self.tc_s_var, format="%02.0f", justify="center")
        c_sec_spin.pack(side="left", padx=(0, 16))

        # Presets for Continue
        c_presets = ttk.Frame(c_frame)
        c_presets.pack(fill="x")
        ttk.Label(c_presets, text="Quick Presets:", font=("Segoe UI", 8, "bold"), foreground="#64748b").pack(side="left", padx=(0, 8))

        def set_c_time(h, m, s):
            self.tc_h_var.set(f"{h:02d}")
            self.tc_m_var.set(f"{m:02d}")
            self.tc_s_var.set(f"{s:02d}")

        ttk.Button(c_presets, text="09:00:00 AM", command=lambda: set_c_time(9, 0, 0)).pack(side="left", padx=3)
        ttk.Button(c_presets, text="10:00:00 AM", command=lambda: set_c_time(10, 0, 0)).pack(side="left", padx=3)
        ttk.Button(c_presets, text="09:00:02 AM (+2s Buffer)", command=lambda: set_c_time(9, 0, 2)).pack(side="left", padx=3)
        ttk.Button(c_presets, text="🔗 Match 'Current Booking' Time", command=lambda: set_c_time(int(self.tb_h_var.get() or 9), int(self.tb_m_var.get() or 0), int(self.tb_s_var.get() or 0))).pack(side="left", padx=3)

        # ---------------- Section 3: Concurrency Settings ----------------
        conc_frame = ttk.LabelFrame(container, text=" 3️⃣ Multi-Browser Concurrency (Browsers Per Family) ", padding=12)
        conc_frame.pack(fill="x", pady=(0, 10))

        row_conc = ttk.Frame(conc_frame)
        row_conc.pack(fill="x", pady=(0, 6))

        ttk.Label(row_conc, text="Browsers per Family Group:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))
        conc_spin = ttk.Spinbox(row_conc, from_=1, to=20, width=5, textvariable=self.b_per_fam_var, format="%01.0f", justify="center")
        conc_spin.pack(side="left", padx=(0, 16))

        ttk.Label(conc_frame, text="💡 Tip: E.g., if you have 5 families and 10 user IDs, set this to 2 to launch 2 parallel browsers per family (10 total browsers).\nEach worker requires a unique login account to prevent session conflicts.", font=("Segoe UI", 8), foreground="#64748b").pack(anchor="w")

        # ---------------- Section 4: Save & Controls ----------------
        action_bar = ttk.Frame(container)
        action_bar.pack(fill="x", pady=(10, 0))

        ttk.Button(action_bar, text="💾 Save Target Timings", command=self.save_timing_config_from_ui, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(action_bar, text="🔄 Reset Defaults (09:00:00)", command=self.reset_timing_defaults).pack(side="left", padx=4)

        self.lbl_save_status = ttk.Label(action_bar, text="", font=("Segoe UI", 9, "bold"), foreground="#16a34a")
        self.lbl_save_status.pack(side="left", padx=12)

        # Load existing config on init
        self.load_timing_config_to_ui()

        # Start live clock tick
        self.tick_live_clock()

    def load_timing_config_to_ui(self):
        cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_config.json")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.tb_h_var.set(f"{int(data.get('TARGET_BOOKING_HOUR', 9)):02d}")
                self.tb_m_var.set(f"{int(data.get('TARGET_BOOKING_MINUTE', 0)):02d}")
                self.tb_s_var.set(f"{int(data.get('TARGET_BOOKING_SECOND', 0)):02d}")

                self.tc_h_var.set(f"{int(data.get('TARGET_HOUR', 9)):02d}")
                self.tc_m_var.set(f"{int(data.get('TARGET_MINUTE', 0)):02d}")
                self.tc_s_var.set(f"{int(data.get('TARGET_SECOND', 0)):02d}")

                self.sched_enabled_var.set(bool(data.get("ENABLE_SCHEDULING", True)))
                self.b_per_fam_var.set(str(int(data.get("BROWSERS_PER_FAMILY", 1))))
            except Exception as e:
                self.log(f"⚠️ Error loading timing_config.json: {e}")

    def set_browsers_per_family(self, count):
        self.b_per_fam_var.set(str(int(count)))
        self.on_browser_count_changed()

    def on_browser_count_changed(self):
        try:
            val = max(1, min(20, int(self.b_per_fam_var.get() or 1)))
        except Exception:
            val = 1
        self.save_timing_config_from_ui(silent=True)
        self.update_browser_summary(val)

    def update_browser_summary(self, val=None):
        if not hasattr(self, 'lbl_browser_summary'):
            return
        if val is None:
            try:
                val = max(1, int(self.b_per_fam_var.get() or 1))
            except Exception:
                val = 1

        fam_count = 0
        login_count = 0
        try:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(DISTINCT group_name) FROM family_groups WHERE status != 'PASSED';")
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        fam_count = int(row[0])
                    cur.execute("SELECT COUNT(*) FROM logins WHERE status = 'ACTIVE';")
                    lrow = cur.fetchone()
                    if lrow and lrow[0] is not None:
                        login_count = int(lrow[0])
                conn.close()
        except Exception:
            pass

        if fam_count == 0:
            fam_count = 2
        if login_count == 0:
            login_count = 12

        max_workers = None
        cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_config.json")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    if "MAX_WORKERS" in cdata:
                        max_workers = int(cdata["MAX_WORKERS"])
            except Exception:
                pass

        requested_workers = min(fam_count * val, login_count)
        total_workers = min(requested_workers, max_workers) if max_workers else requested_workers

        if max_workers and requested_workers > max_workers:
            badge = f"🛡️ Safety Capped: Launching {total_workers} browsers total (Capped by MAX_WORKERS: {max_workers} to prevent CDN throttling). Optimal stability!"
            fg_color = "#16a34a"
        elif total_workers <= 3:
            badge = f"⭐ Stable & Lightweight: Launching {total_workers} browsers total ({val} for each of {fam_count} families). Low CPU & network load."
            fg_color = "#16a34a"
        elif total_workers <= 5:
            badge = f"ℹ️ Moderate Load: Launching {total_workers} browsers total ({val} for each of {fam_count} families using {total_workers} of {login_count} logins)."
            fg_color = "#d97706"
        else:
            badge = f"⚠️ Heavy Load: Launching {total_workers} browsers total (All {login_count} logins). May cause local rendering delays at 09:03."
            fg_color = "#dc2626"

        self.lbl_browser_summary.config(text=badge, foreground=fg_color)

    def save_timing_config_from_ui(self, silent=False):
        try:
            bh = int(self.tb_h_var.get())
            bm = int(self.tb_m_var.get())
            bs = int(self.tb_s_var.get())

            th = int(self.tc_h_var.get())
            tm = int(self.tc_m_var.get())
            ts = int(self.tc_s_var.get())

            try:
                b_fam = max(1, int(self.b_per_fam_var.get() or 1))
            except Exception:
                b_fam = 1

            if not (0 <= bh <= 23 and 0 <= bm <= 59 and 0 <= bs <= 59):
                if not silent:
                    messagebox.showerror("Validation Error", "Current Booking Time values must be:\nHour: 0-23\nMinute: 0-59\nSecond: 0-59")
                return

            if not (0 <= th <= 23 and 0 <= tm <= 59 and 0 <= ts <= 59):
                if not silent:
                    messagebox.showerror("Validation Error", "Continue Click Time values must be:\nHour: 0-23\nMinute: 0-59\nSecond: 0-59")
                return

            cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_config.json")
            data = {}
            if os.path.exists(cfg_file):
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            data["TARGET_BOOKING_HOUR"] = bh
            data["TARGET_BOOKING_MINUTE"] = bm
            data["TARGET_BOOKING_SECOND"] = bs
            data["TARGET_HOUR"] = th
            data["TARGET_MINUTE"] = tm
            data["TARGET_SECOND"] = ts
            data["ENABLE_SCHEDULING"] = bool(self.sched_enabled_var.get())
            data["BROWSERS_PER_FAMILY"] = b_fam

            # Automatically sync MAX_WORKERS = b_fam * active_families (so changing to 4 scales to 8)
            active_fams = 2
            try:
                import pandas as pd
                pdf = pd.read_excel('pilgrims_details.xlsx', dtype={'Group': str})
                if 'Status' in pdf.columns:
                    pdf = pdf[pdf['Status'].fillna('').astype(str).str.strip().str.upper() != 'PASSED']
                ug = [g for g in pdf['Group'].unique() if g and str(g) != 'nan']
                if ug:
                    active_fams = len(ug)
            except Exception:
                pass
            data["MAX_WORKERS"] = b_fam * active_fams

            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            if hasattr(self, 'lbl_save_status'):
                self.lbl_save_status.config(text=f"✅ Saved! Booking: {bh:02d}:{bm:02d}:{bs:02d} | Continue: {th:02d}:{tm:02d}:{ts:02d} | Browsers/Family: {b_fam}", foreground="#16a34a")
            self.log(f"⏱️ Timing & Concurrency updated: Booking={bh:02d}:{bm:02d}:{bs:02d}, Continue={th:02d}:{tm:02d}:{ts:02d}, Browsers/Family={b_fam}")
            if hasattr(self, 'lbl_browser_summary'):
                self.update_browser_summary(b_fam)
            if not silent:
                messagebox.showinfo("Timing Saved", f"Target Timings Saved!\n\nCurrent Booking: {bh:02d}:{bm:02d}:{bs:02d} IST\nContinue Click: {th:02d}:{tm:02d}:{ts:02d} IST\nBrowsers per Family: {b_fam}\nScheduling Enabled: {data['ENABLE_SCHEDULING']}\n\nAll browser workers will automatically use these settings.")
        except ValueError:
            if not silent:
                messagebox.showerror("Error", "Please enter valid numeric integer values for hours, minutes, and seconds.")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to save timing settings:\n{e}")

    def reset_timing_defaults(self):
        self.tb_h_var.set("09")
        self.tb_m_var.set("03")
        self.tb_s_var.set("00")
        self.tc_h_var.set("09")
        self.tc_m_var.set("03")
        self.tc_s_var.set("00")
        self.b_per_fam_var.set("1")
        self.sched_enabled_var.set(True)
        self.save_timing_config_from_ui()

    def tick_live_clock(self):
        try:
            now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
            self.lbl_live_clock.config(text=f"Current IST Time: {now_ist.strftime('%H:%M:%S')} (UTC+5:30)")

            try:
                bh = int(self.tb_h_var.get())
                bm = int(self.tb_m_var.get())
                bs = int(self.tb_s_var.get())
                target_ist = now_ist.replace(hour=bh, minute=bm, second=bs, microsecond=0)
                diff = (target_ist - now_ist).total_seconds()
                if diff > 0:
                    mins = int(diff // 60)
                    secs = int(diff % 60)
                    self.lbl_time_status.config(text=f"⏳ Target in {mins}m {secs}s ({target_ist.strftime('%H:%M:%S')} IST)", foreground="#0284c7")
                else:
                    self.lbl_time_status.config(text="⚡ Target time already passed today (workers will proceed immediately)", foreground="#16a34a")
            except Exception:
                pass
        except Exception:
            pass

        self.after(1000, self.tick_live_clock)

    # ---------------------------------------------------------
    # Database Query Handlers
    # ---------------------------------------------------------
    def refresh_all(self):
        self.refresh_families()
        self.refresh_logins()
        self.refresh_payments()
        self.update_browser_summary()

    def refresh_families(self):
        for item in self.family_tree.get_children():
            self.family_tree.delete(item)
        for item in self.pilgrims_tree.get_children():
            self.pilgrims_tree.delete(item)

        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, group_name, status, payment_method, target_date FROM family_groups ORDER BY id DESC;")
            for row in cur.fetchall():
                self.family_tree.insert("", tk.END, values=(
                    row["id"],
                    row["group_name"],
                    row["status"],
                    row["payment_method"],
                    row["target_date"] if row["target_date"] else "-"
                ))
            cur.close()
            conn.close()
        except Exception as e:
            self.log(f"Error fetching families: {e}")

    def on_family_selected(self, event):
        selected = self.family_tree.selection()
        if not selected:
            return
        item = self.family_tree.item(selected[0])
        group_id = item["values"][0]

        for p in self.pilgrims_tree.get_children():
            self.pilgrims_tree.delete(p)

        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT COALESCE(name, full_name) as name, age, gender, 
                       COALESCE(id_type, 'Aadhaar Card') as id_type, 
                       COALESCE(id_number, aadhar_number) as id_number
                FROM pilgrims WHERE group_id = %s ORDER BY id ASC LIMIT 4;
            """, (group_id,))
            for p in cur.fetchall():
                self.pilgrims_tree.insert("", tk.END, values=(
                    p["name"], p["age"], p["gender"], p["id_type"], p["id_number"]
                ))
            cur.close()
            conn.close()
        except Exception as e:
            self.log(f"Error fetching pilgrims: {e}")

    def refresh_logins(self):
        for item in self.logins_tree.get_children():
            self.logins_tree.delete(item)
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, email, password, status, created_at FROM logins ORDER BY id ASC;")
            for row in cur.fetchall():
                created = str(row["created_at"])[:19] if row["created_at"] else "-"
                self.logins_tree.insert("", tk.END, values=(
                    row["id"], row["email"], row["password"], row["status"], created
                ))
            cur.close()
            conn.close()
        except Exception as e:
            self.log(f"Error fetching logins: {e}")

    def refresh_payments(self):
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT fg.group_name, p.payment_type, p.upi_id, 
                       p.card_number, p.cardholder_name, p.payment_status, p.amount
                FROM payments p
                JOIN family_groups fg ON p.group_id = fg.id
                ORDER BY p.id DESC;
            """)
            for row in cur.fetchall():
                card_str = "-"
                if row["card_number"]:
                    cnum = str(row["card_number"])
                    card_str = f"•••• •••• •••• {cnum[-4:]}" if len(cnum) >= 4 else cnum
                    if row["cardholder_name"]:
                        card_str += f" ({row['cardholder_name']})"

                self.payments_tree.insert("", tk.END, values=(
                    row["group_name"],
                    row["payment_type"],
                    row["upi_id"] if row["upi_id"] else "-",
                    card_str,
                    row["payment_status"],
                    row["amount"] if row["amount"] else "-"
                ))
            cur.close()
            conn.close()
        except Exception as e:
            self.log(f"Error fetching payments: {e}")

    def open_add_family_dialog(self):
        AddFamilyDialog(self, self.refresh_all)

    def open_edit_family_dialog(self):
        selected = self.family_tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select a family group from the table to edit!")
            return
        item = self.family_tree.item(selected[0])
        group_id = item["values"][0]
        AddFamilyDialog(self, self.refresh_all, edit_group_id=group_id)

    def open_add_login_dialog(self):
        AddLoginDialog(self, self.refresh_logins)

    def delete_selected_family(self):
        selected = self.family_tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select a family group to delete!")
            return
        item = self.family_tree.item(selected[0])
        group_id = item["values"][0]
        group_name = item["values"][1]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete family '{group_name}' and all its pilgrims?"):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM family_groups WHERE id = %s;", (group_id,))
                conn.commit()
                cur.close()
                conn.close()
                self.refresh_all()
                messagebox.showinfo("Deleted", f"Family '{group_name}' has been deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete family: {e}")

    def delete_all_families(self):
        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete All Families",
            "Are you sure you want to delete ALL families, pilgrims, and payment details?\n\n"
            "This will permanently erase all passenger groups and cannot be undone!"
        )
        if not confirm:
            return

        final_check = messagebox.askyesno(
            "🚨 Final Warning",
            "This is your last chance.\n\nDelete all family groups, pilgrims, and payments permanently?"
        )
        if not final_check:
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE pilgrims, payments, active_sessions, family_groups RESTART IDENTITY CASCADE;")
            conn.commit()
            cur.close()
            conn.close()
            self.refresh_all()
            messagebox.showinfo("Deleted", "All families, pilgrims, and payment details have been deleted successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete all families: {e}")

    def delete_all_logins(self):
        confirm = messagebox.askyesno(
            "⚠️ Confirm Delete All Logins",
            "Are you sure you want to delete ALL login accounts from the database?\n\n"
            "This action cannot be undone!"
        )
        if not confirm:
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE logins RESTART IDENTITY CASCADE;")
            conn.commit()
            cur.close()
            conn.close()
            self.refresh_logins()
            messagebox.showinfo("Deleted", "All login accounts have been deleted successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete logins: {e}")

    def delete_entire_database(self):
        confirm = messagebox.askyesno(
            "⚠️ Wipe Entire Database",
            "Are you sure you want to wipe the ENTIRE database?\n\n"
            "This will delete ALL:\n"
            "• Families & Pilgrims\n"
            "• Payment configurations\n"
            "• Active sessions\n"
            "• Login accounts\n\n"
            "This action is IRREVERSIBLE!"
        )
        if not confirm:
            return

        final_check = messagebox.askyesno(
            "🚨 Final Warning - Database Wipe",
            "Are you absolutely sure you want to reset everything back to empty?"
        )
        if not final_check:
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE pilgrims, payments, active_sessions, family_groups, logins RESTART IDENTITY CASCADE;")
            conn.commit()
            cur.close()
            conn.close()
            self.refresh_all()
            messagebox.showinfo("Reset Complete", "The database has been completely wiped and reset to clean state.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to wipe database: {e}")

    def open_success_excel(self):
        try:
            import record_success
            record_success.sync_success_from_db()
        except Exception:
            pass
        succ_file = "successful_bookings.xlsx"
        if not os.path.exists(succ_file):
            messagebox.showinfo("No Records Yet", "No successful bookings recorded yet.\n\nOnce a booking is completed, records will be saved automatically to successful_bookings.xlsx.")
            return
        try:
            os.startfile(succ_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {succ_file}:\n{e}")

    def update_family_status(self, new_status):
        selected = self.family_tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select a family group first!")
            return
        item = self.family_tree.item(selected[0])
        group_id = item["values"][0]
        group_name = item["values"][1]
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE family_groups SET status = %s, updated_at = NOW() WHERE id = %s;", (new_status, group_id))
            conn.commit()
            cur.close()
            conn.close()
            self.refresh_families()
            if new_status == "PASSED":
                try:
                    import record_success
                    record_success.sync_success_from_db()
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update status: {e}")

    def delete_selected_login(self):
        selected = self.logins_tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select a login to delete!")
            return
        item = self.logins_tree.item(selected[0])
        login_id = item["values"][0]
        email = item["values"][1]

        if messagebox.askyesno("Confirm Delete", f"Delete login '{email}'?"):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM logins WHERE id = %s;", (login_id,))
                conn.commit()
                cur.close()
                conn.close()
                self.refresh_logins()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete login: {e}")

    def toggle_login_status(self):
        selected = self.logins_tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select a login first!")
            return
        item = self.logins_tree.item(selected[0])
        login_id = item["values"][0]
        curr_status = item["values"][3]
        new_status = "PASSED" if curr_status == "ACTIVE" else "ACTIVE"

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE logins SET status = %s WHERE id = %s;", (new_status, login_id))
            conn.commit()
            cur.close()
            conn.close()
            self.refresh_logins()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle status: {e}")

    def import_logins_from_excel(self):
        default_file = "user_details.xlsx" if os.path.exists("user_details.xlsx") else None
        filepath = filedialog.askopenfilename(
            title="Select Login Accounts Excel File",
            filetypes=[("Excel Files", "*.xlsx;*.xls"), ("All Files", "*.*")],
            initialdir=os.getcwd(),
            initialfile=default_file
        )
        if not filepath:
            return

        try:
            df = pd.read_excel(filepath)
            if df.empty:
                messagebox.showwarning("Empty File", "The selected Excel file is empty.")
                return

            def clean_val(v):
                if pd.isna(v):
                    return ""
                if isinstance(v, float) and v.is_integer():
                    return str(int(v)).strip()
                return str(v).strip()

            # Case-insensitive column search
            col_map = {str(c).strip().lower(): c for c in df.columns}

            email_col = None
            for cand in ["login_email", "login email", "email", "userid", "user_id", "user id", "username", "login", "user"]:
                if cand in col_map:
                    email_col = col_map[cand]
                    break

            pwd_col = None
            for cand in ["password", "pass", "pwd"]:
                if cand in col_map:
                    pwd_col = col_map[cand]
                    break

            status_col = None
            for cand in ["status", "state"]:
                if cand in col_map:
                    status_col = col_map[cand]
                    break

            if not email_col or not pwd_col:
                found_cols = ", ".join(df.columns.astype(str))
                messagebox.showerror(
                    "Missing Columns",
                    f"Could not identify login credentials in Excel columns.\n\n"
                    f"Expected columns: 'Login_Email' (or Email/User ID) and 'password'\n"
                    f"Found columns in file: {found_cols}"
                )
                return

            conn = get_db_connection()
            cur = conn.cursor()
            imported_count = 0

            for _, row in df.iterrows():
                email = clean_val(row.get(email_col, ""))
                pwd = clean_val(row.get(pwd_col, ""))
                status = clean_val(row.get(status_col, "ACTIVE")) if status_col else "ACTIVE"
                if not status or status.lower() == "nan":
                    status = "ACTIVE"
                status = status.upper()

                if email and email.lower() != "nan" and pwd and pwd.lower() != "nan":
                    cur.execute("""
                        INSERT INTO logins (email, password, status)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (email) DO UPDATE SET 
                            password = EXCLUDED.password, 
                            status = EXCLUDED.status;
                    """, (email, pwd, status))
                    imported_count += 1

            conn.commit()
            cur.close()
            conn.close()

            # Refresh GUI treeview
            self.refresh_logins()

            # Sync to local user_details.xlsx so Excel and DB remain identical
            try:
                import sync_db_to_excel
                sync_db_to_excel.sync()
            except Exception:
                pass

            self.log(f"📥 Imported/Updated {imported_count} login account(s) from '{os.path.basename(filepath)}'.")
            messagebox.showinfo(
                "Import Successful",
                f"✅ Successfully imported/updated {imported_count} login account(s)!\n\n"
                f"Source File: {os.path.basename(filepath)}\n"
                f"Database and user_details.xlsx are synchronized."
            )
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import logins from Excel:\n{str(e)}")

    def import_excel_to_db(self):
        if not os.path.exists("pilgrims_details.xlsx") and not os.path.exists("user_details.xlsx"):
            messagebox.showerror("Error", "Neither pilgrims_details.xlsx nor user_details.xlsx was found in project directory.")
            return

        if not messagebox.askyesno("Confirm Import", "Import all active records from pilgrims_details.xlsx and user_details.xlsx into PostgreSQL?"):
            return

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            imported_logins = 0
            imported_families = 0
            imported_pilgrims = 0

            # 1. Import Logins
            if os.path.exists("user_details.xlsx"):
                u_df = pd.read_excel("user_details.xlsx")
                for _, row in u_df.iterrows():
                    email = str(row.get("Login_Email", "")).strip()
                    pwd = str(row.get("password", "")).strip()
                    status = str(row.get("Status", "ACTIVE")).strip()
                    if email and email.lower() != "nan":
                        cur.execute("""
                            INSERT INTO logins (email, password, status)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, status = EXCLUDED.status;
                        """, (email, pwd, status))
                        imported_logins += 1

            # 2. Import Families (Max 4 per group)
            if os.path.exists("pilgrims_details.xlsx"):
                p_df = pd.read_excel("pilgrims_details.xlsx")
                groups = p_df["Group"].unique()
                for grp in groups:
                    grp_name = str(grp).strip()
                    if not grp_name or grp_name.lower() == "nan":
                        continue

                    grp_df = p_df[p_df["Group"] == grp].iloc[:4] # Enforce max 4 passengers
                    status = str(grp_df["Status"].iloc[0]).strip() if "Status" in grp_df.columns else "PENDING"
                    if not status or status.lower() == "nan":
                        status = "PENDING"

                    cur.execute("""
                        INSERT INTO family_groups (group_name, status, payment_method)
                        VALUES (%s, %s, 'UPI')
                        ON CONFLICT (group_name) DO UPDATE SET status = EXCLUDED.status
                        RETURNING id;
                    """, (grp_name, status))
                    group_id = cur.fetchone()[0]
                    imported_families += 1

                    cur.execute("DELETE FROM pilgrims WHERE group_id = %s;", (group_id,))

                    for _, p_row in grp_df.iterrows():
                        name = str(p_row.get("name", "")).strip()
                        age = int(p_row.get("age", 30))
                        gender = str(p_row.get("gender", "Male")).strip()
                        id_type = str(p_row.get("id_type", "Aadhaar Card")).strip()
                        id_num = str(p_row.get("id_number", "")).strip()

                        cur.execute("""
                            INSERT INTO pilgrims (group_id, name, full_name, age, gender, id_type, id_number, aadhar_number)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """, (group_id, name, name, age, gender, id_type, id_num, id_num))
                        imported_pilgrims += 1

                    cur.execute("""
                        INSERT INTO payments (group_id, payment_type, payment_status)
                        VALUES (%s, 'UPI', 'PENDING')
                        ON CONFLICT (group_id) DO NOTHING;
                    """, (group_id,))

            conn.commit()
            cur.close()
            conn.close()

            self.refresh_all()
            messagebox.showinfo("Import Complete", f"Successfully imported:\n• {imported_logins} Logins\n• {imported_families} Families\n• {imported_pilgrims} Pilgrims (capped to max 4/group)")

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import from Excel:\n{str(e)}")

    # ---------------------------------------------------------
    # Automation Runner Logic
    # ---------------------------------------------------------
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def open_logs_folder(self):
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        try:
            os.startfile(log_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open logs folder: {e}")

    def start_automation(self):
        try:
            b_fam = max(1, int(self.b_per_fam_var.get() or 1))
        except Exception:
            b_fam = 1

        # Auto-persist any pending change
        self.save_timing_config_from_ui(silent=True)

        if not messagebox.askyesno("Confirm Launch", f"Launch the automation workers with {b_fam} browser(s) per family?"):
            return

        self.notebook.select(self.tab_automation)
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.log(f"🚀 Starting Automation Process ({b_fam} browser(s) per family)...")
        threading.Thread(target=self.run_automation_thread, daemon=True).start()

    def stop_automation(self):
        if not messagebox.askyesno("Confirm Stop", "⚠️ Are you sure you want to STOP all running automation and browser workers?"):
            return

        self.log("🛑 Stopping automation and terminating all browser processes...")
        try:
            if hasattr(self, 'current_process') and self.current_process:
                self.current_process.terminate()
        except Exception:
            pass

        # Force kill chrome and chromedriver processes
        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log("🛑 Automation stopped.")

    def run_automation_thread(self):
        # Sync all active logins, families, and pilgrims from PostgreSQL to work files
        try:
            import sync_db_to_excel
            sync_db_to_excel.sync()
            self.after(0, self.log, "✅ Database synced to Excel work files.")
        except Exception as e:
            self.after(0, self.log, f"⚠️ Warning syncing database to work files: {e}")

        python_exe = sys.executable
        venv_py = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
        if os.path.exists(venv_py):
            python_exe = venv_py

        cmd = [python_exe, "launcher.py"]
        self.log(f"Executing: {' '.join(cmd)}")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                bufsize=1
            )
            for line in iter(self.current_process.stdout.readline, ''):
                self.after(0, self.log, line.rstrip())
            self.current_process.stdout.close()
            self.current_process.wait()
            ret = self.current_process.returncode
            self.after(0, self.log, f"Automation finished with return code {ret}")
            self.after(0, self.refresh_all)
        except Exception as e:
            self.after(0, self.log, f"❌ Execution error: {e}")
        finally:
            self.after(0, lambda: self.btn_start.config(state="normal"))
            self.after(0, lambda: self.btn_stop.config(state="disabled"))

if __name__ == "__main__":
    app = BookingControlCenter()
    app.mainloop()
