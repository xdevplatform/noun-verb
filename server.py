import base64
import hashlib
import os
import re
import json
import requests
import dbm
import ast

from flask_apscheduler import APScheduler
from requests.auth import AuthBase, HTTPBasicAuth
from requests_oauthlib import OAuth2Session, TokenUpdated
from flask import Flask, request, redirect, session, url_for, render_template


app = Flask(__name__)
app.secret_key = os.urandom(50)
scheduler = APScheduler()

client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.twitter.com/2/oauth2/token"
redirect_uri = os.environ.get("REDIRECT_URI")

scopes = ["tweet.read", "users.read", "tweet.write", "offline.access"]

code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")



def make_token():
    return OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)


# Change logic for your bot
def parse_noun_verb():
    noun_url = "https://random-words-api.vercel.app/word/noun"
    verb_url = "https://random-words-api.vercel.app/word/verb"
    noun_response = requests.request("GET", noun_url).json()
    verb_response = requests.request("GET", verb_url).json()
    noun = noun_response[0]["word"]
    verb = verb_response[0]["word"]
    return "{}/{}".format(noun, verb)


def post_tweet(payload, token):
    print("Tweeting!")
    return requests.request(
        "POST",
        "https://api.twitter.com/2/tweets",
        json=payload,
        headers={
            "Authorization": "Bearer {}".format(token["access_token"]),
            "Content-Type": "application/json",
        },
    )


def every_other():
    db = dbm.open(".my_store", "c")
    t = db["token"]
    bb_t = t.decode("utf8").replace("'", '"')
    data = ast.literal_eval(bb_t)
    refreshed_token = twitter.refresh_token(
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
        refresh_token=data["refresh_token"],
    )
    st_refreshed_token = '"{}"'.format(refreshed_token)
    j_refreshed_token = json.loads(st_refreshed_token)
    db["token"] = j_refreshed_token
    noun_verb = parse_noun_verb()
    payload = {"text": "{}".format(noun_verb)}
    post_tweet(payload, refreshed_token)

    
@app.route("/")
def hello():
    return render_template("index.html")


@app.route("/start")
def demo():
    global twitter
    twitter = make_token()
    authorization_url, state = twitter.authorization_url(
        auth_url, code_challenge=code_challenge, code_challenge_method="S256"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/oauth/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    token = twitter.fetch_token(
        token_url=token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )
    st_token = '"{}"'.format(token)
    j_token = json.loads(st_token)
    with dbm.open(".my_store", "c") as db:
        db["token"] = j_token
    noun_verb = parse_noun_verb()
    payload = {"text": "{}".format(noun_verb)}
    response = post_tweet(payload, token).json()
    posted = response["data"]["text"]
    return render_template("thank-you.html", value=posted)


if __name__ == "__main__":
    # You may want to change the timing of the bot
    scheduler.add_job(id = 'Scheduled Task', func=every_other, trigger="interval", minutes=30)
    scheduler.start()
    app.run()