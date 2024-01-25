# Flask is a library that allows you to create websites in Python
import os

import flask_login
import requests
from flask import Flask, render_template, session, redirect, request, url_for, flash
import csv
import random
# Allows you to sort a list of lists by the inner list
from operator import itemgetter
from openai import OpenAI

from flask_wtf import FlaskForm
from sqlalchemy import create_engine
from wtforms import StringField , PasswordField , SubmitField
import time
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_login import UserMixin, LoginManager, login_user
import psycopg2
# Flask syntax

app = Flask(__name__)

# this is the databse url when you run the app next time i will create a db in this folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://doadmin:AVNS_JkvcfAiuwN-gsSf6K0c@app-784b9fa7-3b44-405e-9170-d80f0dd5e72d-do-user-14798294-0.c.db.ondigitalocean.com:25060/users'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'



# This API key is totally encrypted by separating it onto two lines
OPENAI_API_KEY = 'jk-vWksWz1HhaqkBL105FIqT' + '3BlbkFJYGn5lNEfCWijvPVvY4Vk'
OPENAI_API_KEY = OPENAI_API_KEY.replace('j', 's', 1)
# print(OPENAI_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


app.config['SECRET_KEY'] = '1234'
PASSPHRASE = "talha"


@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return User.query.get(int(user_id))



class User(UserMixin , db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True , nullable=False)
    password = db.Column(db.String(100), nullable=False)
    wins = db.Column(db.Integer(), nullable=True)
    losses = db.Column(db.Integer(), nullable=True)
    draws = db.Column(db.Integer(), nullable=True)


