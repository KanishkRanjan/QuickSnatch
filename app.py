from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import pytz
import os
import bcrypt
import shlex
from riddles import riddle_manager
import io
import math
import json
from config.flags import LEVEL_FLAGS

from datetime import datetime
import random



app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctf3.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

TOTAL_LVL = 6


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    current_level = db.Column(db.Integer, default=1)
    last_correct_submission = db.Column(db.String(20), nullable=True)
    last_correct_submission_serialized = db.Column(db.Integer, default=1)


# Level sections and their corresponding hints



LEVEL_SECTIONS = {
    1: {
        'title': 'Hidden in Kanishk Plain Sight',
        'description': """
        "A secret is hidden in plain sight, though not immediately obvious. Can you find the hidden file within this directory and reveal its contents?"

Intended User Thought Process:

The user should realize that there are hidden files.

They should use ls -al to list files.

They should use cat to reveal the flag.
        """,
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level1.sh | bash',
    },
    2: {
        'title': 'The Hidden Path',
        'description': """
        "A flag is tucked away, hidden from a simple list of files. It's said that a special directory hides the key. Can you navigate your way through and find what lies within and reveal the flag?"

Intended User Thought Process:

The user should realize that there are hidden directories.

They should use ls -al to list files and discover the hidden directory.

They should use cat to reveal the flag file contents.
        """,
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level2.sh | bash',
    },
    3: {
        'title': 'Following the Links',
        'description': """
"A complex path leads to the flag. The flag itself is hidden in a file, and its path includes a symbolic link. Your job is to navigate through the file structure, follow the link and then obtain the flag"

Intended User Thought Process:

The user should be aware of the symbolic link and the hint.

They should navigate into the hidden directory and locate the symlink.

They should then use the script to reveal the flag.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level3.sh | bash',
    },
    4: {
        'title': 'Permission Granted',
        'description': """
        "A direct path is needed, but you must use special permissions to read the content. You have to read the contents of the script to understand how to access the flag. "

Intended User Thought Process:

The user should attempt to read the flag and find out that they don't have the permissions.

They should read the content of the script.

They should execute the script.
        """,
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level4.sh | bash',
    },
    5: {
        'title': 'Decode the Message',
        'description': """
        "A message has been encoded, and the key is available within the directory. You must use command line tools to decode the message. Explore the directory, find the message and decode it."

Intended User Thought Process:

The user should realize that they are given a command and a file, then will need to use it.

The user must find the encoded file, and then realize that they need to use the base64 command to decode it.
        """,
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level5.sh | bash',
    }
}



# Location hints and their QR codes
LOCATION_HINTS = [
    {
        'title': 'The Silent The Object Guardian',
        'description': """A silent guardian bides her time.   
Seek the lady, her story profound,  
A mother, a founder, forever renowned.  
Who is she, and what wisdom does she share?  
Her presence whispers a legacy rare.""",
        'code': 'HTML5GoldRush',
        'is_hint': False
    },
    {
        'title': 'The Rising Temple',
        'description': """At the edge where paths converge and bend,  
A temple is rising, on which peace depends.  
Cradled by green, with a view so vast,  
A quiet refuge, where moments last.  

What place is blooming, serene and bright,  
A haven of calm, bathed in light?""",
        'code': 'CSSMysticTrail',
        'is_hint': False
    },
    {
        'title': 'The Humble Shade',
        'description': """A humble shade stands, quiet and blessed.  
In front of the place where smiles are made,  
A simple retreat, in the shade.  
What is this spot, serene and small,  
A peaceful corner, welcoming all?""",
        'code': 'DecodeTheDOM',
        'is_hint': False
    },
    {
        'title': 'The Sholay Scene',
        'description': """Right by the halls, where footsteps fade,  
A patch of green, like a scene in *Sholay*'s shade.  
Amidst the hustle, a quiet space,  
Like a tale, full of grace.  
What spot is this, where calm is found,  
A green escape, where peace resounds?""",
        'code': 'JSPathfinder',
        'is_hint': False
    },
    {
        'title': 'The Field Haven',
        'description': """Beside the field where the ball does fly,  
A quiet refuge, where footsteps lie.  
A hidden haven where knowledge aligns.  
What place is this, where echoes cease,  
A secret shelter, a moment of peace?""",
        'code': 'APIExplorer22',
        'is_hint': False
    },
    {
        'title': 'The Proud Monument',
        'description': """In front of the building where the name stands tall,  
A statue of pride, a symbol for all.  
Beside the waters, where ripples play,  
A quiet corner to end your day.  
What place is this, where stillness flows,  
A monument of pride where calmness grows?""",
        'code': 'APIExplorer22',
        'is_hint': False
    },
    {
        'title': 'The Gateway',
        'description': """At the gate where daily steps converge,  
A threshold where journeys and minds emerge.    
Yet here, a stillness, softly embraced.  
What is this space, where time slows down,  
A fleeting moment, just beyond the town?""",
        'code': 'CodeQuest2025',
        'is_hint': False
    },
    {
        'title': 'The Cozy Corner',
        'description': """Where the cobblestones meet the sea breeze, and the quiet hum of the city fades, 
a warm corner invites with the scent of roasted beans and a touch of something fresh from the oven, 
waiting to be discovered.""",
        'code': 'XtremeDebugger',
        'is_hint': False
    },
    {
        'title': 'The Peaceful Path',
        'description': """Where worth rest and shadows blend,  
Beside the lot where pathways end.  
Facing knowledge, calm and wide,  
What is this place where peace resides?""",
        'code': 'BugBountyHunt',
        'is_hint': False
    },
    {
        'title': 'The Student Hub',
        'description': """Where hunger meets a daily need,  
A bustling spot where students feed.  
Coupons in hand, the rule is clear,  
What is this place we hold so dear?""",
        'code': 'NirmaanKnights',
        'is_hint': False
    },
    {
        'title': 'The Silent Space',
        'description': """Once alive with chatter and cheer,  
Now silent, its purpose unclear.  
A lone printer hums where meals once lay,  
What is this place of a bygone day?""",
        'code': 'NirmaanKnights',
        'is_hint': False
    },
    {
        'title': 'The Serene Jewel',
        'description': """A heaven of calm, both deep and wide,
Where whispers and silence collide.
A place for the bold, a retreat for the still,
A shimmering jewel that tests your will.
What is this space, so serene and grand?""",
        'code': 'DOMVoyagers',
        'is_hint': False
    },
    {
        'title': 'The Colorful Steps',
        'description': """Steps of color, bright and rare,
A lively path beyond compare.
A place of cheer, where stories unfold,
What is this spot so vibrant and bold?""",
        'code': 'TreasureInCode',
        'is_hint': False
    },
    {
        'title': 'The Elegant Haven',
        'description': """Where whispers of luxury fill the air,
And every corner breathes beauty rare.
A place where elegance and taste collide,
With each sip, a world unfolds,
A treasure trove that quietly holds.
What is this space, where time stands still,
A haven of grace, both rich and tranquil?""",
        'code': 'BackendBandits',
        'is_hint': False
    },
    {
        'title': 'The Arena Lot',
        'description': """Where the arena roars, but wheels stand still,
A parking lot where calmness fills.
In front of the game, where energy flows,
What is this spot where quietness grows?""",
        'code': 'FullStackFury',
        'is_hint': False
    },
    {
        'title': 'The Guarded Gate',
        'description': """Entry and exits with proof in hand,
A threshold where all must make their stand.
Guarded and quiet, yet paths unfold,
Where is the spot, both strict and bold?""",
        'code': 'CipherCrafters',
        'is_hint': False
    },
    {
        'title': 'The Patient Path',
        'description': """Patience Is All The Strength That Man Need's""",
        'code': 'FrontendFrenzy',
        'is_hint': False
    }
]



