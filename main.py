from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# =====================================================
# CONFIGURACIÓN DE FUENTES OPEN ACCESS POR ÁREA
# =====================================================
FUENTES_PERMITIDAS = {
    "Educación": [
        "redalyc.org",
        "scielo.org",
        "dialnet.unirioja.es",
        "clacso.org"
    ],
    "Administración": [
        "redalyc.org",
        "scielo.org",
        "dialnet.unirioja.es",
        "clacso.org"
    ],
    "Ingeniería": [
        "scielo.org",
        "redalyc.org",
        "arxiv.org",
        "doaj.org"
    ],
    "Salud": [
        "pmc.ncbi.nlm.nih.gov",
        "scielo.org",
        "medrxiv.org",
        "redalyc.org"
    ],
    "Ciencias Sociales": [
        "clacso.org",
        "redalyc.org",
        "scielo.org",
        "dialnet.unirioja.es",
        "cepal.org"
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
    """
    Entrada esperada:
    {
        "q": "aprendizaje significativo",
        "area": "Educación"
    }
    """

    data = request.get_json(silent=True) or {}
    query = data.get("q")
    area = data.get("area")

    if not query or not area:
        return jsonify({
            "ok": False,
            "error": "Se requieren los campos 'q' y 'area'"
        }), 400

    dominios_validos = FUENTES_PERMITIDAS.get(area)
    if not dominios_validos:
        return jsonify({
            "ok": False,
            "error": f"Área no soportada: {area}"
        }), 400

    # -------------------------------------------------
    # Usamos Crossref como ÍNDICE ABIERTO (no fuente)
    # -------------------------------------------------
    url = f"https://api.crossref.org/works?query={query}&rows=10"
    r = requests.get(url, timeout=20)

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

        # Filtrar cerrados
        if dominio_prohibido(link):
            continue

        # Filtrar por dominios open access permitidos
        if not any(d in link for d in dominios_validos):
            continue

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
