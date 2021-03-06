import os
from os import path
from datetime import datetime
from flask import Flask, render_template, redirect, request, url_for, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

# when running local load environment variables to protect our credentials
if path.exists("env.py"):
    import env

# create instance of flask, assigned to app
app = Flask(__name__)

# set mongoDB database
app.config["MONGO_DBNAME"] = 'crowd_finding'
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'mongodb://localhost')

# get secret key to enable flask-sessions
app.secret_key = os.getenv('secret_key')

# create pymongo instance of app (constructor method)
mongo = PyMongo(app)


# main page with contest info
@app.route('/')
@app.route('/index')
def index():
    if mongo.db.contests.count_documents({'active': True}) == 0:
        return redirect(url_for('contest_ended'))
    current_contest = mongo.db.contests.find_one({'active': True})
    session['start_date'] = current_contest['start_date']
    session['end_date'] = current_contest['end_date']
    return render_template('main.html',
                           contest=current_contest,
                           tracks=mongo.db.tracks.find().sort("total_votes", -1).limit(1),
                           total_tracks=mongo.db.tracks.count_documents({})
                           )


# login page (no authorization required for this project)
@app.route('/login')
def login():
    return render_template('login.html',
                           users=mongo.db.users.find().sort('user_name'))


# process login form and set session vars
@app.route('/activate_user', methods=['POST'])
def activate_user():
    if mongo.db.users.count_documents({'user_name': request.form.get('user_name')}) == 0:
        return render_template('login.html',
                               message='Your user name is unknown',
                               users=mongo.db.users.find().sort('user_name'))
    current_user = mongo.db.users.find_one(
        {'user_name': request.form.get('user_name')})
    if request.form.get('password') == current_user['password']:
        session['user_id'] = str(current_user['_id'])
        session['user_name'] = current_user['user_name']
        session['user_role'] = current_user['user_role']
        return redirect(url_for('get_tracks'))
    return render_template('login.html',
                           message='Your password is incorrect',
                           users=mongo.db.users.find().sort('user_name'))


# logout and unset session vars
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_role', None)
    return redirect(url_for('get_tracks'))


# start the contest form (admin only)
@app.route('/start_contest')
def start_contest():
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            return render_template('startcontest.html')
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# process contest form, insert in database
@app.route('/insert_contest', methods=['POST'])
def insert_contest():
    contests = mongo.db.contests
    """ request to get the form, converted to dict """
    contest = request.form.to_dict()
    contest.update({'active': True})
    contests.insert_one(contest)
    return redirect(url_for('index'))


# end contest (admin only)
@app.route('/end_contest')
def end_contest():
    mongo.db.contests.update_one({'active': True}, {'$set': {'active': False}})
    return redirect(url_for('get_tracks'))


# Show the 5 winners
@app.route('/contest_ended')
def contest_ended():
    return render_template('contestend.html',
                           contests=mongo.db.contests.find().sort("_id", -1),
                           tracks=mongo.db.tracks.find().sort("total_votes", -1).limit(5),
                           total_tracks=mongo.db.tracks.count_documents({})
                           )


