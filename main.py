import warnings
import random
import os
import time
import ssl
import urllib.request
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def clicar_em_start_watching(driver):
    try:
        start_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-a-target="content-classification-gate-overlay-start-watching-button"]'))
        )
        driver.execute_script("arguments[0].click();", start_btn)
        print("🟢 Gate de conteúdo sensível detectado e aceito com sucesso.")
    except TimeoutException:
        print("⚪️ Nenhum gate de conteúdo sensível detectado.")


def aceitar_banner_cookies(driver):
    xpaths = [
        '//button[.//div[text()="Proceed"]]',
        '//button[.//div[contains(text(), "Continuar")]]',
        '//button[@data-a-target="consent-banner-consent-accept-button"]',
    ]

    for xpath in xpaths:
        try:
            consent_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", consent_btn)
            print(f"🟢 Banner de cookies fechado com sucesso usando selector: {xpath}")
            return
        except Exception:
            continue

    print("⚪️ Nenhum banner de cookies detectado (ou já foi fechado).")


def log_error(message):
    with open("log.txt", "a") as f:
        f.write(f"{time.ctime()} - {message}\n")

# Suprimir warnings desnecessários
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Gerenciamento do ChromeDriver (Selenium 4+ gerencia nativamente)
try:
    import importlib.util
    cda = importlib.util.find_spec("chromedriver_autoinstaller")
    if cda:
        import chromedriver_autoinstaller  # type: ignore
        chromedriver_autoinstaller.install(no_ssl=True)
except Exception:
    pass

# Função para salvar as configurações
def save_settings(twitch_username, set_160p):
    with open('settings.txt', 'w') as file:
        file.write(f"Twitch Username: {twitch_username}\n")
        file.write(f"Set 160p: {set_160p}\n")

# Função para carregar as configurações
def load_settings():
    try:
        with open('settings.txt', 'r') as file:
            lines = file.readlines()
            if len(lines) >= 2:
                twitch_username = lines[0].split(': ')[1].strip()
                set_160p = lines[1].split(': ')[1].strip()
                return twitch_username, set_160p
    except FileNotFoundError:
        pass
    return None, None

# Função para selecionar um proxy aleatório
def select_random_proxy(proxies):
    return random.choice(proxies)

# Função para definir a qualidade do stream
def set_stream_quality(driver, quality):
    if quality.lower() == "yes":
        try:
            # Ocultar iframes
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                driver.execute_script("arguments[0].style.visibility = 'hidden';", iframe)

            # Aguardar o player carregar
            player_xpath = "//div[@data-a-target='player-overlay-click-handler']"
            settings_button_xpath = "//button[@aria-label='Settings']"
            quality_button_xpath = "//div[text()='Quality']"
            quality_option_xpath = "//label[contains(., '160p')]"
            loading_spinner_xpath = "//div[contains(@class, 'ScLoadingSpinner')]"

            # Aguardar o spinner de carregamento desaparecer
            try:
                WebDriverWait(driver, 15).until(
                    EC.invisibility_of_element_located((By.XPATH, loading_spinner_xpath))
                )
            except TimeoutException:
                pass  # Se o spinner não desaparecer, continuar mesmo assim

            # Aguardar o player estar clicável
            player_element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, player_xpath))
            )
            driver.execute_script("arguments[0].click();", player_element)
            time.sleep(1)  # Pequena pausa após clique

            # Abrir configurações
            settings_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, settings_button_xpath))
            )
            driver.execute_script("arguments[0].click();", settings_button)
            time.sleep(0.5)

            # Selecionar a opção de qualidade
            quality_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, quality_button_xpath))
            )
            driver.execute_script("arguments[0].click();", quality_button)
            time.sleep(0.5)

            # Selecionar "160p"
            quality_option = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, quality_option_xpath))
            )
            driver.execute_script("arguments[0].click();", quality_option)
            time.sleep(0.5)

            # Fechar a caixa de configurações
            driver.execute_script("arguments[0].click();", settings_button)
            print("🟢 Qualidade ajustada para 160p.")

        except TimeoutException:
            print("⚪️ Tempo limite ao tentar ajustar a qualidade do stream.")
        except Exception as e:
            print(f"⚠️ Aviso ao ajustar a qualidade do stream: {e}")

