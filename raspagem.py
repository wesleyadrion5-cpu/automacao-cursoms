from playwright.sync_api import sync_playwright


def passo1_mapeamento_passivo(url_principal):
    print("Iniciando o mapeamento passivo (Risco Zero)...")

    with sync_playwright() as p:
        # Abre o navegador de forma visível
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"Acessando: {url_principal}")
        page.goto(url_principal)

        # O script pausa aqui esperando sua ação
        print("\n" + "=" * 50)
        print(">>> AÇÃO NECESSÁRIA NO NAVEGADOR <<<")
        print("1. Faça o seu login.")
        print("2. Vá para a página principal onde aparece a lista de módulos ou aulas.")
        print("3. Só depois que a página com as aulas carregar, volte aqui.")
        input("Pressione ENTER aqui no terminal para eu copiar os links da tela...")
        print("=" * 50 + "\n")

        print("Lendo a página atual e extraindo os links...")

        # Busca todas as tags de link (<a>) na página
        links_encontrados = []
        elementos_a = page.query_selector_all("a")

        for elemento in elementos_a:
            texto = elemento.inner_text().strip()
            href = elemento.get_attribute("href")

            # Filtra links vazios, âncoras na mesma página ou scripts
            if href and not href.startswith("#") and "javascript:" not in href:
                links_encontrados.append(
                    f"Texto Visível: '{texto}'\nDestino (URL): {href}\n{'-'*50}"
                )

        # Salva tudo em um arquivo de texto limpo e fácil de ler
        nome_arquivo = "raio_x_dos_links.txt"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(f"Mapeamento da página: {page.url}\n")
            f.write("=" * 50 + "\n\n")
            f.write("\n".join(links_encontrados))

        print(f"Sucesso! Foram extraídos {len(links_encontrados)} links da página.")
        print(f"Tudo foi salvo no arquivo '{nome_arquivo}'.")

        browser.close()


# Execução
URL_ALVO = "https://cursoms.com.br/ead/admin/principal.asp"
passo1_mapeamento_passivo(URL_ALVO)
