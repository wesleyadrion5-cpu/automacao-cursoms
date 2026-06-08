import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def session_is_active(driver: WebDriver | None) -> bool:
    try:
        return bool(driver and driver.session_id and driver.window_handles)
    except Exception:
        return False


def safe_switch_to_window(driver: WebDriver, handle: str, context: str):
    if not session_is_active(driver):
        raise RuntimeError(f"Sessão do navegador indisponível ao tentar acessar {context}.")
    handles = list(driver.window_handles)
    if handle not in handles:
        raise RuntimeError(
            f"Janela indisponível ao tentar acessar {context}. Handles atuais: {len(handles)}"
        )
    driver.switch_to.window(handle)
    return handle


def build_chrome_options_accepting_old_certificates():
    options = webdriver.ChromeOptions()
    options.set_capability("acceptInsecureCerts", True)
    try:
        options.accept_insecure_certs = True
    except Exception:
        pass
    for argumento in [
        "--ignore-certificate-errors",
        "--ignore-ssl-errors=yes",
        "--allow-insecure-localhost",
    ]:
        options.add_argument(argumento)
    return options


def _chrome_certificate_warning_visible(driver: WebDriver) -> bool:
    try:
        if not session_is_active(driver):
            return False
        url_atual = (driver.current_url or "").lower()
        titulo = (driver.title or "").lower()
    except Exception:
        return False

    if url_atual.startswith("chrome-error://"):
        return True
    if "erro de privacidade" in titulo or "privacy error" in titulo:
        return True

    try:
        return bool(
            driver.execute_script(
                """
                const texto = (document.body && document.body.innerText || '').toLowerCase();
                return Boolean(
                    document.querySelector('#details-button, #proceed-link') ||
                    texto.includes('err_cert') ||
                    texto.includes('sua conexão não é particular') ||
                    texto.includes('sua conexao nao e particular') ||
                    texto.includes('your connection is not private')
                );
                """
            )
        )
    except Exception:
        return False


def bypass_chrome_certificate_warning(driver: WebDriver, context: str = "", timeout=4) -> bool:
    fim = time.time() + timeout
    tentou_bypass = False

    while time.time() < fim:
        if not _chrome_certificate_warning_visible(driver):
            return tentou_bypass

        acao = ""
        try:
            acao = str(
                driver.execute_script(
                    """
                    const visivel = (el) => Boolean(
                        el && !el.disabled &&
                        window.getComputedStyle(el).display !== 'none' &&
                        window.getComputedStyle(el).visibility !== 'hidden'
                    );
                    const proceed = document.querySelector('#proceed-link');
                    if (visivel(proceed)) {
                        proceed.click();
                        return 'proceed';
                    }
                    const details = document.querySelector('#details-button');
                    if (visivel(details)) {
                        details.click();
                        return 'advanced';
                    }
                    return '';
                    """
                )
                or ""
            )
        except Exception:
            acao = ""

        if acao == "advanced":
            tentou_bypass = True
            time.sleep(0.4)
            continue
        if acao == "proceed":
            tentou_bypass = True
            time.sleep(1.0)
            continue

        try:
            driver.find_element(By.TAG_NAME, "body").send_keys("thisisunsafe")
            tentou_bypass = True
            time.sleep(1.0)
        except Exception:
            time.sleep(0.25)

    return tentou_bypass and not _chrome_certificate_warning_visible(driver)


def navigate_with_certificate_bypass(
    driver: WebDriver, url: str, context: str = "", timeout=4
) -> bool:
    driver.get(url)
    return bypass_chrome_certificate_warning(driver, context, timeout=timeout)


def open_new_tab(driver: WebDriver, url: str, context: str, timeout=10):
    anteriores = set(driver.window_handles)
    driver.execute_script("window.open(arguments[0], '_blank');", url)
    WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > len(anteriores))
    novas = list(set(driver.window_handles) - anteriores)
    if not novas:
        raise RuntimeError(f"Não foi possível abrir nova aba para {context}.")
    novo_handle = novas[0]
    safe_switch_to_window(driver, novo_handle, context)
    return novo_handle


def close_extra_windows(driver: WebDriver, keep_handles, context: str):
    ativos = set(keep_handles)
    for handle in list(driver.window_handles):
        if handle in ativos:
            continue
        safe_switch_to_window(driver, handle, context)
        driver.close()
    if ativos:
        safe_switch_to_window(driver, next(iter(ativos)), context)


def clear_and_type(elemento, valor, delay_between_chars=0.0):
    elemento.click()
    elemento.send_keys(Keys.CONTROL + "a")
    elemento.send_keys(Keys.DELETE)
    if delay_between_chars <= 0:
        elemento.send_keys("" if valor is None else str(valor))
        return
    for char in str(valor or ""):
        elemento.send_keys(char)
