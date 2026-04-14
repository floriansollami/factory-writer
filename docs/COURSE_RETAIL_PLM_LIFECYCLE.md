# Comprendre le monde de l'E-Commerce & du Retail (PLM & Go-To-Market)

Dans des entreprises comme Decathlon, Kiabi, Maisons du Monde, ou la marque fictive "The Outdoor Axolotl", le processus de création de produits ne se fait pas au jour le jour. Il s'appuie sur une mécanique de précision appelée le **Go-To-Market (GTM)**, qui est pilotée numériquement par une colonne vertébrale logicielle : le **PLM (Product Lifecycle Management)**.

---

## 1. Le concept de "Collection" (La Saisonnalité)

Dans l'industrie, on raisonne exclusivement en termes de **saisons** (Printemps/Été = *SS* pour Spring/Summer ; Automne/Hiver = *AW* pour Autumn/Winter).

Pour que la collection d'Été 2026 soit disponible en rayons en Mars 2026, l'entreprise ne commence pas à travailler en janvier. Le cycle débute **12 à 18 mois à l'avance**.
Le but du "Go-To-Market", c'est une coordination militaire : l'objectif est que le jour J (le lancement de la collection T0), toutes les planètes soient alignées :
* Les produits physiques de 400 nouvelles références (SKUs) sont dans les entrepôts.
* Les photos ont été prises.
* Le site web est parfaitement à jour avec toutes les fiches, textes, matières et traductions.

---

## 2. Les Acteurs Clés : Qui fait quoi dans le développement ?

Il y a une chaîne d'intervenants très précise dans la création d'une collection. Ils travaillent en parallèle :

1. **Les Merchandisers / Chef de Produit (Le Cerveau Business) :**
   Ce sont les stratèges. Ils analysent les données de vente passées et établissent le plan de collection (le *Line Plan*). Ils décident du budget et des besoins, par exemple : *"Il nous faut 3 nouvelles tables de jardin haut-de-gamme entre 1500€ et 2000€ pour contrer la concurrence l'été prochain."*
