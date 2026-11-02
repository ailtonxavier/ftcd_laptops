import csv
import os
import re

CSV_PATH = os.path.join(os.path.dirname(__file__), "laptops.csv")


def load_laptops_from_csv(csv_path: str = CSV_PATH) -> list[dict]:
    """Lê o arquivo laptops.csv e normaliza os campos para indexação no Elasticsearch."""
    laptops = []
    with open(csv_path, mode="r", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            manufacturer = row.get("Manufacturer", "").strip()
            model_name = row.get("Model Name", "").strip()
            category = row.get("Category", "").strip()
            screen_size_str = row.get("Screen Size", "").strip()
            screen = row.get("Screen", "").strip()
            cpu = row.get("CPU", "").strip()
            ram_str = row.get("RAM", "").strip()
            storage = (row.get(" Storage") or row.get("Storage") or "").strip()
            gpu = row.get("GPU", "").strip()
            os_name = row.get("Operating System", "").strip()
            os_version = row.get("Operating System Version", "").strip()
            weight_str = row.get("Weight", "").strip()
            price_str = row.get("Price (Euros)", "0").strip()

            # Conversões numéricas seguras para filtros de range e métricas
            try:
                price_euros = float(price_str.replace(",", "."))
            except ValueError:
                price_euros = 0.0

            try:
                ram_gb = int(re.sub(r"[^0-9]", "", ram_str))
            except ValueError:
                ram_gb = 0

            try:
                screen_inches = float(re.sub(r"[^0-9.]", "", screen_size_str))
            except ValueError:
                screen_inches = 0.0

            try:
                weight_kg = float(re.sub(r"[^0-9.]", "", weight_str))
            except ValueError:
                weight_kg = 0.0

            os_full = f"{os_name} {os_version}".strip() if os_version else os_name
            title = f"{manufacturer} {model_name}"
            specs_summary = (
                f"{category} | Tela {screen_size_str} {screen} | "
                f"CPU: {cpu} | RAM: {ram_str} | Armazenamento: {storage} | "
                f"GPU: {gpu} | OS: {os_full} | Peso: {weight_str}"
            )

            laptops.append(
                {
                    "title": title,
                    "manufacturer": manufacturer,
                    "model_name": model_name,
                    "category": category,
                    "screen_size": screen_size_str,
                    "screen_inches": screen_inches,
                    "screen": screen,
                    "cpu": cpu,
                    "ram": ram_str,
                    "ram_gb": ram_gb,
                    "storage": storage,
                    "gpu": gpu,
                    "os": os_name,
                    "os_version": os_version,
                    "weight": weight_str,
                    "weight_kg": weight_kg,
                    "price_euros": price_euros,
                    "specs_summary": specs_summary,
                }
            )
    return laptops