#Registration Form
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(min=5, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=5, max=50)])
    password = PasswordField('Password' , validators=[DataRequired() , Length(min=8 ,max=50)])
    confirm_password = PasswordField ('Confirm Password' , validators=[DataRequired() , EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self , field): 
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Error username taken.')


@app.route('/register' , methods=['GET' , 'POST'])
def register(): 
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(email=form.email.data, username=form.username.data, password= form.password.data, wins=0, losses=0, draws=0)
        db.session.add(new_user)
        db.session.commit()
        flash ('Registration Successful !')
        return redirect(url_for('login'))
    return render_template('register.html' , form=form)

@app.route('/login', methods=['GET' , 'POST'])
def login(): 
    if request.method == 'POST' :
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by (username=username).first()
        if user and user.password == password :
            login_user(user)
            flash('Login Successful !' , 'success')
            return redirect (url_for('show_pair_of_items'))
        else : 
            flash('login failed , check your username and password' , 'danger')
    return render_template('login.html')


def update_elo(a, b):
    # We will assume the first parameter a is the item that wins
    # Suppose Player 1 wins: rating1 = rating1 + k*(actual – expected)
    # The expectation of Player 1 winning is given by the formula:
    # P1 = (1.0 / (1.0 + 10^((b-a) / 400)))
    # We will set k to 30 for the time being
    k = 30
    return a + k*(1 - (1 / (1 + (10**((b-a) / 400))))), b + k*(0 - (1 / (1 + (10**((a-b) / 400)))))


# Let's create a list of lists which will look like this:
# [[name, price, link, elo], [name2, price2, link2, elo2], etc...]
elo = 1400 # This is the starting elo for all items
items = []
with open('ebay_active_items.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for row in reader:
        name_price_link_elo_image = []
        name = row[0].split(',')[0]
        price = row[0].split(',')[1]
        link = row[0].split(',')[2]
        name_price_link_elo_image.append(name)
        name_price_link_elo_image.append(price)
        name_price_link_elo_image.append(link)
        name_price_link_elo_image.append(elo)

        # Generate AI images for each item
        prompt1 = name
        # Ignore the first line of the CSV file
        if prompt1 == 'name':
            continue
        directory = 'static'
        image_exists = False
        for filename in os.listdir(directory):
            if filename.endswith('.jpg'):
                with open(os.path.join(directory, filename)) as f:
                    if prompt1 in f.name:
                        image_exists = True
        if not image_exists:
            print(prompt1)
            response1 = client.images.generate(
                model="dall-e-3",
                prompt=prompt1,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url1 = response1.data[0].url
            print(image_url1)
            img_data = requests.get(image_url1).content
            with open('static/' + name + '.jpg', 'wb') as handler:
                handler.write(img_data)
            time.sleep(12)
        items.append(name_price_link_elo_image)


@app.route('/')
def show_pair_of_items():
    user = flask_login.current_user
    if user.is_anonymous:
        return redirect(url_for('register'))
    random_value_1 = random.randint(1, len(items)-1)
    random_value_2 = random.randint(1, len(items)-1)
    session['item1'] = items[random_value_1]
    session['item2'] = items[random_value_2]

    return render_template('index.html',
                           contestant1=str(items[random_value_1][0]),
                           image_url1=url_for('static', filename=items[random_value_1][0] + '.jpg'),
                           contestant2=str(items[random_value_2][0]),
                           image_url2=url_for('static', filename=items[random_value_2][0] + '.jpg'),
                           price1='£' + str(items[random_value_1][1]),
                           price2='£' + str(items[random_value_2][1])
                           )


@app.route('/1')
def item_one_wins():
    item1 = session['item1']
    item2 = session['item2']
    win_or_lose = ''
    user = flask_login.current_user
    if item1[3] > item2[3]:
        win_or_lose = 'You Win!'
        user.wins = user.wins + 1
        db.session.add(user)
        db.session.commit()
    if item1[3] < item2[3]:
        win_or_lose = 'You Lose :('
        user.losses = user.losses + 1
        db.session.add(user)
        db.session.commit()
    if item1[3] == item2[3]:
        win_or_lose = 'You Draw! (Equal value)'
        user.draws = user.draws + 1
        db.session.add(user)
        db.session.commit()

    db.session.add(user)
    db.session.commit()
    item1elo, item2elo = update_elo(item1[3], item2[3])

    for item in items:
        if item == item1:
            item[3] = item1elo
    for item in items:
        if item == item2:
            item[3] = item2elo
    for item in sorted(items, key=itemgetter(3)):
        print(item)

    flash(win_or_lose)
    return render_template('1.html')

@app.route('/2')
def item_two_wins():
    item1 = session['item1']
    item2 = session['item2']

    win_or_lose = ''
    user = flask_login.current_user
    if item2[3] > item1[3]:
        win_or_lose = 'You Win!'
        user.wins = user.wins + 1
        db.session.add(user)
        db.session.commit()
    if item2[3] < item1[3]:
        win_or_lose = 'You Lose :('
        user.losses = user.losses + 1
        db.session.add(user)
        db.session.commit()
    if item2[3] == item1[3]:
        win_or_lose = 'You Draw! (Equal value)'
        user.draws = user.draws + 1
        db.session.add(user)
        db.session.commit()

    item1elo, item2elo = update_elo(item2[3], item1[3])
    for item in items:
        if item == item1:
            item[3] = item1elo
    for item in items:
        if item == item2:
            item[3] = item2elo
    for item in sorted(items[1:], key=itemgetter(3)):
        print(item)
    flash(win_or_lose)
    return render_template('2.html')


def password_prompt(message):
    return f'''
                <form action="/admin" method='post'>
                  <label for="password">{message}:</label><br>
                  <input type="password" id="password" name="password" value=""><br>
                  <input type="submit" value="Submit">
                </form>'''


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    print(request.method)
    if request.method == 'GET':
        return password_prompt("Admin password:")
    elif request.method == 'POST':
        if request.form['password'] != PASSPHRASE:
            return password_prompt("Invalid password, try again. Admin password:")
        else:
            list_of_products_string = ''
            for item in sorted(items[1:], key=itemgetter(3)):
                list_of_products_string = list_of_products_string + item[0] + '<br>' + str(item[1]) + '<br>' + item[2] + '<br>' + str(item[3]) + '<br>' + '----------' + '<br>'
            return list_of_products_string
with app.app_context():
    db.create_all()
if __name__ == '__main__':
    
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)
