import csv
import re
from config import CSV_PATH


def _parse_float(value: str, pattern: str = r"[^0-9.]") -> float:
    try:
        cleaned = re.sub(pattern, "", value.replace(",", "."))
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _parse_int(value: str) -> int:
    try:
        cleaned = re.sub(r"[^0-9]", "", value)
        return int(cleaned) if cleaned else 0
    except ValueError:
        return 0


def build_laptop_doc(
    manufacturer: str,
    model_name: str,
    category: str,
    screen_size: str,
    screen_inches: float,
    screen: str,
    cpu: str,
    ram: str,
    ram_gb: int,
    storage: str,
    gpu: str,
    os_name: str,
    os_version: str,
    weight: str,
    weight_kg: float,
    price_euros: float,
) -> dict:
    """Monta um documento padronizado de laptop para indexação no Elasticsearch."""
    os_full = f"{os_name} {os_version}".strip() if os_version else os_name
    specs_summary = (
        f"{category} | Tela {screen_size} {screen} | "
        f"CPU: {cpu} | RAM: {ram} | Armazenamento: {storage} | "
        f"GPU: {gpu} | OS: {os_full} | Peso: {weight}"
    )

    return {
        "title": f"{manufacturer} {model_name}".strip(),
        "manufacturer": manufacturer,
        "model_name": model_name,
        "category": category,
        "screen_size": screen_size,
        "screen_inches": float(screen_inches),
        "screen": screen,
        "cpu": cpu,
        "ram": ram,
        "ram_gb": int(ram_gb),
        "storage": storage,
        "gpu": gpu,
        "os": os_name,
        "os_version": os_version,
        "weight": weight,
        "weight_kg": float(weight_kg),
        "price_euros": float(price_euros),
        "specs_summary": specs_summary,
    }


def load_laptops_from_csv(csv_path: str = CSV_PATH) -> list[dict]:
    """Lê o arquivo laptops.csv e normaliza os campos para indexação no Elasticsearch."""
    laptops = []
    with open(csv_path, mode="r", encoding="latin-1") as file:
        for row in csv.DictReader(file):
            screen_size = row.get("Screen Size", "").strip()
            ram = row.get("RAM", "").strip()
            weight = row.get("Weight", "").strip()
            storage = (row.get(" Storage") or row.get("Storage") or "").strip()

            laptops.append(
                build_laptop_doc(
                    manufacturer=row.get("Manufacturer", "").strip(),
                    model_name=row.get("Model Name", "").strip(),
                    category=row.get("Category", "").strip(),
                    screen_size=screen_size,
                    screen_inches=_parse_float(screen_size),
                    screen=row.get("Screen", "").strip(),
                    cpu=row.get("CPU", "").strip(),
                    ram=ram,
                    ram_gb=_parse_int(ram),
                    storage=storage,
                    gpu=row.get("GPU", "").strip(),
                    os_name=row.get("Operating System", "").strip(),
                    os_version=row.get("Operating System Version", "").strip(),
                    weight=weight,
                    weight_kg=_parse_float(weight),
                    price_euros=_parse_float(row.get("Price (Euros)", "0")),
                )
            )
    return laptops
