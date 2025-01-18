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



app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctf.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    current_level = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime, nullable=True)
    last_submission = db.Column(db.DateTime, nullable=True)
    level_times = db.relationship('LevelTime', backref='user', lazy=True)

    def get_level_time(self, level):
        level_time = LevelTime.query.filter_by(user_id=self.id, level=level).order_by(LevelTime.start_time.desc()).first()
        if level_time:
            return level_time.calculate_time_spent()
        return None

    def format_time_spent(self, level):
        time_spent = self.get_level_time(level)
        if not time_spent:
            return "Not started"
        
        total_seconds = int(time_spent.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

class LevelTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    time_spent = db.Column(db.Interval, nullable=True)

    def calculate_time_spent(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now(pytz.UTC) - self.start_time
        return None

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)

# Level sections and their corresponding hints
LEVEL_SECTIONS = {
    1: {
        'title': 'Hidden in Kanishk Plain Sight',
        'description': """A secret is hidden in plain sight, though not immediately obvious. Can you find the hidden file within this directory and reveal its contents?

Hint: Sometimes what you can't see is just as important as what you can see.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level1.sh | bash',
    },
    2: {
        'title': 'The Hidden Path',
        'description': """A flag is tucked away, hidden from a simple list of files. It's said that a special directory hides the key. Can you navigate your way through and find what lies within and reveal the flag?

Hint: Some directories prefer to stay out of sight, but they can't hide from the right command.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level2.sh | bash',
    },
    3: {
        'title': 'Following the Links',
        'description': """A complex path leads to the flag. The flag itself is hidden in a file, and its path includes a symbolic link. Your job is to navigate through the file structure, follow the link and then obtain the flag.

Hint: Not all paths are what they seem. Some are just pointers to the real destination.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level3.sh | bash',
    },
    4: {
        'title': 'Permission Granted',
        'description': """A direct path is needed, but you must use special permissions to read the content. You have to read the contents of the script to understand how to access the flag.

Hint: Sometimes you need the right permissions to access what you seek. The script holds the key to gaining access.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level4.sh | bash',
    },
    5: {
        'title': 'Decode the Message',
        'description': """A message has been encoded, and the key is available within the directory. You must use command line tools to decode the message. Explore the directory, find the message and decode it.

Hint: The message may look like gibberish, but with the right decoding tool, its true meaning will be revealed.""",
        'curl_command': 'curl -s https://raw.githubusercontent.com/nst-sdc/cli_ctf/refs/heads/main/level5.sh | bash',
    }
}



# Location hints and their QR codes
LOCATION_HINTS = {
    1: {
        'title': 'The Silent The Object Guardian',
        'description': """A silent guardian bides her time.   
Seek the lady, her story profound,  
A mother, a founder, forever renowned.  
Who is she, and what wisdom does she share?  
Her presence whispers a legacy rare.""",
        'code': 'HTML5GoldRush'
    },
    2: {
        'title': 'The Rising Temple',
        'description': """At the edge where paths converge and bend,  
A temple is rising, on which peace depends.  
Cradled by green, with a view so vast,  
A quiet refuge, where moments last.  

What place is blooming, serene and bright,  
A haven of calm, bathed in light?""",
        'code': 'CSSMysticTrail'
    },
    3: {
        'title': 'The Humble Shade',
        'description': """A humble shade stands, quiet and blessed.  
In front of the place where smiles are made,  
A simple retreat, in the shade.  
What is this spot, serene and small,  
A peaceful corner, welcoming all?""",
        'code': 'DecodeTheDOM'
    },
    4: {
        'title': 'The Sholay Scene',
        'description': """Right by the halls, where footsteps fade,  
A patch of green, like a scene in *Sholay*'s shade.  
Amidst the hustle, a quiet space,  
Like a tale, full of grace.  
What spot is this, where calm is found,  
A green escape, where peace resounds?""",
        'code': 'JSPathfinder'
    },
    5: {
        'title': 'The Field Haven',
        'description': """Beside the field where the ball does fly,  
A quiet refuge, where footsteps lie.  
A hidden haven where knowledge aligns.  
What place is this, where echoes cease,  
A secret shelter, a moment of peace?""",
        'code': 'APIExplorer22'
    },
    6: {
        'title': 'The Proud Monument',
        'description': """In front of the building where the name stands tall,  
A statue of pride, a symbol for all.  
Beside the waters, where ripples play,  
A quiet corner to end your day.  
What place is this, where stillness flows,  
A monument of pride where calmness grows?""",
        'code': 'APIExplorer22'
    },
    7: {
        'title': 'The Gateway',
        'description': """At the gate where daily steps converge,  
A threshold where journeys and minds emerge.    
Yet here, a stillness, softly embraced.  
What is this space, where time slows down,  
A fleeting moment, just beyond the town?""",
        'code': 'CodeQuest2025'
    },
    8: {
        'title': 'The Cozy Corner',
        'description': """Where the cobblestones meet the sea breeze, and the quiet hum of the city fades, 
a warm corner invites with the scent of roasted beans and a touch of something fresh from the oven, 
waiting to be discovered.""",
        'code': 'XtremeDebugger'
    },
    9: {
        'title': 'The Peaceful Path',
        'description': """Where worth rest and shadows blend,  
Beside the lot where pathways end.  
Facing knowledge, calm and wide,  
What is this place where peace resides?""",
        'code': 'BugBountyHunt'
    },
    10: {
        'title': 'The Student Hub',
        'description': """Where hunger meets a daily need,  
A bustling spot where students feed.  
Coupons in hand, the rule is clear,  
What is this place we hold so dear?""",
        'code': 'NirmaanKnights'
    },
    11: {
        'title': 'The Silent Space',
        'description': """Once alive with chatter and cheer,  
Now silent, its purpose unclear.  
A lone printer hums where meals once lay,  
What is this place of a bygone day?""",
        'code': 'NirmaanKnights'
    },
    12: {
        'title': 'The Serene Jewel',
        'description': """A heaven of calm, both deep and wide,
Where whispers and silence collide.
A place for the bold, a retreat for the still,
A shimmering jewel that tests your will.
What is this space, so serene and grand?""",
        'code': 'DOMVoyagers'
    },
    13: {
        'title': 'The Colorful Steps',
        'description': """Steps of color, bright and rare,
A lively path beyond compare.
A place of cheer, where stories unfold,
What is this spot so vibrant and bold?""",
        'code': 'TreasureInCode'
    },
    14: {
        'title': 'The Elegant Haven',
        'description': """Where whispers of luxury fill the air,
And every corner breathes beauty rare.
A place where elegance and taste collide,
With each sip, a world unfolds,
A treasure trove that quietly holds.
What is this space, where time stands still,
A haven of grace, both rich and tranquil?""",
        'code': 'BackendBandits'
    },
    15: {
        'title': 'The Arena Lot',
        'description': """Where the arena roars, but wheels stand still,
A parking lot where calmness fills.
In front of the game, where energy flows,
What is this spot where quietness grows?""",
        'code': 'FullStackFury'
    },
    16: {
        'title': 'The Guarded Gate',
        'description': """Entry and exits with proof in hand,
A threshold where all must make their stand.
Guarded and quiet, yet paths unfold,
Where is the spot, both strict and bold?""",
        'code': 'CipherCrafters'
    },
    17: {
        'title': 'The Patient Path',
        'description': """Patience Is All The Strength That Man Need's""",
        'code': 'FrontendFrenzy'
    }
}

#kanishk function start here

def get_current_time_now():
    return datetime.now().strftime("%H:%M:%S:%f")[:-3]















# kanishk function end
user_progress = {}

class UserProgress:
    def __init__(self):
        self.current_level = 1
        self.at_hint = False
        self.completed_levels = set()

class KUserProgress:
    def __init__(self):
        self.current_req = {}
        self.last_currect_submission = 

def get_user_progress(user_id='default'):
    if user_id not in user_progress:
        user_progress[user_id] = UserProgress()
    return user_progress[user_id]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        progress = get_user_progress(current_user.id)
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
            if not user.start_time:
                user.start_time = datetime.now(pytz.UTC)
                db.session.commit()
            flash('Successfully logged in!', 'success')
            progress = get_user_progress(user.id)
            # print(get_user_progress(user.id))
            return redirect(url_for('level', level_number=progress.current_level))
        
        flash('Invalid username or password', 'danger')
        print("Thios")
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
    progress = get_user_progress(current_user.id)
    
    # If user is at hint page, redirect back to hint
    if progress.at_hint:
        return redirect(url_for('location_hint', level=progress.current_level))
    
    # Ensure level number is valid
    if level_number < 1 or level_number > 17:
        flash('Invalid level number!', 'danger')
        return redirect(url_for('level', level_number=progress.current_level))
    
    # Only allow access to current level
    if level_number != progress.current_level:
        flash('You can only access your current level!', 'danger')
        return redirect(url_for('level', level_number=progress.current_level))
    
    level_data = LEVEL_SECTIONS.get(level_number, {})
    return render_template(f'challenges/level_{level_number}.html', 
                         level=level_number,
                         level_data=level_data)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.current_level.desc(), User.username).all()
    return render_template('leaderboard.html', users=users)

