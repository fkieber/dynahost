# Web-service pour hôtes en adresse IP dynamique

#### Fonctionnalités

- Changement de l'adresse IP d'un domaine. Ce changement ne se fait que si
  l'adresse IP a changé.
- Historique des changements d'IP.
- Envoie d'un mail en cas de changement d'IP.
- L'adresse IP de l'hôte est récupérée par le web-service.
  Il n'est donc pas nécessaire d'installer quoi que ce soit sur l'hôte.
  Il suffit simplement d'appeler régulièrement ce web-service.

#### Utilité

- Si un routeur ne prend pas en charge un service DynHost.
- Si on doit mettre à jour manuellement la nouvelle adresse IP dans
  certains fichier de configuration. L'envoi d'un mail lors du changement
  d'IP est utile pour cela.
- Si on veut garder une trace des changements d'IP pour savoir à quelle
  fréquence le FAI les fait.

#### Services (ou backend) pris en charge

- DynHost OVH.

#### Type d'adresses IP

- IPV4.

## Fonctionnement

Le web-service doit être installé sur un serveur quelque part sur le web.
L'hôte qui est susceptible de changer d'adresse IP appelle régulièrement ce
web-service. Par exemple un hébergement personnel derrière un FAI 
sans adresse IP fixe, 

Le web-service détermine l'adresse IP de l'appelant et, si celle-ci à changé, il
met à jour le nom de domaine avec cette nouvelle adresse en appelant l'API
relative au backend utilisé.

L'évènement est mis en historique et un mail est éventuellement envoyé.


## Comment faire

### Installation

    pip3 install dynahost

Insatller python3-pip si pip3 non trouvé.

Il est fortement conseillé d'installer ce web-service dans un 
environnement virtuel. 
Voir [virtualenvwrapper](https://python-guide-pt-br.readthedocs.io/fr/latest/dev/virtualenvs.html#virtualenvwrapper)


### Lancement du web-service

Afficher l'aide : `dynahost -h`

Les paramètres peuvent être passés en ligne de commande ou à l'aide
d'un fichier de configuration. Un fichier **dynahost_config_sample.ini**
est fourni comme exemple.

Un fichier **dynahost.service** est fourni pour un lancement via *systemd*.

Ces fichiers fournis sont souvent installés dans `/usr/local/etc/`.


### Mise à jour du DynHost

#### Schéma de base

	url/update?paramètres

#### Paramètres

	backend = l'id du service DynHost (Voir l'aide de dynahost).
	secid = Identifiant de sécurité.
	host = Le nom de domaine à traiter
	login = Le login au service DynHost
	pass = Le mot de passe du service DynHost
	email = L'adresse mail à laquelle envoyer les changement d'IP
		Ce paramètre est facultatif.

**`secid`** est un identifiant quelconque. Il est associé à un hôte 
et sauvegardé de façon crypté lors du premier appel pour cet hôte.

Il doit être le même pour les appels suivants. 
Sans celui-ci les accès ultérieurs sont rejetés.

#### Exemples

Pour ceux qui ne veulent pas installer le service, je mets à disposition 
mon propre serveur.
Mon service possède l'url : https://dynhost.frkb.fr

Celui-ci est utilisé dans les exemples suivants.

###### Avec wget ou dans un navigateur

	wget https://dynhost.frkb.fr/update?backend=ovh&\
	secid=abc123xyz&host=test.exemple.com&\
	login=exemmple.com-test&pass=untrucsecret&\
	email=test@exemple.com
	
Pour des raisons de sécurité, il est conseillé d'appeler le service via
la curl (Il se peut que les requêtes GET avec le mot de passe en clair
soient loguées au niveau du serveur web).

###### Avec curl
	
	curl -d "backend=ovh" \
	-d "secid=abc123xyz" \
	-d "host=test.exemple.com" \
	-d "login=exemple.com-test" \
	-d "pass=untrucsecret" \
	-d "email=test@exemple.com" \
	https://dynhost.frkb.fr/update


Voilà ! Il suffit maintenant de placer cela dans une tâche cron.


### Affichage de l'historique
	
#### Schéma de base

	url/log?paramètres

#### Paramètres

	secid = Identifiant de sécurité.
	host = Le nom de domaine à traiter

###### Avec wget ou dans un navigateur

	wget https://dynhost.frkb.fr/log?\
	secid=abc123xyz&host=test.exemple.com&
	
###### Avec curl
	
L'utilisation de curl n'est significative que dans un script.
	
	curl -d "login=exemple.com-test" \
	-d "secid=abc123xyz" \
	-d "host=test.exemple.com" \
	https://dynhost.frkb.fr/log
