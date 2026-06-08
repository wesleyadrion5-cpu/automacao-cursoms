from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SelectorMap:
    modules_search_css: str = 'input[wire\\:model\\.debounce\\.500ms="search"]'
    module_name_css: str = 'input[wire\\:model="module.name"]'
    module_time_css: str = 'input[wire\\:model="module.time"]'
    searchable_term_css: str = 'input[wire\\:model\\.debounce\\.1500ms="searchTerm"]'
    attachment_file_css: str = 'input[wire\\:model="attachment.filename"]'
    attachment_name_css: str = 'input[wire\\:model="attachment.name"]'
    attachment_type_css: str = 'select[wire\\:model="attachment.type"]'
    attachment_attachable_css: str = 'select[wire\\:model="attachment.attachable_type"]'
    old_video_title_name: str = "assunto"
    old_video_link_name: str = "link"
    old_video_channel_name: str = "ativavimeo"
    old_video_vimeo_name: str = "vimeo"


SELECTORS = SelectorMap()
