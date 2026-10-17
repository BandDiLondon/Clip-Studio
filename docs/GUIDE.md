# Guide d'utilisation de Clip Studio

**Français** | [English](GUIDE.en.md)

Ce guide explique comment faire un clip avec Clip Studio, de la chanson à la vidéo publiée, et quoi faire quand quelque
chose coince. Pour l'installation, voir le [README](../README.md). Pour le fonctionnement interne, voir
[TECHNIQUE.md](TECHNIQUE.md).

- [Ce qu'il te faut](#ce-quil-te-faut)
- [Premiers pas : ta première chanson](#premiers-pas--ta-première-chanson)
- [Les 8 étapes en détail](#les-8-étapes-en-détail)
- [Conseils pour de bonnes planches](#conseils-pour-de-bonnes-planches)
- [Temps de calcul](#temps-de-calcul)
- [Sauvegarde et historique](#sauvegarde-et-historique)
- [Dépannage](#dépannage)

---

## Ce qu'il te faut

| | Obligatoire? | Rôle |
|---|---|---|
| **La chanson** (mp3, wav, m4a…) | oui | la bande-son du clip |
| **Les paroles exactes** (texte) | oui | un vers par ligne; elles sont calées automatiquement sur la voix |
| **Un générateur d'images** | oui | c'est toi qui génères les images, à partir des prompts que Clip Studio prépare |
| **Claude Code** (abonnement Claude Pro/Max) | non, mais très utile | rédige les descriptions de scènes et d'autres textes, **uniquement quand tu cliques** |
| **Un générateur de vidéos** (Google Flow / Veo…) | non | pour animer certaines images |
| Environ **5 Go de mémoire vive libre** | oui | pour caler les paroles (modèle Whisper « medium »); 2 Go suffisent avec le modèle « small », moins précis (étape 2) |

**Le générateur d'images** doit accepter de longues consignes et, si possible, le format **32:27** (sinon carré). Il doit
savoir produire une image composée de **6 photos en grille**. Les générateurs récents (Seedream, Qwen-Image, ChatGPT,
Gemini, Midjourney…) en sont capables, avec plus ou moins de fidélité : fais un essai avec la première planche.
Clip Studio vérifie ensuite la grille et signale le texte parasite.

**Sans Claude**, tout reste possible : Clip Studio prépare une demande (`build/a_decrire.md`) que tu peux coller dans
n'importe quel assistant IA, puis tu recolles sa réponse.

**Langue** : l'interface est en français ou en anglais (sélecteur en haut à droite; par défaut, la langue de ton
navigateur). Chaque projet a aussi une **langue de la chanson** (étape 1), qui sert au calage des paroles et à la
langue des textes rédigés : descriptions de scènes, prompts d'images, publication YouTube. Les deux sont
indépendantes : tu peux utiliser l'interface en français pour une chanson en anglais.

---

## Premiers pas : ta première chanson

Compte **15 à 25 minutes** pour une chanson de 3 minutes : environ 4 minutes de calcul pour Clip Studio, le reste pour
générer les planches dans ton générateur (1 à 2 minutes par planche, plus les essais) et relire. Détail dans
[Temps de calcul](#temps-de-calcul).

1. **Lance Clip Studio** (`Clip Studio.bat` sous Windows, `./clip-studio.sh` sous Linux, `Clip Studio.command` sous
   macOS) : la page s'ouvre dans ton navigateur. Clique sur **« + Nouveau projet »** et donne un nom sans espaces (ex. `ma_chanson`).
2. **Étape 1 · Projet** : dépose le mp3, puis colle les paroles dans le cadre et enregistre. Vérifie la **langue de la
   chanson**.
3. **Étape 2 · Préparer** : écris en quelques lignes l'**intention** de la chanson (de quoi elle parle vraiment, le ton,
   l'époque) et le **style visuel** voulu, puis clique sur **Préparer**. Compte environ 1 minute (rythme, calage des paroles,
   nombre d'images à générer), plus un téléchargement unique de 1,5 Go la toute première fois.
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
- **Langue de la chanson** (français ou anglais) : sert au calage des paroles et aux textes rédigés pour ce projet. Si
  tu la changes après « Préparer », les paroles sont recalées au prochain « Préparer » ou au prochain rendu.
- Si tu remplaces le mp3 ou modifies les paroles plus tard, Clip Studio le détecte : un avertissement s'affiche et le
  calage est refait tout seul au prochain « Préparer » ou au prochain rendu.

### 2. Préparer
- **Intention** : ce que les paroles ne disent pas (second degré, hommage, colère, contexte, choses à éviter). Elle
  guide Claude. Le **style** (ex. « photoréaliste années 80, grain VHS ») est, lui, repris dans chaque prompt d'image.
- **Préparer** détecte le rythme, cale chaque mot sur la voix, puis calcule le nombre d'images : **une image par vers
  unique** (un refrain répété réutilise ses images).
- **Évaluation par Claude** : il recommande combien d'images d'**ambiance** ajouter pour les passages sans paroles
  (intro, solos, fin) et un préréglage. Tant qu'aucune planche n'est générée, la recommandation est appliquée d'office.
- **Calage des paroles** : « Précis » (Whisper medium, environ 5 Go de mémoire, par défaut) ou « Mémoire limitée »
  (Whisper small, environ 2 Go, moins précis). Utilise « small » seulement si le calage plante faute de mémoire.
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
- **Texte parasite** : après la découpe, les légendes, enseignes ou t-shirts imprimés lisibles sont signalés. Retouche la case
  concernée si ce n'est pas voulu.
- **Retoucher une seule case** : génère une image 16:9 seule pour la case ratée et dépose-la. Pas besoin de refaire
  toute la planche.

### 5. Vidéos (optionnel)
Clique sur une image de la galerie pour la remplacer par une **vidéo de ~10 s** : Claude écrit le prompt (seulement si
tu le demandes), tu génères la vidéo dans Flow (« Images vers vidéo », image de départ = cette image, format 16:9), puis
tu la déposes. La vidéo remplace l'image partout où elle apparaît; les effets et le karaoké restent par-dessus.

### 6. Options
Commence par un **préréglage** (Ballade, Rock, VHS rétro, Sobre), puis ajuste : mouvements de caméra, étalonnage, grain,
particules (neige, braises, pluie…), fumée, flammes, éclairs, transitions, karaoké (police, couleurs, position,
animation), titre et logo, mention « Version IA », format (16:9, 4K, vertical 9:16, carré). Les réglages restent
d'un rendu à l'autre.

Les effets **automatiques** (particules, fumée, éclairs, rayons de lumière, mouvement de caméra) lisent les descriptions
de scènes, en français ou en anglais : « orage » amène la pluie et les éclairs, « feu » les braises et la fumée,
« plan large » un travelling, et ainsi de suite.

### 7. Rendu
- **Aperçu rapide** : vidéo 960×540 pour vérifier le montage, en environ 30 secondes pour une chanson de 3 minutes.
- **Rendu final** : 1080p avec le son, en 1 à 1 min 30 pour une chanson de 3 minutes; 4 à 6 minutes avec beaucoup
  d'effets (parallaxe 3D, fumée, flou de fond…); environ 3× plus long en 4K.
- **Aperçu d'un passage** : juste un extrait (ex. de 0:30 à 0:50), pour tester un réglage.
- **Variante** : un rendu sous un autre nom, pour comparer des réglages.
- Les vidéos se trouvent dans `projets/<nom>/build/`. Les boutons permettent de les lire, de les ouvrir ou de les supprimer.

### 8. Publication
Claude rédige un titre, une description YouTube et **3 idées de miniature** (avec et sans texte), dans la langue de la chanson. Clip Studio ajoute les **chapitres**
(calculés sur les paroles), les paroles et la **mention IA** adaptée : chanson originale réinterprétée par IA, images
IA seulement, ou clip entièrement IA. Pour la chanson d'un autre artiste, choisis une origine **Fan-made** (chanson
officielle ou reprise IA) : la description déclare que tu ne possèdes aucun droit sur la chanson, que tu es simplement
un fan qui fait un clip avec Clip Studio, sans but lucratif, et que tu retireras la vidéo si un ayant droit le demande.
Ajoute alors le lien officiel de la chanson : il suit la déclaration.

Options de l'étape (enregistrées dans le projet) :
- **Crédits et liens** : paroles, musique, interprétation, clip, mention « Clip réalisé avec Clip Studio », et tes liens
  (un par ligne). Ajoutés tels quels à la description.
- **Rédaction** : ton (automatique, drôle, sérieux, promo, québécois familier), accroche normale ou courte, emojis, et
  blocs de la description à garder (accroche, mention, chapitres, paroles, crédits, liens, hashtags).
- **Miniature** : vignette de référence (la 1re idée reprend cette scène et ses personnages tels que dans le clip),
  texte et couleur du bandeau, formats carré 1:1 et vertical 9:16 en plus du 16:9.
- **Profils** : « Enregistrer comme profil… » garde l'origine, les crédits, les liens, la rédaction et la miniature
  (ex. « KPR », « Fan-made ») ; « Charger » les applique à un autre projet.

---

## Conseils pour de bonnes planches
- **Une nouvelle conversation par planche** dans le générateur : une « variation » de l'image précédente recopie les
  mêmes scènes.
- **Jamais les paroles dans le prompt** : un texte entre guillemets finit écrit dans l'image. Clip Studio ne les met
  jamais; ne les ajoute pas.
- Évite dans les descriptions les **documents, écrans et pancartes** : ils produisent du faux texte.
- Les **plans larges** passent le mieux en 16:9. Pour un gros plan, pense à « tête entière, de l'air au-dessus ».
- Garde une **copie de chaque image générée** : les liens des générateurs expirent.
- Planche presque bonne, mais une case ratée : **retouche la case**, ne régénère pas tout.

---

## Temps de calcul

Mesurés sur une chanson de **3 min 14** (18 images, 3 planches), sur deux machines :
- **PC puissant** : processeur 16 cœurs (Ryzen 9 9950X3D), carte graphique AMD RX 9070 XT;
- **PC ordinaire** : même PC limité à 4 cœurs / 8 threads, encodage vidéo par le processeur.

| Étape | PC puissant | PC ordinaire |
|---|---|---|
| Préparer : rythme + calage des paroles (sans Claude) | 40 s | 55 s |
| Premier calage seulement : téléchargement du modèle Whisper | + 1,5 Go (selon ta connexion) | idem |
| Claude : évaluation / descriptions de 18 images / publication | 20 s / 35 s / 20 s | idem (dépend de Claude) |
| Découpe des 3 planches (18 cases) | 12 s | 12 s avec carte graphique; ~12 min sans |
| Détection de texte dans les cases (après la découpe) | 3 à 6 s | ~5 s |
| Aperçu rapide complet | 35 s | 30 s |
| Rendu final 1080p | 1 min | 1 min 25 |
| Rendu final 1080p avec effets lourds (parallaxe 3D, fumée, particules, flou de fond) | 4 min | 6 min 15 |
| Rendu final 4K | 3 min | — |

- Les temps de rendu sont **proportionnels à la durée de la chanson** : pour 4 minutes, compte environ +25 %.
- Sur un portable ou un vieux PC (2 cœurs, peu de mémoire), compte au moins le double du « PC ordinaire »
  (estimation, non mesuré).

---

## Sauvegarde et historique
- Tes projets (mp3, images, vidéos) ne sont que sur ton ordinateur. **`Sauvegarder les projets.bat`** (Windows) ou
  **`./sauvegarder-projets.sh`** (Linux, macOS) les copie vers le dossier de ton choix (OneDrive par défaut sous
  Windows), sans jamais rien supprimer dans la sauvegarde. Les rendus vidéo ne sont pas copiés : ils se refont.
- Chaque modification des réglages d'un projet est gardée : à l'étape 1, **« 🕘 Historique des réglages »** permet de
  revenir à une version précédente.

---

## Dépannage

| Problème | Solution |
|---|---|
| **Le karaoké démarre trop tôt** (1er vers pendant l'intro) | Étape 2 → **Début du chant** : indique le moment où la voix commence. |
| **Des vers défilent en un éclair** ou sont chantés ailleurs (après une longue intro ou un solo) | Normalement corrigé tout seul : « Préparer » écoute alors la chanson et cale chaque section séparément (environ 1,5 min de plus, message « calage par sections » dans le journal). Si ça persiste, vérifie que le .txt suit l'ordre chanté, avec ses en-têtes [Section]. |
| **Le karaoké est décalé partout** de la même valeur | Étape 6 → Karaoké → **Décalage** (en secondes, + = plus tard). |
| **Les paroles sont mal calées sur une chanson en anglais** | Étape 1 → vérifie la **langue de la chanson**, puis relance **Préparer**. |
| **Les images ne suivent plus les paroles** après un changement de mp3 | Relance **Préparer** (le calage est refait automatiquement), puis un rendu. |
| **Du texte apparaît dans une image** (légende, enseigne) | Étape 4 → **Retoucher une seule case** avec une image sans texte. Ces cases sont signalées à l'étape 4 après la découpe. |
| **« Vignettes … au lieu de 16:9 »** à la vérification | Le générateur n'a pas respecté le format : régénère la planche au format 32:27, ou continue (les images seront un peu recadrées). |
| **La grille n'est pas reconnue** (mauvais découpage) | Le générateur a fait plus ou moins de 6 photos, ou sans séparation nette : régénère la planche. |
| **Le calage des paroles plante** ou l'ordinateur rame | Whisper « medium » demande environ 5 Go de mémoire libre : ferme les autres programmes. Sous WSL ou Docker, augmente la mémoire allouée. En dernier recours, à l'étape 2, choisis « Calage des paroles : mémoire limitée » (modèle « small », environ 2 Go) : le karaoké sera moins précis (sur une chanson test, 12 vers sur 30 décalés de plus d'une demi-seconde). |
| **« Real-ESRGAN indisponible »** | Pas de carte graphique compatible Vulkan : les cases sont agrandies autrement, un peu moins net. Rien à faire. |
| **Un bouton répond « Action inconnue »** / bandeau orange | Clip Studio a été mis à jour pendant qu'il tournait : ferme sa fenêtre noire (ou son terminal) et relance-le. |
| **Les boutons « avec Claude » sont absents** | Claude Code n'est pas installé ou pas trouvé : installe-le (voir le README), puis relance Clip Studio. |
| **« Tempo » visiblement faux** (effets deux fois trop rapides) | Étape 6 → Technique → **Tempo (BPM)** : mets le bon nombre, puis relance Préparer. |
| **La page ne s'ouvre pas** | Regarde l'adresse affichée dans la fenêtre noire (le port peut être 8766, 8767… si 8765 est occupé). |
| **Le rendu est lent** | Il dépend surtout du **processeur** (nombre de cœurs) et des **effets** : parallaxe 3D, fumée et flou de fond multiplient le temps par environ 4, la 4K par 3. La carte graphique change peu (~10 %). Pour les essais, utilise l'**aperçu d'un passage**. |
| **La découpe est très lente** (plusieurs minutes) | Pas de carte graphique Vulkan utilisable (fréquent sous WSL ou dans une machine virtuelle) : Real-ESRGAN calcule sur le processeur, environ 40 s par case. C'est normal; ça ne se fait qu'une fois par planche. |
| **Les messages de l'installateur, de la console ou de la ligne de commande sont dans la mauvaise langue** | Ils suivent la langue du système. Pour la forcer : `CLIP_LANG=fr` (ou `en`) avant la commande, ex. `set CLIP_LANG=fr` dans la console Windows. |

Toujours bloqué? Vérifie l'installation avec `python -m clip check` (depuis le dossier de Clip Studio :
`.venv\Scripts\python.exe -m clip check` ou `.venv/bin/python -m clip check`).
