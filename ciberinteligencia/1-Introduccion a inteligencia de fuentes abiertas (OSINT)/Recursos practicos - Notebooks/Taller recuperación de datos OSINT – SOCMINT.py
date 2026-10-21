import time, re
from datetime import date, timedelta
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def extraer_septiembre_22h(year=2026, pais="spain"):
    todos_los_datos = []
    
    inicio = date(year, 9, 1)
    fin = date(year, 9, 30)
    dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]

    print(f"--- Extrayendo 50 tendencias con Playwright ({pais.capitalize()}, Septiembre {year}, 22:00h) ---")

    with sync_playwright() as p:
        # Lanzamos Chrome evitando la detección automática de Cloudflare
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="es-ES"
        )
        page = context.new_page()

        for fecha in dias:
            fecha_str = fecha.strftime("%Y-%m-%d")
            url = f"https://getdaytrends.com/es/{pais}/{fecha_str}/22/"

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_selector('#trends', timeout=15000)
                print(f"✓ Cargada: {url}")

                # Intentar pulsar 'Ver todo 50' si está disponible
                try:
                    btn = page.query_selector('a[href="#moreTrends"]')
                    if btn:
                        btn.click()
                        page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Extraer los enlaces de tendencias
                enlaces = page.query_selector_all('//*[@id="trends"]//a[contains(@href, "/trend/")]')
                vistos = set()
                filas_dia = []

                for a in enlaces:
                    href = a.get_attribute("href")
                    if not href or href in vistos:
                        continue
                    vistos.add(href)

                    # textContent captura el texto de las filas ocultas
                    nombre = (a.text_content() or "").strip()
                    if not nombre:
                        continue

                    # Obtener volumen de tweets de la celda contenedora
                    volumen = None
                    try:
                        td = a.evaluate_handle("el => el.closest('td')").as_element()
                        if td:
                            texto_td = td.text_content() or ""
                            m = re.search(r"(Menos de [\d.,]+K|[\d.,]+K?) tweets", texto_td)
                            volumen = m.group(0) if m else None
                    except Exception:
                        pass

                    filas_dia.append({
                        "fecha": fecha_str,
                        "hora": "22:00",
                        "posicion": len(filas_dia) + 1,
                        "tendencia": nombre,
                        "volumen": volumen,
                        "url_tendencia": href
                    })

                    if len(filas_dia) == 50:
                        break

                print(f"   -> Extraídas {len(filas_dia)} tendencias para el {fecha_str}")
                todos_los_datos.extend(filas_dia)

            except PlaywrightTimeoutError:
                print(f"⚠️ Timeout/Bloqueo al cargar el día {fecha_str}")
            
            time.sleep(2) # Pausa entre peticiones

        browser.close()

    df = pd.DataFrame(todos_los_datos)
    if not df.empty:
        df = df[["fecha", "hora", "posicion", "tendencia", "volumen", "url_tendencia"]]
    return df


if __name__ == "__main__":
    df_resultado = extraer_septiembre_22h(year=2026, pais="spain")

    if not df_resultado.empty:
        archivo = "tendencias_spain_septiembre_22h.csv"
        df_resultado.to_csv(archivo, index=False, encoding="utf-8-sig")
        print(f"\n¡Éxito total! Se han guardado {len(df_resultado)} filas en '{archivo}'.")
    else:
        print("\nNo se pudieron obtener datos.")
