import tornado.wsgi
import tornado.web
import tornado.websocket
import os
import sae
import json
import uuid
import datetime
import logging
import random
import re
import threading
import time

import pylibmc as memcache
from sae import channel

mc = memcache.Client()

def getData(key):
	data = mc.get(key)
	if not data:
		if key == 'UserData':
			mc.set(key,[])
		else:
			mc.set(key,{})
	return data

def setData(key,data):
	mc.set(key,data)
	return

def findUser(u_id):
	data = mc.get('UserData')
	for (j,t) in enumerate(data):
		if t['u_id'] == u_id:
			return j
	return -1

def sendData(u_id,data):
	channel.send_message(u_id, json.dumps(data))
	return

# request handle
class MainHandler(tornado.web.RequestHandler):

	def get(self):
		user = self.get_secure_cookie('u')
		if not user:
			self.set_secure_cookie('u', user)
		u_id = uuid.uuid4().hex
		url = channel.create_channel(u_id)
		team = Tank().joinTeam(u_id)
		template_values = {'url': url,
							'me': u_id,
							'team':team,
						}
		path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
		self.render(path, **template_values)

class Connected(tornado.web.RequestHandler):

	def post(self):
		return

class Disconnected(tornado.web.RequestHandler):

	def post(self):
		arg = self.request.arguments
		if 'from' in arg:
			u_id = arg['from'][0]
		data = getData('UserData')
		for (j,t) in  enumerate(data):
			if t['u_id'] == u_id:
				data.pop(j)
		setData('UserData',data)

class Message(tornado.web.RequestHandler):

	def post(self):
		#user = self.get_secure_cookie('u')
		#channel.send_message(user,self.request)
		arg = self.request.arguments
		#print arg
		if 'from' in arg:
			u_id = arg['from'][0]
		if 'message' in arg:
			msg = eval(arg['message'][0])
			if 't' in msg:
				if msg['t'] == 'TankPosition':
					Tank().updatePosition(msg,u_id)
				elif msg['t'] == 'AddBullet':
					Bullets().updateBullet(msg,u_id)
		return

class Tank():

	def updatePosition(self,msg,u_id):
		#channel.send_message(user, json.dumps(position))
		t = {}
		if 'x' in msg:
			t['x'] = msg['x']
		if 'y' in msg:
			t['y'] = msg['y']
		if 'd' in msg:
			t['d'] = msg['d']
		if 'c' in msg:
			t['c'] = msg['c']

		data = getData('UserData')
		j = findUser(u_id)
		if j >= 0:
			data[j]['tanks'] = t
			data[j]['bullets'] = msg['b']
		else:
			data.append({'u_id':u_id,'bullets':msg['b'],'tanks':t})
		setData('UserData',data)
		sendData(u_id,data)
		#channel.send_message(user, json.dumps(data))

	def joinTeam(self,u_id):
		team1 = getData('Team1')
		team2 = getData('Team2')
		if 'users' not in team1:
			team1['users'] = []
		t1 = len(team1['users'])
		if 'users' not in team2:
			team2['users'] = []
		t2 = len(team2['users'])
		if t1 > t2:
			t = '2'
		elif t1 < t2:
			t = '1'
		else:
			t = str(random.randint(1,2))
		if t == '1':
			team1['users'].append(u_id)
			setData('Team1',team1)
			return '1'
		else:
			team2['users'].append(u_id)
			setData('Team2',team2)
			return '2'

class Bullets():

	def updateBullet(self,msg,u_id):
		#t = {}
		#data = getUserData()
		#data['bullets'].append({'x':msg['x'],'y':msg['y'],'vx':msg['vx'],'vy':msg['vy'],'color':'1'})
		#setUserData(data)
		#sendData(u_id,data)
		return

# static files settings
settings = {
	"static_path": os.path.join(os.path.dirname(__file__), "static"),
}
# url settings
app = tornado.wsgi.WSGIApplication([
	#('/TankPosition', TankPosition),
	("/", MainHandler),
	#('/Check',Check),
	('/_sae/channel/connected',Connected),
	('/_sae/channel/disconnected',Disconnected),
	('/_sae/channel/message',Message),
], debug=True, cookie_secret='0xcafebabe')

application = sae.create_wsgi_app(app)
