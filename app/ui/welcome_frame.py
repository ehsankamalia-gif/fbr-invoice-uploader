import customtkinter as ctk

class WelcomeFrame(ctk.CTkFrame):
    def __init__(self, master, start_callback):
        super().__init__(master, fg_color=("gray95", "gray10"))
        self.start_callback = start_callback
        
        # Configure grid for centering
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Top spacer
        self.grid_rowconfigure(2, weight=1) # Bottom spacer
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0)
        
        # Branding
        self.title_label = ctk.CTkLabel(self.content_frame, text="HONDA", 
                                      font=ctk.CTkFont(family="Arial", size=64, weight="bold"),
                                      text_color=("#C0392B", "#E74C3C"))
        self.title_label.pack(pady=(0, 10))
        
        self.subtitle_label = ctk.CTkLabel(self.content_frame, text="FBR INVOICE INTEGRATION SYSTEM", 
                                         font=ctk.CTkFont(size=24, weight="bold"),
                                         text_color=("gray40", "gray60"))
        self.subtitle_label.pack(pady=(0, 50))
        
        # Features / Info
        features = [
            "✅ Automated Invoice Uploads",
            "✅ Secure FBR Integration",
            "✅ Real-time Validation",
            "✅ Offline Mode Support"
        ]
        
        for feature in features:
            l = ctk.CTkLabel(self.content_frame, text=feature,
                           font=ctk.CTkFont(size=16),
                           text_color=("gray30", "gray70"))
            l.pack(pady=5)

        # Start Button
        self.start_button = ctk.CTkButton(self.content_frame, text="Get Started", 
                                        command=self.start_callback,
                                        font=ctk.CTkFont(size=20, weight="bold"),
                                        height=60, width=250,
                                        corner_radius=30,
                                        fg_color="#C0392B", hover_color="#E74C3C")
        self.start_button.pack(pady=(60, 20))
        
        # Version/Footer
        self.footer_label = ctk.CTkLabel(self, text="© 2025 Honda Center | v1.0.0", 
                                       font=ctk.CTkFont(size=12),
                                       text_color="gray50")
        self.footer_label.grid(row=3, column=0, pady=20)
