import os
import math
import shutil
import hashlib
from abc import ABC, abstractmethod
from PIL import Image, UnidentifiedImageError
from database import DatabaseManager, APP_DIR

SUPPORTED_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
FORBIDDEN_ID_CHARS = set('\\/:*?"<>|')


class ValidationError(Exception):
    """Ошибка пользовательского ввода с привязкой к конкретному полю."""
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


class IProdus(ABC):
    @abstractmethod
    def get_id(self): pass
    @abstractmethod
    def get_nume(self): pass
    @abstractmethod
    def get_pret(self): pass
    @abstractmethod
    def get_detalii(self): pass
    @abstractmethod
    def get_image_path(self): pass


class Produs(IProdus):
    def __init__(self, item_id, nume, pret, image_path="", image_orig_name=""):
        self.item_id = str(item_id)
        self.nume = str(nume)
        self.pret = float(pret)
        self.image_path = str(image_path) if image_path else ""
        self.image_orig_name = str(image_orig_name) if image_orig_name else ""

    def get_id(self): return self.item_id
    def get_nume(self): return self.nume
    def get_pret(self): return self.pret
    def get_image_path(self): return self.image_path
    def get_image_orig_name(self): return self.image_orig_name


class AerConditionat(Produs):
    def __init__(self, item_id, nume, pret, arie, is_inverter, has_wifi, image_path="", image_orig_name=""):
        super().__init__(item_id, nume, pret, image_path, image_orig_name)
        self.arie = float(arie)
        self.is_inverter = bool(is_inverter)
        self.has_wifi = bool(has_wifi)

    def get_detalii(self):
        inv = "Da" if self.is_inverter else "Nu"
        wifi = "Da" if self.has_wifi else "Nu"
        return f"Arie: {self.arie}m² | Inverter: {inv} | Wi-Fi: {wifi}"


class Frigider(Produs):
    def __init__(self, item_id, nume, pret, volum, is_nofrost, are_dozator, image_path="", image_orig_name=""):
        super().__init__(item_id, nume, pret, image_path, image_orig_name)
        self.volum = float(volum)
        self.is_nofrost = bool(is_nofrost)
        self.are_dozator = bool(are_dozator)

    def get_detalii(self):
        nf = "Da" if self.is_nofrost else "Nu"
        doz = "Da" if self.are_dozator else "Nu"
        return f"Volum: {self.volum}L | NoFrost: {nf} | Dozator: {doz}"


class MasinaSpalat(Produs):
    def __init__(self, item_id, nume, pret, capacitate, rpm, is_smart, image_path="", image_orig_name=""):
        super().__init__(item_id, nume, pret, image_path, image_orig_name)
        self.capacitate = float(capacitate)
        self.rpm = int(rpm)
        self.is_smart = bool(is_smart)

    def get_detalii(self):
        smart = "Da" if self.is_smart else "Nu"
        return f"Capacitate: {self.capacitate}kg | Viteză: {self.rpm} RPM | Smart: {smart}"


