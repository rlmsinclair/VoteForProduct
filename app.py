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
from requests import get
from wtforms import StringField , PasswordField , SubmitField
import time
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_login import UserMixin, LoginManager, login_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from forex_python.converter import CurrencyRates, CurrencyCodes
from bs4 import BeautifulSoup

# Flask syntax

app = Flask(__name__)

# this is the databse url when you run the app next time i will create a db in this folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://doadmin:AVNS_JkvcfAiuwN-gsSf6K0c@app-784b9fa7-3b44-405e-9170-d80f0dd5e72d-do-user-14798294-0.c.db.ondigitalocean.com:25060/users'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

bcrypt = Bcrypt(app)
cr = CurrencyRates()


app.config['MAIL_SERVER'] = 'smtp.office365.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'support@voteforproduct.com'  # Replace with your Gmail address
app.config['MAIL_PASSWORD'] = 'RobbieIsCool'         # Replace with your Gmail password or app password
mail = Mail(app)

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
    country = db.Column(db.String(50), unique=True, nullable=False)
    email=db.Column(db.String(50), unique=True, nullable=False)
    wallet_address = db.Column(db.String(100), unique=True, nullable=True)
    username = db.Column(db.String(50), unique=True , nullable=False)
    password = db.Column(db.String(100), nullable=False)
    wins = db.Column(db.Integer(), nullable=True)
    losses = db.Column(db.Integer(), nullable=True)
    draws = db.Column(db.Integer(), nullable=True)
    balance = db.Column(db.Float(), nullable=True)
    currency = db.Column(db.Integer(), nullable=False)

#Registration Form
class RegistrationForm(FlaskForm):
    country = StringField('Country', validators=[DataRequired(), Length(min=5, max=50)])
    email = StringField('Email', validators=[DataRequired(), Length(min=5, max=50)])
    wallet_address = StringField('Monero Wallet Address', validators=[Length(min=0, max=100)])
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
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(country=request.form.get('country'), email=form.email.data, wallet_address=form.wallet_address.data, username=form.username.data, password= hashed_password, wins=0, losses=1, draws=0, balance=0, currency=request.form.get('currency'))
        db.session.add(new_user)
        db.session.commit()
        flash('Registration Successful !')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login(): 
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by (username=username).first()
        is_valid = bcrypt.check_password_hash(user.password, password)
        if user and is_valid:
            login_user(user)
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


