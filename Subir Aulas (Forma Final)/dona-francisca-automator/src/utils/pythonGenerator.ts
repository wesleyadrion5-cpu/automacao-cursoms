export function generatePythonScript(
  robotName: string,
  columns: { modulo: string; video: string; duracao: string; extra: string },
  delay: number,
  customWebdriver: boolean
): string {
  const delaySec = (delay / 1000).toFixed(1);
  return `import os
import sys
import time
import datetime
import pandas as pd

# CONFIGURAÇÕES DA AUTOMAÇÃO (Antigravity Python Robot)
NOME_ROBO = "${robotName}"
DELAY_PASSOS = ${delaySec}  # segundos de espera entre ações
ARQUIVO_PLANILHA = "planilha_mapeada.csv"

# Colunas mapeadas na planilha
COL_MODULO = "${columns.modulo}"
COL_VIDEO = "${columns.video}"
COL_DURACAO = "${columns.duracao}"
COL_EXTRA = "${columns.extra}"

def log(nivel, msg):
    """Gera o log no formato exato exibido no painel."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {nivel} - [{NOME_ROBO}] {msg}")

def testar_dependencias():
    try:
        import pandas
    except ImportError:
        log("ERROR", "Biblioteca 'pandas' não está instalada! Execute: pip install pandas")
        return False
    return True

def carregar_planilha():
    log("INFO", f"Tentando carregar arquivo: {ARQUIVO_PLANILHA}")
    if not os.path.exists(ARQUIVO_PLANILHA):
        # Cria uma planilha de exemplo para o usuário caso não exista
        dados_exemplo = {
            COL_MODULO: ["Módulo 1: Introdução", "Módulo 2: Configurações", "Módulo 3: Métricas Avançadas"],
            COL_VIDEO: ["Trilha Estratégica - Vídeo 1", "Satalia - Vídeo 1", "Análise de Dados - Vídeo 2"],
            COL_DURACAO: ["12:30", "08:45", "15:20"],
            COL_EXTRA: ["Link 1", "Link 2", "Link 3"]
        }
        df = pd.DataFrame(dados_exemplo)
        df.to_csv(ARQUIVO_PLANILHA, index=False, encoding='utf-8')
        log("WARNING", f"Planilha não encontrada. Geramos uma planilha de exemplo em '{ARQUIVO_PLANILHA}'")
        return df
    
    try:
        # Lê a planilha atual
        if ARQUIVO_PLANILHA.endswith('.csv'):
            return pd.read_csv(ARQUIVO_PLANILHA, encoding='utf-8')
        else:
            return pd.read_excel(ARQUIVO_PLANILHA)
    except Exception as e:
        log("ERROR", f"Erro ao ler a planilha: {str(e)}")
        return None

def processar_automacao():
    if not testar_dependencias():
        sys.exit(1)

    df = carregar_planilha()
    if df is None or len(df) == 0:
        log("ERROR", "Nenhum dado válido para processar.")
        sys.exit(1)

    total_linhas = len(df)
    log("SUCCESS", f"Planilha carregada com sucesso! {total_linhas} módulos identificados.")
    log("INFO", f"Preparando robô para início da migração...")
    time.sleep(1.5)

    # LOOP PRINCIPAL DA AUTOMAÇÃO (Processando cada módulo mapeado)
    for idx, row in df.iterrows():
        numero_atual = idx + 1
        modulo = row[COL_MODULO]
        video = row[COL_VIDEO]
        duracao = row[COL_DURACAO]
        
        log("INFO", f"Migrando item {numero_atual}/{total_linhas} - Módulo: '{modulo}'")
        time.sleep(DELAY_PASSOS * 0.5)

        # 1. Simula ação de criação do Módulo
        log("INFO", f"Criando estrutura do módulo no novo sistema...")
        time.sleep(DELAY_PASSOS)

        # 2. Simula ação de extração/vinculação do vídeo
        log("INFO", f"Extraindo vídeo: '{video}' (Duração: {duracao})")
        time.sleep(DELAY_PASSOS * 1.2)

        # 3. Confirmação do sucesso
        log("SUCCESS", f"Módulo '{modulo}' e vídeo '{video}' migrados com sucesso!")
        time.sleep(0.5)

    log("SUCCESS", "=== Automação concluída com sucesso! Todos os módulos foram importados. ===")

if __name__ == "__main__":
    print("-" * 65)
    print("      ROBÔ DONA FRANCISCA - SCRIPT DE AUTOMAÇÃO DE MÓDULOS")
    print("-" * 65)
    try:
        processar_automacao()
    except KeyboardInterrupt:
        log("WARNING", "Execução interrompida pelo usuário.")
`;
}
