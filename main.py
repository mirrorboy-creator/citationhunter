from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# -------------------------
# 🚫 Lista de dominios prohibidos
# -------------------------
DOMINIOS_PROHIBIDOS = [
    "jstor.org", "sciencedirect.com", "springer.com",
    "tandfonline.com", "wiley.com", "cambridge.org",
    "ieee.org", "uptodate.com", "scopus.com", "jurisdata.com"
]

def url_prohibida(url):
    return any(dominio in url for dominio in DOMINIOS_PROHIBIDOS)

# -------------------------
# 🔎 1. CrossRef API
# -------------------------
def buscar_crossref(query):
    url = f"https://api.crossref.org/works?query={query}&rows=1"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    items = r.json().get("message", {}).get("items", [])
    if not items:
        return None

    item = items[0]
    autor = item.get("author", [{}])[0].get("family", "Autor desconocido")
    anio = item.get("issued", {}).get("date-parts", [[None]])[0][0]
    titulo = item.get("title", ["Sin título"])[0]
    revista = item.get("container-title", ["Revista no especificada"])[0]
    doi = item.get("DOI", "")
    url_final = f"https://doi.org/{doi}" if doi else "URL no disponible"

    if url_prohibida(url_final):
        return None

    return f"{autor} ({anio}). *{titulo}*. *{revista}*. {url_final}"

# -------------------------
# 🧠 2. Semantic Scholar API
# -------------------------
def buscar_semanticscholar(query):
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=1&fields=title,authors,year,url"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json().get("data", [])
    if not data:
        return None

    paper = data[0]
    autor = paper.get("authors", [{}])[0].get("name", "Autor desconocido")
    anio = paper.get("year", "s.f.")
    titulo = paper.get("title", "Sin título")
    url_final = paper.get("url", "URL no disponible")

    if url_prohibida(url_final):
        return None

    return f"{autor} ({anio}). *{titulo}*. Semantic Scholar. {url_final}"

# -------------------------
# 🌍 3. DOAJ API
# -------------------------
def buscar_doaj(query):
    url = f"https://doaj.org/api/v2/search/articles/{query}?page=1&pageSize=1"
    headers = {"Accept": "application/json"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    results = r.json().get("results", [])
    if not results:
        return None

    record = results[0].get("bibjson", {})
    autor = record.get("author", [{}])[0].get("name", "Autor desconocido")
    anio = record.get("year", "s.f.")
    titulo = record.get("title", "Sin título")
    revista = record.get("journal", {}).get("title", "Revista no especificada")
    url_final = record.get("link", [{}])[0].get("url", "URL no disponible")

    if url_prohibida(url_final):
        return None

    return f"{autor} ({anio}). *{titulo}*. *{revista}*. {url_final}"

# -------------------------
# 🧩 Endpoint de búsqueda por tema
# -------------------------
@app.route("/buscar")
def buscar():
    q = request.args.get("q")
    if not q:
        return jsonify({"mensaje": "Falta el parámetro ?q="}), 400

    for fuente in [buscar_crossref, buscar_semanticscholar, buscar_doaj]:
        resultado = fuente(q)
        if resultado:
            return jsonify({"mensaje": resultado})

    return jsonify({"mensaje": "No se encontraron fuentes académicas válidas (acceso abierto y dominio permitido). Intenta con otra búsqueda."})

# -------------------------
# 📂 Nuevo endpoint para carga de syllabus
# -------------------------
@app.route("/cargar-syllabus", methods=["POST"])
def cargar_syllabus():
    file = request.files.get("archivo")
    if not file:
        return jsonify({"error": "Archivo no enviado"}), 400

    contenido = file.read().decode("utf-8", errors="ignore")
    lineas = [line.strip() for line in contenido.splitlines() if len(line.strip()) > 5]
    temas = lineas[:5]  # Máximo 5 temas para evitar spam

    referencias = []
    for tema in temas:
        for fuente in [buscar_crossref, buscar_semanticscholar, buscar_doaj]:
            resultado = fuente(tema)
            if resultado:
                referencias.append({"tema": tema, "referencia": resultado})
                break

    if not referencias:
        return jsonify({"mensaje": "No se encontraron referencias válidas en el archivo."}), 404

    return jsonify({"referencias": referencias})

# -------------------------
# 🏁 Ejecutar en local o producción
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