with open('./ebay_active_items.csv', newline='', encoding='utf8') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for i, row in enumerate(reader, start=1):
        try:
            name_price_link_elo_image = []
            name = row[0]
            price = row[1]
            link = row[2]
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
                print(i)
                response1 = client.images.generate(
                    model="dall-e-2",
                    prompt=prompt1,
                    size="256x256",
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
        except Exception as e:
            print(e)



# def remove_duplicates(x):
#     return list(dict.fromkeys(x[0]))
#
#
# items = remove_duplicates(items)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name1 = request.form['name1']
        email = request.form['email']
        message = request.form['message']
        msg = Message(subject='New message from your website',
                      sender='support@voteforproduct.com',  # Replace with your Gmail address
                      recipients=['support@voteforproduct.com'])  # Replace with your Gmail address
        msg.body = f'Name: {name1}\nEmail: {email}\nMessage: {message}'
        mail.send(msg)

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route('/cashout', methods=['GET', 'POST'])
def cashout():
    user = flask_login.current_user
    if user.is_anonymous:
        return redirect(url_for('login'))
    currency_rates = cr.get_rates('GBP')
    c = CurrencyCodes()
    if user.currency not in currency_rates.keys():
        currency_page = 'https://www.xe.com/currencyconverter/convert/?Amount={}&From={}&To={}'.format(1,
                                                                                                       'GBP',
                                                                                                       user.currency)
        currency = get(currency_page).text
        currency_data = BeautifulSoup(currency, 'html.parser')

        page = currency_data.find('p', attrs={'class': 'result__BigRate-sc-1bsijpp-1 dPdXSB'})

        stripped_page = page.text.strip()
        exchange_rate = float(stripped_page.split(' ')[0].replace(',', ''))
        balance_in_user_currency = user.balance * exchange_rate
    elif user.currency != 'GBP':
        exchange_rate = currency_rates[user.currency]
        balance_in_user_currency = user.balance * exchange_rate
    else:
        balance_in_user_currency = user.balance
        exchange_rate = 1

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        wallet_address = request.form['wallet_address']

        msg = Message(subject='New message from your website',
                      sender='support@voteforproduct.com',  # Replace with your Gmail address
                      recipients=['support@voteforproduct.com'])  # Replace with your Gmail address
        msg.body = ('Given Username: ' + str(username) + '\n' + 'Given Email: ' + str(email) + '\nGiven Monero Wallet Address: ' + str(wallet_address) +
            '\n\nDatabase Username:' + str(user.username) + '\n' +
            'Database Email:' + str(user.email) + '\n' +
            'Database Monero Wallet Address' + str(user.wallet_address) + '\n' +
            '\nCheck these match!\n' +
            '\nIf they do not match, contact Robbie\n' +
            '\nUser has £' + str(user.balance) + ' in their account and wishes to cash out.')
        mail.send(msg)

        flash('Your withdrawal request has been sent successfully!', 'success')
        return redirect(url_for('cashout'))

    withdrawal_limit = 3.00 * exchange_rate
    return render_template('cashout.html', currency_symbol=user.currency, balance=str(balance_in_user_currency), withdrawal_limit=withdrawal_limit)

@app.route('/')
def show_homepage():
    user = flask_login.current_user
    if user.is_anonymous:
        exchange_rate = 1
        user_currency = 'GBP'
    else:
        user_currency = user.currency
        currency_page = 'https://www.xe.com/currencyconverter/convert/?Amount={}&From={}&To={}'.format(1,
                                                                                                       'GBP',
                                                                                                       user.currency)
        currency = get(currency_page).text
        currency_data = BeautifulSoup(currency, 'html.parser')

        page = currency_data.find('p', attrs={'class': 'result__BigRate-sc-1bsijpp-1 dPdXSB'})

        stripped_page = page.text.strip()
        exchange_rate = float(stripped_page.split(' ')[0].replace(',', ''))
        print(exchange_rate)
    win_rate = 0.02 * exchange_rate
    draw_rate = 0.01 * exchange_rate
    loss_rate = 0.01 * exchange_rate
    return render_template('index.html', currency=user_currency, win_rate=win_rate, draw_rate=draw_rate, loss_rate=loss_rate)
@app.route('/vote')
def show_pair_of_items():
    user = flask_login.current_user
    if user.is_anonymous:
        return redirect(url_for('login'))
    try:
        currency_rates = cr.get_rates('GBP')

        c = CurrencyCodes()
        if user.currency not in currency_rates.keys():
            currency_page = 'https://www.xe.com/currencyconverter/convert/?Amount={}&From={}&To={}'.format(1,
                                                                                                           'GBP',
                                                                                                           user.currency)
            currency = get(currency_page).text
            currency_data = BeautifulSoup(currency, 'html.parser')

            page = currency_data.find('p', attrs={'class': 'result__BigRate-sc-1bsijpp-1 dPdXSB'})

            stripped_page = page.text.strip()
            exchange_rate = float(stripped_page.split(' ')[0].replace(',', ''))
            balance_in_user_currency = user.balance * exchange_rate
        elif user.currency != 'GBP':
            exchange_rate = currency_rates[user.currency]
            balance_in_user_currency = user.balance * exchange_rate
        else:
            balance_in_user_currency = user.balance
            exchange_rate = 1

        if session['item1'] != '0' or session['item2'] != '0':
            fun = 'had'
        else:
            session['item1'] = '0'
            session['item2'] = '0'
        session['current_page'] = 'index'
        random_value_1 = random.randint(0, len(items) - 1)
        random_value_2 = random.randint(0, len(items) - 1)
        if session['item1'] == '0' or session['item2'] == '0':
            session['item1'] = items[random_value_1]
            session['item2'] = items[random_value_2]
        price1 = session['item1'][1]
        price2 = session['item2'][1]
        if user.currency != 'GBP':
            price3 = float(price1) * exchange_rate
            price4 = float(price2) * exchange_rate
        else:
            price3 = price1
            price4 = price2
        return render_template('vote.html',
                               contestant1=str(session['item1'][0]),
                               image_url1=url_for('static', filename=session['item1'][0] + '.jpg'),
                               contestant2=str(session['item2'][0]),
                               image_url2=url_for('static', filename=session['item2'][0] + '.jpg'),
                               currency_symbol=user.currency,
                               price3=str(price3),
                               price1=str(price1),
                               price4=str(price4),
                               price2=str(price2),
                               balance=str(balance_in_user_currency)
                               )
    except Exception as e:
        print(e)
        session['item1'] = '0'
        session['item2'] = '0'
        return redirect(url_for('show_pair_of_items'))


@app.route('/1')
def item_one_wins():
    item1 = session['item1']
    item2 = session['item2']

    win_or_lose = ''
    user = flask_login.current_user
    if session['current_page'] == '1':
        return redirect(url_for('show_pair_of_items'))
    session['current_page'] = '1'


    session['item1'] = '0'
    session['item2'] = '0'

    if item1[3] > item2[3]:
        win_or_lose = 'You Win!'
        user.wins = user.wins + 1
        user.balance = user.balance + 0.02
        db.session.add(user)
        db.session.commit()
    if item1[3] < item2[3]:
        win_or_lose = 'You Lose :('
        user.losses = user.losses + 1
        user.balance = user.balance - 0.01
        db.session.add(user)
        db.session.commit()
    if item1[3] == item2[3]:
        win_or_lose = 'You Draw! (Equal value)'
        user.balance = user.balance + 0.01
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

    flash(win_or_lose)
    return render_template('1.html')


@app.route('/2')
def item_two_wins():
    item1 = session['item1']
    item2 = session['item2']


    win_or_lose = ''
    user = flask_login.current_user
    balance = user.balance

    if session['current_page'] == '2':
        return redirect(url_for('show_pair_of_items'))
    session['current_page'] = '2'

    session['item1'] = '0'
    session['item2'] = '0'

    if item2[3] > item1[3]:
        win_or_lose = 'You Win!'
        user.wins = user.wins + 1
        user.balance = user.balance + 0.02
        db.session.add(user)
        db.session.commit()
    if item2[3] < item1[3]:
        win_or_lose = 'You Lose :('
        user.losses = user.losses + 1
        user.balance = user.balance - 0.01
        db.session.add(user)
        db.session.commit()
    if item2[3] == item1[3]:
        win_or_lose = 'You Draw! (Equal value)'
        user.draws = user.draws + 1
        user.balance = user.balance + 0.01
        db.session.add(user)
        db.session.commit()

    item1elo, item2elo = update_elo(item2[3], item1[3])
    for item in items:
        if item == item1:
            item[3] = item1elo
    for item in items:
        if item == item2:
            item[3] = item2elo
    flash(win_or_lose)
    return render_template('2.html')

@app.route('/leaderboard')
def show_leaderboard():
    with app.app_context():
        usernames = []
        for user in User.query.order_by(User.wins / User.losses).all():
            usernames.append([user.username, user.wins / user.losses, user.wins, user.losses, user.draws])
        usernames.reverse()
        output = 'Wins/Losses | Wins | Losses | Draws | Username<br>'
        for username in usernames:
            output = output + str(username[1]) + ' | ' + str(username[2]) + ' | ' + str(username[3]) + ' | '\
                     + str(username[4]) + ' | ' + username[0] + '<br>'
        return render_template('leaderboard.html', usernames=usernames)

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
    print(len(items))
    if request.method == 'GET':
        return password_prompt("Admin password:")
    elif request.method == 'POST':
        if request.form['password'] != PASSPHRASE:
            return password_prompt("Invalid password, try again. Admin password:")
        else:
            list_of_products_string = ''
            for item in sorted(items, key=itemgetter(3)):
                list_of_products_string = list_of_products_string + item[0] + '<br>' + str(item[1]) + '<br>' + item[2] + '<br>' + str(item[3]) + '<br>' + '----------' + '<br>'
            return list_of_products_string


with app.app_context():
    db.create_all()
if __name__ == '__main__':
    
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)
