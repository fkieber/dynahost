Web-service pour administrer des hôtes ayant une adresse IP dynamique
=====================================================================

Ce web-service fournit les fonctionnalité suivantes :
- Changement de l'adresse IP d'un domaine. Ce changement ne se fait que en 
  cas de changement d'adresse IP.
- Historique des changements d'IP.
- Envoie de mail en cas de changement d'IP.

Services pris en charge :
- DynHost OVH.

Type d'adresses IP :
- IPV4.

Fonctionnement
--------------


Comment faire
-------------

- Installation::

    pip3 install dynahost
    (insatller python3-pip si pip3 non trouvé)



- Acces your project:

  http://localhost:6543

- Mise à jour du DynHost via curl::

	curl -d "backend=ovh" \
	-d "host=dyntest.exemple.com" \
	-d "login=exemple.com-dyntest" \
	-d "pass=my sercret thing" \
	-d "mail=contact@exemple.com" \
	https://dynhost.frkb.fr/update

