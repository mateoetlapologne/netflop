import nextcord
from nextcord.ext import commands
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import json 

intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TMDB_API_KEY = ""  # Utilisez la clé API depuis une variable d'environnement
BASE_IMAGE_URL = "https://image.tmdb.org/t/p/original"

@bot.slash_command(guild_ids=[1202362398728785940])  # Remplacez avec l'ID de votre serveur
async def recherche(interaction: nextcord.Interaction, film: str):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={film}&language=fr-FR"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            first_result = data['results'][0]
            title = first_result.get("title", "Titre inconnu")
            overview = first_result.get("overview", "Pas de description disponible.")
            poster_path = first_result.get("poster_path", None)
            poster_url = f"{BASE_IMAGE_URL}{poster_path}" if poster_path else None

            embed = nextcord.Embed(title=title, description=overview)
            if poster_url:
                embed.set_image(url=poster_url)
            await interaction.response.send_message(embed=embed)
            await interaction.followup.send(f"Voici le premier résultat pour votre recherche : {film}")
        else:
            await interaction.response.send_message("Aucun film trouvé pour cette recherche.")
    else:
        await interaction.response.send_message("Erreur lors de la recherche du film.")

@bot.slash_command(guild_ids=[1202362398728785940])  # Remplacez avec l'ID de votre serveur
async def telecharge(interaction: nextcord.Interaction, recherche: str):
    # Envoyer un message d'attente
    await interaction.response.send_message("Recherche en cours...")

    # Appel de la fonction scrape_content
    scrape_content("https://www.zone-telechargement.city", recherche)
    filtrer_films_par_recherche("films_data.json", recherche)
    # ajouter_lien_telechargement("films_data.json")

    # Lire les données du fichier JSON
    with open("films_data.json", "r", encoding='utf-8') as file:
        films = json.load(file)

    # Créer l'embed avec les données
    embed = nextcord.Embed(title="Résultats de la recherche", description=f"Films trouvés pour '{recherche}':", color=0x00ff00)
    for film in films[:10]:  # Limiter le nombre de films affichés
        embed.add_field(name=film['title'], value=f"[Lien]({film['link']})", inline=False)

    # Envoyer l'embed en tant que follow-up
    await interaction.followup.send(embed=embed)

def scrape_content(base_url, search_query):
    films = {}

    for page in range(1, 3):  # Boucle sur les pages 1, 2 et 3
        # Construction de l'URL avec le numéro de page
        page_url = f"{base_url}?p=films&search={quote_plus(search_query)}&page={page}"
        response = requests.get(page_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Parcourir chaque div de cover_global
        for div in soup.find_all('div', class_='cover_global'):
            img_element = div.find('img')
            img_url = urljoin(base_url, img_element['src']) if img_element and img_element.get('src') else None

            cover_info_title = div.find('div', class_='cover_infos_title')
            if cover_info_title:
                link_element = cover_info_title.find('a')
                if link_element:
                    film_title = link_element.get_text(strip=True)
                    film_link = urljoin(base_url, link_element['href']) if link_element.get('href') else None
                    if film_title:
                        films[film_title] = {
                            'title': film_title,
                            'image_url': img_url,
                            'link': film_link
                        }

    # Nom du fichier JSON
    json_file = "films_data.json"

    # Vérifier si le fichier existe déjà et le supprimer si c'est le cas
    if os.path.exists(json_file):
        os.remove(json_file)

    # Enregistrer les données dans un fichier JSON
    with open(json_file, "w", encoding='utf-8') as file:
        json.dump(list(films.values()), file, indent=4, ensure_ascii=False)
    verifier_et_maj_films("films_data.json")
    print(f"{len(films)} entrées uniques enregistrées dans '{json_file}'.")

def verifier_et_maj_films(json_file):
    base_url = "https://www.zone-telechargement.city"
    with open(json_file, "r", encoding='utf-8') as file:
        films = json.load(file)

    films_mis_a_jour = 0

    for film in films:
        response = requests.get(film['link'])
        soup = BeautifulSoup(response.content, 'html.parser')

        qualite_element = soup.find('u', string="Qualité")
        langue_element = soup.find('u', string="Langue")

        qualite = qualite_element.find_next_sibling().get_text(strip=True) if qualite_element and qualite_element.find_next_sibling() else ""
        langue = langue_element.find_next_sibling().get_text(strip=True) if langue_element and langue_element.find_next_sibling() else ""

        if "1080p" in qualite and "french" in langue:
            # print(f"'{film['title']}' correspond déjà aux critères.")
            continue

        other_versions = soup.find('div', class_='otherversions')
        link_updated = False
        if other_versions:
            for a in other_versions.find_all('a'):
                spans = a.find_all('span')
                if any("1080p" in span.get_text().lower() for span in spans) and \
                any("french" in span.get_text().lower() for span in spans):
                    new_link = urljoin(base_url, a['href'])
                    film['link'] = new_link
                    # print(f"Lien mis à jour pour '{film['title']}': {new_link}")
                    link_updated = True
                    films_mis_a_jour += 1
                    break # Sortir de la boucle for

        # if not link_updated:
        #     print(f"Aucune version conforme trouvée pour '{film['title']}'. Lien inchangé.")

    with open(json_file, "w", encoding='utf-8') as file:
        json.dump(films, file, indent=4, ensure_ascii=False)

    # print(f"{len(films)} films vérifiés. {films_mis_a_jour} films mis à jour.")
    # print(f"Les changements ont été enregistrés dans '{json_file}'.")

def filtrer_films_par_recherche(json_file, recherche):
    # Charger les données du fichier JSON
    with open(json_file, "r", encoding='utf-8') as file:
        films = json.load(file)

    # Préparation de la recherche pour la comparaison (case insensitive)
    mots_recherche = recherche.lower().split()

    # Filtrer les films dont le titre contient au moins un des mots de la recherche
    films_filtrés = [film for film in films if any(mot in film['title'].lower() for mot in mots_recherche)]

    # Enregistrer les films filtrés dans le fichier JSON
    with open(json_file, "w", encoding='utf-8') as file:
        json.dump(films_filtrés, file, indent=4, ensure_ascii=False)

    # print(f"{len(films_filtrés)} films restants après filtrage par la recherche '{recherche}'.")

def ajouter_lien_telechargement(json_file):
    with open(json_file, "r", encoding='utf-8') as file:
        films = json.load(file)

    for film in films:
        response = requests.get(film['link'])
        soup = BeautifulSoup(response.content, 'html.parser')

        # Trouver la première balise <a> contenant le texte "Télécharger"
        lien_telecharger = soup.find('a', string=lambda text: text and "télécharger" in text.lower())
        if lien_telecharger:
            film['lien_telecharger'] = lien_telecharger['href']
            print(f"Lien de téléchargement ajouté pour '{film['title']}': {film['lien_telecharger']}")
        else:
            film['lien_telecharger'] = "Non disponible"

    # Réécrire le fichier JSON avec les liens de téléchargement
    with open(json_file, "w", encoding='utf-8') as file:
        json.dump(films, file, indent=4, ensure_ascii=False)

    print("Mise à jour des liens de téléchargement terminée.")

#scrape_content("https://www.zone-telechargement.city/?p=films&search=Spider+qsdqsd")
bot.run("")
