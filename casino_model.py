import os
import sys
import json
import math
import random

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_BALANCE = 1000.0

# Классический порядок чисел европейской рулетки (37 секторов)
WHEEL_NUMBERS = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

MULTIPLIERS = {
    "red": 2,
    "black": 2,
    "green": 35
}


class CasinoError(Exception):
    """Ошибка валидации ставки или состояния игры."""
    pass


def get_number_color(number):
    if number == 0:
        return "green"
    return "red" if number in RED_NUMBERS else "black"


class CasinoModel:
    def __init__(self, state_filename="casino_balance.json"):
        self.state_path = os.path.join(APP_DIR, state_filename)
        self._rng = random.SystemRandom()
        self.balance = self._load_balance()

    def _load_balance(self):
        """
        Загружает баланс при старте:
        - если файла нет, он повреждён или баланс < 1000 MDL -> сброс на 1000 MDL;
        - если пользователь в плюсе (>= 1000 MDL) -> баланс сохраняется.
        """
        if not os.path.exists(self.state_path):
            self._save_balance(DEFAULT_BALANCE)
            return DEFAULT_BALANCE

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            saved = float(payload.get("balance", DEFAULT_BALANCE))
            if not math.isfinite(saved) or saved < DEFAULT_BALANCE:
                self._save_balance(DEFAULT_BALANCE)
                return DEFAULT_BALANCE
            return round(saved, 2)
        except Exception:
            self._save_balance(DEFAULT_BALANCE)
            return DEFAULT_BALANCE

    def _save_balance(self, value):
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({"balance": round(float(value), 2)}, f, indent=2)
        except OSError:
            pass

    def get_balance(self):
        return self.balance

    def validate_bet(self, raw_bet, selected_color):
        if selected_color not in MULTIPLIERS:
            raise CasinoError("Selectați o culoare pe care pariați (Roșu, Verde sau Negru)!")

        text = str(raw_bet).strip().replace(",", ".")
        if not text:
            raise CasinoError("Introduceți suma mizei!")

        try:
            amount = float(text)
        except ValueError:
            raise CasinoError("Miza trebuie să fie un număr valid (ex: 50 sau 100.5)!")

        if not math.isfinite(amount) or amount <= 0:
            raise CasinoError("Miza trebuie să fie mai mare decât 0 MDL!")

        amount = round(amount, 2)
        if amount > self.balance:
            raise CasinoError(
                f"Fonduri insuficiente!\nSold curent: {self.balance:.2f} MDL\nMiză cerută: {amount:.2f} MDL"
            )

        return amount

    def start_spin(self, raw_bet, selected_color):
        """Списывает ставку и определяет выигрышный сектор до начала анимации."""
        bet_amount = self.validate_bet(raw_bet, selected_color)

        # Списываем ставку сразу при запуске вращения
        self.balance = round(self.balance - bet_amount, 2)
        self._save_balance(self.balance)

        target_index = self._rng.randrange(len(WHEEL_NUMBERS))
        rolled_number = WHEEL_NUMBERS[target_index]
        rolled_color = get_number_color(rolled_number)

        won = (rolled_color == selected_color)
        payout = round(bet_amount * MULTIPLIERS[selected_color], 2) if won else 0.0
        final_balance = round(self.balance + payout, 2)

        return {
            "target_index": target_index,
            "number": rolled_number,
            "color": rolled_color,
            "bet_color": selected_color,
            "bet_amount": bet_amount,
            "won": won,
            "payout": payout,
            "final_balance": final_balance
        }

    def finish_spin(self, spin_result):
        """Начисляет выигрыш после остановки колеса."""
        self.balance = spin_result["final_balance"]
        self._save_balance(self.balance)
        return self.balance