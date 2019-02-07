#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
dynahost : Administration d'hôtes ayant une adresse IP dynamique
================================================================
"""

import os
import hashlib
import argparse, textwrap
from __init__ import __version__
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple
import sqlite3
import requests
import smtplib
import html2text

# Pour sendemail
from email.message import EmailMessage

# Config =====================================================================

# Port par défaut
dft_port = 4000

# Interface réseau par défaut
dft_if = '0.0.0.0'

# Nom de la base de données
db_name = "dynahost.db"

# Email : expéditeur
eml_sender = 'dynhost@frkb.fr'

# Création de la base de données =============================================
def create_db():
	
	"""crée la base de données et retourne une connexion vers elle."""
	
	try:
		conn = sqlite3.connect(db_name)
		cursor = conn.cursor()
		cursor.execute("CREATE TABLE hosts(" +
			"id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, " +
			"host TEXT, " +
			"last_ip TEXT)")
		cursor.execute("CREATE INDEX hosts_host ON hosts (host)")
		cursor.execute("CREATE TABLE log(" +
			"id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, " +
			"host_id INTEGER, " +
			"mod_date DATETIME DEFAULT (datetime('now', 'localtime') ), "
			"new_ip TEXT)")
		cursor.execute("CREATE INDEX log_host ON log (host_id, mod_date)")
		conn.commit()
		
	except sqlite3.OperationalError:
		print("db existe.")
		pass
	except Exception as e:
		print("Erreur")
		conn.rollback()
		raise e
	finally:
		conn.close()

# Web service ================================================================
class Websrv(object):

	def __init__(self, args):

		"Lancement du Web-service"

		self.args = args
		run_simple(args.itf, args.port, self.service, use_debugger=args.debug, 
			use_reloader=args.debug)


	@Request.application
	def service(self, request):

		"Traitement des demandes"
		
		# Lecture de l'adresse IP du client
		try:
			self.cip = request.remote_addr
			self.cip = request.environ['REMOTE_ADDR']
			self.cip = request.environ['HTTP_X_REAL_IP']
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
		if self.args.debug:
			print ("IP =", self.cip)
			print ("path =", path)
			print ("data =", self.data)
			
		# Selon le chemin, faire
		if path == '/update':
			return self.update()
		elif path == '/log':
			return self.log()
		else:
			return Response("Chemin invalide")
	
	def update(self):
		
		"""Mise à jour de l'adresse IP si elle à changé.
			self.cip = Adresse IP du client
			self.data = Les paramètres de la requête
		"""
		
		# Extraction des paramètres
		host = None
		login = None
		pwd = None
		email = None
		for prm in self.data.copy().items():
			if self.args.debug:
				print("prm =", prm)
			p = prm[0]
			if p == 'host':
				host = prm[1]
			elif p == 'login':
				login = prm[1]
			elif p == 'pass':
				pwd = prm[1]
			elif p == 'email':
				email = prm[1]
			else:
				return Response("Paramètre '" + p + "' invalide.")
		if host == None:
			return Response("Paramètre 'host' manquant.")
		if login == None:
			return Response("Paramètre 'login' manquant.")
		if pwd == None:
			return Response("Paramètre 'pass' manquant.")
		
		# Ouvrir BD
		try:
			conn = sqlite3.connect(db_name)
			cursor = conn.cursor()
		except Exception as e:
			return Response("Erreur connexion BD.")

		# Recherche de la dernière adresse IP
		cursor.execute('select id, last_ip from hosts where host = ?', (host, ))
		res = cursor.fetchone()
		if res == None:
			cursor.execute('insert into hosts(host) values(?)', 
				(host, ))
			id = cursor.lastrowid
			conn.commit()
			res = (id, '0.0.0.0')
			if self.args.debug:
				print("Nouveau DynHost :", host, "ID =", res[0])
		
		# Si l'adresse IP à changé
		if self.cip != res[1]:
			
			if self.args.debug:
				print("Changement adresse IP {0} en {1} pour host {2}".
					format(res[1], self.cip, host))
			
			# Changer le dynhost
			params = (
				('system', 'dyndns'),
				('hostname', host),
				('myip', self.cip),
			)
			"""response = requests.get('https://www.ovh.com/nic/update', 
				params=params, auth=(login, pwd))
			if not response.ok:
				conn.close()
				return Response("Erreur changement DynHost : " + response.reason)"""
			
			# Mettre à jour la dernière adresse connue
			cursor.execute('update hosts set last_ip = ? ' +
				'where id = ?', (self.cip, res[0]))
			conn.commit()
			
			# L'ajouter dans la log
			cursor.execute("insert into log(host_id, new_ip) values(?, ?)", 
				(res[0], self.cip))
			conn.commit()
			
			if email != None:
				self.sendmail(email, host, res[1], self.cip)
		
		# Plus besoin de la BD
		conn.close()
		
		# Tout est ok
		return Response('OK')
	
	def log(self):
		
		"""Affichage de l'historique d'un hôte.
			self.cip = Adresse IP du client
			self.data = Les paramètres de la requête
		"""
		
		# Extraction des paramètres
		host = None
		for prm in self.data.copy().items():
			if self.args.debug:
				print("prm =", prm)
			p = prm[0]
			if p == 'host':
				host = prm[1]
			else:
				return Response("Paramètre '" + p + "' invalide.")
		if host == None:
			return Response("Paramètre 'host' manquant.")
		
		# Ouvrir BD
		try:
			conn = sqlite3.connect(db_name)
			cursor = conn.cursor()
		except Exception as e:
			return Response("Erreur connexion BD.")

		# Recherche de l'hôte
		cursor.execute('select id, last_ip from hosts where host = ?', (host, ))
		res = cursor.fetchone()
		if res == None:
			return Response("Hôte {0} non connu dans la log.".format(host))
	
		# Entête html
		html = """\
