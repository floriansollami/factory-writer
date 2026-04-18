# Pourquoi choisir Document AI plutôt qu'un OCR directement via LLM

J'ai choisi **Document AI** plutôt qu'un OCR directement via un LLM parce que le besoin du client impose une ingestion documentaire **contrôlée, traçable et reproductible**, pas seulement une compréhension globale du PDF.

Un LLM comme Gemini peut lire un PDF, mais il mélange plusieurs responsabilités en une seule étape : lecture du document, interprétation du contenu, structuration métier et génération de réponse. Pour une démo simple, ça peut fonctionner. Mais pour Factory Writer, on doit pouvoir expliquer d'où vient chaque information, vérifier les erreurs, rejouer le pipeline et réduire au maximum les hallucinations, surtout pour les dossiers techniques d'usine.

Document AI joue le rôle de **parseur documentaire spécialisé**. Il transforme le PDF en contenu structuré : texte, blocs, chunks, pages, tableaux ou éléments de layout selon le processor utilisé. Ensuite seulement, LiteLLM/Gemini intervient pour faire l'extraction sémantique métier, par exemple transformer des fragments du guide de style en règles de ton ou en claims interdits.

La séparation est donc volontaire :

```text
Document AI = extraction documentaire / layout / OCR / structure
LiteLLM = compréhension métier / structuration sémantique / rédaction
```

Cette séparation apporte plusieurs avantages importants :

- **Traçabilité** : on peut relier une règle de style ou un fact technique à un fragment source extrait du document.
- **Débogage** : si une sortie est mauvaise, on sait si le problème vient du parsing documentaire ou de l'interprétation LLM.
- **Reproductibilité** : on peut figer une version de processor Document AI et rejouer le même document avec le même comportement.
- **Scalabilité** : Document AI gère nativement le batch depuis GCS et écrit ses résultats structurés dans GCS.
- **Réduction du risque d'hallucination** : le LLM ne devient pas la source brute de vérité ; il travaille sur des fragments déjà extraits.
- **Alignement avec le besoin client** : pour "Zero Technical Hallucination", les dimensions, matériaux et certifications doivent venir d'une extraction contrôlée, pas d'une réponse générative opaque.

Donc mon choix n'est pas "Document AI parce que Gemini ne sait pas lire un PDF". Gemini sait le faire. Mon choix est : **Document AI pour industrialiser l'ingestion documentaire**, puis **LiteLLM pour garder la flexibilité modèle côté compréhension et génération**.

En résumé :

```text
Utiliser seulement LiteLLM/Gemini = plus rapide à prototyper, mais moins contrôlable.
Utiliser Document AI + LiteLLM = plus robuste, plus traçable, plus défendable en architecture client.
```

Pour Factory Writer, où le client demande productivité, zéro hallucination technique, scalabilité et approche context-first, l'architecture Document AI puis LiteLLM est plus professionnelle et plus sûre.
