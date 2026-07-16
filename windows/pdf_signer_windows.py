import os, json, subprocess, threading, gc, shutil, tkinter as tk
from tkinter import filedialog, messagebox
from fitz import Document, Matrix
from PIL import Image, ImageTk

# --- CONFIGURATION DES CHEMINS (VERSION WINDOWS) ---
LIB_BEID = r"C:\Windows\System32\beidpkcs11.dll"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "pdf_signer_config.json")

class PDFSignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Signateur et Trieur PDF eID Windows - v1.0.3")
        try: self.root.state('zoomed')
        except tk.TclError: pass

        # Variables de l'application
        self.input_dir, self.output_dir, self.reject_dir, self.pdf_list = "", "", "", []
        self.current_file, self.tk_img, self.zoom_factor = "", None, 1.3
        self.last_selected_index, self.current_page_num = 0, 0
        self.fichiers_signes_session = set()
        self.dark_mode = False

        # Variables Tkinter persistantes
        self.var_delete_source = tk.IntVar(value=0)
        self.var_dark_mode = tk.IntVar(value=0)

        # --- BARRE SUPÉRIEURE ÉPURÉE (Ligne unique) ---
        self.top_frame = tk.Frame(root, pady=10, padx=10)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Marge à gauche égale à la largeur du volet (250px + 15px de décalage)
        self.lbl_info_nav = tk.Label(self.top_frame, text="Page 0/0  |  Zoom (Ctrl scroll) : 130%", font=('Arial', 10, 'bold'), fg="gray")
        self.lbl_info_nav.pack(side=tk.LEFT, padx=(265, 10))

        # Boutons alignés à droite
        self.btn_about = tk.Button(self.top_frame, text="À propos", command=self.show_about, font=('Arial', 9, 'italic'))
        self.btn_about.pack(side=tk.RIGHT, padx=5)

        self.btn_config = tk.Button(self.top_frame, text="⚙️ Paramètres", command=self.open_settings, font=('Arial', 10, 'bold'), padx=10)
        self.btn_config.pack(side=tk.RIGHT, padx=5)

        # --- PANNEAU CENTRAL ---
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.left_frame = tk.Frame(self.main_frame, width=250)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.left_frame.pack_propagate(False)
        
        self.lbl_docs_txt = tk.Label(self.left_frame, text="Documents disponibles :", font=('Arial', 10, 'bold'))
        self.lbl_docs_txt.pack(anchor="w", pady=2)
        
        self.list_scroll = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL)
        self.list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(self.left_frame, yscrollcommand=self.list_scroll.set, font=('Arial', 10))
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_scroll.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self.on_pdf_select)
        self.listbox.bind('<KeyRelease-Up>', self.on_keyboard_navigation)
        self.listbox.bind('<KeyRelease-Down>', self.on_keyboard_navigation)
        
        # Raccourcis clavier de navigation purs et validés
        self.root.bind('<Return>', lambda e: self.on_enter_pressed())
        self.root.bind('<Left>', lambda e: self.change_page(-1))
        self.root.bind('<Right>', lambda e: self.change_page(1))

        self.preview_frame = tk.Frame(self.main_frame, bg="darkgray")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.v_scroll = tk.Scrollbar(self.preview_frame, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll = tk.Scrollbar(self.preview_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(self.preview_frame, bg="white", yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.config(command=self.canvas.xview)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # --- PANNEAU ACTIONS (BAS) ---
        self.bottom_frame = tk.Frame(root, pady=10)
        self.status_bar = tk.Label(root, text="Prêt", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=('Arial', 10), bg="#f0f0f0", pady=5, padx=10)
        
        # FIX EN Y : On pack la barre de statut EN PREMIER pour qu'elle prenne le fond absolu
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_sign = tk.Button(self.bottom_frame, text="Signer le document", command=self.sign_current_pdf, bg="#4CAF50", fg="white", activebackground="#45A049", activeforeground="white", disabledforeground="#aaaaaa", font=('Arial', 11, 'bold'), state=tk.DISABLED, height=2, width=22)
        self.btn_sign.pack(side=tk.RIGHT, padx=20)

        self.btn_reject = tk.Button(self.bottom_frame, text="Refuser le document", command=self.reject_current_pdf, bg="#F44336", fg="white", activebackground="#D32F2F", activeforeground="white", disabledforeground="#aaaaaa", font=('Arial', 11, 'bold'), state=tk.DISABLED, height=2, width=22)
        self.btn_reject.pack(side=tk.RIGHT, padx=5)

        self.load_config()

    def open_settings(self):
        """Ouvre un pop-up de configuration avec isolation stricte Valider/Annuler et le Mode Sombre intégré"""
        win = tk.Toplevel(self.root)
        win.title("Paramètres de l'application")
        win.geometry("680x280")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        bg = "#212121" if self.dark_mode else "#f0f0f0"
        fg = "#FFFFFF" if self.dark_mode else "#000000"
        btn_bg = "#2D2D2D" if self.dark_mode else "#e8e8e8"
        win.config(bg=bg)

        # Variables temporaires locales pour isoler les choix
        self.tmp_in, self.tmp_out, self.tmp_rej = self.input_dir, self.output_dir, self.reject_dir
        self.tmp_delete = tk.IntVar(value=self.var_delete_source.get())
        self.tmp_dark = tk.IntVar(value=self.var_dark_mode.get())

        def select_dir(slot, label_obj):
            current_init = {"in": self.tmp_in, "out": self.tmp_out, "rej": self.tmp_rej}[slot]
            d = filedialog.askdirectory(title="Choisir le dossier", initialdir=current_init if current_init else None)
            if d:
                if slot == 'in': self.tmp_in = d
                elif slot == 'out': self.tmp_out = d
                elif slot == 'rej': self.tmp_rej = d
                label_obj.config(text=d, fg=fg)

        # Grille des dossiers
        tk.Button(win, text="Parcourir...", command=lambda: select_dir('in', lbl_in), bg=btn_bg, fg=fg).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        tk.Label(win, text="Dossier Source :", font=('Arial', 9, 'bold'), bg=bg, fg=fg).grid(row=0, column=1, sticky="w")
        lbl_in = tk.Label(win, text=self.tmp_in if self.tmp_in else "Aucun", fg="gray" if not self.tmp_in else fg, bg=bg, anchor="w", width=45)
        lbl_in.grid(row=0, column=2, padx=5, sticky="w")

        tk.Button(win, text="Parcourir...", command=lambda: select_dir('out', lbl_out), bg=btn_bg, fg=fg).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        tk.Label(win, text="Dossier Cible (Signés) :", font=('Arial', 9, 'bold'), bg=bg, fg=fg).grid(row=1, column=1, sticky="w")
        lbl_out = tk.Label(win, text=self.tmp_out if self.tmp_out else "Aucun", fg="gray" if not self.tmp_out else fg, bg=bg, anchor="w", width=45)
        lbl_out.grid(row=1, column=2, padx=5, sticky="w")

        tk.Button(win, text="Parcourir...", command=lambda: select_dir('rej', lbl_rej), bg=btn_bg, fg=fg).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        tk.Label(win, text="Dossier Rejet (Refusés) :", font=('Arial', 9, 'bold'), bg=bg, fg=fg).grid(row=2, column=1, sticky="w")
        lbl_rej = tk.Label(win, text=self.tmp_rej if self.tmp_rej else "Aucun", fg="gray" if not self.tmp_rej else fg, bg=bg, anchor="w", width=45)
        lbl_rej.grid(row=2, column=2, padx=5, sticky="w")

        chk_del = tk.Checkbutton(win, text="Supprimer le fichier source après traitement", variable=self.tmp_delete, font=('Arial', 9, 'bold'), fg="#D32F2F" if not self.dark_mode else "#FF5252", bg=bg, selectcolor="#333333" if self.dark_mode else "#FFFFFF")
        chk_del.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        chk_dk = tk.Checkbutton(win, text="Activer le Mode Sombre de l'application 🌙", variable=self.tmp_dark, font=('Arial', 9, 'bold'), bg=bg, fg=fg, selectcolor="#333333" if self.dark_mode else "#FFFFFF")
        chk_dk.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        # Validation propre alignée à droite (marge fine de 20px)
        actions_panel = tk.Frame(win, bg=bg)
        actions_panel.grid(row=5, column=0, columnspan=3, pady=15, sticky="e", padx=20)

        def save_and_close():
            self.input_dir, self.output_dir, self.reject_dir = self.tmp_in, self.tmp_out, self.tmp_rej
            self.var_delete_source.set(self.tmp_delete.get())
            if self.var_dark_mode.get() != self.tmp_dark.get():
                self.var_dark_mode.set(self.tmp_dark.get())
                self.toggle_theme()
            self.fichiers_signes_session.clear()
            self.save_config_auto()
            self.refresh_pdf_list()
            win.destroy()

        tk.Button(actions_panel, text="Annuler", command=win.destroy, font=('Arial', 9, 'bold'), width=12, bg="#757575", fg="white", activebackground="#616161", activeforeground="white").pack(side=tk.RIGHT, padx=5)
        tk.Button(actions_panel, text="Valider", command=save_and_close, font=('Arial', 9, 'bold'), width=12, bg="#4CAF50", fg="white", activebackground="#45A049", activeforeground="white").pack(side=tk.RIGHT, padx=5)

    def toggle_theme(self):
        self.dark_mode = (self.var_dark_mode.get() == 1)
        bg = "#212121" if self.dark_mode else "#f0f0f0"
        fg = "#FFFFFF" if self.dark_mode else "#000000"
        pane_bg = "#2D2D2D" if self.dark_mode else "#f0f0f0"
        box_bg = "#333333" if self.dark_mode else "#FFFFFF"
        box_fg = "#FFFFFF" if self.dark_mode else "#000000"

        self.root.config(bg=bg)
        for f in [self.top_frame, self.main_frame, self.left_frame, self.bottom_frame]: f.config(bg=bg)
        
        self.lbl_info_nav.config(bg=bg, fg=fg if self.current_file else "gray")
        self.lbl_docs_txt.config(bg=bg, fg=fg)
        self.listbox.config(bg=box_bg, fg=box_fg, selectbackground="#4CAF50")
        self.status_bar.config(bg=pane_bg, fg=fg)
        
        for btn in [self.btn_about, self.btn_config]: btn.config(bg=pane_bg, fg=fg)
        self.save_config_auto()
    def load_config(self):
        """Charge l'historique et applique le thème au démarrage de manière synchronisée"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.input_dir = data.get("input_dir", "")
                    self.output_dir = data.get("output_dir", "")
                    self.reject_dir = data.get("reject_dir", "")
                    self.var_delete_source.set(data.get("delete_source", 0))
                    self.var_dark_mode.set(data.get("dark_mode", 0))
                    
                    # CORRECTION : On rafraîchit la liste et les dossiers AVANT d'appliquer le thème
                    if self.input_dir and os.path.exists(self.input_dir):
                        self.refresh_pdf_list()
                    
                    # On applique le thème graphique en tout dernier pour ne pas casser le Canvas Windows
                    if self.var_dark_mode.get() == 1:
                        self.root.after(50, self.toggle_theme)
            except: pass

    def save_config_auto(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "input_dir": self.input_dir, "output_dir": self.output_dir, "reject_dir": self.reject_dir,
                    "delete_source": self.var_delete_source.get(), "dark_mode": self.var_dark_mode.get()
                }, f, ensure_ascii=False, indent=4)
        except: pass

    def on_mouse_wheel(self, event):
        """Molette robuste sous Windows (Défilement et saut de page fluide)"""
        direction = -1 if event.delta > 0 else 1
        if (event.state & 0x0004):
            self.adjust_zoom(0.2 if direction == -1 else -0.2)
            return

        y_top, y_bottom = self.v_scroll.get()
        if direction == 1 and y_bottom >= 1.0:
            if hasattr(self, 'current_doc') and self.current_page_num < len(self.current_doc) - 1:
                self.change_page(1); self.root.after(10, lambda: self.canvas.yview_moveto(0.0))
        elif direction == -1 and y_top <= 0.0:
            if self.current_page_num > 0:
                self.change_page(-1); self.root.after(10, lambda: self.canvas.yview_moveto(1.0))
        else:
            self.canvas.yview_scroll(direction, "units")

    def on_enter_pressed(self):
        if self.btn_sign.cget('state') == tk.NORMAL: self.sign_current_pdf()

    def on_keyboard_navigation(self, event): self.on_pdf_select(None)

    def show_about(self):
        texte = "Signateur et Trieur PDF eID Windows - v1.0.3\n\nInterface épurée et validation stricte des paramètres.\n\nDéveloppé par info@tmaes.be avec l'aide de son IA."
        messagebox.showinfo("À propos", texte)

    def refresh_pdf_list(self):
        self.listbox.delete(0, tk.END)
        if self.input_dir and os.path.exists(self.input_dir):
            brut_list = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.pdf')]
            self.pdf_list = [f for f in brut_list if not f.lower().endswith('_signe.pdf') and f not in self.fichiers_signes_session]
            for pdf in self.pdf_list: self.listbox.insert(tk.END, pdf)
        self.check_ready_to_sign()

    def check_ready_to_sign(self):
        pret = tk.NORMAL if self.input_dir and self.output_dir and self.reject_dir and self.current_file else tk.DISABLED
        self.btn_sign.config(state=pret)
        self.btn_reject.config(state=pret)

    def on_pdf_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.last_selected_index = int(selection) if isinstance(selection, (tuple, list)) else int(selection)
            self.current_file = self.listbox.get(self.last_selected_index)
            self.current_page_num = 0
            self.render_pdf_preview(os.path.join(self.input_dir, self.current_file))
            self.check_ready_to_sign()
            self.clear_status_message()
    def change_page(self, delta):
        if hasattr(self, 'current_doc') and self.current_doc:
            total_pages = len(self.current_doc)
            nouvelle_page = self.current_page_num + delta
            if 0 <= nouvelle_page < total_pages:
                self.current_page_num = nouvelle_page
                self.render_pdf_preview(os.path.join(self.input_dir, self.current_file))

    def adjust_zoom(self, delta):
        new_zoom = self.zoom_factor + delta
        if 0.5 <= new_zoom <= 3.0 and self.current_file:
            self.zoom_factor = new_zoom
            self.render_pdf_preview(os.path.join(self.input_dir, self.current_file))

    def render_pdf_preview(self, pdf_path):
        try:
            self.tk_img = None
            gc.collect()
            self.current_doc = Document(pdf_path)
            total_pages = len(self.current_doc)
            
            zoom_pct = int(self.zoom_factor * 100)
            self.lbl_info_nav.config(text=f"Page {self.current_page_num + 1}/{total_pages}  |  Zoom (Ctrl scroll) : {zoom_pct}%", fg="#FFFFFF" if self.dark_mode else "black")
            
            page = self.current_doc.load_page(self.current_page_num)
            pix = page.get_pixmap(matrix=Matrix(self.zoom_factor, self.zoom_factor))
            
            # PASSAGE OBLIGATOIRE WINDOWS : Décodage par flux d'octets bruts de l'image
            img_data = bytes(pix.samples)
            img = Image.frombytes("RGBA" if pix.alpha else "RGB", [pix.width, pix.height], img_data)
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            self.canvas.yview_moveto(0)
        except Exception as e: messagebox.showerror("Erreur", f"Erreur de lecture :\n{str(e)}")

    def sign_current_pdf(self):
        if not self.current_file: return
        # FIX LOGIQUE TEXTE : C'est bien le bouton vert qui bascule son étiquette en attente
        self.btn_sign.config(state=tk.DISABLED, text="Connexion à l'eID...")
        self.btn_reject.config(state=tk.DISABLED)
        self.show_status_message("Veuillez valider votre code PIN sur la fenêtre eID...", bg_color="#FFC107", fg_color="black")
        self.root.update()
        threading.Thread(target=self._execute_signature_thread, daemon=True).start()

    def _execute_signature_thread(self):
        try:
            f_nom = self.current_file
            i_path = os.path.join(self.input_dir, f_nom)
            base, ext = os.path.splitext(f_nom)
            
            if os.path.abspath(self.input_dir) == os.path.abspath(self.output_dir):
                o_path = os.path.join(self.output_dir, f"{base}_signe{ext}")
                msg_fin = f"Sauvegarde de sécurité : '{base}_signe{ext}' créé dans le même dossier."
            else:
                o_path = os.path.join(self.output_dir, f_nom)
                msg_fin = f"Succès : '{f_nom}' signé et enregistré dans le dossier cible."
            
            cmd = ["python", "-m", "pyhanko", "sign", "addsig", "--no-strict-syntax", "--field", f"1/257,734,337,814/Sig_{base.replace(' ', '_')}", "beid", "--lib", LIB_BEID, i_path, o_path]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=startupinfo)
            
            if self.var_delete_source.get() == 1: os.remove(i_path)
            else: self.fichiers_signes_session.add(f_nom)
                
            self.root.after(0, lambda: self.show_status_message(msg_fin, bg_color="#4CAF50", fg_color="white", auto_clear=True))
            self.root.after(0, self.refresh_pdf_list)
            self.root.after(0, self._auto_select_next)
        except subprocess.CalledProcessError:
            self.root.after(0, lambda: messagebox.showerror("Erreur pyHanko", "La signature a échoué. Vérifiez votre carte et votre PIN."))
            self.root.after(0, lambda: self.show_status_message("Échec de la signature", bg_color="#F44336", fg_color="white"))
        finally: 
            # FIX FINALE TEXTE : Restauration du libellé sur le bouton de signature vert
            self.root.after(0, lambda: self.btn_sign.config(text="Signer le document"))

    def reject_current_pdf(self):
        if not self.current_file or not self.reject_dir: return
        try:
            f_nom = self.current_file
            src_path = os.path.join(self.input_dir, f_nom)
            dest_path = os.path.join(self.reject_dir, f_nom)
            
            if self.var_delete_source.get() == 1: shutil.move(src_path, dest_path)
            else:
                shutil.copy(src_path, dest_path)
                self.fichiers_signes_session.add(f_nom)
                
            self.show_status_message(f"Document écarté : '{f_nom}' déplacé vers le dossier Rejet.", bg_color="#E53935", fg_color="white", auto_clear=True)
            self.refresh_pdf_list()
            self._auto_select_next()
        except Exception as e: messagebox.showerror("Erreur de tri", f"Impossible d'écarter le document :\n{str(e)}")

    def _auto_select_next(self):
        total_fichiers = len(self.pdf_list)
        if total_fichiers > 0:
            if self.last_selected_index >= total_fichiers: self.last_selected_index = total_fichiers - 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.last_selected_index)
            self.listbox.activate(self.last_selected_index)
            self.current_file = self.listbox.get(self.last_selected_index)
            self.current_page_num = 0
            self.render_pdf_preview(os.path.join(self.input_dir, self.current_file))
            self.check_ready_to_sign()
        else: self.canvas.delete("all"); self.current_file = ""; self.check_ready_to_sign()

    def show_status_message(self, message, bg_color=None, fg_color="black", auto_clear=False):
        if bg_color is None: bg_color = "#2D2D2D" if self.dark_mode else "#f0f0f0"
        if self.dark_mode and fg_color == "black": fg_color = "white"
        self.status_bar.config(text=message, bg=bg_color, fg=fg_color)
        if auto_clear: self.root.after(5000, self.clear_status_message)

    def clear_status_message(self):
        bg = "#2D2D2D" if self.dark_mode else "#f0f0f0"
        fg = "#FFFFFF" if self.dark_mode else "#000000"
        self.status_bar.config(text="Prêt", bg=bg, fg=fg)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSignerApp(root)
    root.mainloop()
