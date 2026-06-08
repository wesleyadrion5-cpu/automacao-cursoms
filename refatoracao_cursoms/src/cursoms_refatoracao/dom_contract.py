from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MirrorExpectation:
    relative_path: str
    required_markers: tuple[str, ...] = field(default_factory=tuple)


def get_default_mirror_base() -> Path:
    return Path(r"C:\Users\Wesley Adrion\Documents\Todo Site novo e Antigo")


def build_contract() -> dict[str, list[MirrorExpectation]]:
    return {
        "plataforma_antiga": [
            MirrorExpectation(
                relative_path=r"cursoms.com.br\ead\admin\aulas\alterar_video.asp",
                required_markers=(
                    'name="assunto"',
                    'name="link"',
                    'name="ativavimeo"',
                    'name="vimeo"',
                ),
            ),
        ],
        "plataforma_nova": [
            MirrorExpectation(
                relative_path=r"novo.cursoms.com.br\modules.html",
                required_markers=(
                    'wire:model.debounce.500ms="search"',
                    "modules/lessons/",
                    "<h6>",
                ),
            ),
            MirrorExpectation(
                relative_path=r"novo.cursoms.com.br\modules\create.html",
                required_markers=(
                    'wire:model="module.name"',
                    'wire:model="module.time"',
                    'wire:model.debounce.1500ms="searchTerm"',
                    "Salvar",
                ),
            ),
            MirrorExpectation(
                relative_path=r"novo.cursoms.com.br\attachments\create.html",
                required_markers=(
                    'wire:model="attachment.filename"',
                    'wire:model="attachment.name"',
                    'wire:model="attachment.type"',
                    'wire:model="attachment.attachable_type"',
                    "Salvar",
                ),
            ),
        ],
    }