@app.route('/check_flag/<int:level>', methods=['POST'])
def check_flag(level):
    progress = get_user_progress(current_user.id)
    data = request.get_json()
    submitted_flag = data.get('flag', '').strip()
    
    if not submitted_flag:
        return jsonify({'success': False, 'message': 'No flag submitted'})
    
    if level not in LEVEL_FLAGS:
        return jsonify({'success': False, 'message': 'Invalid level'})
    
    if submitted_flag == LEVEL_FLAGS[level]:
        progress.at_hint = True  # Mark that user should be at hint page
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
    if level != get_user_progress(current_user.id).current_level:
        flash('Please complete the current level first!', 'error')
        return redirect(url_for('level', level_number=get_user_progress(current_user.id).current_level))
    
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if riddle_manager.check_answer(current_user.id, answer):
            # Clear the riddle and progress to next level
            riddle_manager.clear_riddle(current_user.id)
            progress = get_user_progress(current_user.id)
            progress.current_level = level + 1
            db.session.commit()
            flash('Congratulations! You\'ve completed this level!', 'success')
            
            # If user completed level 5, redirect to congratulations page
            if level == 5:
                return redirect(url_for('congratulations'))
                
            return redirect(url_for('level', level_number=level + 1))
        else:
            riddle = riddle_manager.user_riddles[current_user.id]['current_riddle']['riddle']
            flash('Incorrect answer. Try again!', 'error')
            return render_template('riddle.html', level=level, riddle=riddle, 
                                error="Incorrect answer. Try again!")

    # Check if user already has a riddle assigned
    if current_user.id in riddle_manager.user_riddles and \
       riddle_manager.user_riddles[current_user.id].get('level') == level:
        riddle = riddle_manager.user_riddles[current_user.id]['current_riddle']['riddle']
    else:
        # Assign a new riddle for this level
        riddle_data = riddle_manager.assign_riddle(current_user.id, level)
        riddle = riddle_data['riddle']
    
    return render_template('riddle.html', level=level, riddle=riddle)