#kanishk function start here

def get_current_time_now():
    return datetime.now().strftime("%H:%M:%S:%f")[:-3]

def get_current_time_now_serialized():
    return int(datetime.now().strftime("%H%M%S%f")[:-3])


class KUserProgress:
    def __init__(self):
        self.current_req = {}
        self.last_currect_submission = get_current_time_now()
        self.current_level = 0
        self.is_hint = False
        self.locations = LOCATION_HINTS[::]
        self.completed_levels = set()
        self.move_to_next_lvl()


    def move_to_next_lvl(self):
        random_index = random.randint(0, len(self.locations) - 1)
        random_element = self.locations.pop(random_index)  
        self.current_req = random_element



def Kget_user_progress(user_id='default'):
    if user_id not in user_progress:
        user_progress[user_id] = KUserProgress()
    return user_progress[user_id]



# kanishk function end
user_progress = {}

class UserProgress:
    def __init__(self):
        self.current_level = 1
        self.at_hint = False
        self.completed_levels = set()



def get_user_progress(user_id='default'):
    if user_id not in user_progress:
        user_progress[user_id] = UserProgress()
    return user_progress[user_id]

@login_manager.user_loader
def load_user(user_id):
    return  db.session.get(User, int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        progress = Kget_user_progress(current_user.id)
        return redirect(url_for('level', level_number=progress.current_level))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password):
            login_user(user)
            flash('Successfully logged in!', 'success')
            progress = Kget_user_progress(user.id)

            if user != None:
                progress.current_level = user.current_level
                # progress.is_hint = True
                # progress.current_level = user.current_level

                # progress.is_hint = user.is_hint
            # print(get_user_progress(user.id))
            return redirect(url_for('level', level_number=progress.current_level))
        
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'warning')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'warning')
            return render_template('register.html')
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/level/<int:level_number>')
def level(level_number):
    # print(current_user.id)
    try:
        progress = Kget_user_progress(current_user.id)
    except Exception:
        return redirect('/')
    # If user is at hint page, redirect back to hint
    #LASTOPTION
    if progress.is_hint:
        return redirect(url_for('location_hint', level=progress.current_level))
    
    # Ensure level number is valid
    if level_number < 1 or level_number > TOTAL_LVL:
        flash('Invalid level number!', 'danger')
        return redirect(url_for('level', level_number=progress.current_level))
    
    # Only allow access to current level
    if level_number != progress.current_level:
        flash('You can only access your current level!', 'danger')
        return redirect(url_for('level', level_number=progress.current_level))
    print(level_number ,progress.current_level )
    level_data = LEVEL_SECTIONS.get(level_number, {})
    return render_template(f'challenges/level_{level_number}.html', 
                         level=level_number,
                         level_data=level_data)

