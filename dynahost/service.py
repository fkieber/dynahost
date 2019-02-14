#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
dynahost : Administration d'hôtes ayant une adresse IP dynamique
================================================================
"""

import os
import hashlib
import argparse, textwrap
from dynahost.__init__ import __version__
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
import sqlite3
import requests
import smtplib
import html2text
import configparser
import bcrypt

# Pour sendemail
from email.message import EmailMessage

# Config =====================================================================

# Port par défaut
dft_port = 4000

# Interface réseau par défaut
dft_itf = 'localhost'

# Nom de la base de données
db_name = "dynahost.db"

# Mot de passe maître par défaut (préférer celui du fichier de config)
master_pw = 'rAvKISjBEiteLP6vXy2S77'

# Liste des backends
bkends = {
	'ovh': 'OVH',
}

# Corps du message de changement d'adresse IP
tpl_msg_chg_ip = """\
<html>
  <head></head>
  <body>
	<p>Bonjour,<br>
		<br>
		L'adresse IP de l'hôte "{host}" à changé.<br>
		Elle est passée de {old} à {new}.<br>
		<br>
		Cordialement,<br>
		Dynhost service.
	</p>
  </body>
</html>
"""

# Sortie html de la log
tpl_log_header = """\
<!DOCTYPE html>
<html>
	<head>
		<style>
			table, th, td {{
				border: 1px solid black;
			}}
		</style>
	</head>
	<body>
		<p>Log de l'hôte <b>{host}</b> : (<b>{ip}</b>)</p>
		<table>
			<tr>
				<th>Date/heure</th>
				<th>Adresse IP</th>
			</tr>
"""

tpl_log_line = """\
			<tr>
				<td>{date}</td>
				<td>{ip}</td>
			</tr>
"""

tpl_log_foot = """\
		</table>
	</body>
