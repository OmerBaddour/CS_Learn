#!/usr/bin/env python2.7

from sqlalchemy import *
from flask import Flask, request, render_template, g, redirect, Response
import click
import forms
import re
import os
import copy
import string

def sql_inj(s):
    if string.find(s, '\'') != -1 or string.find(s, '\"') != -1 or string.find(s, ';') != -1 or string.find(s, '=') != -1 or string.find(s.lower(), ' OR ') != -1:
        return True
    else:
        return False


# application module/package, tells Flask where to look for templates, static files, etc.
#tmp1_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__) #, template_folder=tmp1_dir)
app.config['SECRET_KEY'] = '4111'

# connect to database
DATABASEURI = "postgresql://akh2161:0244@34.74.165.156/proj1part2"

# create database engine using above URI
engine = create_engine(DATABASEURI)

# called at the beginning of every web request
@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
        print('Connected to database!')
    except:
        g.conn = None
        print('Error connecting to database')


# bind function home() to URL http://127.0.0.1:5000/ when accessed with GET method
# if multiple methods, can check type with: if request.method == 'GET'
@app.route('/', methods=['GET', 'POST'])
def login():
    form_l = forms.LoginForm()

    # login
    if form_l.is_submitted():
        result = request.form
        # check if credentials match user in database
        values = list(result.values())
        index = 0
        
        if sql_inj(values[0]) or sql_inj(values[1]):
            return 'No SQL injection for you good sir'
        
        username = str(values[0])
        password = str(values[1])

        # check for existence of user
        db_result = g.conn.execute('SELECT * FROM Users WHERE username=\'' + username + '\' AND password=\'' + password + '\'')
        db_result = db_result.fetchall()
        if len(db_result) == 1:
            return redirect('user/{}'.format(username))

    # otherwise keep client on page
    return render_template('login.html', form=form_l)


# sign up
@app.route('/signup/', methods=['GET', 'POST'])
def sign_up():

    form_s = forms.SignUpForm()

    # sign up
    if form_s.is_submitted():
        result = request.form
        # check credentials meet constraints
        values = list(result.values()) # 0 = first_name, 1 = email, 2 = username, 3 = password
        
        vals_copy = copy.deepcopy(values)
        values[0] = vals_copy[1].encode('ascii')
        values[1] = vals_copy[3].encode('ascii')
        values[2] = vals_copy[0].encode('ascii')
        values[3] = vals_copy[2].encode('ascii')
        values[4] = vals_copy[4].encode('ascii')
     
        if sql_inj(values[0]) or sql_inj(values[1]) or sql_inj(values[2]) or sql_inj(values[3]):
            return 'No SQL injection for you good sir.'    

        if values[0] == '' or values[1] == '' or values[2] == '' or values[3] == '':
            return 'You cannot enter blank values for any of the login fields'

        if len(values[0]) > 20 or len(values[1]) > 40 or len(values[2]) > 20 or len(values[3]) > 40:
            return 'Please enter shorter entries for these fields.' 

        db_result = g.conn.execute('SELECT * FROM Users WHERE username=\'' + values[2] + '\' OR email=\'' + values[1] + '\'')
        db_result = db_result.fetchall()
        if not len(db_result) == 0:
            return 'Invalid sign up attempt - non unique username or email.'
        g.conn.execute(' '.join((
                'INSERT INTO Users (firstname, email, username, password)',
                'VALUES (\''+values[0]+'\', \''+values[1]+'\', \''+values[2]+'\', \'' +values[3]+'\')'
        )))

    return render_template('signup.html', form=form_s)


