#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, request, make_response, Response, jsonify
import json
import time
import thread
from multiprocessing import Process,Queue,Pipe
# from s1bot import createChildConnection
from s1bot import slackLaunchS1APITokenDialog, sentinelShutdownAgent, sentinelRestartAgent, sentinelDisconnectAgentFromNetwork,sentinelReconnectAgentToNetwork, sentinelTest
from s1bot import update_invalid_token, updateSlackMessage, slackS1SendMessage, slackGetRealNameFromID, updateJSONCredentials
from s1bot import sentinelRegenerateAPIToken, sentinelUninstallAgent
from jirabot import jiraLoginDialog, jiraAttemptLogin, jiraPhishingMain, jiraSlackSendMessage, JiraSendNext, get_current_comment_URLs
from jirabot import JiraAssignCommentAndResolveTicket, launchCustomCommentDialog, put_JSON_key, update_JSON_keys, jiraUpdateSlackMessage
from jirabot import delete_current_comment_URLs, JiraResend
from mimecastapi import mimecast_create_managed_URL

app = Flask('SlackReceiver')





@app.route('/slack/s1', methods=['POST'])
def incoming_s1_slack_action():
	#data = request.get_data()
	slack_payload = json.loads(request.form.get("payload"))
	#print json.dumps(slack_payload, indent=4, sort_keys=True)

	if slack_payload["callback_id"] == "confirmTestButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'true':
			if sentinelTest(slackID):
				return 'You clicked yes!'
			else:
				return 'got button but failed s1 call'
		elif action_value== 'false':
			return 'Cancelled action!'
		return 'Invalid response...'

	if slack_payload["callback_id"] == "confirmShutdownButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			if sentinelShutdownAgent(slackID, action_value):
				return 'Shutdown ' + action_value
			else:
				return 'Failed to Shutdown: ' + action_value

	if slack_payload["callback_id"] == "confirmRestartButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			if sentinelRestartAgent(slackID, action_value):
				return 'Restarted: ' + action_value
			else:
				return 'Failed to Restart: ' + action_value

	if slack_payload["callback_id"] == "confirmUninstallButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			if sentinelUninstallAgent(slackID, action_value):
				return 'Uninstalled: ' + action_value
			else:
				return 'Failed to Uninstall: ' + action_value

	if slack_payload["callback_id"] == "confirmDisconnectButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			if sentinelDisconnectAgentFromNetwork(slackID, action_value):
				return 'Disconnected ' + action_value
			else:
				return 'Failed to Disconnect: ' + action_value

	if slack_payload["callback_id"] == "confirmReconnectButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			if sentinelReconnectAgentToNetwork(slackID, action_value):
				return 'Reconnected ' + action_value
			else:
				return 'Failed to Reconnect: ' + action_value

	if slack_payload["callback_id"] == "buttonDialogNewS1APIToken":
		action_value = slack_payload["actions"][0].get("value")
		trigger_id = slack_payload.get("trigger_id")
		#channel = slack_payload["channel"].get("id")
		#ts = slack_payload.get("message_ts")
		if action_value == 'false':
			return 'Cancelled action!'
		else:
			slackLaunchS1APITokenDialog(trigger_id)
			return 'Alright, lets update that token...'
			#return make_response("", 200)

	if slack_payload["callback_id"] == "s1apidialog":
		action_value = slack_payload["submission"].get("apitoken")
		slackID = slack_payload["user"].get("id")
		channel = slack_payload["channel"].get("id")
		ts = slack_payload.get("message_ts")
		if update_invalid_token(slackID, action_value):
			#return "Successfully updated token"
			slackS1SendMessage(channel, "We successfully updated your token!\nTry some commands!")
			time.sleep(.100)
			return make_response('', 200)

		#return "You gave me a bad token"
		#return make_response('', 200)
		#updateSlackMessage(channel, ts, "You gave me a bad token, try again")
		slackS1SendMessage(channel, "You gave me an invalid token.. Please try again")

	if slack_payload["callback_id"] == "test_menuu":
		action_value = slack_payload["actions"][0]['selected_options'][0].get("value")
		slackID = slack_payload["user"].get("id")
		slackUserName = slackGetRealNameFromID(slackID)
		#return json.dumps(slack_payload,sort_keys=True, indent=4)
		return slackUserName + ' clicked ' + action_value

	if slack_payload["callback_id"] == "confirmAPIRegenerateButtonID":
		action_value = slack_payload["actions"][0].get("value")
		slackID = slack_payload["user"].get("id")
		if action_value == 'confirm':
			token = sentinelRegenerateAPIToken(slackID)
			if token == False:
				return 'unable to update your token...'
			else:
				updateJSONCredentials(slackID, token)
				return 'updated your token!'
		elif action_value== 'false':
			return 'Cancelled action!'



	#data = request.get_data()
	#print data
	return 'I have no Idea what you did to me\nYou should probably get Luke to fix this'