</html>
"""

# Programme ==================================================================

def lst_backends():
	
	"Affichage des backends supportés"
	
	print("Liste des backends supportés :")
	print("ID", "\t", "Description")
	print("===============================")
	
	for bke in bkends.keys():
		print(bke, "\t", bkends[bke])

def hash_password(pw):

	"""Crypte le mot de passe pw et retourne son hash"""

	return bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt()).decode('utf8')


def check_password(pw, hashed_pw):

	"""Test le mot de passe pw par rapport à son hash hashed_pw.
	S"il y a correspondance, renvoie True, sinon False.
	"""

	return bcrypt.checkpw(pw.encode('utf8'), hashed_pw.encode('utf8'))


def create_db(prm):
	
	"Création la base de données."
	
	try:
		conn = sqlite3.connect(prm['db_name'])
		cursor = conn.cursor()
		cursor.execute("CREATE TABLE hosts(" +
			"id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, " +
			"host TEXT, " +
			"last_ip TEXT, " +
			"sec_id TEXT)")
		cursor.execute("CREATE INDEX hosts_host ON hosts (host)")
		cursor.execute("CREATE TABLE log(" +
			"id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, " +
			"host_id INTEGER, " +
			"mod_date DATETIME DEFAULT (datetime('now', 'localtime') ), "
			"new_ip TEXT)")
		cursor.execute("CREATE INDEX log_host ON log (host_id, mod_date)")
		conn.commit()
		if prm['debug']:
			print('Nouvelle base de donnée "{0}" créée.'.format(prm['db_name']))
		
	except sqlite3.OperationalError:
		if prm['debug']:
			print('Utilisation de la base de donnée "{0}".'.format(prm['db_name']))
	except Exception as e:
		print("Erreur")
		conn.rollback()
		raise e
	finally:
		conn.close()


# Web service ================================================================
class Websrv(object):

	def __init__(self, prm):

		"Lancement du Web-service"

		self.prm = prm
		run_simple(prm['itf'], prm['port'], self.service, 
			use_debugger=prm['debug'], 
			use_reloader=prm['debug'])

	@Request.application
	def service(self, request):

		"Traitement des demandes"
		
		# Lecture de l'adresse IP du client
		try:
			cip = request.remote_addr
			cip = request.environ['REMOTE_ADDR']
			cip = request.environ['HTTP_X_REAL_IP']
		except:
			pass
		
		# Lecture du chemin
		path = request.path
		
		# Lecture des paramètres
		if request.method == 'POST':
			self.data = request.form
		else:
			self.data = request.args
		
		# Debogage
		if self.prm['debug']:
			print ("IP =", cip)
			print ("path =", path)
			print ("data =", self.data)
			
		# Selon le chemin, faire
		if path == '/update':
			return self.update(cip)
		elif path == '/log':
			return self.log()
		else:
			return Response("Chemin invalide")
	

	def update(self, nip):
		
		"""Mise à jour de l'adresse IP si elle à changé.
			self.data = Les paramètres de la requête
		"""
		
		# Extraction des paramètres
		bkend = None
		host = None
		login = None
		pwd = None
		email = None
		secid = None
		for par in self.data.copy().items():
			if self.prm['debug']:
				print("par =", par)
			p = par[0]
			if p == 'backend':
				bkend = par[1]
			elif p == 'host':
				host = par[1]
			elif p == 'login':
				login = par[1]
			elif p == 'pass':
				pwd = par[1]
			elif p == 'email':
				email = par[1]
			elif p == 'secid':
				secid = par[1]
			else:
				return Response("Paramètre '" + p + "' invalide.")
		if bkend == None:
			return Response("Paramètre 'backend' manquant.")
		if bkend not in bkends.keys():
			return Response("Backend {0} non reconnu.".
					format(bkend))
		if host == None:
			return Response("Paramètre 'host' manquant.")
		if login == None:
			return Response("Paramètre 'login' manquant.")
		if pwd == None:
			return Response("Paramètre 'pass' manquant.")
		if secid == None:
			return Response("Paramètre 'secid' manquant.")
		
		# Ouvrir BD
		try:
			conn = sqlite3.connect(self.prm['db_name'])
			cursor = conn.cursor()
		except Exception as e:
			return Response("Erreur connexion BD.")

		# Recherche de la dernière adresse IP
		cursor.execute('select id, last_ip, sec_id from hosts where host = ?', (host, ))
		res = cursor.fetchone()
		if res == None:
			# Ajout d'un nouveau hôte
			cursor.execute('insert into hosts(host, sec_id) values(?, ?)', 
				(host, hash_password(self.prm['master_pw'] + secid)))
			id = cursor.lastrowid
			res = (id, '0.0.0.0', hash_password(self.prm['master_pw'] + secid))
			if self.prm['debug']:
				print("Nouveau DynHost : {0} ID = {1}".format(host, res[0]))
		
		# Autoriser seulement la bonne ID de sécurité
		if not check_password(self.prm['master_pw'] + secid, res[2]):
			return Response("Clé de sécurité invalide.")
		
		# Si l'adresse IP à changé
		if nip != res[1]:
			
			if self.prm['debug']:
				print("Changement adresse IP {0} en {1} pour host {2}".
					format(res[1], nip, host))
			
			# Changer le dynhost selon le backend
			if bkend == 'ovh':
				ret = self.bk_ovh(host, nip, login, pwd)
			else:
				return Response("Impossible de traiter le backend {0}.".
					format(bkend))
			if ret != None:
				conn.rollback()
				conn.close()
				return ret
			
			# Mettre à jour la dernière adresse connue
			cursor.execute('update hosts set last_ip = ? ' +
				'where id = ?', (nip, res[0]))
			
			# L'ajouter dans la log
			cursor.execute("insert into log(host_id, new_ip) values(?, ?)", 
				(res[0], nip))
			conn.commit()
			
			if email != None:
				self.sendmail(email, host, res[1], nip)
		
		# Plus besoin de la BD
		conn.close()
		
		# Tout est ok
		return Response('OK')


	def bk_ovh(self, host, nip, login, pwd):
		
		"Dynhost OVH"
		
		params = (
			('system', 'dyndns'),
			('hostname', host),
			('myip', nip),
		)
		response = requests.get('https://www.ovh.com/nic/update', 
			params=params, auth=(login, pwd))
		if not response.ok:
			return Response("Erreur changement DynHost : " + response.reason)
		return None
		

	def log(self):
		
		"""Affichage de l'historique d'un hôte.
			self.data = Les paramètres de la requête
		"""
		
		# Extraction des paramètres
		host = None
		secid = None
		for par in self.data.copy().items():
			if self.prm['debug']:
				print("par =", par)
			p = par[0]
			if p == 'host':
				host = par[1]
			elif p == 'secid':
				secid = par[1]
			else:
				return Response("Paramètre '" + p + "' invalide.")
		if host == None:
			return Response("Paramètre 'host' manquant.")
		if secid == None:
			return Response("Paramètre 'secid' manquant.")
		
		# Ouvrir BD
		try:
			conn = sqlite3.connect(self.prm['db_name'])
			cursor = conn.cursor()
		except Exception as e:
			return Response("Erreur connexion BD.")

		# Recherche de l'hôte
		cursor.execute('select id, last_ip, sec_id from hosts where host = ?', (host, ))
		res = cursor.fetchone()
		if res == None:
			return Response("Hôte {0} non connu dans la log.".format(host))
	
		# Autoriser seulement la bonne ID de sécurité
		if not check_password(self.prm['master_pw'] + secid, res[2]):
			return Response("Clé de sécurité invalide.")
		
		# Entête html
		html = self.prm['tpl_log_header'].format(host=host, ip=res[1])

		# Recherche de la dernière adresse IP
		cursor.execute('select mod_date, new_ip from log ' +
			'where host_id = ? order by mod_date desc', (res[0], ))
		for row in cursor:
			
			# Liste des entrées
			html += self.prm['tpl_log_line'].format(date=row[0], ip=row[1])
		
		# Plus besoin de la BD
		conn.close()

		# Fin html
		html += self.prm['tpl_log_foot']
		
		# Tout est ok
		return Response(html, mimetype='text/html')
	

	def sendmail(self, mailto, host, old_ip, new_ip):
		
		"Envoi d'un email en cas de changement d'IP"
		
		# Pas d'envoi si expéditeur non renseigné
		if self.prm['eml_sender'] == None:
			if self.prm['debug']:
				print("Pas d'envoi de mail.")
			return
		
		msg = EmailMessage()
		msg['From'] = self.prm['eml_sender']
		msg['To'] = mailto
		msg['Subject'] = "Changement d'adresse IP pour {0}".format(host)
		html = self.prm['tpl_msg_chg_ip'].format(host=host, old=old_ip, new=new_ip)
		
		msg.set_content(html2text.html2text(html))
		msg.add_alternative(html, subtype='html')
		
		with smtplib.SMTP('localhost') as s:
			s.send_message(msg)
		

class MyFormatter(argparse.ArgumentDefaultsHelpFormatter,
		argparse.RawTextHelpFormatter):
	pass
def get_prm():
	
	"Lecture des paramètres de la ligne de commandee."
	
	# Valeurs par défaut -----------------------------------------------------
	prm = {
		'debug': False,
		'port': dft_port,
		'itf': dft_itf,
		'db_name': db_name,
		'master_pw': master_pw,
		'eml_sender': None,
		'lst_bkends': None,
		'get_secid': None,
		'tpl_msg_chg_ip': tpl_msg_chg_ip,
		'tpl_log_header': tpl_log_header,
		'tpl_log_line': tpl_log_line,
		'tpl_log_foot': tpl_log_foot,
	}
	
	# Définition des arguments de la ligne de commande -----------------------
	parser = argparse.ArgumentParser(
		formatter_class=MyFormatter,
		argument_default=argparse.SUPPRESS,
		description=textwrap.dedent("""\
			Lance le web-service de gestion d'hôtes dynamiques.
			
			Ce service permet à des hôtes ayant une adresse IP dynamique
			(qui change), de mettre celle-ci à jour dans un service du genre
			DynDns.
			Les changements d'adresses sont stockés dans une base de donnée
			dans un but d'analyse.
			Un mail peut être envoyé en cas de changement d'adresse.
			"""))

	parser.add_argument("-V", "--version", action='version', 
		version='%(prog)s ' + __version__)

	parser.add_argument("-p", "--port", type=int,
		help="N° du port pour accéder au web-service.\n"
			"(Défaut: {0})".format(dft_port))

	parser.add_argument("-i", "--itf",
		help="Interface sur laquelle le service est actif.\n"
			"'0.0.0.0' pour toutes les interfaces.\n"
			"(Défaut: {0})".format(dft_itf))

	parser.add_argument("--db_name",
		help="Nom de la base de données Sqlite3.\n"
			"Doit être le nom d'un fichier avec son chemin d'accès.\n"
			"(Défaut: {0})".format(db_name))

	parser.add_argument("--eml_sender",
		help="Adresse mail de l'expéditeur.\n"
			"Si pas renseigné, pas d'envoi de mails.")

	parser.add_argument("-L", "--lst_bkends",
		action="store_true",
		help="Affiche la liste des backends supportés.")

	parser.add_argument("-c", "--config",
		type=argparse.FileType('r'),
		help="Fichier de configuration.\n"
			"Contient les paramètres précédent et d'autres valeurs.\n"
			"Voir dynahost_config_sample.ini pour un exemple.")

	parser.add_argument("--get_secid",
		help="Renvoie un secid crypté.\n"
			"Utile pour mettre à jour une base de donnée non cryptée")

	parser.add_argument("--debug",
		action="store_true",
		help="Affiche plein de trucs.")

	args = parser.parse_args()
	del parser
	
	# Lecture du fichier de configuration ------------------------------------
	try:
		if args.config != None:
			cfg = configparser.ConfigParser()
			cfg.read_file(args.config)
	except:
		pass

	# Prendre les paramètres selon la  priorité ------------------------------
	# 1 Ligne de commande
	# 2 Fichier de config
	# 3 Valeur par défaut (en dur dans le script)
	
	# debug
	try:
		prm['debug'] = args.debug
	except:
		try:
			prm['debug'] = cfg.getboolean('general', 'debug')
		except:
			pass

	# Port
	try:
		prm['port'] = args.port
	except:
		try:
			prm['port'] = cfg.getint('server', 'port')
		except:
			pass

	# Interface
	try:
		prm['itf'] = args.itf
	except:
		try:
			prm['itf'] = cfg.get('server', 'itf')
		except:
			pass

	# Base de donnée
	try:
		prm['db_name'] = args.db_name
	except:
		try:
			prm['db_name'] = cfg.get('general', 'db_name')
		except:
			pass

	# Mot de passe maitre
	try:
		prm['master_pw'] = cfg.get('general', 'master_pw')
	except:
		pass

	# Email de l'expéditeur
	try:
		prm['eml_sender'] = args.eml_sender
	except:
		try:
			prm['eml_sender'] = cfg.get('general', 'eml_sender')
		except:
			pass

	# Liste des backends
	try:
		prm['lst_bkends'] = args.lst_bkends
	except:
		pass

	# Cryptage d'une clé de sécurité
	try:
		prm['get_secid'] = args.get_secid
	except:
		pass

	# Templates 
	try:
		prm['tpl_msg_chg_ip'] = cfg.get('msg', 'tpl_msg_chg_ip')
	except:
		pass
	try:
		prm['tpl_log_header'] = cfg.get('log', 'tpl_log_header')
	except:
		pass
	try:
		prm['tpl_log_line'] = cfg.get('log', 'tpl_log_line')
	except:
		pass
	try:
		prm['tpl_log_foot'] = cfg.get('log', 'tpl_log_foot')
	except:
		pass
	
	if prm['debug']:
		print("debug actif: Dump des paramètres ---------------------")
		print("Options :")
		for k in prm.keys():
			if k[:4] != 'tpl_':
				print("\t{0} =".format(k), prm[k])
			
	return prm


def main():
	
	"Pilotage du programme"
	
	# Lecture des paramètres
	prm = get_prm()
	
	# Liste des backends
	if prm['lst_bkends']:
		lst_backends()
		return
	
	# Cryptage d'une clé de sécurité
	if prm['get_secid']:
		hh =  hash_password(prm['master_pw'] + prm['get_secid'])
		print("l'id '{0}' est crypté en '{1}'".format(prm['get_secid'], hh))
		return

	# Création base donné si pas déjà fait
	create_db(prm)
	
	# Lancer le web-service
	webs = Websrv(prm)
	if prm['debug']:
		print ("Fin du web-service")

if __name__ == '__main__':
	main()
