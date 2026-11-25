import os
import sys
import queue
import ctypes
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image, ImageOps, UnidentifiedImageError
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from casino_view import CasinoTabView

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SUPPORTED_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def resolve_product_image(data_obj):
    custom_path = data_obj.get_image_path()
    if custom_path and os.path.exists(custom_path):
        return custom_path

    for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
        fallback = os.path.join(APP_DIR, "pics", f"{data_obj.get_id()}{ext}")
        if os.path.exists(fallback):
            return fallback
    return None


class AlertDialog(ctk.CTkToplevel):
    """Модальное окно для ошибок, предупреждений и подтверждений в едином стиле."""
    def __init__(self, parent, title, message, kind="error"):
        super().__init__(parent)
        self.parent_win = parent
        self.result = False

        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        palette = {
            "error":   ("#e74c3c", "#c0392b", "✕"),
            "warning": ("#f39c12", "#d68910", "!"),
            "confirm": ("#e67e22", "#d35400", "?")
        }
        accent, hover, symbol = palette.get(kind, palette["error"])

        container = ctk.CTkFrame(self, corner_radius=12, border_width=2, border_color=accent)
        container.pack(fill="both", expand=True, padx=14, pady=14)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))

        badge = ctk.CTkLabel(
            header, text=symbol, width=34, height=34,
            fg_color=accent, corner_radius=17,
            text_color="white", font=("Segoe UI", 16, "bold")
        )
        badge.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            header, text=title,
            font=("Segoe UI", 16, "bold"), text_color="white"
        ).pack(side="left")

        ctk.CTkLabel(
            container, text=message,
            justify="left", anchor="w", wraplength=380,
            font=("Segoe UI", 13), text_color="#e0e0e0"
        ).pack(fill="x", padx=20, pady=(4, 18))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 16))

        if kind == "confirm":
            btn_yes = ctk.CTkButton(
                btn_row, text="Da, continuă", width=120, height=34,
                fg_color=accent, hover_color=hover,
                font=("Segoe UI", 13, "bold"),
                command=self._on_yes
            )
            btn_yes.pack(side="right", padx=(8, 0))

            btn_no = ctk.CTkButton(
                btn_row, text="Anulează", width=110, height=34,
                fg_color="#4a4a4a", hover_color="#666666",
                font=("Segoe UI", 13),
                command=self._on_no
            )
            btn_no.pack(side="right")
            self.bind("<Return>", lambda e: self._on_yes())
        else:
            btn_ok = ctk.CTkButton(
                btn_row, text="OK", width=110, height=34,
                fg_color=accent, hover_color=hover,
                font=("Segoe UI", 13, "bold"),
                command=self._on_no
            )
            btn_ok.pack(side="right")
            self.bind("<Return>", lambda e: self._on_no())

        self.bind("<Escape>", lambda e: self._on_no())
        self.protocol("WM_DELETE_WINDOW", self._on_no)

        self.update_idletasks()
        w = max(430, self.winfo_reqwidth())
        h = max(180, self.winfo_reqheight())
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")
        self.focus_force()

    def _on_yes(self):
        self.result = True
        self._close()

    def _on_no(self):
        self.result = False
        self._close()

    def _close(self):
        self.grab_release()
        self.destroy()
        if self.parent_win and self.parent_win.winfo_exists():
            if isinstance(self.parent_win, ctk.CTkToplevel):
                self.parent_win.grab_set()
            self.parent_win.focus_force()


class GraphFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.figure = Figure(figsize=(9, 5), dpi=100)
        self.figure.patch.set_facecolor('#2b2b2b')

        self.ax1 = self.figure.add_subplot(121)
        self.ax2 = self.figure.add_subplot(122)

        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

    def draw_chart(self, data_dict):
        self.ax1.clear()
        self.ax2.clear()

        for ax in (self.ax1, self.ax2):
            ax.set_facecolor('#2b2b2b')
            ax.tick_params(colors='#e0e0e0')
            ax.title.set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#555555')
            ax.spines['bottom'].set_color('#555555')

        avg_data = data_dict.get("avg", {})
        count_data = data_dict.get("count", {})

        if not avg_data:
            self.canvas.draw()
            return

        categorii = list(avg_data.keys())
        valori_avg = list(avg_data.values())
        valori_count = list(count_data.values())

        culori = ['#3498db', '#e74c3c', '#2ecc71'][:len(categorii)]

        self.ax1.bar(categorii, valori_avg, color=culori, width=0.6)
        self.ax1.set_title("Prețul mediu (MDL)", pad=15, fontdict={'fontsize': 14, 'fontweight': 'bold'})
        for i, v in enumerate(valori_avg):
            self.ax1.text(i, v + (max(valori_avg) * 0.02 if valori_avg else 0), f"{v}", color='white', ha='center')

        wedges, texts, autotexts = self.ax2.pie(
            valori_count, labels=categorii, colors=culori,
            autopct='%1.1f%%', startangle=90,
            wedgeprops={'edgecolor': '#2b2b2b', 'linewidth': 2}
        )
        self.ax2.set_title("Proporția produselor", pad=15, fontdict={'fontsize': 14, 'fontweight': 'bold'})
        for text in texts:
            text.set_color('white')
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        self.canvas.draw()


class ItemFrame(ctk.CTkFrame):
    def __init__(self, master, data_obj, edit_callback, delete_callback, **kwargs):
        super().__init__(master, corner_radius=10, border_width=1, border_color="#3a3a3a", **kwargs)
        self.data_obj = data_obj

        img_path = resolve_product_image(data_obj)
        pil_img = None
        if img_path:
            try:
                with Image.open(img_path) as raw_img:
                    pil_img = ImageOps.contain(raw_img.convert("RGBA"), (80, 80))
            except Exception:
                pil_img = None

        if pil_img is None:
            pil_img = Image.new('RGB', (80, 80), color='#4a4a4a')

        self.img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        self.lbl_img = ctk.CTkLabel(self, image=self.img, text="", width=80, height=80)
        self.lbl_img.pack(side="left", padx=15, pady=15)

        tip_produs = self.data_obj.__class__.__name__
        info = (f"[{tip_produs}] {data_obj.get_nume()} (ID: {data_obj.get_id()})\n"
                f"Preț: {data_obj.get_pret()} MDL\n"
                f"{data_obj.get_detalii()}")

        self.lbl_info = ctk.CTkLabel(
            self, text=info, justify="left", anchor="w",
            font=("Segoe UI", 14), wraplength=450
        )
        self.lbl_info.pack(side="left", padx=15, fill="both", expand=True)

        self.btn_delete = ctk.CTkButton(
            self, text="Șterge", fg_color="#c0392b", hover_color="#e74c3c",
            width=90, font=("Segoe UI", 12, "bold"),
            command=lambda: delete_callback(self.data_obj.get_id(), self.data_obj.get_nume())
        )
        self.btn_delete.pack(side="right", padx=15)

        self.btn_edit = ctk.CTkButton(
            self, text="Editează", fg_color="#f39c12", hover_color="#d68910",
            width=90, font=("Segoe UI", 12, "bold"),
            command=lambda: edit_callback(self.data_obj)
        )
        self.btn_edit.pack(side="right", padx=5)


class AddEditDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save_callback, data_obj=None):
        super().__init__(master)
        self.title("Adaugă/Editează Produs")
        self.geometry("490x790")
        self.transient(master)
        self.grab_set()
        self.on_save_callback = on_save_callback
        self.is_edit = data_obj is not None
        self.data_obj = data_obj

        self._user32 = None
        self._shell32 = None
        self._set_wnd_long = None
        self._hwnd = None
        self._old_wndproc = None
        self._wndproc_ref = None
        self._drop_queue = queue.SimpleQueue()
        self._poll_after_id = None

        self.preview_ctk_img = None
        self.field_widgets = {}

        ctk.CTkLabel(self, text="Tip Produs:", font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))
        self.type_var = ctk.StringVar(value="AerConditionat")
        self.type_menu = ctk.CTkOptionMenu(
            self, variable=self.type_var,
            values=["AerConditionat", "Frigider", "MasinaSpalat"],
            command=self.build_dynamic_fields, width=280
        )
        self.type_menu.pack(pady=4)

        if self.is_edit:
            self.type_var.set(self.data_obj.__class__.__name__)
            self.type_menu.configure(state="disabled")

        self.frame_comun = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_comun.pack(fill="x", padx=25, pady=6)

        ctk.CTkLabel(self.frame_comun, text="ID Produs unic (ex: ae1, f1, ms1):").pack()
        self.entry_id = ctk.CTkEntry(self.frame_comun, width=280)
        self.entry_id.pack(pady=3)

        ctk.CTkLabel(self.frame_comun, text="Nume / Model:").pack()
        self.entry_nume = ctk.CTkEntry(self.frame_comun, width=280)
        self.entry_nume.pack(pady=3)

        ctk.CTkLabel(self.frame_comun, text="Preț (MDL):").pack()
        self.entry_pret = ctk.CTkEntry(self.frame_comun, width=280)
        self.entry_pret.pack(pady=3)

        # --- Блок выбора пути и Drag-and-Drop изображения ---
        self.frame_img = ctk.CTkFrame(self, corner_radius=10, border_width=2, border_color="#3b8ed0")
        self.frame_img.pack(fill="x", padx=25, pady=8)

        ctk.CTkLabel(
            self.frame_img,
            text="Imagine produs (trage fișierul aici sau alege calea):",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(8, 4))

        self.lbl_preview = ctk.CTkLabel(
            self.frame_img,
            text="Trage o imagine (.png / .jpg / .webp)\noriunde în această fereastră",
            width=360, height=78,
            fg_color="#232323", corner_radius=8,
            text_color="#aaaaaa", font=("Segoe UI", 12)
        )
        self.lbl_preview.pack(padx=12, pady=4)

        path_row = ctk.CTkFrame(self.frame_img, fg_color="transparent")
        path_row.pack(fill="x", padx=12, pady=(4, 10))

        self.entry_img_path = ctk.CTkEntry(path_row, placeholder_text="Calea către imagine...")
        self.entry_img_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_img_path.bind("<FocusOut>", lambda e: self.update_image_preview(self.entry_img_path.get().strip(), show_popup=False))
        self.entry_img_path.bind("<Return>", lambda e: self.update_image_preview(self.entry_img_path.get().strip(), show_popup=True))

        self.btn_browse = ctk.CTkButton(
            path_row, text="Răsfoiește...", width=95,
            command=self.browse_image
        )
        self.btn_browse.pack(side="left", padx=(0, 4))

        self.btn_clear_img = ctk.CTkButton(
            path_row, text="✕", width=32, fg_color="#555555", hover_color="#777777",
            command=self.clear_image
        )
        self.btn_clear_img.pack(side="left")
        # -----------------------------------------------------

        if self.is_edit:
            self.entry_id.insert(0, self.data_obj.get_id())
            self.entry_nume.insert(0, self.data_obj.get_nume())
            self.entry_pret.insert(0, str(self.data_obj.get_pret()))
            existing_img = resolve_product_image(self.data_obj) or self.data_obj.get_image_path()
            if existing_img:
                self.entry_img_path.insert(0, existing_img)
                self.update_image_preview(existing_img, show_popup=False)

        self.frame_specific = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_specific.pack(fill="x", padx=25, pady=4)

        self.dynamic_widgets = {}
        self.build_dynamic_fields(self.type_var.get())

        self.btn_save = ctk.CTkButton(
            self, text="Salvează", command=self.save_data,
            fg_color="#27ae60", hover_color="#2ecc71",
            font=("Segoe UI", 14, "bold"), width=200, height=40
        )
        self.btn_save.pack(pady=14)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(150, self._enable_windows_dnd)

    def _register_field_map(self):
        self.field_widgets = {
            "item_id": self.entry_id,
            "nume": self.entry_nume,
            "pret": self.entry_pret,
            "image_path": self.entry_img_path,
        }
        for key, widget in self.dynamic_widgets.items():
            if isinstance(widget, ctk.CTkEntry):
                self.field_widgets[key] = widget

    def reset_highlights(self):
        self._register_field_map()
        for widget in self.field_widgets.values():
            widget.configure(border_color=["#979DA2", "#565B5E"])

    def highlight_field(self, field_name):
        self.reset_highlights()
        if not field_name:
            return
        if field_name == "image_path":
            self.frame_img.configure(border_color="#e74c3c")
        widget = self.field_widgets.get(field_name)
        if widget:
            widget.configure(border_color="#e74c3c")
            widget.focus_set()

    def _enable_windows_dnd(self):
        if sys.platform != "win32" or not self.winfo_exists():
            return
        try:
            GWLP_WNDPROC = -4
            WM_DROPFILES = 0x0233
            GA_ROOT = 2

            HWND = ctypes.c_void_p
            UINT = ctypes.c_uint
            WPARAM = ctypes.c_size_t
            LPARAM = ctypes.c_ssize_t
            LRESULT = ctypes.c_ssize_t

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            shell32 = ctypes.WinDLL("shell32", use_last_error=True)

            WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)

            user32.GetAncestor.argtypes = [HWND, UINT]
            user32.GetAncestor.restype = HWND

            set_wnd_long = user32.SetWindowLongPtrW if hasattr(user32, "SetWindowLongPtrW") else user32.SetWindowLongW
            set_wnd_long.argtypes = [HWND, ctypes.c_int, ctypes.c_void_p]
            set_wnd_long.restype = ctypes.c_void_p

            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, HWND, UINT, WPARAM, LPARAM]
            user32.CallWindowProcW.restype = LRESULT

            shell32.DragAcceptFiles.argtypes = [HWND, ctypes.c_bool]
            shell32.DragAcceptFiles.restype = None

            shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, UINT, ctypes.c_wchar_p, UINT]
            shell32.DragQueryFileW.restype = UINT

            shell32.DragFinish.argtypes = [ctypes.c_void_p]
            shell32.DragFinish.restype = None

            hwnd = user32.GetAncestor(HWND(self.winfo_id()), GA_ROOT)
            if not hwnd:
                return

            self._user32 = user32
            self._shell32 = shell32
            self._set_wnd_long = set_wnd_long
            self._hwnd = hwnd

            shell32.DragAcceptFiles(hwnd, True)

            drop_queue = self._drop_queue
            call_window_proc = user32.CallWindowProcW

            def wndproc(h, msg, wparam, lparam):
                try:
                    if msg == WM_DROPFILES:
                        hdrop = ctypes.c_void_p(wparam)
                        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                        dropped_path = ""
                        if count > 0:
                            length = shell32.DragQueryFileW(hdrop, 0, None, 0)
                            buf = ctypes.create_unicode_buffer(length + 1)
                            shell32.DragQueryFileW(hdrop, 0, buf, length + 1)
                            dropped_path = buf.value
                        shell32.DragFinish(hdrop)
                        drop_queue.put((count, dropped_path))
                        return 0
                except Exception:
                    pass
                return call_window_proc(self._old_wndproc, h, msg, wparam, lparam)

            self._wndproc_ref = WNDPROC(wndproc)
            new_proc_ptr = ctypes.cast(self._wndproc_ref, ctypes.c_void_p)
            self._old_wndproc = set_wnd_long(hwnd, GWLP_WNDPROC, new_proc_ptr)
            self._poll_drop_queue()
        except Exception:
            pass

    def _poll_drop_queue(self):
        if not self.winfo_exists():
            return
        try:
            while not self._drop_queue.empty():
                count, dropped_path = self._drop_queue.get_nowait()
                self._handle_dropped_files(count, dropped_path)
        except Exception:
            pass
        self._poll_after_id = self.after(100, self._poll_drop_queue)

    def _handle_dropped_files(self, count, dropped_path):
        if count > 1:
            self.master.show_error(
                "Prea multe fișiere",
                "Ați tras mai multe fișiere simultan.\nTrageți o singură imagine pentru produs.",
                parent=self
            )
            return
        if dropped_path:
            self.set_image_path(dropped_path, show_popup=True)

    def _disable_windows_dnd(self):
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None

        if sys.platform == "win32" and self._hwnd and self._old_wndproc and self._set_wnd_long:
            try:
                GWLP_WNDPROC = -4
                self._set_wnd_long(self._hwnd, GWLP_WNDPROC, self._old_wndproc)
            except Exception:
                pass
        self._hwnd = None
        self._old_wndproc = None
        self._wndproc_ref = None
        self._set_wnd_long = None

    def set_image_path(self, path, show_popup=True):
        clean_path = path.strip().strip('"')
        self.entry_img_path.delete(0, "end")
        self.entry_img_path.insert(0, clean_path)
        self.update_image_preview(clean_path, show_popup=show_popup)

    def browse_image(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Selectează imaginea produsului",
            filetypes=[("Imagini", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Toate fișierele", "*.*")]
        )
        if file_path:
            self.set_image_path(file_path, show_popup=True)

    def clear_image(self):
        self.entry_img_path.delete(0, "end")
        self.preview_ctk_img = None
        self.lbl_preview.configure(
            image="",
            compound="center",
            text="Trage o imagine (.png / .jpg / .webp)\noriunde în această fereastră",
            text_color="#aaaaaa"
        )
        self.frame_img.configure(border_color="#3b8ed0")

    def update_image_preview(self, path, show_popup=False):
        if not path:
            self.clear_image()
            return

        if os.path.isdir(path):
            self.preview_ctk_img = None
            self.lbl_preview.configure(
                image="", compound="center",
                text="Ați selectat un dosar, nu o imagine!", text_color="#e74c3c"
            )
            self.frame_img.configure(border_color="#e74c3c")
            if show_popup:
                self.master.show_error("Dosar invalid", "Nu puteți adăuga un dosar.\nSelectați un fișier imagine (.png, .jpg, .webp).", parent=self)
            return

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_IMG_EXTS:
            self.preview_ctk_img = None
            self.lbl_preview.configure(
                image="", compound="center",
                text="Format nesuportat! Alege PNG, JPG sau WEBP.",
                text_color="#e74c3c"
            )
            self.frame_img.configure(border_color="#e74c3c")
            if show_popup:
                self.master.show_error(
                    "Format nesuportat",
                    f"Fișierul «{os.path.basename(path)}» nu este o imagine suportată.\nFolosiți PNG, JPG, JPEG, WEBP sau BMP.",
                    parent=self
                )
            return

        if not os.path.exists(path):
            self.preview_ctk_img = None
            self.lbl_preview.configure(
                image="", compound="center",
                text="Fișierul nu a fost găsit la această cale.",
                text_color="#e67e22"
            )
            self.frame_img.configure(border_color="#e67e22")
            if show_popup:
                self.master.show_error("Fișier inexistent", f"Nu s-a găsit fișierul la calea:\n{path}", parent=self)
            return

        try:
            with Image.open(path) as raw_img:
                thumb = ImageOps.contain(raw_img.convert("RGBA"), (70, 70))
            self.preview_ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.lbl_preview.configure(
                image=self.preview_ctk_img,
                text=f"  {os.path.basename(path)}",
                compound="left",
                text_color="#2ecc71"
            )
            self.frame_img.configure(border_color="#27ae60")
        except (UnidentifiedImageError, OSError, Exception):
            self.preview_ctk_img = None
            self.lbl_preview.configure(
                image="", compound="center",
                text="Fișierul este deteriorat sau nu este imagine.",
                text_color="#e74c3c"
            )
            self.frame_img.configure(border_color="#e74c3c")
            if show_popup:
                self.master.show_error(
                    "Imagine deteriorată",
                    f"Fișierul «{os.path.basename(path)}» este deteriorat și nu poate fi deschis.",
                    parent=self
                )

    def on_close(self):
        self._disable_windows_dnd()
        self.grab_release()
        self.master.focus_set()
        self.destroy()

    def build_dynamic_fields(self, tip):
        for widget in self.frame_specific.winfo_children():
            widget.destroy()
        self.dynamic_widgets.clear()

        if tip == "AerConditionat":
            ctk.CTkLabel(self.frame_specific, text="Suprafață (m²):").pack()
            e_arie = ctk.CTkEntry(self.frame_specific, width=280)
            e_arie.pack(pady=3)
            chk_inv = ctk.CTkCheckBox(self.frame_specific, text="Inverter")
            chk_inv.pack(pady=3)
            chk_wifi = ctk.CTkCheckBox(self.frame_specific, text="Wi-Fi")
            chk_wifi.pack(pady=3)

            if self.is_edit and tip == self.data_obj.__class__.__name__:
                e_arie.insert(0, str(self.data_obj.arie))
                if self.data_obj.is_inverter: chk_inv.select()
                if self.data_obj.has_wifi: chk_wifi.select()

            self.dynamic_widgets = {"arie": e_arie, "is_inverter": chk_inv, "has_wifi": chk_wifi}

        elif tip == "Frigider":
            ctk.CTkLabel(self.frame_specific, text="Volum (L):").pack()
            e_vol = ctk.CTkEntry(self.frame_specific, width=280)
            e_vol.pack(pady=3)
            chk_nf = ctk.CTkCheckBox(self.frame_specific, text="Sistem NoFrost")
            chk_nf.pack(pady=3)
            chk_doz = ctk.CTkCheckBox(self.frame_specific, text="Dozator Apă")
            chk_doz.pack(pady=3)

            if self.is_edit and tip == self.data_obj.__class__.__name__:
                e_vol.insert(0, str(self.data_obj.volum))
                if self.data_obj.is_nofrost: chk_nf.select()
                if self.data_obj.are_dozator: chk_doz.select()

            self.dynamic_widgets = {"volum": e_vol, "is_nofrost": chk_nf, "are_dozator": chk_doz}

        elif tip == "MasinaSpalat":
            ctk.CTkLabel(self.frame_specific, text="Capacitate (kg):").pack()
            e_cap = ctk.CTkEntry(self.frame_specific, width=280)
            e_cap.pack(pady=3)
            ctk.CTkLabel(self.frame_specific, text="Rotații (RPM):").pack()
            e_rpm = ctk.CTkEntry(self.frame_specific, width=280)
            e_rpm.pack(pady=3)
            chk_smart = ctk.CTkCheckBox(self.frame_specific, text="Funcții Smart")
            chk_smart.pack(pady=3)

            if self.is_edit and tip == self.data_obj.__class__.__name__:
                e_cap.insert(0, str(self.data_obj.capacitate))
                e_rpm.insert(0, str(self.data_obj.rpm))
                if self.data_obj.is_smart: chk_smart.select()

            self.dynamic_widgets = {"capacitate": e_cap, "rpm": e_rpm, "is_smart": chk_smart}

        self._register_field_map()

    def save_data(self):
        self.reset_highlights()
        tip = self.type_var.get()

        data = {
            "type": tip,
            "item_id": self.entry_id.get().strip(),
            "nume": self.entry_nume.get().strip(),
            "pret": self.entry_pret.get().strip(),
            "image_path": self.entry_img_path.get().strip().strip('"')
        }

        for key, widget in self.dynamic_widgets.items():
            if isinstance(widget, ctk.CTkEntry):
                data[key] = widget.get().strip()
            elif isinstance(widget, ctk.CTkCheckBox):
                data[key] = widget.get() == 1

        old_id = self.data_obj.get_id() if self.is_edit else None

        success = self.on_save_callback(data, self.is_edit, old_id, dialog=self)
        if success:
            self.on_close()


class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Magazin Electrocasnice (Database Edition)")
        self.geometry("1000x750")

        self.sort_callback = None
        self.add_edit_request_callback = None
        self.delete_request_callback = None
        self.search_callback = None

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.tab_lista = self.tabview.add("Lista Produse")
        self.tab_grafice = self.tabview.add("Statistici & Grafice")
        self.tab_casino = self.tabview.add("Cazinou")

        self.top_frame = ctk.CTkFrame(self.tab_lista, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=5, pady=(5, 15))

        self.btn_add = ctk.CTkButton(
            self.top_frame, text="+ Adaugă Element",
            fg_color="#27ae60", hover_color="#2ecc71",
            font=("Segoe UI", 13, "bold"), width=150, height=35,
            command=self.open_add_dialog
        )
        self.btn_add.pack(side="left")

        self.entry_search = ctk.CTkEntry(self.top_frame, placeholder_text="Caută după nume...", width=200, height=35)
        self.entry_search.pack(side="left", padx=(20, 5))
        self.entry_search.bind("<KeyRelease>", self.trigger_search)

        self.btn_sort_desc = ctk.CTkButton(
            self.top_frame, text="Preț ↘", width=90, height=35,
            fg_color="#2980b9", hover_color="#3498db", font=("Segoe UI", 12, "bold"),
            command=lambda: self.trigger_sort("pret_desc")
        )
        self.btn_sort_desc.pack(side="right", padx=5)

        self.btn_sort_asc = ctk.CTkButton(
            self.top_frame, text="Preț ↗", width=90, height=35,
            fg_color="#2980b9", hover_color="#3498db", font=("Segoe UI", 12, "bold"),
            command=lambda: self.trigger_sort("pret_asc")
        )
        self.btn_sort_asc.pack(side="right", padx=5)

        self.btn_sort_name = ctk.CTkButton(
            self.top_frame, text="Nume A-Z", width=90, height=35,
            fg_color="#2980b9", hover_color="#3498db", font=("Segoe UI", 12, "bold"),
            command=lambda: self.trigger_sort("nume")
        )
        self.btn_sort_name.pack(side="right", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_lista, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True)

        self.graph_frame = GraphFrame(self.tab_grafice, fg_color="transparent")
        self.graph_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.casino_frame = CasinoTabView(self.tab_casino)
        self.casino_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def show_error(self, title, message, parent=None):
        target = parent if (parent and parent.winfo_exists()) else self
        dlg = AlertDialog(target, title, message, kind="error")
        self.wait_window(dlg)

    def show_warning(self, title, message, parent=None):
        target = parent if (parent and parent.winfo_exists()) else self
        dlg = AlertDialog(target, title, message, kind="warning")
        self.wait_window(dlg)

    def ask_confirm(self, title, message, parent=None):
        target = parent if (parent and parent.winfo_exists()) else self
        dlg = AlertDialog(target, title, message, kind="confirm")
        self.wait_window(dlg)
        return dlg.result

    def set_callbacks(self, sort_cb, add_edit_cb, delete_cb, search_cb):
        self.sort_callback = sort_cb
        self.add_edit_request_callback = add_edit_cb
        self.delete_request_callback = delete_cb
        self.search_callback = search_cb

    def trigger_sort(self, sort_mode):
        if self.sort_callback:
            self.sort_callback(sort_mode)

    def trigger_search(self, event):
        if self.search_callback:
            search_text = self.entry_search.get()
            self.search_callback(search_text)

    def display_items(self, items):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not items:
            ctk.CTkLabel(
                self.scroll_frame,
                text="Nu există produse de afișat.",
                font=("Segoe UI", 15),
                text_color="#888888"
            ).pack(pady=40)
            return

        for prod in items:
            frame = ItemFrame(
                self.scroll_frame, data_obj=prod,
                edit_callback=self.open_edit_dialog,
                delete_callback=self.delete_request_callback
            )
            frame.pack(fill="x", pady=5)

        self.update_idletasks()

    def open_add_dialog(self):
        AddEditDialog(self, on_save_callback=self.add_edit_request_callback)

    def open_edit_dialog(self, data_obj):
        AddEditDialog(self, on_save_callback=self.add_edit_request_callback, data_obj=data_obj)