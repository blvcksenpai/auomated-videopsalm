"""Service-plan and multi-translation models for phase-2 workflow support."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PassageItem:
    reference: str
    label: str
    translation_id: str = "web"
    language: str = "en"

    def __post_init__(self) -> None:
        if not self.reference.strip() or not self.label.strip():
            raise ValueError("passage reference and label are required")
        if not self.translation_id.strip() or not self.language.strip():
            raise ValueError("translation_id and language are required")


@dataclass(frozen=True, slots=True)
class ServicePlan:
    id: str
    name: str
    translation_id: str = "web"
    language: str = "en"
    items: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("service plan id and name are required")
        if not self.translation_id.strip() or not self.language.strip():
            raise ValueError("translation_id and language are required")

    def song_ids(self) -> tuple[str, ...]:
        return tuple(item.target_id for item in self.items if getattr(item, 'kind', None) == 'song')

    def passage_ids(self) -> tuple[str, ...]:
        return tuple(item.reference for item in self.items if isinstance(item, PassageItem))
