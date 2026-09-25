# Guide d'utilisation de Clip Studio

Ce guide explique comment faire un clip avec Clip Studio, de la chanson à la vidéo publiée, et quoi faire quand quelque
chose coince. Pour l'installation, voir le [README](../README.md). Pour le fonctionnement interne, voir
[TECHNIQUE.md](TECHNIQUE.md).

- [Ce qu'il te faut](#ce-quil-te-faut)
- [Premiers pas : ta première chanson](#premiers-pas--ta-première-chanson)
- [Les 8 étapes en détail](#les-8-étapes-en-détail)
- [Conseils pour de bonnes planches](#conseils-pour-de-bonnes-planches)
- [Sauvegarde et historique](#sauvegarde-et-historique)
- [Dépannage](#dépannage)

---

## Ce qu'il te faut

| | Obligatoire ? | Rôle |
|---|---|---|
| **La chanson** (mp3, wav, m4a…) | oui | la bande-son du clip |
| **Les paroles exactes** (texte) | oui | un vers par ligne ; elles sont calées automatiquement sur la voix |
| **Un générateur d'images** | oui | c'est toi qui génères les images, à partir des prompts que Clip Studio prépare |
| **Claude Code** (abonnement Claude Pro/Max) | non, mais très utile | rédige les descriptions de scènes et d'autres textes, **uniquement quand tu cliques** |
| **Un générateur de vidéos** (Google Flow / Veo…) | non | pour animer certaines images |
| Environ **5 Go de mémoire vive libre** | oui | pour caler les paroles (modèle Whisper « medium ») |

**Le générateur d'images** doit accepter de longues consignes et, si possible, le format **32:27** (sinon carré). Il doit
savoir produire une image composée de **6 photos en grille**. Les générateurs récents (Seedream, Qwen-Image, ChatGPT,
Gemini, Midjourney…) en sont capables, avec plus ou moins de fidélité : fais un essai avec la première planche.
Clip Studio vérifie ensuite la grille et signale le texte parasite.

**Sans Claude**, tout reste possible : Clip Studio prépare une demande (`build/a_decrire.md`) que tu peux coller dans
n'importe quel assistant IA, puis tu recolles sa réponse.

---

## Premiers pas : ta première chanson

Compte 30 à 60 minutes, surtout pour générer les images.

1. **Lance Clip Studio** (`Clip Studio.bat` sous Windows, `./clip-studio.sh` sous Linux) : la page s'ouvre dans ton
   navigateur. Clique sur **« + Nouveau projet »** et donne un nom sans espaces (ex. `ma_chanson`).
2. **Étape 1 · Projet** : dépose le mp3, puis colle les paroles dans le cadre et enregistre.
3. **Étape 2 · Préparer** : écris en quelques lignes l'**intention** de la chanson (de quoi elle parle vraiment, le ton,
   l'époque) et le **style visuel** voulu, puis clique sur **Préparer**. Compte 1 à 3 minutes : rythme, calage des paroles,
   nombre d'images à générer.
4. **Étape 3 · Descriptions** : clique sur **« ✨ Rédiger avec Claude »**. Relis les scènes et refais celles qui ne te
   plaisent pas (bouton ↻).
5. **Étape 4 · Planches** : pour chaque planche, **copie le prompt**, génère l'image dans ton générateur (nouvelle
   conversation à chaque fois), puis **colle-la** (Ctrl+V) ou dépose-la sur sa planche. Clique ensuite sur **Découper**.
6. **Étape 7 · Rendu** : lance un **Aperçu** (petite vidéo rapide) pour vérifier. Si tout va bien, lance le **Rendu final**.
7. **Étape 8 · Publication** (optionnel) : titre, description YouTube avec chapitres, et prompts de miniature.

Les étapes 5 (Vidéos) et 6 (Options) sont facultatives : les réglages par défaut donnent déjà un clip propre. Essaie
ensuite un préréglage (Ballade, Rock…) à l'étape 6.

---

## Les 8 étapes en détail

### 1. Projet
- **Chanson** : mp3, wav, m4a, flac ou ogg.
- **Paroles** : le texte **exact** chanté, un vers par ligne, une ligne vide entre les couplets. Les en-têtes `[Verse 1]`,
  `[Chorus]`, `[Bridge]` sont facultatifs. Sans en-tête, un bloc répété à l'identique est reconnu comme refrain.
- Si tu remplaces le mp3 ou modifies les paroles plus tard, Clip Studio le détecte : un avertissement s'affiche et le
  calage est refait tout seul au prochain « Préparer » ou au prochain rendu.

### 2. Préparer
- **Intention** : ce que les paroles ne disent pas (second degré, hommage, colère, contexte, choses à éviter). Elle
  guide Claude. Le **style** (ex. « photoréaliste années 80, grain VHS ») est, lui, repris dans chaque prompt d'image.
- **Préparer** détecte le rythme, cale chaque mot sur la voix, puis calcule le nombre d'images : **une image par vers
  unique** (un refrain répété réutilise ses images).
- **Évaluation par Claude** : il recommande combien d'images d'**ambiance** ajouter pour les passages sans paroles
  (intro, solos, fin) et un préréglage. Tant qu'aucune planche n'est générée, la recommandation est appliquée d'office.
- **Début du chant** : si le karaoké commence trop tôt (le 1er vers affiché pendant l'intro), indique quand le chant
  commence vraiment (ex. `0:34`) : les premiers vers sont recalés aussitôt.
- **Photos de solo** (optionnel) : images panoramiques très larges (21:9) sur lesquelles la caméra glisse pendant les
  passages instrumentaux. Claude peut en écrire les prompts. Photos de solo et images d'ambiance alternent.

### 3. Descriptions
Une courte scène par image : type de plan, sujet, action, décor, lumière. L'action doit **illustrer littéralement le
vers**. Rédige-les avec Claude, corrige-les à la main, ou refais-en une avec une consigne (« plus sombre », « en extérieur »).
Les **personnages récurrents** sont définis une fois (par Claude à la première rédaction, visibles en haut de
l'étape 3, modifiables dans `projet.json` → `"personnages"`) et gardent le même aspect d'une image à l'autre.

### 4. Planches
Une **planche** est une seule image générée qui contient **6 scènes** (grille 2×3). Clip Studio la découpe ensuite en
6 images. C'est ce qui permet de faire un clip entier avec quelques générations seulement (ex. 18 images → 3 planches).
- **Copier le prompt**, générer, puis coller ou déposer l'image sur la bonne planche (P1, P2…).
- **Vérifier** contrôle le format et la grille. **Découper** extrait et agrandit les cases (×4 avec Real-ESRGAN).
- **Texte parasite** (Windows) : après la découpe, les légendes ou enseignes lisibles sont signalées. Retouche la case
  concernée si ce n'est pas voulu.
- **Retoucher une seule case** : génère une image 16:9 seule pour la case ratée et dépose-la. Pas besoin de refaire
  toute la planche.

### 5. Vidéos (optionnel)
Clique sur une image de la galerie pour la remplacer par une **vidéo de ~10 s** : Claude écrit le prompt (seulement si
tu le demandes), tu génères la vidéo dans Flow (« Images vers vidéo », image de départ = cette image, format 16:9), puis
tu la déposes. La vidéo remplace l'image partout où elle apparaît ; les effets et le karaoké restent par-dessus.

### 6. Options
Commence par un **préréglage** (Ballade, Rock, VHS rétro, Sobre), puis ajuste : mouvements de caméra, étalonnage, grain,
particules (neige, braises, pluie…), fumée, flammes, éclairs, transitions, karaoké (police, couleurs, position,
animation), titre et logo, mention « Version IA », format (16:9, 4K, vertical 9:16, carré). Les réglages restent
d'un rendu à l'autre.

### 7. Rendu
- **Aperçu rapide** : vidéo 960×540 pour vérifier le montage, en environ 1 minute.
- **Rendu final** : 1080p avec le son, en 1 à 3 minutes selon ta machine.
- **Aperçu d'un passage** : juste un extrait (ex. de 0:30 à 0:50), pour tester un réglage.
- **Variante** : un rendu sous un autre nom, pour comparer des réglages.
- Les vidéos se trouvent dans `projets/<nom>/build/`. Les boutons permettent de les lire, de les ouvrir ou de les supprimer.

### 8. Publication
Claude rédige un titre, une description YouTube et deux prompts de miniature. Clip Studio ajoute les **chapitres**
(calculés sur les paroles), les paroles et la **mention IA** adaptée : chanson originale réinterprétée par IA, images
IA seulement, ou clip entièrement IA.

---

## Conseils pour de bonnes planches
- **Une nouvelle conversation par planche** dans le générateur : une « variation » de l'image précédente recopie les
  mêmes scènes.
- **Jamais les paroles dans le prompt** : un texte entre guillemets finit écrit dans l'image. Clip Studio ne les met
  jamais ; ne les ajoute pas.
- Évite dans les descriptions les **documents, écrans et pancartes** : ils produisent du faux texte.
- Les **plans larges** passent le mieux en 16:9. Pour un gros plan, pense à « tête entière, de l'air au-dessus ».
- Garde une **copie de chaque image générée** : les liens des générateurs expirent.
- Planche presque bonne, mais une case ratée : **retouche la case**, ne régénère pas tout.

---

## Sauvegarde et historique
- Tes projets (mp3, images, vidéos) ne sont que sur ton ordinateur. **`Sauvegarder les projets.bat`** (Windows) ou
  **`./sauvegarder-projets.sh`** (Linux) les copie vers le dossier de ton choix (OneDrive par défaut sous Windows), sans jamais rien
  supprimer dans la sauvegarde. Les rendus vidéo ne sont pas copiés : ils se refont.
- Chaque modification des réglages d'un projet est gardée : à l'étape 1, **« 🕘 Historique des réglages »** permet de
  revenir à une version précédente.

---

## Dépannage

| Problème | Solution |
|---|---|
| **Le karaoké démarre trop tôt** (1er vers pendant l'intro) | Étape 2 → **Début du chant** : indique le moment où la voix commence. |
| **Le karaoké est décalé partout** de la même valeur | Étape 6 → Karaoké → **Décalage** (en secondes, + = plus tard). |
| **Les images ne suivent plus les paroles** après un changement de mp3 | Relance **Préparer** (le calage est refait automatiquement), puis un rendu. |
| **Du texte apparaît dans une image** (légende, enseigne) | Étape 4 → **Retoucher une seule case** avec une image sans texte. Sous Windows, ces cases sont signalées après la découpe. |
| **« Vignettes … au lieu de 16:9 »** à la vérification | Le générateur n'a pas respecté le format : régénère la planche au format 32:27, ou continue (les images seront un peu recadrées). |
| **La grille n'est pas reconnue** (mauvais découpage) | Le générateur a fait plus ou moins de 6 photos, ou sans séparation nette : régénère la planche. |
| **Le calage des paroles plante** ou l'ordinateur rame | Whisper « medium » demande environ 5 Go de mémoire libre : ferme les autres programmes. Sous WSL ou Docker, augmente la mémoire allouée. |
| **« Real-ESRGAN indisponible »** | Pas de carte graphique compatible Vulkan : les cases sont agrandies autrement, un peu moins net. Rien à faire. |
| **Un bouton répond « Action inconnue »** / bandeau orange | Clip Studio a été mis à jour pendant qu'il tournait : ferme sa fenêtre noire (ou son terminal) et relance-le. |
| **Les boutons « avec Claude » sont absents** | Claude Code n'est pas installé ou pas trouvé : installe-le (voir le README), puis relance Clip Studio. |
| **« Tempo » visiblement faux** (effets deux fois trop rapides) | Étape 6 → Technique → **Tempo (BPM)** : mets le bon nombre, puis relance Préparer. |
| **La page ne s'ouvre pas** | Regarde l'adresse affichée dans la fenêtre noire (le port peut être 8766, 8767… si 8765 est occupé). |
| **Le rendu est lent** | Normal sans carte graphique AMD (encodage processeur). Utilise l'aperçu rapide pour les essais. |

Toujours bloqué ? Vérifie l'installation avec `python -m clip check` (depuis le dossier de Clip Studio :
`.venv\Scripts\python.exe -m clip check` ou `.venv/bin/python -m clip check`).
