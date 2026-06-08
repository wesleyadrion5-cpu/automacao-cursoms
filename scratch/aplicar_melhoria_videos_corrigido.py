import os

novo_bloco = '''    def _localizar_elemento_recursivo_frames(self, xpath):
        """
        Busca um elemento por XPath varrendo recursivamente a página principal e todos os frames/iframes.
        Retorna o elemento encontrado ou None.
        Ao final da execução (seja sucesso ou falha), restaura o driver para o default_content().
        """
        def _buscar():
            alvo = self.driver.find_elements(By.XPATH, xpath)
            if alvo:
                return alvo[0]
            
            # Buscar frames no contexto atual
            frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
            for f in frames:
                try:
                    self.driver.switch_to.frame(f)
                    res = _buscar()
                    if res:
                        return res
                    self.driver.switch_to.parent_frame()
                except:
                    try:
                        self.driver.switch_to.parent_frame()
                    except:
                        pass
            return None

        self.driver.switch_to.default_content()
        el = _buscar()
        if not el:
            self.driver.switch_to.default_content()
        return el

    def _clicar_elemento_em_frames(self, xpath):
        el = self._localizar_elemento_recursivo_frames(xpath)
        if el:
            try:
                self.driver.execute_script("arguments[0].click();", el)
                return True
            except Exception as e:
                self.log("ERRO", f"Erro ao clicar no elemento {xpath} no frame: {str(e)}")
        return False

    def _extrair_dados_ativos(self, capturar_videos=True, capturar_materiais=True):
        d_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()

        if capturar_videos:
            self.log("INFO", "Iniciando captura de vídeos do módulo no site antigo...")
            botao_video = self._localizar_elemento_recursivo_frames("//a[contains(@href, 'videos.asp')]")
            if botao_video:
                self.log("INFO", "Botão de vídeos (videos.asp) encontrado! Acessando...")
                href_videos = botao_video.get_attribute("href") or ""
                if href_videos and not href_videos.startswith("#") and "javascript" not in href_videos:
                    self._abrir_url_com_certificado(href_videos, "lista de vídeos do site antigo")
                else:
                    self.driver.execute_script("arguments[0].click();", botao_video)
                time.sleep(2.5)
                
                try:
                    self.driver.switch_to.default_content()
                    p = self.driver.find_element(
                        By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                    )
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(0.5)
                    self.driver.execute_script(
                        "arguments[0].click();",
                        self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                    )
                    time.sleep(2.5)
                except:
                    pass

                def buscar_todos_links(lista_acumulada):
                    lk = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'alterar_video.asp')]")
                    for l in lk:
                        href = l.get_attribute("href")
                        if href and href not in lista_acumulada:
                            lista_acumulada.append(href)
                    
                    frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                    for f in frames:
                        try:
                            self.driver.switch_to.frame(f)
                            buscar_todos_links(lista_acumulada)
                            self.driver.switch_to.parent_frame()
                        except:
                            try:
                                self.driver.switch_to.parent_frame()
                            except:
                                pass

                self.log("INFO", "Procurando links de vídeos (alterar_video.asp)...")
                self.driver.switch_to.default_content()
                urls = []
                buscar_todos_links(urls)
                
                if urls:
                    self.log("INFO", f"Encontrados {len(urls)} vídeos para extrair.")
                    urls.reverse()
                    jp = self.driver.current_window_handle
                    for idx, url in enumerate(urls, 1):
                        janelas_antes = set(self.driver.window_handles)
                        try:
                            self.log("INFO", f"Extraindo vídeo {idx}/{len(urls)}...")
                            na = open_new_tab(self.driver, url, "extração de vídeo em nova aba", timeout=5)
                            self._trocar_para_janela_segura(na, "extração de vídeo em nova aba")
                            self._ignorar_aviso_certificado_se_aparecer("extração de vídeo em nova aba")
                            wt = WebDriverWait(self.driver, 5)
                            et = wt.until(EC.presence_of_element_located((By.ID, "assunto")))
                            raw_title = et.get_attribute("value") or ""
                            tit = " ".join(
                                [
                                    (
                                        p
                                        if p
                                        in [
                                            "de",
                                            "da",
                                            "do",
                                            "e",
                                            "a",
                                            "o",
                                            "em",
                                            "na",
                                            "no",
                                            "com",
                                            "por",
                                            "para",
                                        ]
                                        else p.capitalize()
                                    )
                                    for p in " ".join(raw_title.strip().split())
                                    .lower()
                                    .split()
                                ]
                            )
                            dados_video = self._extrair_dados_video_antigo()
                            self.log("OK", f"Vídeo {idx} extraído: '{tit}' -> Vimeo: {dados_video.get('vimeo')}, Youtube: {dados_video.get('youtube_link')}")
                            self.fila_videos.append({"titulo": tit, **dados_video})
                            self.driver.close()
                            self._trocar_para_janela_segura(jp, "retorno da extração de vídeo")
                        except Exception as ex:
                            self.log("ERRO", f"Falha ao extrair vídeo na URL {url}: {str(ex)}")
                            close_extra_windows(
                                self.driver,
                                {jp},
                                "fechamento de aba temporária de vídeo",
                            )
                            self._trocar_para_janela_segura(jp, "retorno após falha na extração de vídeo")
                else:
                    self.log("AVISO", "Nenhum link de vídeo (alterar_video.asp) encontrado na página de listagem!")
            else:
                self.log("AVISO", "Botão de vídeos (videos.asp) NÃO encontrado na página do módulo!")
            self._abrir_url_com_certificado(d_url, "retorno ao módulo antigo após vídeos")

        if capturar_materiais:
            self.log("INFO", "Iniciando captura de materiais do módulo no site antigo...")
            setores = {
                "Material Impresso": {"xp": "//a[contains(@href, 'setor=1')]", "id": "1"},
                "Slides": {"xp": "//a[contains(@href, 'setor=2')]", "id": "4"},
                "Atividades": {"xp": "//a[contains(@href, 'setor=4')]", "id": "3"},
            }
            for nm, inf in setores.items():
                self.driver.switch_to.default_content()
                botao_setor = self._localizar_elemento_recursivo_frames(inf["xp"])
                if botao_setor:
                    try:
                        self.log("INFO", f"Acessando setor de materiais: {nm}...")
                        href_setor = botao_setor.get_attribute("href") or ""
                        if href_setor and not href_setor.startswith("#") and "javascript" not in href_setor:
                            self._abrir_url_com_certificado(href_setor, f"setor antigo: {nm}")
                        else:
                            self.driver.execute_script("arguments[0].click();", botao_setor)
                        time.sleep(2)
                        
                        try:
                            self.driver.switch_to.default_content()
                            p = self.driver.find_element(
                                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                            )
                            self.driver.execute_script("arguments[0].click();", p)
                            time.sleep(0.5)
                            self.driver.execute_script(
                                "arguments[0].click();",
                                self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                            )
                            time.sleep(2.5)
                        except:
                            pass
                        
                        sp = BeautifulSoup(self.driver.page_source, "html.parser")
                        ls = []
                        for it in sp.find_all("div", class_="list-item box"):
                            subject = it.find("td", class_="subject")
                            t = subject.text.strip() if subject and subject.text else "Sem Titulo"
                            for a in it.find_all("a", href=True):
                                href = str(a.get("href", ""))
                                if "arquivoid.asp" in href.lower():
                                    ls.append(
                                        {
                                            "titulo": t,
                                            "url_ver": urljoin(self.driver.current_url, href),
                                            "categoria_id": inf["id"],
                                            "nome_categoria": nm,
                                        }
                                    )
                                    break
                        if ls:
                            self.log("INFO", f"Encontrados {len(ls)} materiais no setor {nm}.")
                            ls.reverse()
                            self.fila_arquivos.extend(ls)
                        else:
                            self.log("INFO", f"Nenhum material encontrado no setor {nm}.")
                    except Exception as e_mat:
                        self.log("ERRO", f"Erro no setor {nm}: {str(e_mat)}")
                    self._abrir_url_com_certificado(d_url, "retorno ao módulo antigo após materiais")
                else:
                    self.log("INFO", f"Setor {nm} não disponível neste módulo.")

    def _extrair_dados_modulo_antigo_unico(self, capturar_videos=True, capturar_materiais=True):
        dashboard_url = self.driver.current_url
        self.fila_videos.clear()
        self.fila_arquivos.clear()

        if capturar_videos:
            self.log("INFO", "Iniciando captura de vídeos do módulo único no site antigo...")
            botao_video = self._localizar_elemento_recursivo_frames("//a[contains(@href, 'videos.asp')]")
            if botao_video:
                self.log("INFO", "Botão de vídeos (videos.asp) encontrado! Acessando...")
                href_videos = botao_video.get_attribute("href") or ""
                if href_videos and not href_videos.startswith("#") and "javascript" not in href_videos:
                    self._abrir_url_com_certificado(href_videos, "lista de vídeos do módulo único no site antigo")
                else:
                    self.driver.execute_script("arguments[0].click();", botao_video)
                time.sleep(2)
                
                try:
                    self.driver.switch_to.default_content()
                    p = self.driver.find_element(
                        By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                    )
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(0.5)
                    self.driver.execute_script(
                        "arguments[0].click();",
                        self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                    )
                    time.sleep(2.5)
                except Exception:
                    pass

                def buscar_todos_links(lista_acumulada):
                    lk = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'alterar_video.asp')]")
                    for l in lk:
                        href = l.get_attribute("href")
                        if href and href not in lista_acumulada:
                            lista_acumulada.append(href)
                    
                    frames = self.driver.find_elements(By.TAG_NAME, "frame") + self.driver.find_elements(By.TAG_NAME, "iframe")
                    for f in frames:
                        try:
                            self.driver.switch_to.frame(f)
                            buscar_todos_links(lista_acumulada)
                            self.driver.switch_to.parent_frame()
                        except:
                            try:
                                self.driver.switch_to.parent_frame()
                            except:
                                pass

                self.log("INFO", "Procurando links de vídeos (alterar_video.asp) para módulo único...")
                self.driver.switch_to.default_content()
                urls = []
                buscar_todos_links(urls)
                
                if urls:
                    self.log("INFO", f"Encontrados {len(urls)} vídeos para extrair.")
                    urls.reverse()
                    janela_princ = self.driver.current_window_handle
                    for idx, url in enumerate(urls, 1):
                        janelas_antes = set(self.driver.window_handles)
                        try:
                            self.log("INFO", f"Extraindo vídeo {idx}/{len(urls)}...")
                            self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                            WebDriverWait(self.driver, 5).until(
                                lambda d: len(d.window_handles) > len(janelas_antes)
                            )
                            nova_aba = list(set(self.driver.window_handles) - janelas_antes)[0]
                            self.driver.switch_to.window(nova_aba)
                            self._ignorar_aviso_certificado_se_aparecer("extração de vídeo do módulo único")

                            wait_local = WebDriverWait(self.driver, 5)
                            elem_t = wait_local.until(EC.presence_of_element_located((By.ID, "assunto")))
                            raw_title = elem_t.get_attribute("value") or ""
                            tit = " ".join(
                                [
                                    (
                                        p
                                        if p in ["de", "da", "do", "e", "a", "o", "em", "na", "no", "com", "por", "para"]
                                        else p.capitalize()
                                    )
                                    for p in " ".join(raw_title.strip().split()).lower().split()
                                ]
                            )
                            dados_video = self._extrair_dados_video_antigo()
                            self.log("OK", f"Vídeo {idx} extraído: '{tit}' -> Vimeo: {dados_video.get('vimeo')}, Youtube: {dados_video.get('youtube_link')}")
                            self.fila_videos.append({"titulo": tit, **dados_video})
                        except Exception as e:
                            self.log("ERRO", f"Falha ao extrair vídeo na URL {url}: {str(e)}")
                            self._registrar_falha_worker(
                                f"Frota {self.worker_id} - extracao de video do modulo unico",
                                e,
                                "extracao_video_unico",
                                url,
                            )
                        finally:
                            for aba in list(set(self.driver.window_handles) - janelas_antes):
                                try:
                                    self.driver.switch_to.window(aba)
                                    self.driver.close()
                                except Exception:
                                    pass
                            self.driver.switch_to.window(janela_princ)
                else:
                    self.log("AVISO", "Nenhum link de vídeo (alterar_video.asp) encontrado!")
            else:
                self.log("AVISO", "Botão de vídeos (videos.asp) NÃO encontrado na página do módulo único!")
            self._abrir_url_com_certificado(dashboard_url, "retorno ao módulo único após vídeos")

        if capturar_materiais:
            self.log("INFO", "Iniciando captura de materiais do módulo único no site antigo...")
            links_setores = {
                "Material Impresso": {"xpath": "//a[contains(@href, 'setor=1')]", "cat_id": "1"},
                "Slides": {"xpath": "//a[contains(@href, 'setor=2')]", "cat_id": "4"},
                "Atividades": {"xpath": "//a[contains(@href, 'setor=4')]", "cat_id": "3"},
            }

            for nome, info in links_setores.items():
                self.driver.switch_to.default_content()
                botao_setor = self._localizar_elemento_recursivo_frames(info["xpath"])
                if botao_setor:
                    try:
                        self.log("INFO", f"Acessando setor de materiais do módulo único: {nome}...")
                        href_setor = botao_setor.get_attribute("href") or ""
                        if href_setor and not href_setor.startswith("#") and "javascript" not in href_setor:
                            self._abrir_url_com_certificado(href_setor, f"setor do módulo único: {nome}")
                        else:
                            self.driver.execute_script("arguments[0].click();", botao_setor)
                        time.sleep(2)
                        
                        try:
                            self.driver.switch_to.default_content()
                            p = self.driver.find_element(
                                By.CSS_SELECTOR, "div[data-control-name='paging'] .jplist-dd-panel"
                            )
                            self.driver.execute_script("arguments[0].click();", p)
                            time.sleep(0.5)
                            self.driver.execute_script(
                                "arguments[0].click();",
                                self.driver.find_element(By.CSS_SELECTOR, "span[data-number='all']"),
                            )
                            time.sleep(2.5)
                        except Exception:
                            pass

                        soup = BeautifulSoup(self.driver.page_source, "html.parser")
                        lote_setor = []
                        for item in soup.find_all("div", class_="list-item box"):
                            subject = item.find("td", class_="subject")
                            titulo = subject.text.strip() if subject and subject.text else "Sem Titulo"
                            for a_tag in item.find_all("a", href=True):
                                href = str(a_tag.get("href", ""))
                                if "arquivoid.asp" in href.lower():
                                    lote_setor.append(
                                        {
                                            "titulo": titulo,
                                            "url_ver": urljoin(self.driver.current_url, href),
                                            "categoria_id": info["cat_id"],
                                            "nome_categoria": nome,
                                        }
                                    )
                                    break
                        if lote_setor:
                            self.log("INFO", f"Encontrados {len(lote_setor)} materiais no setor {nome}.")
                            lote_setor.reverse()
                            self.fila_arquivos.extend(lote_setor)
                        else:
                            self.log("INFO", f"Nenhum material encontrado no setor {nome}.")
                    except Exception as e:
                        self.log("ERRO", f"Erro no setor de material {nome}: {str(e)}")
                        self._registrar_falha_worker(
                            f"Frota {self.worker_id} - extracao de materiais do modulo unico",
                            e,
                            "extracao_materiais_unico",
                            nome,
                        )
                    self._abrir_url_com_certificado(dashboard_url, "retorno ao módulo único após materiais")
                else:
                    self.log("INFO", f"Setor {nome} não disponível neste módulo único.")
'''

