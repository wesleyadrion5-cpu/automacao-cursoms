import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configurações do navegador
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # Remova o comentário desta linha se quiser rodar invisível no futuro
driver = webdriver.Chrome(options=options)

# 1. Fazer o Login no site novo
print("Iniciando login...")
driver.get("https://novo.cursoms.com.br/login")

try:
    # Preenche as credenciais automaticamente
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(
        "wesleyadrion5@gmail.com"
    )

    driver.find_element(By.NAME, "password").send_keys("123456789")

    # Clica no botão de entrar (ajuste o seletor do botão se necessário)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("Login realizado!")
    time.sleep(3)  # Aguarda o dashboard carregar
except Exception as e:
    print(f"Erro no login: {e}")

# Lista que vai guardar os dicionários com os dados coletados
dados_extraidos = []

# No seu HTML, a última página era a 293. Se esse número mudar, basta alterar aqui.
ultima_pagina = 293

# 2. Navegar página por página usando a URL
for pagina in range(1, ultima_pagina + 1):
    url_alvo = f"https://novo.cursoms.com.br/modules?page={pagina}"
    print(f"Extraindo dados da página {pagina} de {ultima_pagina}...")

    driver.get(url_alvo)

    try:
        # Aguardar a tabela com a classe 'dash_list' carregar na tela
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dash_list"))
        )
        # Pausa extra breve de segurança por conta do carregamento assíncrono do Livewire
        time.sleep(1)

        # Encontrar todas as linhas (tr) dentro do corpo da tabela (tbody)
        linhas_tabela = driver.find_elements(By.CSS_SELECTOR, "table.dash_list tbody tr")

        for linha in linhas_tabela:
            try:
                # O nome do módulo está dentro da tag <h6>
                nome_modulo = linha.find_element(By.TAG_NAME, "h6").text.strip()

                # O nome do curso está na 3ª coluna (td), dentro da tag 'a' com a classe 'badge'
                nome_curso = linha.find_element(
                    By.CSS_SELECTOR, "td:nth-child(3) a.badge"
                ).text.strip()

                # Adiciona na nossa lista
                dados_extraidos.append({"Módulo": nome_modulo, "Curso": nome_curso})
            except Exception as e:
                # Se falhar em uma linha específica (ex: linha vazia), ele avisa e continua
                print(f"Erro ao extrair uma linha na página {pagina}.")
                continue

    except Exception as e:
        print(f"Erro ao carregar a tabela na página {pagina}: {e}")

# Fecha o navegador
driver.quit()

# 3. Gerar o arquivo Excel
print(f"\nExtração concluída! Total de módulos capturados: {len(dados_extraidos)}")
print("Gerando arquivo Excel...")

# Converte a lista para um DataFrame do Pandas e salva em xlsx
df = pd.DataFrame(dados_extraidos)
df.to_excel("relatorio_modulos_site_novo.xlsx", index=False)

print("Arquivo 'relatorio_modulos_site_novo.xlsx' salvo com sucesso!")
