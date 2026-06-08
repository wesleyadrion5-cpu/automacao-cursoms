# Analise do Espelho das Plataformas

Diretorio base:

- `C:\\Users\\Wesley Adrion\\Documents\\Todo Site novo e Antigo`

## Plataforma antiga

Arquivo-chave:

- `cursoms.com.br\\ead\\admin\\aulas\\alterar_video.asp`

Campos confirmados:

- titulo: `name="assunto"`
- link: `name="link"`
- canal: `name="ativavimeo"`
- vimeo: `name="vimeo"`

## Plataforma nova

Arquivos-chave:

- `novo.cursoms.com.br\\modules.html`
- `novo.cursoms.com.br\\modules\\create.html`
- `novo.cursoms.com.br\\attachments\\create.html`

Seletores confirmados:

- busca de modulo: `wire:model.debounce.500ms="search"`
- nome do modulo: `wire:model="module.name"`
- carga horaria: `wire:model="module.time"`
- busca do curso/professor: `wire:model.debounce.1500ms="searchTerm"`
- upload do arquivo: `wire:model="attachment.filename"`
- nome do anexo: `wire:model="attachment.name"`
- tipo do anexo: `wire:model="attachment.type"`
- vinculo do anexo: `wire:model="attachment.attachable_type"`

Padrao util para matching:

- o nome do modulo aparece em `<h6>`
- o professor aparece na mesma linha do modulo
- o link de aulas fica na linha e aponta para `modules/lessons/<uuid>`

Conclusao:

Ja temos base suficiente para:

- centralizar seletores da plataforma nova
- validar DOM offline antes de rodar Selenium
- melhorar matching de modulos com base em nome e professor
