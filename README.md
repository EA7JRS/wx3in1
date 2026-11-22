# WX3in1 Plus 2.0 · firmware v1.13

[![Licencia: GPL v3+](https://img.shields.io/badge/licencia-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Donar con PayPal](https://img.shields.io/badge/PayPal.me-ea7jrs-00457C?logo=paypal&logoColor=white)](https://paypal.me/ea7jrs)

Documentación y herramientas para el **Microsat WX3in1 Plus 2.0** (digipetidor, I-Gate y estación meteorológica APRS) con firmware y Configurador **v1.13**.

*[English below](#english)*

## Contenido

| Ruta | Qué es |
|---|---|
| [`docs/manual/wx3in1plus20_v113_manual_espanol.pdf`](docs/manual/wx3in1plus20_v113_manual_espanol.pdf) | Manual completo v1.13 en español (57 págs.) |
| [`docs/manual/wx3in1plus20_v113_manual_english.pdf`](docs/manual/wx3in1plus20_v113_manual_english.pdf) | Manual completo v1.13 en inglés (56 págs.) |
| [`docs/guia-rapida/wx3in1plus20_guia_rapida.pdf`](docs/guia-rapida/wx3in1plus20_guia_rapida.pdf) | Guía rápida de puesta en marcha de un digi/I-Gate (3 págs.) |
| [`config/wx3in1plus20_EA_plantilla.cfg`](config/wx3in1plus20_EA_plantilla.cfg) | Plantilla de configuración para estaciones EA |
| [`tools/wx3cfg.py`](tools/wx3cfg.py) | Comprueba y corrige archivos `.cfg` |
| [`tools/extract_forms.py`](tools/extract_forms.py), [`tools/render_form.py`](tools/render_form.py) | Extraen las ventanas del Configurador y dibujan las capturas del manual |
| [`manual-src/`](manual-src) | Fuentes HTML de los PDF y script de compilación |
| [`tests/`](tests) | Pruebas de `wx3cfg` |

## Manuales

El manual original de Microsat (revisión del 15 de marzo de 2016) cubre el firmware v1.09. Esta revisión lo pone al día con la v1.13:

- **GPS SmartBeaconing** (v1.12), con todos los campos de la nueva subpestaña.
- **Condiciones “Enable if”** de las balizas, incluida “No APRS-IS” (v1.10).
- **Envío de estadísticas**, “Statistics upload” (v1.10).
- Filtro de indicativos con **20 entradas** y filtro APRS-IS→RF con **24 entradas** (v1.11), con el tipo “Bulletin”.
- Nuevas fuentes internas de telemetría y máximo de 999 (v1.12); corrección de Weather Underground (v1.13).
- Funciones web, pestaña “Other” (calibración de tensión) y monitor gamma RSS-131, que no estaban documentados.
- Apéndices con el **historial de cambios** del firmware y los **rangos de valores** que comprueba el Configurador.
- Corrección de errores del original: por ejemplo, en las coordenadas “YY.ZZ” son minutos y centésimas de minuto, no segundos.

Las capturas de las pestañas que cambiaron se han reconstruido a partir de las definiciones de las ventanas guardadas en el propio ejecutable del Configurador v1.13; en el PDF llevan la etiqueta “Configurator v1.13 layout”.

## wx3cfg: comprobar y corregir archivos .cfg

Necesita solo Python 3.8 o posterior, sin dependencias. Funciona en Linux, macOS y Windows.

```bash
# Comprobar un archivo (mismas reglas que el Configurador v1.13 + buenas prácticas APRS)
python3 tools/wx3cfg.py check mi_estacion.cfg

# Crear una configuración a partir de la plantilla EA
python3 tools/wx3cfg.py fix config/wx3in1plus20_EA_plantilla.cfg -o mi_estacion.cfg \
    --callsign EA7XXX-10 --lat 3631.20N --lon 00612.30W --random-passwords

# Cambiar cualquier clave
python3 tools/wx3cfg.py fix mi_estacion.cfg -o mi_estacion.cfg --set Beacon1_txrate_rf=20

# Passcode APRS-IS de un indicativo
python3 tools/wx3cfg.py passcode EA7XXX

# Ver un archivo con los valores de las listas en palabras
python3 tools/wx3cfg.py show mi_estacion.cfg Radio
```

**`check`** devuelve 0 si todo está bien, 1 si hay avisos y 2 si hay errores. El informe sale en español o en inglés según el idioma del sistema (o con `--lang es|en`). Comprueba, entre otras cosas:

- Los rangos y formatos que valida el Configurador v1.13: indicativo, SSID, coordenadas, TX delay, rutas n-N, intervalos, IP, puertos, longitud de mensajes y caracteres no permitidos.
- El usuario y el **passcode APRS-IS** del indicativo.
- Las reglas WIDEn-N con n>2, la ruta polaca SP con indicativos de otros países y los servidores APRS-IS y NTP polacos.
- Las contraseñas admin/admin y el servidor APRS-IS simple abierto a T2/RF.
- Las incoherencias entre funciones: SmartBeaconing sin GPS o con Bluetooth, cadenas `<temp>`/`<gps…>`/`<gamma>` sin el dispositivo, Weather Underground sin estación, puertos serie duplicados…

**`fix`** escribe una copia respetando la codificación, los finales de línea y el orden de las claves, así que el archivo se carga sin problemas con “Read from file” en el Configurador oficial. Solo hace correcciones seguras: usuario y passcode APRS-IS, WIDEn-N a n≤2, desactivar la ruta SP y cambiar los servidores APRS-IS y NTP polacos por los del país del indicativo. Con `--random-passwords` cambia admin/admin por contraseñas aleatorias y las muestra una sola vez. Con `--keep-digi` no toca las reglas del digipetidor.

## Plantilla EA

`config/wx3in1plus20_EA_plantilla.cfg` parte de la configuración por defecto v1.13 de Microsat con estos cambios:

- Regla WIDEn-N con n≤2 y ruta SP desactivada.
- APRS-IS: euro.aprs2.net y rotate.aprs2.net; NTP: 0.es.pool.ntp.org.
- Baliza 1 cada 30 min por RF y 10 min a APRS-IS, con ruta WIDE2-1; telemetría y meteorología también con WIDE2-1.
- Sin estación meteorológica, termómetro ni GPS (puertos serie en “None”).
- Mensajes de depuración telnet desactivados.

Lo que hay que completar está marcado a propósito para que `wx3cfg check` lo señale: indicativo NOCALL, posición 0/0, passcode -1 y contraseñas admin/admin.

## Recompilar los PDF

Necesita Python 3, [Playwright](https://playwright.dev/python/) con Chromium, `pypdf`, `pdftotext` (poppler-utils) y la fuente Carlito.

```bash
cd manual-src
python3 build.py all        # o: en | es | guia
```

Para volver a dibujar las capturas reconstruidas hace falta su propia copia del Configurador oficial, que **no se incluye** en este repositorio:

```bash
python3 tools/extract_forms.py "WX3in1 Plus 2 Configurator.exe" forms/
python3 tools/render_form.py spec.json      # ver el formato en la cabecera de render_form.py
```

## Pruebas

```bash
python3 -m unittest discover -s tests
```

## Referencias y normas

- *APRS Protocol Reference* 1.0.1 (APRS Working Group): formatos de posición, Mic-E, telemetría y mensajes.
- Paradigma New-N (WIDEn-N) para rutas de digipetidores.
- Plan de bandas de VHF de la IARU Región 1: 144,800 MHz para APRS.
- Red de servidores APRS-IS Tier 2 [aprs2.net](https://www.aprs2.net/) y su sistema de passcode.
- SmartBeaconing (algoritmo desarrollado para HamHUD): parámetros de velocidad y giro.

## Créditos y licencia

El WX3in1 Plus 2.0, su firmware y su Configurador son de **Microsat** (diseño de Mateusz Płociński SQ3PLX). Este repositorio **no es oficial** y no incluye el Configurador ni el firmware: descárguelos de Microsat.

- **Código** (`tools/`, `tests/`, `manual-src/build.py`): © 2026 Manuel - EA7JRS, bajo licencia [GNU GPL v3 o posterior](LICENSE).
- **Documentación** (`docs/`, `manual-src/`): el texto y las imágenes originales del manual son de Microsat / SQ3PLX. La actualización a la v1.13, la traducción al español, la guía rápida y las capturas reconstruidas son © 2026 Manuel - EA7JRS.

Si este trabajo le resulta útil, puede invitarme a un café: [paypal.me/ea7jrs](https://paypal.me/ea7jrs). 73 de EA7JRS.

---

<a id="english"></a>
## English

Documentation and tools for the **Microsat WX3in1 Plus 2.0** APRS digipeater / I-Gate / weather station, **firmware and Configurator v1.13**.

- **Manuals**: [English](docs/manual/wx3in1plus20_v113_manual_english.pdf) and [Spanish](docs/manual/wx3in1plus20_v113_manual_espanol.pdf). The original Microsat manual (15 March 2016) covers firmware v1.09. This revision adds GPS SmartBeaconing, beacon “Enable if” conditions, statistics upload, 20-entry callsign filter, 24-entry APRS-IS→RF filter, new telemetry sources, the Weather Underground fix and features that were never documented. It also adds a change history and a table of the Configurator value ranges, and fixes errors of the original (e.g. lat/long “YY.ZZ” are minutes and hundredths of a minute). Screenshots of the changed tabs are reconstructed from the form definitions inside the v1.13 Configurator executable.
- **Quick start guide** (Spanish): [docs/guia-rapida](docs/guia-rapida/wx3in1plus20_guia_rapida.pdf).
- **wx3cfg** (`tools/wx3cfg.py`, Python 3.8+, no dependencies): `check` validates a `.cfg` file with the Configurator v1.13 rules plus APRS good practice (APRS-IS passcode, WIDEn-N n≤2, foreign state paths, default passwords, feature conflicts). `fix` writes a corrected copy that keeps encoding, line endings and key order, so the official Configurator loads it with “Read from file”. `passcode` prints the APRS-IS passcode of a callsign, and `show` prints a file with combo values in words. Use `--lang en` for English output.
- **EA template**: `config/wx3in1plus20_EA_plantilla.cfg`, the v1.13 default with WIDEn-N n≤2, SP path off, euro/rotate.aprs2.net, Spanish NTP pool, WIDE2-1 paths and no weather station, thermometer or GPS.
- **Rebuild**: `cd manual-src && python3 build.py all` (Playwright + Chromium, pypdf, pdftotext, Carlito font). To redraw the reconstructed screenshots, extract the forms from your own copy of the Configurator with `tools/extract_forms.py`. The Configurator and firmware are **not included**: get them from Microsat.

Code © 2026 Manuel - EA7JRS, licensed under the [GNU GPL v3 or later](LICENSE). The original manual text and images are © Microsat / SQ3PLX. The v1.13 update, translation, quick start guide and reconstructed screenshots are © 2026 Manuel - EA7JRS. This is not an official Microsat project.

[![Donate with PayPal](https://img.shields.io/badge/PayPal.me-ea7jrs-00457C?logo=paypal&logoColor=white)](https://paypal.me/ea7jrs)