<!DOCTYPE html>
<html>
	<head>
		<style>
			table, th, td {ao}
				border: 1px solid black;
			{ac}
		</style>
	</head>
	<body>
		<p>Log de l'hôte <b>{hote}</b> : (<b>{ip}</b>)</p>
		<table>
			<tr>
				<th>Date/heure</th>
				<th>Adresse IP</th>
			</tr>
""".format(ao='{', ac='}', hote=host, ip=res[1])

		# Recherche de la dernière adresse IP
		cursor.execute('select mod_date, new_ip from log ' +
			'where host_id = ? order by mod_date desc', (res[0], ))
		for row in cursor:
			
			# Liste des entrées
			html += """\
			<tr>
				<td>{date}</td>
				<td>{ip}</td>
			</tr>
""".format(date=row[0], ip=row[1])
		
		# Plus besoin de la BD
		conn.close()

		# Fin html
		html += """\
		</table>
	</body>
</html>
"""
		
		# Tout est ok
		return Response(html, mimetype='text/html')
	
	def sendmail(self, mailto, host, old_ip, new_ip):
		
		"Envoi d'un email en cas de changement d'IP"
		
		msg = EmailMessage()
		msg['From'] = eml_sender
		msg['To'] = mailto
		msg['Subject'] = "Changement d'adresse IP pour {0}".format(host)
		html = """\
		<html>
		  <head></head>
		  <body>
			<p>Bonjour,<br>
				<br>
				L'adresse IP de l'hôte "{host} à changé.<br>
				Elle est passée de {old} à {new}.<br>
				<br>
				Cordialement,<br>
				Dynhost service.
			</p>
		  </body>
		</html>
		""".format(host=host, old=old_ip, new=new_ip)
		
		msg.set_content(html2text.html2text(html))
		msg.add_alternative(html, subtype='html')
		
		with smtplib.SMTP('localhost') as s:
			s.send_message(msg)
		

# Read command line arguments ================================================

class MyFormatter(argparse.ArgumentDefaultsHelpFormatter,
		argparse.RawTextHelpFormatter):
	pass

def get_args():
	
	parser = argparse.ArgumentParser(
		formatter_class=MyFormatter,
		description=textwrap.dedent("""\
			Lance le web-service de gestion d'hôtes dynamiques.
			
			Ce service est utile quand on a un fournisseur d'accès qui ne 
			fournit pas d'adresse IP fixe.
			"""))

	parser.add_argument("-V", "--version", action='version', version='%(prog)s ' + __version__)

	parser.add_argument("-p", "--port", type=int,
		default = dft_port,
		help="N° du port pour accéder au web-service.")

	parser.add_argument("-i", "--itf",
		default = dft_if,
		help="Interface sur laquelle le service est actif.\n"
			"'0.0.0.0' pour toutes les interfaces.")

	parser.add_argument("--debug",
		action="store_true",
		help="Interface sur laquelle le service est actif.\n"
			"'0.0.0.0' pour toutes les interfaces.")

	args = parser.parse_args()

	del parser

	if args.debug:
		print("debug actif: Dump des paramètres ---------------------")
		print("Options :")
		keys = vars(args).keys()
		for k in keys:
			print("\t%s =" % k, eval('args.' + k))
			
	return args

# Lancement du programme =====================================================
def main():
	
	# Création base donné si pas déjà fait
	create_db()

	# Read cmd line arguments
	args = get_args()

	# Lancer le web-service
	webs = Websrv(args)
	print ("Fin du web-service")

if __name__ == '__main__':
	main()
