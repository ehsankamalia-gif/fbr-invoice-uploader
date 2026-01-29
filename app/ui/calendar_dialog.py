import customtkinter as ctk
import calendar
from datetime import datetime

class CalendarDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback, current_date=None):
        super().__init__(parent)
        self.callback = callback
        self.title("Select Date")
        self.geometry("340x350") # Slightly larger for comfort
        self.resizable(False, False)
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        # Center relative to parent
        try:
            x = parent.winfo_rootx() + 50
            y = parent.winfo_rooty() + 50
            self.geometry(f"+{x}+{y}")
        except:
            pass

        # Set initial month/year
        if current_date:
            try:
                self.year = current_date.year
                self.month = current_date.month
            except:
                now = datetime.now()
                self.year = now.year
                self.month = now.month
        else:
            now = datetime.now()
            self.year = now.year
            self.month = now.month
            
        self.setup_ui()
        self.draw_calendar()
        
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header (Month/Year and Nav)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.header.grid_columnconfigure(1, weight=1)
        
        self.btn_prev = ctk.CTkButton(self.header, text="<", width=40, command=self.prev_month)
        self.btn_prev.grid(row=0, column=0)
        
        self.lbl_month = ctk.CTkLabel(self.header, text="", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_month.grid(row=0, column=1)
        
        self.btn_next = ctk.CTkButton(self.header, text=">", width=40, command=self.next_month)
        self.btn_next.grid(row=0, column=2)
        
        # Calendar Grid
        self.cal_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cal_frame.grid(row=1, column=0, padx=15, pady=(0, 15))
        
    def draw_calendar(self):
        # Clear existing
        for widget in self.cal_frame.winfo_children():
            widget.destroy()
            
        # Days Header
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, day in enumerate(days):
            ctk.CTkLabel(self.cal_frame, text=day, width=40, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=2, pady=5)
            
        # Days
        cal = calendar.monthcalendar(self.year, self.month)
        today = datetime.now()
        
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day != 0:
                    # Highlight today
                    is_today = (day == today.day and self.month == today.month and self.year == today.year)
                    fg_color = "green" if is_today else "transparent"
                    border_width = 2 if is_today else 1
                    
                    btn = ctk.CTkButton(self.cal_frame, text=str(day), width=40, height=35, 
                                      fg_color=fg_color if is_today else ["#F9F9FA", "#343638"], # Light/Dark mode bg
                                      border_width=border_width,
                                      border_color=["gray70", "gray40"],
                                      text_color=("black", "white"),
                                      hover_color=["#E0E0E0", "#4A4A4A"],
                                      command=lambda d=day: self.select_date(d))
                    btn.grid(row=r+1, column=c, padx=2, pady=2)
                    
        self.lbl_month.configure(text=f"{calendar.month_name[self.month]} {self.year}")
        
    def prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.draw_calendar()
        
    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.draw_calendar()
        
    def select_date(self, day):
        date_str = f"{self.year}-{self.month:02d}-{day:02d}"
        self.callback(date_str)
        self.destroy()
