# Roadmap da Refatoracao

## Fase 1 - Organizacao

- criar uma copia de trabalho do robo
- separar documentacao, referencias e utilitarios offline
- centralizar contrato do DOM da plataforma antiga e nova

## Fase 2 - Robustez do Selenium

- concentrar troca segura de abas e sessao
- reduzir `time.sleep()` onde couber
- padronizar captura de screenshot e HTML ao falhar

## Fase 3 - Matching de Modulos

- normalizar nomes com acentos, pontuacao e espacos extras
- aceitar variacoes reais de `Plano de Estudos`
- comparar nome, professor e pistas do curso antes de criar modulo
- montar cache local dos modulos ja existentes no site novo

## Fase 4 - Videos

- unificar regra de Vimeo, YouTube e excecoes especiais
- validar payload antes de tentar cadastrar
- registrar motivo de pulo quando o conteudo nao estiver apto

## Fase 5 - Materiais e Slides

- usar seletores exatos de `attachments/create.html`
- separar tipo de anexo por regra
- evitar reenvio de arquivos ja existentes

## Fase 6 - Auditoria Offline

- validar contrato do DOM com o espelho salvo
- extrair indice offline de modulos da plataforma nova
- criar modo auditoria antes da migracao real
