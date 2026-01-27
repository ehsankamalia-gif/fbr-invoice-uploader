import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, Menu
from datetime import datetime
import calendar
from app.services.spare_ledger_service import spare_ledger_service

class SpareLedgerFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow tabview to expand
        
        self.month_key_var = ctk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.type_filter = ctk.StringVar(value="All")
        self.min_amount = ctk.StringVar(value="")
        self.start_date = ctk.StringVar(value="")
        self.end_date = ctk.StringVar(value="")
        
        # Track open dialogs
        self.current_txn_dialog = None
        self.current_date_dialog = None

        # Global Header
        ctk.CTkLabel(self, text="Spare Parts Ledger", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.tabview.add("Transactions")
        self.tabview.add("Monthly Summary")
        
        # Build Transactions Tab
        self._build_transactions_tab()
        
        # Build Monthly Summary Tab
        self._build_monthly_summary_tab()
        
        self.refresh()

    def _build_transactions_tab(self):
        parent = self.tabview.tab("Transactions")
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1) # Tree expands

        # Month Filter (Top of Tab)
        self._build_month_filter(parent)
        
        # Summary Cards
        self._build_summary(parent)
        
        # Transaction Table + Filters
        self._build_table(parent)
        
        # Actions
        self._build_actions(parent)

    def _build_month_filter(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(frame, text="Select Month:").pack(side="left")
        self.month_entry = ctk.CTkEntry(frame, width=120, placeholder_text="YYYY-MM", textvariable=self.month_key_var)
        self.month_entry.pack(side="left", padx=5)
        ctk.CTkButton(frame, text="Load", width=80, command=self.refresh).pack(side="left", padx=5)

    def _build_summary(self, parent):
        self.summary_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.lbl_opening = ctk.CTkLabel(self.summary_frame, text="Opening: 0.00")
        self.lbl_credits = ctk.CTkLabel(self.summary_frame, text="Credits: 0.00")
        self.lbl_debits = ctk.CTkLabel(self.summary_frame, text="Debits: 0.00")
        self.lbl_closing = ctk.CTkLabel(self.summary_frame, text="Closing: 0.00", font=ctk.CTkFont(size=14, weight="bold"))
        for w in (self.lbl_opening, self.lbl_credits, self.lbl_debits, self.lbl_closing):
            w.pack(side="left", padx=15)

    def _build_table(self, parent):
        # Filter Bar
        filter_bar = ctk.CTkFrame(parent, fg_color="transparent")
        filter_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(10,5))
        
        ctk.CTkLabel(filter_bar, text="Type:").pack(side="left")
        ctk.CTkOptionMenu(filter_bar, values=["All","CREDIT","DEBIT"], variable=self.type_filter, command=lambda _: self.refresh()).pack(side="left", padx=5)
        ctk.CTkLabel(filter_bar, text="Min Amount:").pack(side="left")
        ctk.CTkEntry(filter_bar, width=100, textvariable=self.min_amount).pack(side="left", padx=5)
        ctk.CTkLabel(filter_bar, text="Start:").pack(side="left")
        self.start_btn = ctk.CTkButton(filter_bar, text=self._btn_date_text(self.start_date.get()), width=120, command=lambda: self._open_date_picker(self.start_date, self.start_btn))
        self.start_btn.pack(side="left", padx=5)
        ctk.CTkLabel(filter_bar, text="End:").pack(side="left")
        self.end_btn = ctk.CTkButton(filter_bar, text=self._btn_date_text(self.end_date.get()), width=120, command=lambda: self._open_date_picker(self.end_date, self.end_btn))
        self.end_btn.pack(side="left", padx=5)
        ctk.CTkButton(filter_bar, text="Apply", width=80, command=self.refresh).pack(side="left", padx=10)

        # Tree
        table_frame = ctk.CTkFrame(parent, fg_color="transparent")
        table_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        parent.grid_rowconfigure(3, weight=1)
        
        self.tree = ttk.Treeview(table_frame, columns=("date","type","desc","credit","debit","balance","ref"), show="headings")
        for col, text, width in (("date","Date",150),("type","Type",80),("desc","Description",250),("credit","Credit",100),("debit","Debit",100),("balance","Balance",120),("ref","Reference",160)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        
        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        # Context Menu
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self._on_edit_transaction)
        self.context_menu.add_command(label="Delete", command=self._on_delete_transaction)
        self.tree.bind("<Button-3>", self._show_context_menu)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _on_edit_transaction(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        # values: date, type, desc, credit, debit, balance, ref
        
        # Parse data
        dt_str = values[0]
        t_type = values[1]
        desc = values[2]
        credit = values[3]
        debit = values[4]
        ref = values[6]
        
        amount = float(credit) if credit else float(debit)
        
        data = {
            "id": int(item_id),
            "date": dt_str,
            "type": t_type,
            "description": desc,
            "amount": amount,
            "reference": ref
        }
        self._add_transaction_dialog(edit_mode=True, data=data)

    def _on_delete_transaction(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction?"):
            return
            
        try:
            spare_ledger_service.delete_transaction(int(item_id))
            self.refresh()
            messagebox.showinfo("Success", "Transaction deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _build_actions(self, parent):
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(actions, text="Add Transaction", command=self._add_transaction_dialog, fg_color="#2980B9", width=150).pack(side="left", padx=10)
        ctk.CTkButton(actions, text="Export CSV", command=self._export_csv).pack(side="right", padx=10)
        ctk.CTkButton(actions, text="Export HTML/PDF", command=self._export_html).pack(side="right", padx=10)
        ctk.CTkButton(actions, text="Close Month", command=self._close_month).pack(side="right", padx=10)

    def _build_monthly_summary_tab(self):
        parent = self.tabview.tab("Monthly Summary")
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
        table_frame = ctk.CTkFrame(parent, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.summary_tree = ttk.Treeview(table_frame, columns=("month","credits","debits","balance","remarks"), show="headings")
        self.summary_tree.heading("month", text="Closing Date")
        self.summary_tree.heading("credits", text="Total Credit")
        self.summary_tree.heading("debits", text="Total Debit")
        self.summary_tree.heading("balance", text="Balance")
        self.summary_tree.heading("remarks", text="Remarks")
        
        self.summary_tree.column("month", width=150, anchor="center")
        self.summary_tree.column("credits", width=120, anchor="center")
        self.summary_tree.column("debits", width=120, anchor="center")
        self.summary_tree.column("balance", width=120, anchor="center")
        self.summary_tree.column("remarks", width=250, anchor="center")
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=vsb.set)
        self.summary_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.summary_tree.bind("<<TreeviewSelect>>", self.ensure_visible_summary)


    def ensure_visible_txn(self, event):
        try:
            focus_item = self.tree.focus()
            if focus_item:
                self.tree.see(focus_item)
        except Exception:
            pass

    def ensure_visible_summary(self, event):
        try:
            focus_item = self.summary_tree.focus()
            if focus_item:
                self.summary_tree.see(focus_item)
        except Exception:
            pass


    def _add_transaction_dialog(self, edit_mode=False, data=None):
        if self.current_txn_dialog is not None and self.current_txn_dialog.winfo_exists():
            self.current_txn_dialog.lift()
            self.current_txn_dialog.focus()
            return

        dialog = ctk.CTkToplevel(self)
        self.current_txn_dialog = dialog
        dialog.title("Edit Transaction" if edit_mode else "Add Transaction")
        dialog.geometry("400x450")
        dialog.attributes("-topmost", True)
        
        # Cleanup reference on close
        def on_close():
            self.current_txn_dialog = None
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # Date
        ctk.CTkLabel(dialog, text="Date").pack(pady=(10,5))
        
        initial_date = datetime.now()
        if edit_mode and data:
            try:
                # data['date'] format YYYY-MM-DD HH:MM
                initial_date = datetime.strptime(data['date'], "%Y-%m-%d %H:%M")
            except:
                pass
                
        now_str = initial_date.strftime("%Y-%m-%d")
        date_var = ctk.StringVar(value=now_str)
        date_btn = ctk.CTkButton(dialog, text=now_str, width=200, fg_color="transparent", border_width=1, text_color=("black", "white"))
        date_btn.configure(command=lambda: self._open_date_picker(date_var, date_btn))
        date_btn.pack()

        # Reference
        ctk.CTkLabel(dialog, text="Reference").pack(pady=(10,5))
        ref_var = ctk.StringVar(value=data['reference'] if edit_mode and data else "")
        ref_entry = ctk.CTkEntry(dialog, textvariable=ref_var, width=200)
        ref_entry.pack()

        # Description
        ctk.CTkLabel(dialog, text="Description").pack(pady=(10,5))
        desc_var = ctk.StringVar(value=data['description'] if edit_mode and data else "")
        desc_entry = ctk.CTkEntry(dialog, textvariable=desc_var, width=200)
        desc_entry.pack()
        
        # Bind Reference Enter -> Focus Description
        ref_entry.bind("<Return>", lambda e: desc_entry.focus())

        # Type (Radio)
        ctk.CTkLabel(dialog, text="Transaction Type").pack(pady=(15,5))
        type_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        type_frame.pack()
        type_var = ctk.StringVar(value=data['type'] if edit_mode and data else "CREDIT")
        
        def toggle_amount_fields():
            t = type_var.get()
            if t == "CREDIT":
                debit_frame.pack_forget()
                credit_frame.pack(pady=10, after=type_frame)
            else:
                credit_frame.pack_forget()
                debit_frame.pack(pady=10, after=type_frame)

        r1 = ctk.CTkRadioButton(type_frame, text="Credit (Deposit)", variable=type_var, value="CREDIT", command=toggle_amount_fields)
        r1.pack(side="left", padx=10)
        r2 = ctk.CTkRadioButton(type_frame, text="Debit (Order)", variable=type_var, value="DEBIT", command=toggle_amount_fields)
        r2.pack(side="left", padx=10)

        # Amount Fields (Container Frames)
        # Credit Field
        credit_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        ctk.CTkLabel(credit_frame, text="Credit Amount").pack()
        credit_amt_var = ctk.StringVar(value=str(data['amount']) if edit_mode and data and data['type'] == 'CREDIT' else "")
        credit_entry = ctk.CTkEntry(credit_frame, textvariable=credit_amt_var, width=200)
        credit_entry.pack()

        # Debit Field
        debit_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        ctk.CTkLabel(debit_frame, text="Debit Amount").pack()
        debit_amt_var = ctk.StringVar(value=str(data['amount']) if edit_mode and data and data['type'] == 'DEBIT' else "")
        debit_entry = ctk.CTkEntry(debit_frame, textvariable=debit_amt_var, width=200)
        debit_entry.pack()

        # Initial State
        toggle_amount_fields()

        def save():
            try:
                # Parse Date
                dt = datetime.strptime(date_var.get(), "%Y-%m-%d")
                # Use preserved time if editing and date hasn't changed, or just keep time component?
                # Simplification: If date matches original date (YY-MM-DD), keep original time. Else use current time.
                if edit_mode and data:
                    orig_dt = datetime.strptime(data['date'], "%Y-%m-%d %H:%M")
                    if dt.date() == orig_dt.date():
                        dt = dt.replace(hour=orig_dt.hour, minute=orig_dt.minute, second=orig_dt.second)
                    else:
                        now = datetime.now()
                        dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second)
                else:
                    now = datetime.now()
                    dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second)

                t_type = type_var.get()
                amt_str = credit_amt_var.get() if t_type == "CREDIT" else debit_amt_var.get()
                if not amt_str:
                    raise ValueError("Amount is required")
                amt = float(amt_str)

                if edit_mode:
                    spare_ledger_service.update_transaction(
                        txn_id=data['id'],
                        amount=amt,
                        reference=ref_var.get(),
                        description=desc_var.get(),
                        trans_type=t_type,
                        timestamp=dt
                    )
                    messagebox.showinfo("Success", "Transaction updated.", parent=dialog)
                    on_close() # Close dialog on update
                else:
                    if t_type == "CREDIT":
                        spare_ledger_service.add_credit(amt, ref_var.get(), desc_var.get(), timestamp=dt)
                    else:
                        spare_ledger_service.add_debit(amt, ref_var.get(), desc_var.get(), timestamp=dt)
                    
                    # Clear fields for next entry (except date)
                    credit_amt_var.set("")
                    debit_amt_var.set("")
                    ref_var.set("")
                    desc_var.set("")
                    messagebox.showinfo("Success", "Transaction added successfully.", parent=dialog)
                
                self.refresh()
                # Optional: focus back to amount or reference
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        # Bind Enter on Amount fields to Save
        credit_entry.bind("<Return>", lambda e: save())
        debit_entry.bind("<Return>", lambda e: save())

        # Bind Enter on Description -> Focus Amount
        def focus_amount(_):
            if type_var.get() == "CREDIT":
                credit_entry.focus()
            else:
                debit_entry.focus()
        desc_entry.bind("<Return>", focus_amount)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=20)
        ctk.CTkButton(btn_frame, text="Update Transaction" if edit_mode else "Save Transaction", command=save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Close", command=on_close, fg_color="#C0392B").pack(side="left", padx=10)

    def refresh(self):
        try:
            # --- 1. Transactions Tab ---
            month_key = self.month_key_var.get().strip()
            # Summary
            summary = spare_ledger_service.calculate_month_summary(month_key)
            self.lbl_opening.configure(text=f"Opening: {summary['opening_balance']:.2f}")
            self.lbl_credits.configure(text=f"Credits: {summary['total_credits']:.2f}")
            self.lbl_debits.configure(text=f"Debits: {summary['total_debits']:.2f}")
            self.lbl_closing.configure(text=f"Closing: {summary['closing_balance']:.2f}")

            # Table
            for i in self.tree.get_children():
                self.tree.delete(i)
            rows = spare_ledger_service.get_running_balance(month_key)
            # Filters
            t_filter = self.type_filter.get()
            min_amt = self._parse_amount(self.min_amount.get())
            s_date = self._parse_date(self.start_date.get())
            e_date = self._parse_date(self.end_date.get(), end=True)

            for t, bal in rows:
                if t_filter != "All" and t.trans_type != t_filter:
                    continue
                if min_amt is not None and t.amount < min_amt:
                    continue
                if s_date and t.timestamp < s_date:
                    continue
                if e_date and t.timestamp > e_date:
                    continue
                credit_val = f"{t.amount:.2f}" if t.trans_type == "CREDIT" else ""
                debit_val = f"{t.amount:.2f}" if t.trans_type == "DEBIT" else ""
                self.tree.insert("", "end", iid=str(t.id), values=(
                    t.timestamp.strftime("%Y-%m-%d %H:%M"),
                    t.trans_type,
                    t.description or "",
                    credit_val,
                    debit_val,
                    f"{bal:.2f}",
                    t.reference_number or ""
                ))

            # --- 2. Monthly Summary Tab ---
            for i in self.summary_tree.get_children():
                self.summary_tree.delete(i)
            
            monthly_summaries = spare_ledger_service.get_all_months_summary()
            for rec in monthly_summaries:
                self.summary_tree.insert("", "end", values=(
                    rec["month_label"],
                    f"{rec['total_credits']:.2f}",
                    f"{rec['total_debits']:.2f}",
                    f"{rec['balance']:.2f}",
                    rec["status"]
                ))

        except Exception as e:
            messagebox.showerror("Ledger Error", str(e))

    def _parse_amount(self, txt: str):
        try:
            txt = (txt or "").strip()
            return float(txt) if txt else None
        except ValueError:
            return None

    def _parse_date(self, txt: str, end: bool = False):
        try:
            txt = (txt or "").strip()
            if not txt:
                return None
            dt = datetime.strptime(txt, "%Y-%m-%d")
            if end:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            return None

    def _btn_date_text(self, val: str) -> str:
        return val if val else "Select Date"

    def _open_date_picker(self, target_var: ctk.StringVar, target_btn: ctk.CTkButton):
        if self.current_date_dialog is not None and self.current_date_dialog.winfo_exists():
            self.current_date_dialog.destroy()

        dlg = ctk.CTkToplevel(self)
        self.current_date_dialog = dlg
        dlg.title("Select Date")
        dlg.geometry("300x350")
        dlg.attributes("-topmost", True)
        
        def on_close():
            self.current_date_dialog = None
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", on_close)

        now = datetime.now()
        year_var = ctk.IntVar(value=now.year)
        month_var = ctk.IntVar(value=now.month)

        header = ctk.CTkFrame(dlg)
        header.pack(fill="x", pady=5)
        def refresh_calendar():
            for w in cal_frame.winfo_children():
                w.destroy()
            mtx = calendar.monthcalendar(year_var.get(), month_var.get())
            days_row = ctk.CTkFrame(cal_frame)
            days_row.pack()
            for d in ["Mo","Tu","We","Th","Fr","Sa","Su"]:
                ctk.CTkLabel(days_row, text=d, width=28).pack(side="left", padx=2)
            for week in mtx:
                row = ctk.CTkFrame(cal_frame)
                row.pack()
                for day in week:
                    txt = "" if day == 0 else str(day)
                    btn = ctk.CTkButton(row, text=txt or " ", width=28,
                                        command=(lambda d=day: select_day(d)) if day != 0 else None)
                    btn.pack(side="left", padx=2, pady=2)

        def select_day(day: int):
            date_str = f"{year_var.get():04d}-{month_var.get():02d}-{day:02d}"
            target_var.set(date_str)
            target_btn.configure(text=self._btn_date_text(date_str))
            on_close()

        ctk.CTkButton(header, text="<", width=40, command=lambda: self._shift_month(month_var, year_var, -1, refresh_calendar)).pack(side="left", padx=5)
        ctk.CTkLabel(header, text=" ").pack(side="left")
        header_lbl = ctk.CTkLabel(header, text=f"{calendar.month_name[month_var.get()]} {year_var.get()}")
        header_lbl.pack(side="left", padx=10)
        ctk.CTkButton(header, text=">", width=40, command=lambda: self._shift_month(month_var, year_var, 1, refresh_calendar)).pack(side="right", padx=5)

        cal_frame = ctk.CTkFrame(dlg)
        cal_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Manual Entry
        manual_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        manual_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(manual_frame, text="Or enter date:").pack(side="left", padx=5)
        manual_entry = ctk.CTkEntry(manual_frame, placeholder_text="YYYY-MM-DD")
        manual_entry.pack(side="left", fill="x", expand=True, padx=5)
        if target_var.get():
            manual_entry.insert(0, target_var.get())
            
        def manual_save(event=None):
            try:
                txt = manual_entry.get().strip()
                # Handle YYYYMMDD format
                if len(txt) == 8 and txt.isdigit():
                    txt = f"{txt[:4]}-{txt[4:6]}-{txt[6:]}"
                
                datetime.strptime(txt, "%Y-%m-%d") # Validate format
                target_var.set(txt)
                target_btn.configure(text=self._btn_date_text(txt))
                on_close()
            except ValueError:
                messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD or YYYYMMDD format", parent=dlg)

        manual_entry.bind("<Return>", manual_save)
        ctk.CTkButton(manual_frame, text="Set", width=50, command=manual_save).pack(side="right", padx=5)
        
        # Hook into refresh to update label
        original_refresh = refresh_calendar
        def refresh_wrapper():
            header_lbl.configure(text=f"{calendar.month_name[month_var.get()]} {year_var.get()}")
            original_refresh()
        
        # Re-bind buttons to use wrapper
        for child in header.winfo_children():
            if isinstance(child, ctk.CTkButton):
                if child.cget("text") == "<":
                    child.configure(command=lambda: self._shift_month(month_var, year_var, -1, refresh_wrapper))
                elif child.cget("text") == ">":
                    child.configure(command=lambda: self._shift_month(month_var, year_var, 1, refresh_wrapper))

        refresh_wrapper()

    def _shift_month(self, m_var: ctk.IntVar, y_var: ctk.IntVar, delta: int, refresh_cb):
        m = m_var.get() + delta
        y = y_var.get()
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        m_var.set(m)
        y_var.set(y)
        refresh_cb()



    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path:
            return
        ok = spare_ledger_service.export_month_csv(self.month_key_var.get().strip(), path)
        if ok:
            messagebox.showinfo("Export", "CSV exported successfully.")

    def _export_html(self):
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML","*.html")])
        if not path:
            return
        ok = spare_ledger_service.export_month_html(self.month_key_var.get().strip(), path)
        if ok:
            messagebox.showinfo("Export", "HTML exported. Open in browser and print to PDF if needed.")

    def _close_month(self):
        try:
            mk = self.month_key_var.get().strip()
            rec = spare_ledger_service.close_month(mk)
            messagebox.showinfo("Monthly Close", f"Closed {rec.month_key}. Closing balance: {rec.closing_balance:.2f}\nCarried forward to next month.")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Close Error", str(e))
