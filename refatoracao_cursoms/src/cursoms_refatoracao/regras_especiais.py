from dataclasses import dataclass

from .matching import is_plano_estudos_module


PLANO_ESTUDOS_TITULO = "Acesse seu Material"
PLANO_ESTUDOS_VIMEO = "1173006649"


@dataclass(slots=True)
class VideoPayload:
    titulo: str
    canal: str
    valor: str
    origem: str


def resolve_video_payload(
    module_name: str,
    title: str = "",
    vimeo: str = "",
    youtube_link: str = "",
    canal: str = "",
) -> VideoPayload | None:
    if is_plano_estudos_module(module_name):
        return VideoPayload(
            titulo=PLANO_ESTUDOS_TITULO,
            canal="vimeo",
            valor=PLANO_ESTUDOS_VIMEO,
            origem="regra_especial_plano_estudos",
        )

    clean_title = (title or "").strip()
    clean_vimeo = (vimeo or "").strip()
    clean_youtube = (youtube_link or "").strip()
    clean_canal = (canal or "").strip().lower()

    if clean_vimeo.isdigit():
        return VideoPayload(
            titulo=clean_title,
            canal="vimeo",
            valor=clean_vimeo,
            origem="vimeo_extraido",
        )

    if clean_youtube:
        return VideoPayload(
            titulo=clean_title,
            canal="youtube",
            valor=clean_youtube,
            origem="youtube_extraido",
        )

    if clean_canal == "youtube" and clean_youtube:
        return VideoPayload(
            titulo=clean_title,
            canal="youtube",
            valor=clean_youtube,
            origem="youtube_canal_indicado",
        )

    return None