arquivos = ['Meus testes copy melhorado.py']
pasta_final = 'Subir Aulas (Forma Final)'
if os.path.exists(pasta_final):
    for f in os.listdir(pasta_final):
        if f.endswith('.py'):
            arquivos.append(os.path.join(pasta_final, f))

for arq in arquivos:
    try:
        with open(arq, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        # Encontrar onde começa a busca pelos frames
        idx_alvo = code.find('def _localizar_elemento_recursivo_frames')
        if idx_alvo == -1:
            idx_alvo = code.find('def _extrair_dados_ativos')
            
        idx_vincular = code.find('def _vincular_material_ao_modulo')

        if idx_alvo != -1 and idx_vincular != -1:
            # Achar a linha anterior da nossa substituição (retroceder até \n)
            inicio_linha = code.rfind('\n', 0, idx_alvo) + 1
            fim_linha_anterior = code.rfind('\n', 0, idx_vincular) + 1
            
            # Substituir todo o bloco pelo novo_bloco perfeitamente indentado
            # Usando uma concatenação que previne duplicação de espaços
            codigo_novo = code[:inicio_linha] + novo_bloco + '\n' + code[fim_linha_anterior:]
            
            with open(arq, 'w', encoding='utf-8') as f:
                f.write(codigo_novo)
            print(f"[OK] Corrigido com sucesso: {arq}")
        else:
            print(f"[ERRO] Índices não encontrados em {arq}: idx_alvo={idx_alvo}, idx_vincular={idx_vincular}")
            
    except Exception as e:
        print(f"[ERRO] Falha ao processar {arq}: {str(e)}")