2. **Les Designers (L'Esthétique) :**
   Ils dessinent l'objet, choisissent les courbes, le style, les palettes de couleurs.
3. **Les Ingénieurs / Bureau d'Études (La Technique) :**
   Ils transforment le joli dessin d'un designer en un document technique d'une rigueur mathématique (le **Tech Pack** ou Blueprint). Ils définissent l'épaisseur du bois, les types de vis, la densité des mousses.
4. **Les Sourcing Managers (L'Achat & L'Usine) :**
   Ils voyagent avec le Tech Pack sous le bras (souvent en Asie ou en Europe de l'Est) pour trouver l'usine partenaire qui saura fabriquer le meuble, au bon prix, tout en respectant le cahier des charges éthique et qualitatif de la marque.

---

## 3. Le Cheminement Industriel (De l'idée au site Web)

Voici la ligne de temps typique ("Timeline") du lancement massif des 400 produits que tu vas automatiser avec Factory Writer.

### Étape 1 : Ideation & Plan de Collection (T - 18 mois)
Les Merchandisers figent leur tableau Excel (Line Plan). Les équipes savent qu'ils devront sortir 400 meubles l'année prochaine.

### Étape 2 : Design & Tech Packs (T - 12 mois)
Les ingénieurs rentrent en jeu. Tout le monde travaille dans le même logiciel d'entreprise (le système de **PLM** central).
C'est à cette étape que sont créés numériquement les **Blueprints** et les **plans AutoCAD** qui détaillent les dimensions au millimètre, l'essence du bois, et les contraintes d'assemblage de chaque chaise.

### Étape 3 : Sourcing & Prototypage (T - 9 mois)
L'équipe Sourcing envoie les Tech Packs à l'usine partenaire (ex: usine de Teck en Indonésie).
L'usine fabrique un prototype unique et l'envoie chez Axolotl. L'équipe valide la solidité, exige des modifications, et s'assure d'obtenir les certificats nécessaires (FSC, résistance à l'humidité).

### Étape 4 : L'Ordre de Production et la Création ERP (T - 6 mois)
Le "Gel de la Collection". Tout est validé.
L'équipe financière crée l'article dans l'**ERP** (le logiciel de cœur de la société). C'est là qu'est généré le fameux **SKU** (Stock Keeping Unit).
L'ordre d'achat de masse est envoyé : l'usine lance des chaînes de montage et fabrique les 10 000 chaises.

### Étape 5 : L'Enfer de "L'Enrichissement de Données" (T - 3 mois)
Pendant que les 10 000 chaises sont entassées dans des cargos sur l'océan Indien, l'équipe Marketing / E-commerce au siège commence à paniquer.
Ils doivent créer **400 fiches descriptives complètes** pour le site Web.
* Ils pourchassent les Ingénieurs pour avoir les poids exacts, les notices de montage.
* Ils réclament les validations de "matériaux écolos" à l'équipe conformité.
* Ils embauchent 10 rédacteurs humains ("Copywriters") pour taper au clavier pendant 3 semaines des textes à la chaîne. La fatigue génère inévitablement des "coquilles" : une dimension fausse est copiée-collée, un matériau est mal nommé (Erreur Humaine / "Hallucination" Manuelle).

> 💡 **Le Miracle Factory Writer (L'Architecture 2026 expliquée) :**
> C'est très exactement ici que ton logiciel bouleverse l'industrie !
> 
> À la fin de l'**Étape 4**, l'ERP crée la référence (`Eventarc Push`). En parallèle, l'usine vient de terminer la validation des normes. 
>
> 🔍 **Zoom Opérationnel (Norme Silicon Valley 2026) : Qui valide et comment ça déclenche l'IA ?**
> *En tant qu'Architecte Cloud, c'est ta pire angoisse : si l'usine uploade 5 PDF un par un pour le même meuble, vas-tu déclencher 5 workflows IA mutilés ? NON. Voici le pattern "Event-Driven" robuste :*
> * *1. **L'Usine** se connecte sur le **"Vendor Portal"** (le web du PLM `suppliers.axolotl.com`). Elle y dépose ses plans finaux, certificats, etc. Elle clique sur "Soumettre".*
> * *2. **Le Contrôleur Qualité Axolotl** (l'employé de la marque) reçoit une alerte dans son PLM. Il vérifie que les PDF ne sont pas flous, et qu'ils correspondent bien au produit. C'est lui qui clique sur le bouton fatal : **"Approuver le Dossier d'Industrialisation"**. (C'est la décision métier).*
> * *3. **Le Logiciel PLM** prend le relais de manière invisible. Il compile tous les PDF validés de ce produit en une seule archive compressée (ex: `SKU-12345_TechPack.zip`). Il pousse informatiquement ce seul et unique fichier `.zip` vers le **Google Cloud Storage** via API.*
> * *4. **Eventarc** est configuré avec un filtre strict : il ne réagit qu'aux fichiers de type `*.zip` (Ce qu'on appelle en architecture l'**Archive Scellée / Sealed Archive**). L'API ne sera déclenchée qu'une seule fois, avec la certitude à 100% que le dossier est définitif, complet, et validé par un humain.*
> 
> C'est cette intégration purement B2B qui lève l'événement furtif `v1.finalized` sur le `.zip` et réveille notre orchestrateur **Temporal**. 
> 
> 🌍 **Zoom sur le Passage à l'Échelle (Scale) : Comment gérer 4000 produits ?**
> *Face à 4000 nouveaux produits pour l'été, l'architecture doit absorber un volume massif. Voici la réalité logistique d'un géant du Retail :*
> * *1. **Massivement Parallèle :** Axolotl ne travaille pas avec une seule usine, mais avec **200 usines** (Vietnam, Portugal, Chine, etc.) travaillant toutes en même temps.*
> * *2. **Plusieurs SKUs par Usine :** L'Usine A (spécialiste du bois) se voit confier 40 tables différentes. Sur son Vendor Portal, elle verra 40 dossiers distincts à remplir.*
> * *3. **Le Flux Continu (Stream) :** Les usines ne soumettent pas les 4000 dossiers le même jour. Les soumissions s'étalent sur 4 à 6 semaines. L'équipe Qualité d'Axolotl (divisée par pôles : Outdoor, Déco, etc.) se connecte chaque matin au PLM et valide les dossiers au fur et à mesure (ex: 150 dossiers validés le mardi, 300 le mercredi).*
> * *4. **L'Élasticité du Cloud :** Ce volume est la raison d'être du Serverless. Chaque fois qu'un dossier est validé, un `.zip` part sur Google Cloud. Ton architecture (Cloud Run + Temporal) scale mathématiquement de 0 à 1000 instances pour absorber les pics du "Mardi", puis redescend à 0 le week-end, traitant chaque SKU de manière isolée et asynchrone.*
> 
> Au lieu de la phase d'enfer humain, notre système intercepte ce flux continu d'Archives Scellées :
> 1. Décompresse et lit tous les PDF de l'usine simultanément (*Google Document AI Batch*).
> 2. Extrait les dimensions de la source de vérité, sans aucune erreur mathématique (*Locked Technical Rendering*).
> 3. Croise ces faits techniques (*Truth Context*) avec le ton de marque (*Editorial Store*).
> 4. Rédige les fiches produits en 15 minutes, générant des textes ultra vendeurs.
> 5. Zéro burnout pour les rédacteurs, et le site est mis à jour en continu, au rythme des usines, pour 0€.

### Étape 6 : Réception Entrepôts et Lancement Web (T0)
Les cargos arrivent. Les meubles entrent physiquement dans les entrepôts. 
Toutes les fiches (écrites par ton Intelligence Artificielle) sont déjà pré-chargées. L'équipe clique sur "Publier la collection".
Les fiches s'affichent, les clients ajoutent au panier, la saison démarre. La "Supply Chain" Data et Physique est parfaitement alignée.