class ModelMagazin:
    def __init__(self):
        self.db = DatabaseManager()
        self.pics_dir = os.path.join(APP_DIR, "pics")

    def _row_to_produs(self, row):
        t = row["type"]
        keys = row.keys()
        img_path = row["image_path"] if "image_path" in keys and row["image_path"] else ""
        orig_name = row["image_orig_name"] if "image_orig_name" in keys and row["image_orig_name"] else ""
        if t == "AerConditionat":
            return AerConditionat(row["item_id"], row["nume"], row["pret"], row["arie"], row["is_inverter"], row["has_wifi"], img_path, orig_name)
        elif t == "Frigider":
            return Frigider(row["item_id"], row["nume"], row["pret"], row["volum"], row["is_nofrost"], row["are_dozator"], img_path, orig_name)
        elif t == "MasinaSpalat":
            return MasinaSpalat(row["item_id"], row["nume"], row["pret"], row["capacitate"], row["rpm"], row["is_smart"], img_path, orig_name)
        return None

    def _id_exists(self, item_id):
        row = self.db.fetch_one("SELECT 1 FROM produse WHERE item_id = ?", (item_id,))
        return row is not None

    @staticmethod
    def _parse_positive_float(raw_val, field_name, label, max_val=1_000_000):
        text = str(raw_val).strip().replace(",", ".")
        if not text:
            raise ValidationError(f"Câmpul «{label}» este obligatoriu!", field=field_name)
        try:
            val = float(text)
        except ValueError:
            raise ValidationError(f"Câmpul «{label}» trebuie să fie un număr valid (ex: 1200 sau 1200.50)!", field=field_name)
        if not math.isfinite(val) or val <= 0:
            raise ValidationError(f"Câmpul «{label}» trebuie să fie mai mare decât 0!", field=field_name)
        if val > max_val:
            raise ValidationError(f"Valoarea din câmpul «{label}» este prea mare (maxim {max_val})!", field=field_name)
        return val

    @staticmethod
    def _parse_positive_int(raw_val, field_name, label, max_val=100_000):
        text = str(raw_val).strip()
        if not text:
            raise ValidationError(f"Câmpul «{label}» este obligatoriu!", field=field_name)
        try:
            val = int(text)
        except ValueError:
            raise ValidationError(f"Câmpul «{label}» trebuie să fie un număr întreg pozitiv (ex: 1200)!", field=field_name)
        if val <= 0 or val > max_val:
            raise ValidationError(f"Câmpul «{label}» trebuie să fie între 1 și {max_val}!", field=field_name)
        return val

    @staticmethod
    def _file_sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def validate_data(self, data, is_edit=False, old_id=None):
        """Проверяет все поля и файл изображения до записи в БД."""
        cleaned = dict(data)

        # 1. Проверка ID
        item_id = str(data.get("item_id", "")).strip()
        if not item_id:
            raise ValidationError("ID-ul produsului nu poate fi gol!", field="item_id")
        if any(ch in FORBIDDEN_ID_CHARS for ch in item_id):
            raise ValidationError(
                'ID-ul nu poate conține caracterele speciale: \\ / : * ? " < > |',
                field="item_id"
            )
        if len(item_id) > 50:
            raise ValidationError("ID-ul produsului este prea lung (maxim 50 caractere)!", field="item_id")

        if not is_edit and self._id_exists(item_id):
            raise ValidationError(
                f"Există deja un produs cu ID-ul «{item_id}»!\nAlegeți un alt ID unic.",
                field="item_id"
            )
        if is_edit and item_id != old_id and self._id_exists(item_id):
            raise ValidationError(
                f"Nu puteți schimba ID-ul în «{item_id}», deoarece este deja folosit de alt produs!",
                field="item_id"
            )
        cleaned["item_id"] = item_id

        # 2. Проверка названия
        nume = str(data.get("nume", "")).strip()
        if not nume:
            raise ValidationError("Numele / modelul produsului nu poate fi gol!", field="nume")
        if len(nume) < 2:
            raise ValidationError("Numele produsului trebuie să conțină cel puțin 2 caractere!", field="nume")
        cleaned["nume"] = nume

        # 3. Проверка цены
        cleaned["pret"] = self._parse_positive_float(data.get("pret", ""), "pret", "Preț (MDL)", max_val=10_000_000)

        # 4. Проверка специфичных полей категории
        tip = data.get("type")
        if tip == "AerConditionat":
            cleaned["arie"] = self._parse_positive_float(data.get("arie", ""), "arie", "Suprafață (m²)", max_val=10_000)
        elif tip == "Frigider":
            cleaned["volum"] = self._parse_positive_float(data.get("volum", ""), "volum", "Volum (L)", max_val=10_000)
        elif tip == "MasinaSpalat":
            cleaned["capacitate"] = self._parse_positive_float(data.get("capacitate", ""), "capacitate", "Capacitate (kg)", max_val=500)
            cleaned["rpm"] = self._parse_positive_int(data.get("rpm", ""), "rpm", "Rotații (RPM)", max_val=10_000)
        else:
            raise ValidationError("Tip de produs necunoscut!", field="type")

        # 5. Проверка файла изображения (если путь указан)
        img_path = str(data.get("image_path", "")).strip().strip('"')
        if img_path:
            if os.path.isdir(img_path):
                raise ValidationError("Calea indicată este un dosar, nu un fișier imagine!", field="image_path")
            if not os.path.exists(img_path):
                raise ValidationError(f"Fișierul imagine nu a fost găsit:\n{img_path}", field="image_path")
            ext = os.path.splitext(img_path)[1].lower()
            if ext not in SUPPORTED_IMG_EXTS:
                raise ValidationError(
                    "Format de imagine nesuportat!\nFolosiți PNG, JPG, JPEG, WEBP sau BMP.",
                    field="image_path"
                )
            try:
                with Image.open(img_path) as test_img:
                    test_img.verify()
            except (UnidentifiedImageError, OSError, Exception):
                raise ValidationError(
                    "Fișierul selectat este deteriorat sau nu este o imagine validă!",
                    field="image_path"
                )
        cleaned["image_path"] = img_path
        return cleaned

    def find_duplicate_image(self, image_path, exclude_id=None):
        """
        Проверяет, не используется ли уже фото с таким же именем файла
        или идентичным содержимым (SHA-256) у другого товара.
        Возвращает dict с информацией о совпадении или None.
        """
        if not image_path or not os.path.isfile(image_path):
            return None

        new_basename = os.path.basename(image_path).lower()
        try:
            new_hash = self._file_sha256(image_path)
        except OSError:
            return None

        rows = self.db.fetch_all("SELECT item_id, nume, image_path, image_orig_name FROM produse")
        for row in rows:
            other_id = row["item_id"]
            if exclude_id and other_id == exclude_id:
                continue

            other_path = row["image_path"] or ""
            other_orig = (row["image_orig_name"] or "").lower()

            # Совпадение по содержимому файла (даже если файл переименован)
            if other_path and os.path.isfile(other_path):
                try:
                    if self._file_sha256(other_path) == new_hash:
                        return {
                            "reason": "content",
                            "item_id": other_id,
                            "nume": row["nume"],
                            "filename": os.path.basename(image_path)
                        }
                except OSError:
                    pass

            # Совпадение по исходному имени файла (например, оба называются photo.png)
            if other_orig and other_orig == new_basename:
                return {
                    "reason": "name",
                    "item_id": other_id,
                    "nume": row["nume"],
                    "filename": os.path.basename(image_path)
                }

        return None

    def _store_product_image(self, src_path, item_id, old_id=None, existing_orig_name=""):
        """
        Копирует картинку в локальную папку pics/ под именем {item_id}{ext},
        чтобы исключить перезапись файлов с одинаковыми именами и потерю фото.
        """
        if not src_path:
            # Если пользователь очистил фото, удаляем старую копию из pics/
            self._remove_managed_images(old_id or item_id)
            return "", ""

        os.makedirs(self.pics_dir, exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower()
        target_path = os.path.join(self.pics_dir, f"{item_id}{ext}")

        abs_src = os.path.abspath(src_path)
        abs_target = os.path.abspath(target_path)

        # Определяем исходное имя файла для отслеживания дубликатов названий
        if abs_src.startswith(os.path.abspath(self.pics_dir) + os.sep) and existing_orig_name:
            orig_name = existing_orig_name
        else:
            orig_name = os.path.basename(src_path)

        if abs_src != abs_target:
            try:
                shutil.copy2(src_path, target_path)
            except OSError as e:
                raise ValidationError(f"Nu s-a putut copia imaginea în folderul aplicației:\n{e}", field="image_path")

        # Удаляем старые файлы в pics/, если изменился ID или расширение (.png -> .jpg)
        for check_id in {item_id, old_id}:
            if not check_id:
                continue
            for old_ext in SUPPORTED_IMG_EXTS:
                candidate = os.path.join(self.pics_dir, f"{check_id}{old_ext}")
                if os.path.abspath(candidate) != abs_target and os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except OSError:
                        pass

        return target_path, orig_name

    def _remove_managed_images(self, item_id):
        if not item_id or not os.path.isdir(self.pics_dir):
            return
        for ext in SUPPORTED_IMG_EXTS:
            candidate = os.path.join(self.pics_dir, f"{item_id}{ext}")
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except OSError:
                    pass

    def add_item(self, data):
        clean = self.validate_data(data, is_edit=False)
        saved_img_path, orig_name = self._store_product_image(clean["image_path"], clean["item_id"])

        query = """
        INSERT INTO produse (
            item_id, type, nume, pret, arie, is_inverter, has_wifi,
            volum, is_nofrost, are_dozator, capacitate, rpm, is_smart,
            image_path, image_orig_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            clean["item_id"], clean["type"], clean["nume"], clean["pret"],
            clean.get("arie"), clean.get("is_inverter"), clean.get("has_wifi"),
            clean.get("volum"), clean.get("is_nofrost"), clean.get("are_dozator"),
            clean.get("capacitate"), clean.get("rpm"), clean.get("is_smart"),
            saved_img_path, orig_name
        )
        self.db.execute_query(query, params)

    def remove_item(self, item_id):
        self.db.execute_query("DELETE FROM produse WHERE item_id = ?", (item_id,))
        self._remove_managed_images(item_id)

    def update_item(self, old_item_id, data):
        clean = self.validate_data(data, is_edit=True, old_id=old_item_id)

        old_row = self.db.fetch_one("SELECT image_orig_name FROM produse WHERE item_id = ?", (old_item_id,))
        prev_orig_name = old_row["image_orig_name"] if old_row and old_row["image_orig_name"] else ""

        saved_img_path, orig_name = self._store_product_image(
            clean["image_path"], clean["item_id"], old_id=old_item_id, existing_orig_name=prev_orig_name
        )

        # Атомарный UPDATE: если что-то пойдёт не так, старый товар не потеряется
        query = """
        UPDATE produse SET
            item_id = ?, type = ?, nume = ?, pret = ?,
            arie = ?, is_inverter = ?, has_wifi = ?,
            volum = ?, is_nofrost = ?, are_dozator = ?,
            capacitate = ?, rpm = ?, is_smart = ?,
            image_path = ?, image_orig_name = ?
        WHERE item_id = ?
        """
        params = (
            clean["item_id"], clean["type"], clean["nume"], clean["pret"],
            clean.get("arie"), clean.get("is_inverter"), clean.get("has_wifi"),
            clean.get("volum"), clean.get("is_nofrost"), clean.get("are_dozator"),
            clean.get("capacitate"), clean.get("rpm"), clean.get("is_smart"),
            saved_img_path, orig_name,
            old_item_id
        )
        self.db.execute_query(query, params)

    def get_sorted_and_filtered(self, sort_mode=None, search_term=""):
        query = "SELECT * FROM produse WHERE nume LIKE ?"
        params = (f"%{search_term}%",)

        if sort_mode == "nume":
            query += " ORDER BY nume COLLATE NOCASE ASC"
        elif sort_mode == "pret_asc":
            query += " ORDER BY pret ASC"
        elif sort_mode == "pret_desc":
            query += " ORDER BY pret DESC"

        rows = self.db.fetch_all(query, params)
        return [self._row_to_produs(row) for row in rows]

    def get_statistics(self):
        query = """
        SELECT type, AVG(pret) as avg_pret, COUNT(item_id) as count_items 
        FROM produse 
        GROUP BY type
        """
        rows = self.db.fetch_all(query)

        avg_stats = {}
        count_stats = {}
        for row in rows:
            avg_stats[row["type"]] = round(row["avg_pret"], 2)
            count_stats[row["type"]] = row["count_items"]

        return {"avg": avg_stats, "count": count_stats}