# track listing page
@app.route('/get_tracks')
def get_tracks():
    if mongo.db.contests.count_documents({}) == 0:
        return render_template('permission.html',
                               message='No contest is running at the moment')
    if mongo.db.tracks.count_documents({}) == 0:
        return render_template('tracks.html',
                               no_tracks=True)
    else:
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find().sort("total_votes", -1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'))


# process the filter form for track listing page
@app.route('/get_tracks_filtered', methods=['POST'])
def get_tracks_filtered():
    if request.form.get('style'):
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find(
                                   {"style": request.form.get('style')}).sort("total_votes", -1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'),
                               ranking='false')
    if request.form.get('creation_method'):
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find(
                                   {"creation_method": request.form.get('creation_method')}).sort("total_votes", -1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'),
                               ranking='false')
    return render_template('tracks.html',
                           tracks=mongo.db.tracks.find().sort("total_votes", -1),
                           users=mongo.db.users.find().sort('user_name'),
                           styles=mongo.db.styles.find().sort('style'),
                           methods=mongo.db.methods.find().sort('method'))


# process the sort form for track listing page
@app.route('/get_tracks_sorted', methods=['POST'])
def get_tracks_sorted():
    if request.form.get('sort_tracks') == 'date_ascending':
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find().sort("_id", +1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'),
                               ranking='false')
    if request.form.get('sort_tracks') == 'date_descending':
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find().sort("_id", -1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'),
                               ranking='false')
    if request.form.get('sort_tracks') == 'score_ascending':
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find().sort("total_votes", +1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'),
                               ranking='false')
    if request.form.get('sort_tracks') == 'score_descending':
        return render_template('tracks.html',
                               tracks=mongo.db.tracks.find().sort("total_votes", -1),
                               users=mongo.db.users.find().sort('user_name'),
                               styles=mongo.db.styles.find().sort('style'),
                               methods=mongo.db.methods.find().sort('method'))
    return render_template('tracks.html',
                           tracks=mongo.db.tracks.find().sort("total_votes", -1),
                           users=mongo.db.users.find().sort('user_name'),
                           styles=mongo.db.styles.find().sort('style'),
                           methods=mongo.db.methods.find().sort('method'))


# add a new track form
@app.route('/add_track')
def add_track():
    """ check if a user is logged in and wether they are allowed to use this funtion """
    if 'user_name' in session:
        if session['user_role'] == 'contributor':
            return render_template('addtrack.html',
                                   styles=mongo.db.styles.find().sort('style'),
                                   methods=mongo.db.methods.find().sort('method'))
        else:
            return render_template('permission.html',
                                   message='As a voter you are not allowed to participate in the contest.')
    else:
        return render_template('login.html',
                               message='Please login first to add a new track',
                               users=mongo.db.users.find().sort('user_name'))


# process add track form
@app.route('/insert_track', methods=['POST'])
def insert_track():
    """ Get soundcloud embed code and strip the track number
        so we can use our own modified embed code """
    embed_code = request.form.get('soundcloud')
    track_position = embed_code.find('track')
    track_number = embed_code[track_position+7:track_position+16]
    if len(track_number) != 9:
        return render_template('addtrack.html',
                               message='Please provide a valid embed-code')
    """ get the current date and time, and add to the track """
    now = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    """ insert track in database and return to the track overview page """
    mongo.db.tracks.insert_one({'user': session['user_name'],
                                'user_id': ObjectId(session['user_id']),
                                'submitted': now,
                                'soundcloud': track_number,
                                'artist_name': request.form.get('artist_name'),
                                'title': request.form.get('title'),
                                'style': request.form.get('style'),
                                'free_text': request.form.get('free_text'),
                                'creation_method': request.form.get('creation_method'),
                                'credits_who': request.form.get('credits_who'),
                                'credits_what': request.form.get('credits_what'),
                                'creation_date': request.form.get('creation_date'),
                                'license': request.form.get('license'),
                                'last_updated': now,
                                'total_votes': 0})
    return redirect(url_for('get_tracks'))


# view and edit a specific track
@app.route('/view_track/<track_id>')
def view_track(track_id):
    current_track = mongo.db.tracks.find_one(
        {"_id": ObjectId(track_id)})
    """ check if the right user is logged in """
    if 'user_name' in session:
        if current_track['user_id'] == ObjectId(session['user_id']):
            return render_template('viewtrack.html',
                                   track=mongo.db.tracks.find_one(
                                       {"_id": ObjectId(track_id)}),
                                   users=mongo.db.users.find().sort('user_name'),
                                   styles=mongo.db.styles.find().sort('style'),
                                   methods=mongo.db.methods.find().sort('method'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to edit this track')
    else:
        return render_template('login.html',
                               message='Please login first to add a new track',
                               users=mongo.db.users.find().sort('user_name'))


# process edit track form
@app.route('/update_track/<track_id>', methods=['POST'])
def update_track(track_id):
    tracks = mongo.db.tracks
    """ get the current date and time, and add to the user record """
    now = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    """ insert user in database and return to the track overview page """
    tracks.update({"_id": ObjectId(track_id)},
                  {'$set':
                   {'artist_name': request.form.get('artist_name'),
                    'title': request.form.get('title'),
                    'style': request.form.get('style'),
                    'free_text': request.form.get('free_text'),
                    'creation_method': request.form.get('creation_method'),
                    'credits_who': request.form.get('credits_who'),
                    'credits_what': request.form.get('credits_what'),
                    'creation_date': request.form.get('creation_date'),
                    'license': request.form.get('license'),
                    'last_updated': now
                    }})
    return redirect(url_for('get_tracks'))


# delete a track (admin only)
@app.route('/delete_track/<track_id>')
def delete_track(track_id):
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            tracks = mongo.db.tracks
            tracks.delete_one({'_id': ObjectId(track_id)})
            return redirect(url_for('get_tracks'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# register new user form
@app.route('/add_user')
def add_user():
    return render_template('adduser.html',
                           users=mongo.db.users.find())


# process register user form
@app.route('/insert_user', methods=['POST'])
def insert_user():
    """ get the current date and time, and add to the user record """
    now = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    """ insert user in database and return to the log-in page """
    mongo.db.users.insert_one({'user_name': request.form.get('user_name'),
                               'user_email': request.form.get('user_email'),
                               'password': request.form.get('password'),
                               'user_role': request.form.get('user_role'),
                               'profile_pic': request.form.get('profile_pic'),
                               'user_city': request.form.get('user_city'),
                               'user_country': request.form.get('user_country'),
                               'user_website': request.form.get('website'),
                               'mailing_list': request.form.get('mailing_list'),
                               'registered': now,
                               'last_updated': now
                               })
    return redirect(url_for('login'))


# view and edit specific user, the template checks if the logged user can edit
@app.route('/view_user/<user_id>')
def view_user(user_id):
    if 'user_name' in session:
        return render_template('viewuser.html',
                               user=mongo.db.users.find_one(
                                   {"_id": ObjectId(user_id)}))
    else:
        return render_template('login.html',
                               message='Please login first to view a user profile',
                               users=mongo.db.users.find().sort('user_name'))


# process edit user form
@app.route('/update_user/<user_id>', methods=['POST'])
def update_user(user_id):
    users = mongo.db.users
    """ get the current date and time, and add to the user record """
    now = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    """ insert user in database and return to the track overview page """
    users.update({"_id": ObjectId(user_id)},
                 {'$set':
                  {'user_name': request.form.get('user_name'),
                   'user_email': request.form.get('user_email'),
                   'profile_pic': request.form.get('profile_pic'),
                   'user_city': request.form.get('user_city'),
                   'user_country': request.form.get('user_country'),
                   'website': request.form.get('website'),
                   'mailing_list': request.form.get('mailing_list'),
                   'last_updated': now
                   }})
    return redirect(url_for('get_tracks'))


# delete a user (admin only)
@app.route('/delete_user/<user_id>')
def delete_user(user_id):
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            users = mongo.db.users
            users.delete_one({'_id': ObjectId(user_id)})
            return redirect(url_for('view_users'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# See the users list (admin only)
@app.route('/view_users')
def view_users():
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            return render_template('viewusers.html',
                                   users=mongo.db.users.find().sort('user_name'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# See the users for mailinglist (admin only)
@app.route('/mailinglist_users')
def mailinglist_users():
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            return render_template('viewusers.html',
                                   users=mongo.db.users.find({'mailing_list': 'true'}).sort('user_name'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# vote for a track form
@app.route('/vote_track/<track_id>')
def vote_track(track_id):
    """ check if a user is logged in and wether they are allowed to use this funtion """
    if 'user_name' in session:
        if session['user_role'] == 'voter':
            voted_track = mongo.db.tracks.find_one({"_id": ObjectId(track_id)})
            return render_template('votetrack.html',
                                   track=voted_track)
        else:
            return render_template('permission.html',
                                   message='As a contributor you are not allowed to vote in the contest.')
    else:
        return render_template('login.html',
                               message='Please login first to vote for a track',
                               users=mongo.db.users.find().sort('user_name'))


# process vote form
@app.route('/insert_vote/<track_id>', methods=['POST'])
def insert_vote(track_id):
    tracks = mongo.db.tracks
    tracks.update_one({'_id': ObjectId(track_id)},
                      {'$push': {'votes': {
                          'user': session['user_name'],
                          'user_id': ObjectId(session['user_id']),
                          'vote': int(request.form.get('vote')),
                          'motivation': request.form.get('motivation')
                      }}})
    """ add the vote to the total score for this track """
    tracks.update_one({'_id': ObjectId(track_id)},
                      {'$inc': {'total_votes': int(request.form.get('vote'))}})
    return redirect(url_for('get_tracks'))


# edit available creation methods form (admin only)
@app.route('/edit_methods')
def edit_methods():
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            return render_template('editmethods.html',
                                   methods=mongo.db.methods.find().sort('method'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# process add method form (admin only)
@app.route('/insert_method', methods=['POST'])
def insert_method():
    method = request.form.to_dict()
    methods = mongo.db.methods
    methods.insert_one(method)
    return redirect(url_for('edit_methods'))


# delete a method (admin only)
@app.route('/delete_method/<method_id>')
def delete_method(method_id):
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            methods = mongo.db.methods
            methods.delete_one({'_id': ObjectId(method_id)})
            return redirect(url_for('edit_methods'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# edit available styles form (admin only)
@app.route('/edit_styles')
def edit_styles():
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            return render_template('editstyles.html',
                                   styles=mongo.db.styles.find().sort('style'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# process add style form (admin only)
@app.route('/insert_style', methods=['POST'])
def insert_style():
    style = request.form.to_dict()
    styles = mongo.db.styles
    styles.insert_one(style)
    return redirect(url_for('edit_styles'))


# delete a style (admin only)
@app.route('/delete_style/<style_id>')
def delete_style(style_id):
    """ check if the administrator is logged in """
    if 'user_name' in session:
        if session['user_role'] == 'administrator':
            styles = mongo.db.styles
            styles.delete_one({'_id': ObjectId(style_id)})
            return redirect(url_for('edit_styles'))
        else:
            return render_template('permission.html',
                                   message='You are not allowed to use this function')
    else:
        return render_template('login.html',
                               message='Please login first to use this function',
                               users=mongo.db.users.find().sort('user_name'))


# Missing page handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('permission.html',
                           message='This page does not exist.')


# Missing user or track handling
@app.errorhandler(500)
def internal_error(error):
    return render_template('permission.html',
                           message='This page does not exist.')


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=os.environ.get('PORT'),
            debug=False)
