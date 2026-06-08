# Refatoracao CursoMS

Esta pasta concentra a proxima fase de evolucao do robo de migracao entre a
plataforma antiga e a nova do CursoMS.

Objetivos desta area:

- preservar os scripts originais da raiz do projeto
- organizar as melhorias por assunto
- reaproveitar o espelho local das plataformas
- reduzir manutencao espalhada em um unico arquivo gigante

Estrutura:

- `scripts/`
  Scripts de trabalho e utilitarios offline.
- `src/cursoms_refatoracao/`
  Helpers reutilizaveis para matching, regras especiais e contrato do DOM.
- `docs/`
  Analises e roadmap da refatoracao.
- `referencias/`
  Manifestos e apontamentos do espelho das plataformas.

Arquivos importantes:

- `scripts/Meus testes copy refatoracao.py`
  Copia de trabalho do script melhorado atual.
- `scripts/validar_espelho.py`
  Valida se os arquivos espelhados ainda contem os seletores/trechos esperados.
- `scripts/indice_modulos_espelho.py`
  Extrai um indice offline de modulos do `modules.html`.

Referencia externa usada nesta fase:

- `C:\\Users\\Wesley Adrion\\Documents\\Todo Site novo e Antigo`

Proximo passo recomendado:

1. validar o espelho com `python refatoracao_cursoms/scripts/validar_espelho.py`
2. gerar o indice de modulos com `python refatoracao_cursoms/scripts/indice_modulos_espelho.py`
3. comecar a extrair helpers do script grande para `src/cursoms_refatoracao/`