@app.route('/leaderboard')
@login_required
def leaderboard():
    # user = User.query.get(current_user.id) 
    # users = User.query.order_by(User.current_level.desc(), User.username).all() #DELETE
    users = User.query.order_by(User.current_level.desc(), User.last_correct_submission_serialized.asc()).all()

    # print(user_progress)
    for usr in user_progress.keys():
        print(usr, user_progress[usr].locations)
    return render_template('leaderboard.html', users=users)

@app.route('/check_flag/<int:level>', methods=['POST'])
def check_flag(level):
    progress = Kget_user_progress(current_user.id)
    data = request.get_json()
    submitted_flag = data.get('flag', '').strip()
    
    if not submitted_flag:
        return jsonify({'success': False, 'message': 'No flag submitted'})
    
    if level not in LEVEL_FLAGS:
        return jsonify({'success': False, 'message': 'Invalid level'})
    
    if submitted_flag == LEVEL_FLAGS[level]:
        # print(progress.)
        progress.is_hint = True
        return jsonify({
            'success': True,
            'message': 'Flag correct! Proceed to find the location.',
            'redirect': f'/location_hint/{level}'
        })
    
    return jsonify({
        'success': False,
        'message': 'Incorrect flag. Try again!'
    })

@app.route('/level/<int:level>/complete', methods=['GET', 'POST'])
@login_required
def level_complete(level):
    # Ensure user has actually completed the level
    progress = Kget_user_progress(current_user.id)

    if level != get_user_progress(current_user.id).current_level:
        flash('Please complete the current level first!', 'error')
        return redirect(url_for('level', level_number=progress.current_level))
    
    if request.method == 'POST':
        print("Hello World")
        # print(progress.locations)
        # print("This could be nothing")
        # user = User.query.get(current_user.id) 
        # user.current_level = progress.current_level
        # user.last_correct_submission = get_current_time_now()
        # user.last_correct_submission_serialized = get_current_time_now_serialized()
        # print(f"Progress Level: {progress.current_level}")
        # print(f"Current Time: {get_current_time_now()}")
        # print(f"Serialized Time: {get_current_time_now_serialized()}")
        # db.session.commit()
        # flash('Congratulations! You\'ve completed this level!', 'success')
        
        # If user completed level 5, redirect to congratulations page
        # if level == 5:
        #     return redirect(url_for('congratulations'))
            
        # return redirect(url_for('level', level_number=progress.current_level))
        

