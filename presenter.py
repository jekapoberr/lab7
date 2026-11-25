import sqlite3
from model import ModelMagazin, ValidationError
from view import MainView
from casino_presenter import CasinoPresenter


class AppPresenter:
    def __init__(self):
        self.model = ModelMagazin()
        self.view = MainView()
        self.casino_presenter = CasinoPresenter(self.view.casino_frame, self.view)

        self.view.set_callbacks(
            sort_cb=self.handle_sort,
            add_edit_cb=self.handle_add_edit,
            delete_cb=self.handle_delete,
            search_cb=self.handle_search
        )
        self.current_sort = None
        self.current_search = ""
        self.update_view()

    def run(self):
        self.view.mainloop()

    def update_view(self):
        try:
            data = self.model.get_sorted_and_filtered(self.current_sort, self.current_search)
            self.view.display_items(data)

            stats = self.model.get_statistics()
            self.view.graph_frame.draw_chart(stats)
        except Exception as e:
            self.view.show_error("Eroare Bază de Date", f"Nu s-au putut încărca datele:\n{e}")

    def handle_sort(self, sort_mode):
        self.current_sort = sort_mode
        self.update_view()

    def handle_search(self, search_term):
        self.current_search = search_term
        self.update_view()

    def handle_add_edit(self, data, is_edit, old_id=None, dialog=None):
        try:
            clean_data = self.model.validate_data(data, is_edit=is_edit, old_id=old_id)

            dup = self.model.find_duplicate_image(
                clean_data.get("image_path", ""),
                exclude_id=old_id if is_edit else clean_data["item_id"]
            )
            if dup:
                if dup["reason"] == "content":
                    msg = (
                        f"Această fotografie (conținut identic) este deja folosită la produsul:\n"
                        f"«{dup['nume']}» (ID: {dup['item_id']}).\n\n"
                        f"Doriți să o folosiți oricum?"
                    )
                else:
                    msg = (
                        f"O fotografie cu același nume de fișier («{dup['filename']}»)\n"
                        f"este deja folosită la produsul «{dup['nume']}» (ID: {dup['item_id']}).\n\n"
                        f"Doriți să continuați?"
                    )
                if not self.view.ask_confirm("Atenție — Fotografie duplicată", msg, parent=dialog):
                    return False

            if is_edit:
                self.model.update_item(old_id, clean_data)
            else:
                self.model.add_item(clean_data)

            self.update_view()
            return True

        except ValidationError as ve:
            if dialog and hasattr(dialog, "highlight_field"):
                dialog.highlight_field(ve.field)
            self.view.show_error("Date invalide", str(ve), parent=dialog)
            return False

        except sqlite3.IntegrityError:
            if dialog and hasattr(dialog, "highlight_field"):
                dialog.highlight_field("item_id")
            self.view.show_error(
                "ID Duplicat",
                f"Există deja un produs cu ID-ul «{data.get('item_id', '')}»!",
                parent=dialog
            )
            return False

        except Exception as e:
            self.view.show_error("Eroare la salvare", f"A apărut o eroare neașteptată:\n{e}", parent=dialog)
            return False

    def handle_delete(self, item_id, item_name=""):
        label = f"«{item_name}» (ID: {item_id})" if item_name else f"cu ID-ul «{item_id}»"
        if not self.view.ask_confirm(
            "Confirmare ștergere",
            f"Sigur doriți să ștergeți produsul {label}?\nAceastă acțiune este ireversibilă."
        ):
            return

        try:
            self.model.remove_item(item_id)
            self.update_view()
        except Exception as e:
            self.view.show_error("Eroare la ștergere", f"Nu s-a putut șterge produsul:\n{e}")