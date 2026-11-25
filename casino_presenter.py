from casino_model import CasinoModel, CasinoError


class CasinoPresenter:
    def __init__(self, casino_view, main_view):
        self.model = CasinoModel()
        self.view = casino_view
        self.main_view = main_view

        self.view.set_callbacks(
            spin_cb=self.handle_spin,
            quick_bet_cb=self.handle_quick_bet
        )
        self.view.update_balance(self.model.get_balance())

    def handle_quick_bet(self, action):
        balance = self.model.get_balance()
        try:
            current = float(self.view.entry_bet.get().strip().replace(",", "."))
            if current < 0:
                current = 0.0
        except ValueError:
            current = 0.0

        if action == "add_50":
            new_bet = min(balance, current + 50)
        elif action == "add_100":
            new_bet = min(balance, current + 100)
        elif action == "half":
            new_bet = max(1.0, round(current / 2.0, 2)) if current > 0 else min(balance, 50.0)
        elif action == "double":
            new_bet = min(balance, current * 2.0) if current > 0 else min(balance, 100.0)
        elif action == "max":
            new_bet = balance
        else:
            return

        if new_bet <= 0:
            self.main_view.show_error(
                "Fonduri epuizate",
                "Soldul este 0 MDL! Reporniți aplicația pentru a reseta soldul la 1000 MDL."
            )
            return

        formatted = str(int(new_bet)) if new_bet.is_integer() else f"{new_bet:.2f}"
        self.view.set_bet_text(formatted)

    def handle_spin(self, raw_bet, selected_color):
        if self.view.wheel.is_spinning:
            return

        try:
            spin_result = self.model.start_spin(raw_bet, selected_color)
        except CasinoError as err:
            self.main_view.show_error("Miză invalidă", str(err))
            return

        # Обновляем баланс сразу после списания ставки и блокируем кнопки на время вращения
        self.view.update_balance(self.model.get_balance())
        self.view.set_controls_locked(True)
        self.view.set_status("Roata se învârte... Mult noroc!", text_color="#f1c40f")

        def on_wheel_stopped():
            final_balance = self.model.finish_spin(spin_result)
            self.view.update_balance(final_balance)
            self.view.set_controls_locked(False)

            num = spin_result["number"]
            col = spin_result["color"]
            self.view.add_history_badge(num, col)

            color_ro = {"red": "ROȘU", "black": "NEGRU", "green": "VERDE"}[col]
            if spin_result["won"]:
                self.view.wheel.set_rim_highlight("#2ecc71")
                self.view.set_status(
                    f"A căzut {num} ({color_ro})! AI CÂȘTIGAT +{spin_result['payout']:.2f} MDL!",
                    text_color="#2ecc71"
                )
            else:
                self.view.wheel.set_rim_highlight("#e74c3c")
                self.view.set_status(
                    f"A căzut {num} ({color_ro}). Ai pierdut {spin_result['bet_amount']:.2f} MDL.",
                    text_color="#e74c3c"
                )

        self.view.wheel.spin_to_index(spin_result["target_index"], on_complete=on_wheel_stopped)