@app.route('/slack/jira/actions', methods=['POST'])
def incoming_jira_slack_action():
	#data = request.get_data()
	slack_payload = json.loads(request.form.get("payload"))
	#print json.dumps(slack_payload, indent=4, sort_keys=True)

	if slack_payload["callback_id"] == "initiateJira":
		action_value = slack_payload["actions"][0].get("value")
		trigger_id = slack_payload.get("trigger_id")
		slackID = slack_payload["user"].get("id")
		data = action_value.split("|")
		if data[0] == 'confirm':
			jiraLoginDialog(trigger_id, data[1])
			return 'Okay - Let\'s login!'
		elif data[0]== 'false':
			return 'Cancelled action!'

	if slack_payload["callback_id"] == "jiraLoginDialog":
		uname = slack_payload["submission"].get("username")
		pword = slack_payload["submission"].get("password")
		channel = slack_payload["channel"].get("id")
		jira, pwd = jiraAttemptLogin(uname, pword)
		if jira == False or pwd == False:
			return 'you probably need to go to https://jira.company.com/login.jsp to fix your capatcha.'
		else:
			jiraSlackSendMessage(channel, "Were working on your request...")
			thread.start_new_thread(jiraPhishingMain, (channel, jira, uname, pwd))
			return make_response('', 200)

	if slack_payload["callback_id"] == "jiraLoginDialogUpdate":
		uname = slack_payload["submission"].get("username")
		pword = slack_payload["submission"].get("password")
		channel = slack_payload["channel"].get("id")
		jira, pwd = jiraAttemptLogin(uname, pword)
		if jira == False or pwd == False:
			return 'you probably need to go to https://jira.company.com/login.jsp to fix your capatcha.'
		else:
			jiraSlackSendMessage(channel, "Were working on your request...")
			thread.start_new_thread(update_JSON_keys, (uname, pword, channel))
			return make_response('', 200)

	if slack_payload["callback_id"] == "phishingTicketResolution":
		action_value = slack_payload["actions"][0].get("value")
		channel = slack_payload["channel"].get("id")
		trigger_id = slack_payload.get("trigger_id")
		slackID = slack_payload["user"].get("id")
		ts = None
		#key = slack_payload["fields"].get("key")
		#JiraUserName = slack_payload["fields"].get("currentUser")
		data = action_value.split("|")
		key = data[1]
		JiraUserName = data[2]
		JiraPassword = data[3]
		if action_value.startswith('blocked'):
			comment = ('Thank you reporting this. Our security systems identified the link or attachment as malicious and '
				'has blocked it. Please go ahead and delete the email.\n\nThank you for helping keep Company secure.')
			thread.start_new_thread(JiraAssignCommentAndResolveTicket, (key, JiraUserName, comment, channel, JiraPassword))
			return ':heavy_check_mark:*Assigned* ~' + key + '~ to ' + JiraUserName + '\n*Comment:* ' + comment + '\n*Marked as resolved.*\n_Getting next ticket..._'
		elif action_value.startswith('threat'):
			comment = ('This email is an attempt to shock the receiver into paying a fee with no substance. The sender does '
				'not have any incriminating evidence or anything of the sort, but has simply emailed you in the hope that you '
				'will pay the "ransom". DO NOT pay this fee and disregard the email. DO NOT contact the sender in any way and '
				'please report any further emails that follow this pattern.\n\nThank you for helping make Company a bit more '
				'secure by reporting this email.')
			thread.start_new_thread(JiraAssignCommentAndResolveTicket, (key, JiraUserName, comment, channel, JiraPassword))
			return ':heavy_check_mark:*Assigned* ~' + key + '~ to ' + JiraUserName + '\n*Comment:* ' + comment + '\n*Marked as resolved.*\n_Getting next ticket..._'
		elif action_value.startswith('spam'):
			comment = ('The email you reported does not appear to have any malicious links or attachments.  This may either be '
				'spam or junk email. Due to this there is limited activities that we could do for these but you can block the '
				'sender on your end if you like. Open up the email and in the upper left click "Junk" then click on "Block Sender".'
				'\n\nThank you for helping keep Company secure.')
			thread.start_new_thread(JiraAssignCommentAndResolveTicket, (key, JiraUserName, comment, channel, JiraPassword))
			return ':heavy_check_mark:*Assigned* ~' + key + '~ to ' + JiraUserName + '\n*Comment:* ' + comment + '\n*Marked as resolved.*\n_Getting next ticket..._'
		elif action_value.startswith('donotreply'):
			comment = ('This is a simple phishing attempt to extort personal data or wealth.  Do not reply to the email or give any information.  You can block the '
				'sender on your end if you like. Open up the email and in the upper left click "Junk" then click on "Block Sender".'
				'\n\nThank you for helping keep Company secure.')
			thread.start_new_thread(JiraAssignCommentAndResolveTicket, (key, JiraUserName, comment, channel, JiraPassword))
			return ':heavy_check_mark:*Assigned* ~' + key + '~ to ' + JiraUserName + '\n*Comment:* ' + comment + '\n*Marked as resolved.*\n_Getting next ticket..._'
		elif action_value.startswith('custom'):
			launchCustomCommentDialog(key, JiraUserName, trigger_id, JiraPassword)
			#thread.start_new_thread(, ())
			return 'Okay - let\'s put in a custom comment - the ticket will still be assigned and resolved.'
		elif action_value.startswith('cancel'):
			thread.start_new_thread(put_JSON_key, (key,))
			thread.start_new_thread(JiraSendNext, (channel, JiraUserName, JiraPassword))
			return ':x:No action taken for ' + key + '\n_Getting next ticket..._'
		elif action_value.startswith('close'):
			thread.start_new_thread(put_JSON_key, (key,))
			return 'Thanks for playing!'
		elif action_value.startswith('reload'):
			thread.start_new_thread(JiraResend, (channel, JiraUserName, JiraPassword, key))
			return '_Reloading ticket..._'

	if slack_payload["callback_id"].startswith("customCommentDialog"):
		comment = slack_payload["submission"].get("comment")
		channel = slack_payload["channel"].get("id")
		data = slack_payload["callback_id"].split("|")
		ts = None
		key = data[1]
		JiraUserName = data[2]
		JiraPassword = data[3]
		#jiraSlackSendMessage(channel, comment)
		#jiraSlackSendMessage(channel, "Were working on your request...")
		thread.start_new_thread(JiraAssignCommentAndResolveTicket, (key, JiraUserName, comment, channel, JiraPassword))
		#TODO set ts
		#thread.start_new_thread(jiraUpdateSlackMessage(channel, ts, ':heavy_check_mark:*Assigned* ~' + key + '~ to ' + JiraUserName + '\n*Comment:* ' + comment + '\n*Marked as resolved.*\n_Getting next ticket..._'))
		return make_response('', 200)

	if slack_payload["callback_id"].startswith("mimeCastBlock"):
		data = slack_payload["callback_id"].split("|")
		key = data[1]
		value = slack_payload["actions"][0]["selected_options"][0].get("value")
		value = value.replace("&amp;", "&")
		value = value.replace("&lt;", "<")
		value = value.replace("&gt;", ">")
		#print 'block: ' + value#This is where we will make our mimecast call to block the url
		mimecast_create_managed_URL(value)
		delete_current_comment_URLs(key, value)
		return make_response('', 200)