# Função principal
def main():
    twitch_username, set_160p = load_settings()

    # Pergunta se deseja reutilizar as configurações salvas
    if twitch_username is not None and set_160p is not None:
        reuse = input(f"As configurações salvas são:\n- Canal: {twitch_username}\n- Qualidade 160p: {set_160p}\nDeseja reutilizar essas configurações? (yes/no): ").strip().lower()
        if reuse == "no":
            twitch_username = input("Digite o nome do canal (e.g. Kichi779): ")
            set_160p = input("Definir qualidade para 160p? (yes/no): ")
            save_settings(twitch_username, set_160p)
    else:
        twitch_username = input("Digite o nome do canal (e.g. Kichi779): ")
        set_160p = input("Definir qualidade para 160p? (yes/no): ")
        save_settings(twitch_username, set_160p)

    # Perguntar ao usuário se deseja executar em modo headless
    headless_mode = "no"
    if set_160p.lower() == "no":
        headless_mode = input("Deseja executar o navegador em modo headless (sem interface gráfica)? (yes/no): ").strip().lower()
    else:
        print("🔆 Modo gráfico ativado automaticamente para permitir alteração da qualidade para 160p.")

    proxy_count = int(input("Quantas abas proxy deseja abrir? "))
    proxies = [
        'https://www.blockaway.net',
        'https://www.croxyproxy.com',
        'https://www.croxyproxy.rocks',
        'https://www.croxy.network',
        'https://www.croxy.org',
        'https://www.youtubeunblocked.live',
        'https://www.croxyproxy.net'
    ]


    print("Proxies externos serão usados para acessar o Twitch.")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--lang=en')
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-features=Translate,OptimizationHints,MediaRouter')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')

    # Configurar o modo headless
    if headless_mode == "yes":
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')

    # Inicia o navegador
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print("Erro ao criar o driver do Chrome:", e)
        return
    
    sucesso_count = 0
    total_attempts = 0
    attempt_in_tab = 0
    max_retries = proxy_count * 4

    def close_failed_tab():
        if len(driver.window_handles) > 1:
            print("🔧 Erro persistente: fechando aba atual e voltando para a aba anterior.")
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
        else:
            print("🔧 Erro persistente: sem abas extras para fechar. Reutilizando a aba atual.")

    try:
        while sucesso_count < proxy_count and total_attempts < max_retries:
            total_attempts += 1
            attempt_in_tab += 1
            proxy_url = select_random_proxy(proxies)
            print(f"\n🔄 [{sucesso_count + 1}/{proxy_count}] Tentativa da aba {attempt_in_tab} / Tentativa total {total_attempts}/{max_retries}: Abrindo proxy: {proxy_url}")
            sucesso = False

            try:
                if total_attempts == 1:
                    driver.get(proxy_url)
                else:
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.get(proxy_url)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )

                try:
                    text_box = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.ID, 'url'))
                    )
                    text_box.send_keys(f'https://www.twitch.tv/{twitch_username}')
                    text_box.send_keys(Keys.RETURN)

                    print(f"🧑‍💻 Visualizador virtual enviado via proxy {proxy_url}. Aguardando carregamento...")

                    time.sleep(25)

                    clicar_em_start_watching(driver)
                    aceitar_banner_cookies(driver)
                    set_stream_quality(driver, set_160p)

                    sucesso = True

                except TimeoutException:
                    print(f"⚠️ Proxy {proxy_url} não conseguiu carregar o player da Twitch. Tentando outro...")
                    close_failed_tab()

            except Exception as e:
                print(f"❌ Erro ao tentar usar o proxy {proxy_url}: {e}")
                close_failed_tab()
                continue

            if sucesso:
                sucesso_count += 1
                attempt_in_tab = 0
                if sucesso_count < proxy_count:
                    print("Abrindo a próxima aba...")
                    time.sleep(60)
            else:
                print("🚫 Proxy ignorado. Repetindo tentativa com outro proxy...")

        if sucesso_count == proxy_count:
            print(f"\n✅ {sucesso_count}/{proxy_count} visualizadores válidos enviados para o canal {twitch_username}.")
        else:
            print(f"\n⚠️ Resultado parcial: {sucesso_count}/{proxy_count} visualizadores enviados após {total_attempts} tentativas.")
            print("Considere reduzir o número de abas ou trocar os proxies configurados.")

    finally:
        input("\nPressione Enter para encerrar o programa...")
        driver.quit()
if __name__ == '__main__':
    main()