@app.route('/level_time/<int:level>')
@login_required
def level_time(level):
    time_spent = current_user.format_time_spent(level)
    return jsonify({'time_spent': time_spent})

@app.route('/challenges/level<int:level>/level_info.json')
@login_required
def level_info(level):
    try:
        with open(f'challenges/level{level}/level_info.json', 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({
            'level': level,
            'title': 'Unknown Level',
            'description': 'Level information not available.',
            'prompt': 'user@quicksnatch',
            'files': {},
            'hints': ['Level information not available']
        })

@app.route('/location_hint/<int:level>')
@login_required
def location_hint(level):
    progress = get_user_progress(current_user.id)
    
    # Only allow access to current level's hint
    if level != progress.current_level:
        return redirect(url_for('level', level_number=progress.current_level))
    
    # If not marked as at_hint, redirect to level
    if not progress.at_hint:
        return redirect(url_for('level', level_number=progress.current_level))
    
    hint_data = LOCATION_HINTS.get(level, {})
    print(hint_data)
    # print(hint_data.title)
    return render_template('location_hint.html', 
                         level=level,
                         hint_title=hint_data.get('title', ''),
                         location_hint=hint_data.get('description', ''))

@app.route('/verify_location/<int:level>', methods=['POST'])
@login_required
def verify_location(level):
    progress = get_user_progress(current_user.id)
    data = request.get_json()
    submitted_code = data.get('code', '').strip()
    
    if not submitted_code:
        return jsonify({
            'success': False,
            'message': 'No location code provided'
        })
    
    hint_data = LOCATION_HINTS.get(level)
    if not hint_data:
        return jsonify({
            'success': False,
            'message': 'Invalid level'
        })
    
    expected_code = hint_data['code']
    if submitted_code == expected_code:
        # Mark current level as completed
        progress.completed_levels.add(level)
        progress.at_hint = False  # Reset hint status
        
        # Move to next level
        next_level = level + 1
        if next_level > 17:
            return jsonify({
                'success': True,
                'message': 'Congratulations! You have completed all levels!',
                'redirect': '/congratulations'
            })
            
        progress.current_level = next_level
        return jsonify({
            'success': True,
            'message': f'Location verified! Moving to level {next_level}',
            'redirect': f'/level/{next_level}'
        })
    
    return jsonify({
        'success': False,
        'message': 'Incorrect location code. Try again!'
    })

@app.route('/congratulations')
def congratulations():
    return render_template('congratulations.html')

@app.route('/levels')
def levels():
    progress = get_user_progress()
    return render_template('levels.html', progress=progress)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()    
    app.run(host='0.0.0.0', port=7771, debug=True)