@app.route('/slack/jira/mimecast', methods=['POST'])
def incoming_jira_slack_menu_request():
	slack_payload = json.loads(request.form.get("payload"))
	#print json.dumps(slack_payload, indent=4, sort_keys=True)
	data = slack_payload["callback_id"].split("|")
	key = data[1]
	current_comment_URLs = get_current_comment_URLs(key)
	#current_comment_URLs = ["example1.com","example2.com","example3.com"]

	options = []
	builder_dict = {}
	optionsFinal = dict()

	if current_comment_URLs is not None:
		for url in current_comment_URLs:
			builder_dict = {}
			builder_dict["text"] = url
			builder_dict["value"] = url
			options.append(builder_dict)

		optionsFinal["options"] = options


		return make_response(jsonify(optionsFinal) ,200)
	else:
		optionsFinal["options"] = options
		return make_response(jsonify(optionsFinal),200)


@app.route('/slack/jira/mimecast', methods=['GET'])
def incoming_jira_slack_menu_request_answer():
	slack_payload = json.loads(request.form.get("payload"))
	#print json.dumps(slack_payload, indent=4, sort_keys=True)
	if slack_payload["callback_id"].startswith("mimeCastBlock"):
		#urlToBlock = slack_payload.get("value")
		#print 'block: ' + urlToBlock
		#thread.start_new_thread( , ())
		return make_response('', 200)








	return 'I have no Idea what you did to me\nYou should probably get Luke to fix this'





#useful
#return json.dumps(slack_payload,sort_keys=True, indent=4)



















if __name__ == '__main__':


	app.run('0.0.0.0', 443,ssl_context = ('/certs/server.crt', '/certs/server.key'), debug=True)


