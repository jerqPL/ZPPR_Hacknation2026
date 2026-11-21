import json
from pathlib import Path
from app.config import settings
from app.models.parameters import LegalParameters


class ParameterStore:
    """Przechowuje i udostępnia edytowalne parametry prawne (panel administracyjny)."""

    def __init__(self, path: Path | None = None):
        self.path = path or (settings.data_dir / "legal_parameters.json")
        # Oryginalne ustawowe wartości domyślne 2026 są niezmienne niezależnie od restartu kontenera
        self._factory_defaults = LegalParameters()
        self._current = self._load_from_disk()

    def _load_from_disk(self) -> LegalParameters:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return LegalParameters(**data)
        return self._factory_defaults.model_copy(deep=True)

    def get(self) -> LegalParameters:
        return self._current

    def update(self, new_params: LegalParameters) -> LegalParameters:
        self._current = new_params
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(new_params.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return self._current

    def reset(self) -> LegalParameters:
        self._current = self._factory_defaults.model_copy(deep=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._current.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return self._current


parameter_store = ParameterStore()
