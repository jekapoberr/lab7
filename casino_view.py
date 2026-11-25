import math
import random
import tkinter as tk
import customtkinter as ctk
from casino_model import WHEEL_NUMBERS, get_number_color, DEFAULT_BALANCE


class RouletteWheelCanvas(tk.Canvas):
    """Анимированное колесо рулетки с плавным торможением."""
    def __init__(self, master, size=330, **kwargs):
        super().__init__(
            master, width=size, height=size,
            bg="#2b2b2b", highlightthickness=0, **kwargs
        )
        self.size = size
        self.cx = size / 2
        self.cy = size / 2 + 6
        self.outer_r = size * 0.44
        self.inner_r = size * 0.17

        self.current_angle = 0.0
        self.is_spinning = False
        self._anim_id = None
        self.highlight_color = "#f1c40f"

        self.draw_wheel()

    def set_rim_highlight(self, color):
        self.highlight_color = color
        self.draw_wheel()

    def draw_wheel(self):
        self.delete("all")
        n = len(WHEEL_NUMBERS)
        step = 360.0 / n

        # Внешний декоративный обод
        rim_r = self.outer_r + 10
        self.create_oval(
            self.cx - rim_r, self.cy - rim_r,
            self.cx + rim_r, self.cy + rim_r,
            fill="#1f1f1f", outline=self.highlight_color, width=3
        )

        # Сектора рулетки
        for i, num in enumerate(WHEEL_NUMBERS):
            start_deg = self.current_angle + i * step
            col_key = get_number_color(num)
            if col_key == "red":
                fill_col = "#c0392b"
            elif col_key == "black":
                fill_col = "#1c1c1c"
            else:
                fill_col = "#27ae60"

            self.create_arc(
                self.cx - self.outer_r, self.cy - self.outer_r,
                self.cx + self.outer_r, self.cy + self.outer_r,
                start=start_deg, extent=step,
                fill=fill_col, outline="#3d3d3d", width=1, style=tk.PIESLICE
            )

            # Подпись числа в середине сектора
            mid_deg = start_deg + step / 2.0
            rad = math.radians(mid_deg)
            text_r = self.outer_r * 0.81
            tx = self.cx + text_r * math.cos(rad)
            ty = self.cy - text_r * math.sin(rad)

            self.create_text(
                tx, ty, text=str(num),
                fill="white", font=("Segoe UI", 8, "bold"),
                angle=(mid_deg - 90) % 360
            )

        # Внутренний металлический круг
        self.create_oval(
            self.cx - self.inner_r, self.cy - self.inner_r,
            self.cx + self.inner_r, self.cy + self.inner_r,
            fill="#232323", outline="#d4ac0d", width=3
        )

        # Крестовина в центре барабана
        spoke_r = self.inner_r * 0.72
        for k in range(4):
            ang = math.radians(self.current_angle * 1.4 + k * 45)
            x1 = self.cx + spoke_r * math.cos(ang)
            y1 = self.cy - spoke_r * math.sin(ang)
            x2 = self.cx - spoke_r * math.cos(ang)
            y2 = self.cy + spoke_r * math.sin(ang)
            self.create_line(x1, y1, x2, y2, fill="#d4ac0d", width=2)

        self.create_oval(
            self.cx - 8, self.cy - 8, self.cx + 8, self.cy + 8,
            fill="#f1c40f", outline="#7d6608", width=2
        )

        # Золотой указатель сверху (на 90 градусах)
        tip_y = self.cy - self.outer_r + 5
        top_y = self.cy - self.outer_r - 16
        self.create_polygon(
            self.cx - 11, top_y,
            self.cx + 11, top_y,
            self.cx, tip_y,
            fill="#f1c40f", outline="#111111", width=2
        )

    def spin_to_index(self, target_index, on_complete, duration_ms=3400):
        if self.is_spinning:
            return

        self.is_spinning = True
        self.highlight_color = "#f1c40f"

        n = len(WHEEL_NUMBERS)
        step = 360.0 / n

        desired_mod = (90.0 - (target_index + 0.5) * step) % 360.0
        current_mod = self.current_angle % 360.0
        delta_to_target = (desired_mod - current_mod) % 360.0

        total_delta = 360.0 * 6 + delta_to_target
        start_angle = self.current_angle
        total_frames = max(1, duration_ms // 16)
        frame = 0

        def animate():
            nonlocal frame
            if not self.winfo_exists():
                return

            frame += 1
            t = min(1.0, frame / total_frames)
            ease = 1.0 - (1.0 - t) ** 4
            self.current_angle = start_angle + total_delta * ease
            self.draw_wheel()

            if t < 1.0:
                self._anim_id = self.after(16, animate)
            else:
                self.current_angle = (start_angle + total_delta) % 360.0
                self.is_spinning = False
                self._anim_id = None
                self.draw_wheel()
                if on_complete:
                    on_complete()

        animate()


class CasinoTabView(ctk.CTkFrame):
    """Интерфейс третьей вкладки с рулеткой и убегающей кнопкой Cash-Out."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.selected_color = None
        self.spin_callback = None
        self.quick_bet_callback = None
        self.history_items = []
        self._cashout_moved = False

        # Жёсткая фиксация пропорций 50/50 между колонками
        self.grid_columnconfigure(0, weight=1, uniform="casino_cols")
        self.grid_columnconfigure(1, weight=1, uniform="casino_cols")
        self.grid_rowconfigure(0, weight=1)

        # --- Левая колонка: колесо, фиксированная лента истории, баннер результата ---
        left_panel = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#3a3a3a")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(5, 8), pady=5)

        ctk.CTkLabel(
            left_panel, text="Ruletă Europeană",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(12, 4))

        self.history_frame = ctk.CTkFrame(left_panel, fg_color="#222222", height=40, corner_radius=8)
        self.history_frame.pack(fill="x", padx=20, pady=(4, 8))
        self.history_frame.pack_propagate(False)

        self.history_slots_container = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        self.history_slots_container.place(relx=0.5, rely=0.5, anchor="center")

        self.history_badges = []
        for _ in range(10):
            badge = ctk.CTkLabel(
                self.history_slots_container,
                text="•",
                width=28,
                height=26,
                corner_radius=6,
                fg_color="#2c2c2c",
                text_color="#555555",
                font=("Segoe UI", 11, "bold")
            )
            badge.pack(side="left", padx=2)
            self.history_badges.append(badge)

        wheel_holder = ctk.CTkFrame(left_panel, fg_color="transparent", width=340, height=340)
        wheel_holder.pack(pady=4)
        wheel_holder.pack_propagate(False)

        self.wheel = RouletteWheelCanvas(wheel_holder, size=330)
        self.wheel.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_result = ctk.CTkLabel(
            left_panel,
            text="Alege o culoare, introdu miza și apasă «ÎNVÂRTE»!",
            font=("Segoe UI", 13, "bold"),
            fg_color="#232323",
            corner_radius=8,
            height=56,
            wraplength=350
        )
        self.lbl_result.pack(fill="x", padx=20, pady=(6, 14))

        # --- Правая колонка: баланс, ставка, цвета, крутка и убегающий Cash-Out ---
        right_panel = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#3a3a3a")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 5), pady=5)

        balance_card = ctk.CTkFrame(right_panel, fg_color="#222222", corner_radius=10, border_width=1, border_color="#d4ac0d")
        balance_card.pack(fill="x", padx=22, pady=(16, 10))

        ctk.CTkLabel(
            balance_card, text="SOLD CURENT",
            font=("Segoe UI", 11, "bold"), text_color="#aaaaaa"
        ).pack(pady=(8, 0))

        self.lbl_balance = ctk.CTkLabel(
            balance_card, text=f"{DEFAULT_BALANCE:.2f} MDL",
            font=("Segoe UI", 26, "bold"), text_color="#f1c40f"
        )
        self.lbl_balance.pack(pady=(2, 2))

        ctk.CTkLabel(
            balance_card,
            text=f"* Dacă soldul scade sub {int(DEFAULT_BALANCE)} MDL, se resetează la repornire",
            font=("Segoe UI", 11), text_color="#888888"
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            right_panel, text="Suma mizei (MDL):",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=22, pady=(2, 4))

        self.entry_bet = ctk.CTkEntry(
            right_panel, placeholder_text="Ex: 100",
            height=38, font=("Segoe UI", 15)
        )
        self.entry_bet.pack(fill="x", padx=22, pady=(0, 6))
        self.entry_bet.insert(0, "100")

        quick_row = ctk.CTkFrame(right_panel, fg_color="transparent")
        quick_row.pack(fill="x", padx=22, pady=(0, 12))

        for label, action in [("+50", "add_50"), ("+100", "add_100"), ("1/2", "half"), ("x2", "double"), ("MAX", "max")]:
            btn = ctk.CTkButton(
                quick_row, text=label, width=56, height=28,
                fg_color="#3a3a3a", hover_color="#505050",
                font=("Segoe UI", 12, "bold"),
                command=lambda a=action: self._on_quick_bet(a)
            )
            btn.pack(side="left", expand=True, padx=2)

        ctk.CTkLabel(
            right_panel, text="Alege culoarea (multiplicator):",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=22, pady=(2, 6))

        colors_row = ctk.CTkFrame(right_panel, fg_color="transparent")
        colors_row.pack(fill="x", padx=22, pady=(0, 14))

        self.color_buttons = {}
        color_specs = [
            ("red",   "ROȘU\n(x2)",   "#c0392b", "#e74c3c"),
            ("green", "VERDE\n(x35)", "#27ae60", "#2ecc71"),
            ("black", "NEGRU\n(x2)",  "#1c1c1c", "#333333"),
        ]
        for key, title, fg, hover in color_specs:
            btn = ctk.CTkButton(
                colors_row, text=title, height=58,
                fg_color=fg, hover_color=hover,
                border_width=2, border_color="#4a4a4a",
                font=("Segoe UI", 14, "bold"),
                command=lambda k=key: self.select_color(k)
            )
            btn.pack(side="left", fill="x", expand=True, padx=4)
            self.color_buttons[key] = btn

        self.btn_spin = ctk.CTkButton(
            right_panel, text="ÎNVÂRTE RULETA",
            height=48, fg_color="#f39c12", hover_color="#f1c40f",
            text_color="#111111", font=("Segoe UI", 16, "bold"),
            command=self._on_spin_click
        )
        self.btn_spin.pack(fill="x", padx=22, pady=(4, 8))

        # --- Свободная зона для убегающей кнопки Cash-Out ---
        self.cashout_arena = ctk.CTkFrame(
            right_panel,
            fg_color="#232323",
            corner_radius=8,
            border_width=1,
            border_color="#343434"
        )
        self.cashout_arena.pack(fill="both", expand=True, padx=22, pady=(2, 14))

        self.btn_cashout = ctk.CTkButton(
            self.cashout_arena,
            text="CASH-OUT",
            width=130,
            height=34,
            fg_color="#2c3e50",
            hover_color="#34495e",
            border_width=1,
            border_color="#5d6d7e",
            text_color="#ecf0f1",
            font=("Segoe UI", 13, "bold"),
            command=lambda: None
        )
        try:
            self.btn_cashout._canvas.configure(takefocus=False)
        except Exception:
            pass
        self.btn_cashout.place(relx=0.5, rely=0.5, anchor="center")

        self.cashout_arena.bind("<Motion>", self._on_arena_mouse_move)
        self.cashout_arena.bind("<Configure>", self._keep_cashout_in_bounds)
        for w in (self.btn_cashout, self.btn_cashout._canvas, self.btn_cashout._text_label):
            w.bind("<Enter>", self._on_cashout_enter)
            w.bind("<Motion>", self._on_cashout_enter)

        self.select_color("red")

    def _on_arena_mouse_move(self, event):
        bx = self.btn_cashout.winfo_x()
        by = self.btn_cashout.winfo_y()
        bw = self.btn_cashout.winfo_width()
        bh = self.btn_cashout.winfo_height()

        margin = 20
        if (bx - margin) <= event.x <= (bx + bw + margin) and (by - margin) <= event.y <= (by + bh + margin):
            self._dodge_cashout(event.x, event.y)

    def _on_cashout_enter(self, _event):
        mx = self.cashout_arena.winfo_pointerx() - self.cashout_arena.winfo_rootx()
        my = self.cashout_arena.winfo_pointery() - self.cashout_arena.winfo_rooty()
        self._dodge_cashout(mx, my)

    def _dodge_cashout(self, cursor_x, cursor_y):
        arena_w = self.cashout_arena.winfo_width()
        arena_h = self.cashout_arena.winfo_height()
        btn_w = self.btn_cashout.winfo_width()
        btn_h = self.btn_cashout.winfo_height()

        if arena_w <= 1 or arena_h <= 1 or btn_w <= 1 or btn_h <= 1:
            return

        pad = 6
        max_x = arena_w - btn_w - pad
        max_y = arena_h - btn_h - pad
        if max_x <= pad and max_y <= pad:
            return

        max_x = max(pad, max_x)
        max_y = max(pad, max_y)

        # Выбираем из 15 случайных позиций внутри рамки самую далёкую от курсора
        best_x, best_y = pad, pad
        best_dist_sq = -1.0
        for _ in range(15):
            nx = random.randint(pad, max_x)
            ny = random.randint(pad, max_y)
            cx = nx + btn_w / 2.0
            cy = ny + btn_h / 2.0
            dist_sq = (cx - cursor_x) ** 2 + (cy - cursor_y) ** 2
            if dist_sq > best_dist_sq:
                best_dist_sq = dist_sq
                best_x, best_y = nx, ny

        self._cashout_moved = True
        # Используем tk.Widget.place, чтобы CustomTkinter не умножал пиксели на DPI-масштаб повторно
        tk.Widget.place(self.btn_cashout, x=best_x, y=best_y, relx=0, rely=0, anchor="nw")

    def _keep_cashout_in_bounds(self, event):
        if not self._cashout_moved:
            return
        btn_w = self.btn_cashout.winfo_width()
        btn_h = self.btn_cashout.winfo_height()
        if btn_w <= 1 or btn_h <= 1:
            return
        pad = 6
        max_x = max(pad, event.width - btn_w - pad)
        max_y = max(pad, event.height - btn_h - pad)
        cur_x = min(max(pad, self.btn_cashout.winfo_x()), max_x)
        cur_y = min(max(pad, self.btn_cashout.winfo_y()), max_y)
        tk.Widget.place(self.btn_cashout, x=cur_x, y=cur_y, relx=0, rely=0, anchor="nw")

    def set_callbacks(self, spin_cb, quick_bet_cb):
        self.spin_callback = spin_cb
        self.quick_bet_callback = quick_bet_cb

    def select_color(self, color_key):
        if self.wheel.is_spinning:
            return
        self.selected_color = color_key
        for key, btn in self.color_buttons.items():
            if key == color_key:
                btn.configure(border_color="#f1c40f", border_width=3)
            else:
                btn.configure(border_color="#4a4a4a", border_width=1)

    def _on_quick_bet(self, action):
        if not self.wheel.is_spinning and self.quick_bet_callback:
            self.quick_bet_callback(action)

    def _on_spin_click(self):
        if not self.wheel.is_spinning and self.spin_callback:
            self.spin_callback(self.entry_bet.get(), self.selected_color)

    def set_bet_text(self, value_str):
        self.entry_bet.delete(0, "end")
        self.entry_bet.insert(0, value_str)

    def update_balance(self, amount):
        self.lbl_balance.configure(text=f"{amount:.2f} MDL")

    def set_controls_locked(self, locked):
        state = "disabled" if locked else "normal"
        self.btn_spin.configure(
            state=state,
            text="SE ÎNVÂRTE..." if locked else "ÎNVÂRTE RULETA"
        )
        self.entry_bet.configure(state=state)
        for btn in self.color_buttons.values():
            btn.configure(state=state)

    def set_status(self, text, text_color="white"):
        self.lbl_result.configure(text=text, text_color=text_color)

    def add_history_badge(self, number, color_key):
        self.history_items.insert(0, (number, color_key))
        self.history_items = self.history_items[:10]

        bg_map = {"red": "#c0392b", "green": "#27ae60", "black": "#111111"}
        for idx, badge in enumerate(self.history_badges):
            if idx < len(self.history_items):
                num, col = self.history_items[idx]
                badge.configure(
                    text=str(num),
                    fg_color=bg_map.get(col, "#333333"),
                    text_color="white"
                )
            else:
                badge.configure(
                    text="•",
                    fg_color="#2c2c2c",
                    text_color="#555555"
                )