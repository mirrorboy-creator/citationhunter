from flask import Flask, request, jsonify
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 🚫 Dominios que deben excluirse por restricción de acceso
DOMINIOS_PROHIBIDOS = [
    "jstor.org", "sciencedirect.com", "springer.com", "tandfonline.com",
    "wiley.com", "cambridge.org", "ieee.org", "uptodate.com",
    "scopus.com", "jurisdata.com"
]

def url_prohibida(url):
    return any(dominio in url for dominio in DOMINIOS_PROHIBIDOS)

# 🔎 1. Semantic Scholar
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

    if not autor or not anio or not titulo or not url_final or url_prohibida(url_final):
        return None

    return {
        "fuente": "Semantic Scholar",
        "autor": autor,
        "anio": anio,
        "titulo": titulo,
        "revista": "Semantic Scholar",
        "url": url_final,
        "referencia_formateada": f"{autor} ({anio}). *{titulo}*. Semantic Scholar. {url_final}"
    }

# 🔎 2. arXiv API
def buscar_arxiv(query):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=1"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    if "<entry>" not in r.text:
        return None

    root = ET.fromstring(r.text)
    entry = root.find('{http://www.w3.org/2005/Atom}entry')
    if entry is None:
        return None

    titulo = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
    url_final = entry.find('{http://www.w3.org/2005/Atom}id').text.strip()
    autor = entry.find('{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name').text.strip()
    anio = entry.find('{http://www.w3.org/2005/Atom}published').text[:4]

    if not autor or not anio or not titulo or not url_final or url_prohibida(url_final):
        return None

    return {
        "fuente": "arXiv",
        "autor": autor,
        "anio": anio,
        "titulo": titulo,
        "revista": "arXiv",
        "url": url_final,
        "referencia_formateada": f"{autor} ({anio}). *{titulo}*. *arXiv*. {url_final}"
    }

# 🔎 3. CrossRef
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

    if not autor or not anio or not titulo or not url_final or url_prohibida(url_final):
        return None

    return {
        "fuente": "CrossRef",
        "autor": autor,
        "anio": anio,
        "titulo": titulo,
        "revista": revista,
        "url": url_final,
        "referencia_formateada": f"{autor} ({anio}). *{titulo}*. *{revista}*. {url_final}"
    }

# 🔎 4. DOAJ
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

    if not autor or not anio or not titulo or not url_final or url_prohibida(url_final):
        return None

    return {
        "fuente": "DOAJ",
        "autor": autor,
        "anio": anio,
        "titulo": titulo,
        "revista": revista,
        "url": url_final,
        "referencia_formateada": f"{autor} ({anio}). *{titulo}*. *{revista}*. {url_final}"
    }

# 🚀 Endpoint principal
@app.route("/buscar")
def buscar():
    q = request.args.get("q")
    if not q:
        return jsonify({"error": "Falta el parámetro ?q="}), 400

    for fuente in [buscar_semanticscholar, buscar_arxiv, buscar_crossref, buscar_doaj]:
        resultado = fuente(q)
        if resultado:
            return jsonify(resultado)

    return jsonify({"mensaje": "No se encontraron fuentes académicas válidas (abiertas y con dominio permitido). Intenta otro término."})

# 🔧 Ejecutar local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