@app.route('/user/<username>/')
def user(username):
    # get list of recommended concepts for user
    # query for all hasLearnt
    # join with isRelatedTo and fetch all related concepts
    # except those which are in hasLearnt
    db_recommended = g.conn.execute(' '.join((
        'SELECT R.cname2',
        'FROM hasLearnt H1, isRelatedTo R',
        'WHERE H1.username=\'' + username + '\' AND H1.cname=R.cname1',
        'EXCEPT (',
        'SELECT H2.cname',
        'FROM hasLearnt H2',
        'WHERE H2.username=\'' + username + '\')',
    )))
    db_recommended = db_recommended.fetchall()
    index = 0
    ordered_list = []
    for concept in db_recommended:
        db_recommended[index] = re.sub('[^a-zA-z\s]*', '', str(concept[0]).encode('ascii'))
        # get videos of concept
        cursor = g.conn.execute(' '.join((
            'SELECT V.vname, V.vurl, V.vrating',
            'FROM Videos V, DescribedByV D',
            'WHERE V.vurl = D.vurl AND cname=\'' +db_recommended[index]+'\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([db_recommended[index], 'video', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])
        # get images of concept
        cursor = g.conn.execute(' '.join((
            'SELECT I.iname, I.iurl, I.irating',
            'FROM Images I, DescribedByI D',
            'WHERE I.iurl = D.iurl AND cname=\'' + db_recommended[index] + '\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([db_recommended[index], 'image', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])
        # get text of concept
        cursor = g.conn.execute(' '.join((
            'SELECT T.tname, T.turl, T.trating',
            'FROM Text T, DescribedByT D',
            'WHERE T.turl = D.turl AND cname=\'' +db_recommended[index]+'\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([db_recommended[index], 'text', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])
        index += 1

    # retrieve user preferences
    cursor = g.conn.execute('SELECT avgvideos, avgimages, avgtext FROM Users WHERE username=\''+username+'\'')
    cursor = cursor.fetchall()
    avgvideos = float(cursor[0][0])
    avgimages = float(cursor[0][1])
    avgtext = float(cursor[0][2])

    # calculate weights
    for entry in ordered_list:
        if entry[1] == 'video':
            entry.append(entry[len(entry)-1]*avgvideos)
        elif entry[1] == 'image':
            entry.append(entry[len(entry) - 1] * avgimages)
        else:
            entry.append(entry[len(entry) - 1] * avgtext)

    # sort
    ordered_list.sort(key=lambda x:x[5])
    ordered_list.reverse()

    return render_template('user.html', result=ordered_list, username=username)


@app.route('/search/<username>/')
def search(username):

    query = request.args.get('q', default='')
    
    if sql_inj(query):
        return 'No SQL injection for you good sir.'    

    cursor = g.conn.execute('SELECT * FROM Concepts WHERE cname = \'{}\''.format(query))
    cursor = cursor.fetchall()  
    ordered_list = []

    if len(cursor) == 1:

        # get videos of concept
        cursor = g.conn.execute(' '.join((
            'SELECT V.vname, V.vurl, V.vrating',
            'FROM Videos V, DescribedByV D',
            'WHERE V.vurl = D.vurl AND cname=\'' +query+'\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([query.encode('ascii'), 'video', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])
        # get images of concept
        cursor = g.conn.execute(' '.join((
            'SELECT I.iname, I.iurl, I.irating',
            'FROM Images I, DescribedByI D',
            'WHERE I.iurl = D.iurl AND cname=\'' + query + '\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([query.encode('ascii'), 'image', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])
        # get text of concept
        cursor = g.conn.execute(' '.join((
            'SELECT T.tname, T.turl, T.trating',
            'FROM Text T, DescribedByT D',
            'WHERE T.turl = D.turl AND cname=\'' +query+'\''
        )))
        cursor = cursor.fetchall()
        for i in range(len(cursor)):
            ordered_list.append([query.encode('ascii'), 'text', cursor[i][0].encode('ascii'), cursor[i][1].encode('ascii'), cursor[i][2]])

        # retrieve user preferences
        cursor = g.conn.execute('SELECT avgvideos, avgimages, avgtext FROM Users WHERE username=\''+username+'\'')
        cursor = cursor.fetchall()
        avgvideos = float(cursor[0][0])
        avgimages = float(cursor[0][1])
        avgtext = float(cursor[0][2])

        # calculate weights
        for entry in ordered_list:
            if entry[1] == 'video':
                entry.append(entry[len(entry)-1]*avgvideos)
            elif entry[1] == 'image':
                entry.append(entry[len(entry) - 1] * avgimages)
            else:
                entry.append(entry[len(entry) - 1] * avgtext)

        # sort
        ordered_list.sort(key=lambda x:x[5])
        ordered_list.reverse()

    return render_template('concepts.html', result=ordered_list, username=username)


@app.route('/review/<username>/', methods=['GET', 'POST'])
def review(username):

    form_r = forms.ReviewForm()
    if form_r.is_submitted():
        result = request.form
        values = list(result.values()) # 0 is rating, 1 is URL

        temp = values[0].encode('ascii')
        try:
            values[0] = float(values[1])
        except ValueError:
            return 'Invalid value entered for rating. Must be a float.'
        values[1] = temp
        values[2] = values[2].encode('ascii')
        
        if sql_inj(values[1]):
            return 'No SQL injection for you good sir.'    

        if float(values[0]) < 0 or float(values[0]) > 5:
            return 'Invalid rating, review not processed.'
        vids_matching_url = []
        imgs_matching_url = []
        txts_matching_url = []
        db_result = g.conn.execute('SELECT * FROM Videos V WHERE V.vurl=\''+values[1]+'\'')
        vids_matching_url.append(db_result.fetchall())
        db_result = g.conn.execute('SELECT * FROM Images I WHERE I.iurl=\'' + values[1] + '\'')
        imgs_matching_url.append(db_result.fetchall())
        db_result = g.conn.execute('SELECT * FROM Text T WHERE T.turl=\'' + values[1] + '\'')
        txts_matching_url.append(db_result.fetchall())
        if not ((len(vids_matching_url[0]) == 1 and len(imgs_matching_url[0]) == 0 and len(txts_matching_url[0]) == 0) or
                (len(vids_matching_url[0]) == 0 and len(imgs_matching_url[0]) == 1 and len(txts_matching_url[0]) == 0) or
                (len(vids_matching_url[0]) == 0 and len(imgs_matching_url[0]) == 0 and len(txts_matching_url[0]) == 1)):
            return 'Invalid URL, review not processed.'
        if len(vids_matching_url[0]) == 1:
            # video avg of resource
            rating = float(vids_matching_url[0][0][2])
            num_reviews = int(vids_matching_url[0][0][3])
            new_rating = ((rating * num_reviews) + float(values[0])) / (num_reviews + 1)
            g.conn.execute(' '.join((
                'UPDATE Videos',
                'SET vrating='+str(new_rating)+',',
                'vnumraters='+str(num_reviews+1),
                'WHERE vurl=\''+values[1]+'\''
            )))
            # video avg of user
            cursor = g.conn.execute(' '.join((
                'SELECT avgvideos, percentagevideos, numresourcesused',
                'FROM Users',
                'WHERE username=\''+username+'\''
            )))
            cursor = cursor.fetchall()
            print(cursor)
            avgvideos = float(cursor[0][0])
            percentagevideos = float(cursor[0][1])
            numresourcesused = int(cursor[0][2])
            num_vids = round(percentagevideos * numresourcesused)
            new_avgvideos = ((avgvideos * num_vids) + float(values[0])) / (num_vids + 1)
            cursor = g.conn.execute(' '.join((
                'UPDATE Users',
                'SET avgvideos='+str(new_avgvideos)+',',
                'percentagevideos='+str((num_vids+1)/(numresourcesused+1))+',',
                'numresourcesused='+str(numresourcesused+1),
                'WHERE username=\''+username+'\''
            )))
        elif len(imgs_matching_url[0]) == 1:
            # update image resource fields
            print(imgs_matching_url[0])
            rating = float(imgs_matching_url[0][0][2])
            num_reviews = int(imgs_matching_url[0][0][3])
            new_rating = ((rating * num_reviews) + float(values[0])) / (num_reviews + 1)
            g.conn.execute(' '.join((
                'UPDATE Images',
                'SET irating='+str(new_rating)+',',
                'inumraters='+str(num_reviews+1),
                'WHERE iurl=\''+values[1]+'\''
            )))
            # image avg of user
            cursor = g.conn.execute(' '.join((
                'SELECT avgimages, percentageimages, numresourcesused',
                'FROM Users',
                'WHERE username=\'' + username + '\''
            )))
            cursor = cursor.fetchall()
            print(cursor)
            avgimages = float(cursor[0][0])
            percentageimages = float(cursor[0][1])
            numresourcesused = int(cursor[0][2])
            num_imgs = round(percentageimages * numresourcesused)
            new_avgimages = ((avgimages * num_imgs) + float(values[0])) / (num_imgs + 1)
            cursor = g.conn.execute(' '.join((
                'UPDATE Users',
                'SET avgimages=' + str(new_avgimages) + ',',
                'percentageimages=' + str((num_imgs + 1) / (numresourcesused + 1)) + ',',
                'numresourcesused=' + str(numresourcesused + 1),
                'WHERE username=\'' + username + '\''
            )))
        else:
            # change text resource fields
            rating = float(txts_matching_url[0][0][3])
            num_reviews = int(txts_matching_url[0][0][4])
            new_rating = ((rating * num_reviews) + float(values[0])) / (num_reviews + 1)
            g.conn.execute(' '.join((
                'UPDATE Text',
                'SET trating=' + str(new_rating) + ',',
                'tnumraters=' + str(num_reviews + 1),
                'WHERE turl=\'' + values[1] + '\''
            )))
            # text avg of user
            cursor = g.conn.execute(' '.join((
                'SELECT avgtext, percentagetext, numresourcesused',
                'FROM Users',
                'WHERE username=\'' + username + '\''
            )))
            cursor = cursor.fetchall()
            print(cursor)
            avgtext = float(cursor[0][0])
            percentagetext = float(cursor[0][1])
            numresourcesused = int(cursor[0][2])
            num_texts = round(percentagetext * numresourcesused)
            new_avgtext = ((avgtext * num_texts) + float(values[0])) / (num_texts + 1)
            cursor = g.conn.execute(' '.join((
                'UPDATE Users',
                'SET avgtext=' + str(new_avgtext) + ',',
                'percentagetext=' + str((num_texts + 1) / (numresourcesused + 1)) + ',',
                'numresourcesused=' + str(numresourcesused + 1),
                'WHERE username=\'' + username + '\''
            )))

        return redirect('http://35.227.74.174:8111/user/{}'.format(username))

    return render_template('review.html', form=form_r)


# closes database connection at end of web request
@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
        return 'bye'
    except Exception as e:
        return e


if __name__ == '__main__':

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)

    def run(debug, threaded, host, port):

        HOST, PORT = host, port
        print("running on " + str(HOST) + ':' +str(PORT))
        app.jinja_env.cache = {}
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded) # 0.0.0.0 means can be accessed by others
    run()

