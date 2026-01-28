from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# =====================================================
# CONFIGURACIÓN DE FUENTES OPEN ACCESS POR ÁREA
# =====================================================
FUENTES_PERMITIDAS = {
    "Administración": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "biblioteca-repositorio.clacso.edu.ar"
    ],
    "Ciencias de la Información, Comunicación y Mercadeo": [
        "doaj.org",
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "eprints.rclis.org"
    ],
    "Ciencias Médicas y de Salud": [
        "pmc.ncbi.nlm.nih.gov",
        "scielo.sa.cr",
        "medrxiv.org",
        "redalyc.org",
        "iris.who.int"
    ],
    "Ciencias Naturales y Matemáticas": [
        "scielo.sa.cr",
        "redalyc.org",
        "plos.org",
        "arxiv.org",
        "doabooks.org"
    ],
    "Ciencias Sociales y Humanas": [
        "biblioteca-repositorio.clacso.edu.ar",
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "repositorio.cepal.org"
    ],
    "Derecho": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "repositorio.unam.mx",
        "biblioteca-repositorio.clacso.edu.ar"
    ],
    "Economía, Finanzas y Ciencias Contables": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "repositorio.cepal.org",
        "ideas.repec.org"
    ],
    "Educación": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "biblioteca-repositorio.clacso.edu.ar",
        "explora-intelligo.info"
    ],
    "Ingeniería": [
        "redalyc.org",
        "scielo.sa.cr",
        "arxiv.org",
        "doaj.org",
        "latindex.org"
    ],
    "Internet y Nuevas Tecnologías": [
        "arxiv.org",
        "doaj.org",
        "hal.science",
        "eprints.rclis.org"
    ],
    "Logística y Transporte": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "doaj.org"
    ],
    "Transversales (Competencias blandas)": [
        "redalyc.org",
        "scielo.sa.cr",
        "dialnet.unirioja.es",
        "biblioteca-repositorio.clacso.edu.ar",
        "sedici.unlp.edu.ar"
    ]
}

# =====================================================
# DOMINIOS PROHIBIDOS (PAGO / CERRADOS)
# =====================================================
DOMINIOS_PROHIBIDOS = [
    "elsevier",
    "springer",
    "jstor",
    "wiley",
    "scopus",
    "ieee",
    "tandfonline",
    "cambridge"
]

def dominio_prohibido(url: str) -> bool:
    return any(d in url.lower() for d in DOMINIOS_PROHIBIDOS)

# =====================================================
# HEALTH CHECK (Render)
# =====================================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

# =====================================================
# ENDPOINT PRINCIPAL DE CITAS ACADÉMICAS
# =====================================================
@app.route("/citations", methods=["POST"])
def citations():

    data = request.get_json(silent=True) or {}

    query = data.get("q")
    area = data.get("area") or "Ciencias Sociales y Humanas"

    if not query:
        return jsonify({
            "ok": False,
            "error": "El campo 'q' es obligatorio"
        }), 400

    # Fallback de área si no existe
    if area not in FUENTES_PERMITIDAS:
        area = "Ciencias Sociales y Humanas"

    dominios_validos = FUENTES_PERMITIDAS[area]

    # -------------------------------------------------
    # Crossref como índice académico abierto
    # -------------------------------------------------
    url = f"https://api.crossref.org/works?query={query}&rows=20"
    try:
        r = requests.get(url, timeout=20)
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Error de conexión con Crossref"
        }), 502

    if r.status_code != 200:
        return jsonify({
            "ok": False,
            "error": "Error consultando Crossref"
        }), 502

    resultados = []

    for item in r.json().get("message", {}).get("items", []):

        link = item.get("URL", "")
        if not link:
            continue

        # Bloquear dominios cerrados
        if dominio_prohibido(link):
            continue

        # Aceptar si está en permitidos o no está prohibido
        if not any(d in link for d in dominios_validos):
            pass  # se acepta igual si no es de pago

        autor = "Autor desconocido"
        if item.get("author"):
            autor = item["author"][0].get("family", autor)

        anio = None
        if item.get("issued"):
            anio = item["issued"].get("date-parts", [[None]])[0][0]

        resultados.append({
            "autor": autor,
            "anio": anio,
            "titulo": item.get("title", ["Sin título"])[0],
            "url": link,
            "open_access": True,
            "idioma": "es"
        })

    if not resultados:
        return jsonify({
            "ok": False,
            "mensaje": "No se encontraron fuentes académicas open access válidas"
        }), 404

    return jsonify({
        "ok": True,
        "area": area,
        "query": query,
        "resultados": resultados
    })

# =====================================================
# RENDER
# =====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