@app.route('/level_time/<int:level>')
@login_required
def level_time(level):
    time_spent = current_user.format_time_spent(level)
    return jsonify({'time_spent': time_spent})

@app.route('/location_hint/<int:level>')
@login_required
def location_hint(level):
    progress = Kget_user_progress(current_user.id)
    
    # Only allow access to current level's hint
    if level != progress.current_level:
        return redirect(url_for('level', level_number=progress.current_level))
        
    # If not marked as at_hint, redirect to level
    if not progress.is_hint:
        return redirect(url_for('level', level_number=progress.current_level))
    
    # hint_data = LOCATION_HINTS.get(level, {})
    hint_data = progress.current_req 
    
    # print(hint_data.title)
    return render_template('location_hint.html', 
                         level=level,
                         hint_title=hint_data.get('title', ''),
                         location_hint=hint_data.get('description', ''))

@app.route('/verify_location/<int:level>', methods=['POST'])
@login_required
def verify_location(level):
    progress = Kget_user_progress(current_user.id)
    data = request.get_json()
    submitted_code = data.get('code', '').strip()
    
    if not submitted_code:
        return jsonify({
            'success': False,
            'message': 'No location code provided'
        })
    
    hint_data = progress.current_req 

    if not hint_data:
        return jsonify({
            'success': False,
            'message': 'Invalid level'
        })
    
    expected_code = hint_data['code']
    print(submitted_code , expected_code)
    if submitted_code == expected_code:
        # Mark current level as completed

        progress.current_level = level+1
        # print(progress.locations)
        print("This could be nothing")
        user = db.session.get(User, current_user.id)
        user.current_level = progress.current_level
        user.last_correct_submission = get_current_time_now()
        user.last_correct_submission_serialized = get_current_time_now_serialized() #UPDATE
        print(user_progress)
        try:
            db.session.commit()
            progress.completed_levels.add(level)
            progress.is_hint = False 
            progress.move_to_next_lvl() #MOVE
        except Exception :
            return jsonify({
                'success': False,
                'message': 'Server Internal Issue. Reload and try again!'
            })


        # Move to next level
        if level > TOTAL_LVL:
            return jsonify({
                'success': True,
                'message': 'Congratulations! You have completed all levels!',
                'redirect': '/congratulations'
            })
            
        return jsonify({
            'success': True,
            'message': f'Location verified! Moving to level {progress.current_level}',
            'redirect': f'/level/{progress.current_level}'
        })

    
    return jsonify({
        'success': False,
        'message': 'Incorrect location code. Try again!'
    })

@app.route('/congratulations')
def congratulations():
    print("This function was called ")
    return render_template('congratulations.html')

@app.route('/levels')
def levels():
    progress = get_user_progress()
    return render_template('levels.html', progress=progress)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()    
    app.run(host='0.0.0.0', port=7771, debug=True)
