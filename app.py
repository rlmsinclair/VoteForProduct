# Flask is a library that allows you to create websites in Python
from flask import Flask, render_template, session, redirect
import csv
import random

# Flask syntax
app = Flask(__name__)


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
        name_price_link_elo = []
        name = row[0].split(',')[0]
        price = row[0].split(',')[1]
        link = row[0].split(',')[2]
        name_price_link_elo.append(name)
        name_price_link_elo.append(price)
        name_price_link_elo.append(link)
        name_price_link_elo.append(elo)
        items.append(name_price_link_elo)


@app.route('/')
def show_pair_of_items():
    random_value_1 = random.randint(1, len(items)-1)
    random_value_2 = random.randint(1, len(items)-1)
    session['item1'] = items[random_value_1]
    session['item2'] = items[random_value_2]
    return render_template('index.html',
                           contestant1=str(items[random_value_1][0]),
                           contestant2=str(items[random_value_2][0]),
                           price1='£' + str(items[random_value_1][1]),
                           price2='£' + str(items[random_value_2][1])
                           )


@app.route('/1')
def item_one_wins():
    item1 = session['item1']
    item2 = session['item2']
    item1elo, item2elo = update_elo(item1[3], item2[3])
    for item in items:
        if item == item1:
            item[3] = item1elo
    for item in items:
        if item == item2:
            item[3] = item2elo
    for item in items:
        print(item[3])
    return redirect("/")

@app.route('/2')
def item_two_wins():
    item1 = session['item1']
    item2 = session['item2']
    item1elo, item2elo = update_elo(item2[3], item1[3])
    for item in items:
        if item == item1:
            item[3] = item1elo
    for item in items:
        if item == item2:
            item[3] = item2elo
    for item in items:
        print(item[3])
    return redirect("/")


if __name__ == '__main__':
    app.secret_key = "12345"
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()
