from flask import Flask, request, render_template, redirect, url_for, jsonify
import json
from celery import Celery
import sqlite3 as sql
from flask import g
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.decomposition import PCA
import math
import numpy as np
import sys
from flask_cors import CORS

DATABASE = './players_20.db'

def connect_db():
    return sql.connect(DATABASE)

def get_connection():
    db = getattr(g, '_db', None)
    if db is None:
        db = g._db = connect_db()
    return db

goalkeeper_attributes = ['Aerial Reach', 'Command of Area', 'Communication', 'Eccentricity', 'First Touch', 'Handling', 'Kicking', 'One on Ones', 'Passing', 'Punching (Tendency)', 'Reflexes', 'Rushing Out (Tendency)', 'Throwing']
technical_attributes = ['Corners', 'Crossing', 'Dribbling', 'Finishing', 'First Touch', 'Free Kick Taking', 'Heading', 'Long Shots', 'Long Throws', 'Marking', 'Passing', 'Penalty Taking', 'Tackling', 'Technique']
physical_attributes = ['Acceleration', 'Agility', 'Balance', 'Jumping Reach', 'Natural Fitness', 'Pace', 'Stamina', 'Strength']
mental_attributes = ['Aggression', 'Anticipation', 'Bravery', 'Composure', 'Concentration', 'Decisions', 'Determination', 'Flair', 'Off the Ball', 'Positioning', 'Teamwork', 'Vision', 'Work Rate']
player_information_attributes = ['Name', 'Position', 'Club', 'Division', 'Based', 'Nation','Height', 'Weight', 'Age', 'Preferred Foot', 'Best Pos', 'Best Role','Value', 'Wage']
margin_ratio_for_name = 1.2

def create_visualization(value_down, value_up, position, font_size):
    conn = sql.connect(DATABASE)
    df = pd.read_sql_query("SELECT * FROM player WHERE Value BETWEEN {} AND {} AND is{} = 1".format(str(value_down), str(value_up), position), conn)
    conn.close()
    player_information = df[player_information_attributes]
    if position == "GK":
        player_attributes = df[goalkeeper_attributes + physical_attributes + mental_attributes]
    else:
        player_attributes = df[technical_attributes + physical_attributes + mental_attributes]
    pca = PCA()
    pipe = Pipeline(steps=[    
        ('scaling',StandardScaler()),
        ('pca',PCA(n_components=2))
    ])
    player_attributes_pca = pipe.fit_transform(player_attributes)
    pca1 = np.array([point[1] for point in player_attributes_pca])
    pca0 = np.array([point[0] for point in player_attributes_pca])
    print(pipe['pca'].explained_variance_ratio_)
    canvas_width = 2000
    canvas_height = 16000
    pca1 -= np.min(pca1)
    pca0 -= np.max(pca0)
    pca0 = -pca0
    points_0 = canvas_width/(np.max(pca1) - np.min(pca1)) * pca1
    points_1 = canvas_height/(np.max(pca0) - np.min(pca0)) * pca0
    player_information['point0'] = points_0
    player_information['point1'] = points_1
    players = player_information.to_dict()
    data = {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "players": players,
    }
    return data

app = Flask(__name__, static_folder="dist/static", template_folder="dist")

CORS(app, origins="http://localhost:8080")

class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyJSONEncoder, self).default(obj)

@app.route("/", methods=['Get', 'POST'])
def index():
    if request.method == 'POST':
        #search page of the players
        bot = int(request.json.get('bottom'))
        top = int(request.json.get('top'))
        position = request.json.get('position')
        data = create_visualization(bot, top, position, 12)

        return jsonify(data)
    
    return render_template("index.html")

@app.route("/map")
def map():
    data = request.args.get('data')
    print('go to map')
    return render_template("map.html", width=data['canvas_width'], height=data['canvas_height'], playerdata=data['players'])


@app.route("/player", methods=["POST"])
def player():
    #fetch player data from the user database and render the template
    name = request.json.get('name')
    age = request.json.get('age')
    db = get_connection()
    cur = db.cursor()
    cur.execute('SELECT * FROM player WHERE name=(?) AND age=(?)', [name, age])
    res = cur.fetchone()
    col_name_list = [tuple[0] for tuple in cur.description]
    playerdata = {}
    for i in range(1, len(col_name_list)):
        playerdata[col_name_list[i]] = res[i]
        # print(res[i])
    return jsonify(playerdata)



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
